"""
Broken Wing Butterfly Put Strategy - 3-leg risk-defined neutral strategy.

Structure:
- Long Put (Lower Strike - ITM or ATM)
- 2x Short Puts (Middle Strike - OTM)
- Long Put (Highest Strike - Further OTM) - "broken wing" is further out

This is a neutral strategy with a directional bias. The "broken wing" creates an
unbalanced structure that can collect credit or reduce cost while maintaining defined risk.

Key Characteristics:
- Defined maximum risk
- Defined maximum profit
- Lower cost than standard butterfly
- Can be structured for credit in some cases
- Slightly bearish bias (profits if stock stays/falls to sweet spot)
- Benefits from low volatility at expiration

Best Used When:
- Expect stock to trade in narrow range near short strikes
- Want defined risk with lower capital
- Prefer higher probability over larger profit
- IV is moderate to high (sell more premium at short strikes)

Profit/Loss:
- Max Profit: At short put strike at expiration
- Max Loss: Either at long put strikes (difference in strikes - net premium)
- Breakevens: Two breakeven points (one on each side of short strikes)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import BaseStrategy
from utils.pipeline_tracker import PipelineTracker
from utils.calculations import (
    get_stock_price,
    get_risk_free_rate,
    get_options_data,
    compute_avg_iv,
    prob_in_range,
    parse_options_chain,
    get_eastern_now
)


class BrokenWingButterflyPutStrategy(BaseStrategy):
    """Broken Wing Butterfly Put - Unbalanced 3-leg put butterfly."""
    
    def __init__(self):
        super().__init__(
            strategy_id='bwb_put',
            strategy_name='bwb_put',
            display_name='Broken Wing Butterfly - Put',
            description='Risk-defined neutral strategy with unbalanced wings using puts. Lower cost and higher probability than standard butterfly, with slight bearish bias.',
            num_legs=3,
            complexity_level='advanced'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for BWB Put strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_dte': 30,
            'max_dte': 60,
            'short_put_delta_min': 0.25,
            'short_put_delta_max': 0.40,
            'lower_wing_width': 5.0,  # Width between low long put and short puts (% of stock)
            'upper_wing_width': 8.0,  # Width between short puts and high long put (% of stock)
            'min_credit': 0.0,  # Can accept small debit
            'max_debit': 2.0,  # Maximum debit to pay
            'min_volume': 10,
            'min_prob_profit': 0.40,  # Minimum 40% probability of profit
            'prefer_credit': True,  # Prefer credit positions over debit
            # Scoring weights (must sum to 1.0)
            'weight_roi': 0.20,
            'weight_pop': 0.35,
            'weight_risk_reward': 0.20,
            'weight_volume': 0.10,
            'weight_credit_bonus': 0.15
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate strategy-specific parameters.
        
        Args:
            params: Dictionary of strategy parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        defaults = self.get_default_parameters()
        
        # Merge with defaults
        full_params = {**defaults, **params}
        
        # Validate DTE range
        if full_params['min_dte'] < 7:
            return False, "Minimum DTE must be at least 7 days"
        if full_params['max_dte'] < full_params['min_dte']:
            return False, "Maximum DTE must be greater than minimum DTE"
        
        # Validate delta range
        if not (0 < full_params['short_put_delta_min'] < full_params['short_put_delta_max'] <= 0.50):
            return False, "Short put delta range must be between 0 and 0.50"
        
        # Validate wing widths
        if full_params['lower_wing_width'] <= 0 or full_params['upper_wing_width'] <= 0:
            return False, "Wing widths must be positive"
        
        # Validate credit/debit
        if full_params['max_debit'] < 0:
            return False, "Maximum debit cannot be negative"
        
        # Validate volume
        if full_params['min_volume'] < 1:
            return False, "Minimum volume must be at least 1"
        
        # Validate probability
        if not (0 <= full_params['min_prob_profit'] <= 1.0):
            return False, "Probability must be between 0 and 1.0"
        
        return True, None
    
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], api_key: str, session=None) -> List[Dict[str, Any]]:
        """
        Scan for Broken Wing Butterfly Put opportunities.
        
        Args:
            symbol: Stock ticker symbol
            filter_criteria: Strategy filter parameters
            api_key: Alpha Vantage API key
            session: Database session (optional)
            
        Returns:
            List of opportunity dictionaries, sorted by score
        """
        # Merge with defaults
        defaults = self.get_default_parameters()
        params = {**defaults, **(filter_criteria or {})}
        
        # Validate parameters
        is_valid, error = self.validate_parameters(params)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {error}")
        
        # Get market data
        stock_price = get_stock_price(symbol, api_key)
        if not stock_price:
            return []
        
        # Initialize pipeline tracker
        tracker = PipelineTracker(
            symbol=symbol,
            stock_price=stock_price,
            strategy_name=self.strategy_name,
            strategy_display_name=self.display_name,
            filter_criteria=params
        )
        
        risk_free_rate = get_risk_free_rate(api_key)
        options_data = get_options_data(symbol, api_key)
        if not options_data:
            tracker.finalize(0)
            return []
        
        options_chain = parse_options_chain(options_data)
        if not options_chain:
            tracker.finalize(0)
            return []
        
        # Count total raw options
        total_raw_options = sum(len(opts) for opts in options_chain.values())
        tracker.add_step(
            name="Raw Options",
            description="Total options from API across all expirations",
            input_count=total_raw_options,
            passed_count=total_raw_options
        )
        
        avg_iv = compute_avg_iv(options_data)
        current_date = get_eastern_now()
        
        opportunities = []
        
        # Step 2: Filter by DTE
        dte_filtered_options = []
        for expiry_date, options in options_chain.items():
            days_to_expiry = (expiry_date - current_date).days
            if params['min_dte'] <= days_to_expiry <= params['max_dte']:
                for opt in options:
                    opt['expiry_date'] = expiry_date
                    opt['days_to_expiry'] = days_to_expiry
                    dte_filtered_options.append(opt)
        
        tracker.add_step(
            name="DTE Filter",
            description=f"Options with {params['min_dte']}-{params['max_dte']} days to expiry",
            input_count=total_raw_options,
            passed_count=len(dte_filtered_options)
        )
        
        # Step 3: Filter to PUT options only
        put_options = [opt for opt in dte_filtered_options if opt['type'] == 'PUT']
        tracker.add_step(
            name="PUT Filter",
            description="Filter to PUT options only",
            input_count=len(dte_filtered_options),
            passed_count=len(put_options)
        )
        
        # Step 4: Find suitable short puts (middle of butterfly)
        suitable_short_puts = []
        for opt in put_options:
            put_delta_abs = abs(opt.get('delta', 0))
            if (params['short_put_delta_min'] <= put_delta_abs <= params['short_put_delta_max'] and
                opt.get('volume', 0) >= params['min_volume'] and
                opt['strike'] < stock_price):
                suitable_short_puts.append(opt)
        
        tracker.add_step(
            name="Short Put Filter",
            description=f"Puts with delta {params['short_put_delta_min']}-{params['short_put_delta_max']}, volume >= {params['min_volume']}, OTM",
            input_count=len(put_options),
            passed_count=len(suitable_short_puts)
        )
        
        # Step 5: Build butterfly combinations
        butterfly_combos = []
        for short_put in suitable_short_puts:
            short_strike = short_put['strike']
            expiry_date = short_put['expiry_date']
            
            # Get all puts for this expiry
            expiry_puts = {opt['strike']: opt for opt in put_options 
                         if opt['expiry_date'] == expiry_date}
            
            # Calculate wing widths
            lower_width = stock_price * params['lower_wing_width'] / 100
            upper_width = stock_price * params['upper_wing_width'] / 100
            
            # Find low long put (smaller wing - closer to short)
            low_long_strike_target = short_strike - lower_width
            low_long_put = None
            min_diff = float('inf')
            for strike, put in expiry_puts.items():
                if strike < short_strike and put.get('volume', 0) >= params['min_volume']:
                    diff = abs(strike - low_long_strike_target)
                    if diff < min_diff:
                        min_diff = diff
                        low_long_put = put
            
            # Find high long put (broken wing - further from short)
            high_long_strike_target = short_strike + upper_width
            high_long_put = None
            min_diff = float('inf')
            for strike, put in expiry_puts.items():
                if strike > short_strike and put.get('volume', 0) >= params['min_volume']:
                    diff = abs(strike - high_long_strike_target)
                    if diff < min_diff:
                        min_diff = diff
                        high_long_put = put
            
            if low_long_put and high_long_put:
                butterfly_combos.append({
                    'short_put': short_put,
                    'low_long_put': low_long_put,
                    'high_long_put': high_long_put,
                    'expiry_date': expiry_date,
                    'days_to_expiry': short_put['days_to_expiry']
                })
        
        tracker.add_step(
            name="Wing Matching",
            description="Matching lower and upper wing long puts to each short put",
            input_count=len(suitable_short_puts),
            passed_count=len(butterfly_combos)
        )
        
        # Step 6: Filter by credit/debit requirements
        credit_filtered = []
        for combo in butterfly_combos:
            low_long_debit = combo['low_long_put'].get('premium', 0)
            short_credit = combo['short_put'].get('premium', 0) * 2
            high_long_debit = combo['high_long_put'].get('premium', 0)
            net_credit_debit = short_credit - low_long_debit - high_long_debit
            
            if net_credit_debit >= params['min_credit'] and -net_credit_debit <= params['max_debit']:
                combo['net_credit_debit'] = net_credit_debit
                credit_filtered.append(combo)
        
        tracker.add_step(
            name="Credit/Debit Filter",
            description=f"Min credit >= {params['min_credit']}, max debit <= {params['max_debit']}",
            input_count=len(butterfly_combos),
            passed_count=len(credit_filtered)
        )
        
        # Step 7: Filter by probability of profit
        pop_filtered = []
        for combo in credit_filtered:
            short_put = combo['short_put']
            low_long_put = combo['low_long_put']
            high_long_put = combo['high_long_put']
            days_to_expiry = combo['days_to_expiry']
            time_to_expiry = days_to_expiry / 365.0
            
            short_strike = short_put['strike']
            low_long_strike = low_long_put['strike']
            high_long_strike = high_long_put['strike']
            net_credit_debit = combo['net_credit_debit']
            
            # Calculate wing widths and risk
            lower_wing_width_actual = short_strike - low_long_strike
            upper_wing_width_actual = high_long_strike - short_strike
            max_profit = lower_wing_width_actual + net_credit_debit
            max_loss_lower = -net_credit_debit if net_credit_debit < 0 else 0
            max_loss_upper = upper_wing_width_actual - lower_wing_width_actual - net_credit_debit
            max_loss = max(max_loss_lower, max_loss_upper)
            
            lower_breakeven = low_long_strike + max_profit
            upper_breakeven = high_long_strike - max_loss_upper
            
            position_iv = np.mean([
                low_long_put.get('iv', avg_iv),
                short_put.get('iv', avg_iv),
                high_long_put.get('iv', avg_iv)
            ])
            
            pop = prob_in_range(
                lower_breakeven,
                upper_breakeven,
                stock_price,
                position_iv,
                risk_free_rate,
                time_to_expiry
            )
            
            if pop >= params['min_prob_profit']:
                combo['pop'] = pop
                combo['max_profit'] = max_profit
                combo['max_loss'] = max_loss
                combo['lower_breakeven'] = lower_breakeven
                combo['upper_breakeven'] = upper_breakeven
                combo['lower_wing_width'] = lower_wing_width_actual
                combo['upper_wing_width'] = upper_wing_width_actual
                combo['position_iv'] = position_iv
                pop_filtered.append(combo)
        
        tracker.add_step(
            name="Probability Filter",
            description=f"Probability of profit >= {params['min_prob_profit']*100:.0f}%",
            input_count=len(credit_filtered),
            passed_count=len(pop_filtered)
        )
        
        # Step 8: Build final opportunities with scoring
        for combo in pop_filtered:
            short_put = combo['short_put']
            low_long_put = combo['low_long_put']
            high_long_put = combo['high_long_put']
            expiry_date = combo['expiry_date']
            days_to_expiry = combo['days_to_expiry']
            time_to_expiry = days_to_expiry / 365.0
            
            short_strike = short_put['strike']
            low_long_strike = low_long_put['strike']
            high_long_strike = high_long_put['strike']
            
            low_long_debit = low_long_put.get('premium', 0)
            short_credit = short_put.get('premium', 0) * 2
            high_long_debit = high_long_put.get('premium', 0)
            net_credit_debit = combo['net_credit_debit']
            
            max_profit = combo['max_profit']
            max_loss = combo['max_loss']
            pop = combo['pop']
            position_iv = combo['position_iv']
            
            # Probability near max profit
            prob_max_profit = prob_in_range(
                short_strike * 0.95,
                short_strike * 1.05,
                stock_price,
                position_iv,
                risk_free_rate,
                time_to_expiry
            )
            
            # Calculate metrics
            capital_required = max_loss
            roi = (max_profit / capital_required * 100) if capital_required > 0 else 0
            annualized_roi = roi * (365 / days_to_expiry) if days_to_expiry > 0 else 0
            
            is_credit = net_credit_debit > 0
            credit_bonus = 15 if (is_credit and params['prefer_credit']) else 0
            
            roi_score = min(annualized_roi / 100.0, 1.0) * 100
            pop_score = pop * 100
            risk_reward = max_profit / max_loss if max_loss > 0 else 0
            risk_reward_score = min(risk_reward / 2.0, 1.0) * 100
            
            avg_volume = (low_long_put.get('volume', 0) + short_put.get('volume', 0) * 2 + 
                         high_long_put.get('volume', 0)) / 4
            volume_score = min(avg_volume / 100, 1.0) * 100
            
            # Use configurable weights from params
            w_roi = params.get('weight_roi', 0.20)
            w_pop = params.get('weight_pop', 0.35)
            w_rr = params.get('weight_risk_reward', 0.20)
            w_volume = params.get('weight_volume', 0.10)
            w_credit = params.get('weight_credit_bonus', 0.15)
            
            score = (
                roi_score * w_roi +
                pop_score * w_pop +
                risk_reward_score * w_rr +
                volume_score * w_volume +
                credit_bonus * w_credit
            )
            
            opportunity = {
                'symbol': symbol,
                'stock_price': stock_price,
                'strategy': self.strategy_name,
                'expiration': expiry_date.strftime('%Y-%m-%d'),
                'dte': days_to_expiry,
                
                'low_long_put_strike': low_long_strike,
                'low_long_put_premium': low_long_debit,
                'low_long_put_delta': low_long_put.get('delta', 0),
                'low_long_put_iv': low_long_put.get('iv', avg_iv),
                'low_long_put_volume': low_long_put.get('volume', 0),
                
                'short_put_strike': short_strike,
                'short_put_premium': short_credit / 2,
                'short_put_delta': short_put.get('delta', 0),
                'short_put_iv': short_put.get('iv', avg_iv),
                'short_put_volume': short_put.get('volume', 0),
                'short_put_quantity': 2,
                
                'high_long_put_strike': high_long_strike,
                'high_long_put_premium': high_long_debit,
                'high_long_put_delta': high_long_put.get('delta', 0),
                'high_long_put_iv': high_long_put.get('iv', avg_iv),
                'high_long_put_volume': high_long_put.get('volume', 0),
                
                'net_credit_debit': net_credit_debit,
                'is_credit': is_credit,
                'lower_wing_width': combo['lower_wing_width'],
                'upper_wing_width': combo['upper_wing_width'],
                'max_profit': max_profit,
                'max_loss': max_loss,
                'lower_breakeven': combo['lower_breakeven'],
                'upper_breakeven': combo['upper_breakeven'],
                
                'capital_required': capital_required,
                'roi': roi,
                'annualized_roi': annualized_roi,
                'risk_reward_ratio': risk_reward,
                
                'prob_max_profit': prob_max_profit,
                'pop': pop,
                'avg_iv': position_iv,
                
                'score': score
            }
            
            opportunities.append(opportunity)
        
        tracker.add_step(
            name="Final Selection",
            description="Scored and ranked opportunities",
            input_count=len(pop_filtered),
            passed_count=len(opportunities)
        )
        
        # Finalize pipeline tracking
        tracker.finalize(len(opportunities))
        
        # Sort by score descending
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities
    
    def calculate_payoff(self, opportunity: Dict[str, Any], price_range: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Calculate payoff diagram data for BWB Put position.
        
        Args:
            opportunity: Opportunity dictionary from scan()
            price_range: Optional list of stock prices to calculate payoff for
            
        Returns:
            Dictionary with payoff data for visualization
        """
        stock_price = opportunity['stock_price']
        
        # Extract position details
        low_strike = opportunity['low_long_put_strike']
        short_strike = opportunity['short_put_strike']
        high_strike = opportunity['high_long_put_strike']
        net_credit_debit = opportunity['net_credit_debit']
        
        # Generate price range if not provided
        if price_range is None:
            # Range from low strike - 10% to high strike + 10%
            price_min = low_strike * 0.90
            price_max = high_strike * 1.10
            price_range = np.linspace(price_min, price_max, 100)
        
        payoffs = []
        
        for price in price_range:
            # Low long put payoff (we bought it)
            if price < low_strike:
                low_put_payoff = (low_strike - price) - opportunity['low_long_put_premium']
            else:
                low_put_payoff = -opportunity['low_long_put_premium']
            
            # Short puts payoff (we sold 2, so multiply by 2)
            if price < short_strike:
                short_puts_payoff = -(short_strike - price) * 2 + opportunity['short_put_premium'] * 2
            else:
                short_puts_payoff = opportunity['short_put_premium'] * 2
            
            # High long put payoff (we bought it)
            if price < high_strike:
                high_put_payoff = (high_strike - price) - opportunity['high_long_put_premium']
            else:
                high_put_payoff = -opportunity['high_long_put_premium']
            
            # Total payoff
            total_payoff = low_put_payoff + short_puts_payoff + high_put_payoff
            
            payoffs.append({
                'stock_price': price,
                'payoff': total_payoff,
                'low_put_payoff': low_put_payoff,
                'short_puts_payoff': short_puts_payoff,
                'high_put_payoff': high_put_payoff
            })
        
        return {
            'payoffs': payoffs,
            'current_price': stock_price,
            'max_profit': opportunity['max_profit'],
            'max_loss': opportunity['max_loss'],
            'lower_breakeven': opportunity['lower_breakeven'],
            'upper_breakeven': opportunity['upper_breakeven'],
            'short_strike': short_strike,
            'is_credit': opportunity['is_credit']
        }


# Test code
if __name__ == '__main__':
    print("=" * 60)
    print("Broken Wing Butterfly Put Strategy Module")
    print("=" * 60)
    
    # Initialize strategy
    strategy = BrokenWingButterflyPutStrategy()
    
    print(f"\nStrategy: {strategy.display_name}")
    print(f"Complexity: {strategy.complexity_level}")
    print(f"Legs: {strategy.num_legs}")
    print(f"Description: {strategy.description}")
    
    # Test parameter validation
    print("\n✓ Testing parameter validation...")
    
    # Valid parameters
    valid_params = strategy.get_default_parameters()
    is_valid, error = strategy.validate_parameters(valid_params)
    assert is_valid, f"Default parameters should be valid: {error}"
    print("  ✓ Default parameters: PASS")
    
    # Invalid parameters - bad DTE
    invalid_params = valid_params.copy()
    invalid_params['min_dte'] = 100
    invalid_params['max_dte'] = 50
    is_valid, error = strategy.validate_parameters(invalid_params)
    assert not is_valid, "Should reject max_dte < min_dte"
    print("  ✓ DTE validation: PASS")
    
    # Invalid parameters - bad probability
    invalid_params = valid_params.copy()
    invalid_params['min_prob_profit'] = 1.5
    is_valid, error = strategy.validate_parameters(invalid_params)
    assert not is_valid, "Should reject probability > 1.0"
    print("  ✓ Probability validation: PASS")
    
    print("\n✓ Parameter validation: PASS")
    
    # Test payoff calculation with mock data
    print("\n✓ Testing payoff calculation...")
    
    mock_opportunity = {
        'symbol': 'SPY',
        'stock_price': 100.0,
        'low_long_put_strike': 90.0,
        'low_long_put_premium': 1.50,
        'short_put_strike': 95.0,
        'short_put_premium': 3.00,  # Per contract
        'short_put_quantity': 2,
        'high_long_put_strike': 103.0,
        'high_long_put_premium': 2.50,
        'net_credit_debit': 2.00,  # Credit: (3.00 * 2) - 1.50 - 2.50
        'is_credit': True,
        'lower_wing_width': 5.0,
        'upper_wing_width': 8.0,
        'max_profit': 7.0,  # 5.0 + 2.0
        'max_loss': 1.0,  # 8.0 - 5.0 - 2.0
        'lower_breakeven': 97.0,
        'upper_breakeven': 102.0
    }
    
    # Calculate payoff at specific prices
    test_prices = [85, 90, 95, 100, 103, 108]
    payoff_data = strategy.calculate_payoff(mock_opportunity, test_prices)
    
    print("\n  Payoff calculation test:")
    print(f"  Max Profit: ${payoff_data['max_profit']:.2f}")
    print(f"  Max Loss: ${payoff_data['max_loss']:.2f}")
    print(f"  Lower BE: ${payoff_data['lower_breakeven']:.2f}")
    print(f"  Upper BE: ${payoff_data['upper_breakeven']:.2f}")
    
    for payoff_point in payoff_data['payoffs']:
        price = payoff_point['stock_price']
        pl = payoff_point['payoff']
        print(f"  Stock @ ${price:.0f}: P/L = ${pl:.1f}")
    
    # Verify payoff characteristics
    payoffs_list = [p['payoff'] for p in payoff_data['payoffs']]
    
    # At 85 (far below): payoff is stable (protected by long put)
    assert payoffs_list[0] > 0, "Should have stable payoff below lower strike"
    
    # At 90 (at low long put): payoff is same (flat wing)
    assert payoffs_list[1] == payoffs_list[0], "Should be flat below low long put"
    
    # At 95 (at short strike): should be at max profit
    assert payoffs_list[2] >= 7.0, "Should be at max profit at short strike"
    
    # At 100 (between short and high strike): still profitable
    assert payoffs_list[3] > 0, "Should still profit between strikes"
    
    # At 103 (at high long put): approaching upper breakeven
    assert payoffs_list[4] > 0, "Should still be profitable at high strike"
    
    # At 108 (far above): loss limited by broken wing (flat)
    assert payoffs_list[5] == payoffs_list[4], "Loss should be capped and flat"
    
    print("\n✓ Payoff calculation: PASS")
    
    print("\n" + "=" * 60)
    print("✅ All BWB Put tests passed!")
    print("=" * 60)
