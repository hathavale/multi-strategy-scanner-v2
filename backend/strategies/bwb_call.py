"""
Broken Wing Butterfly Call Strategy - 3-leg risk-defined neutral strategy.

Structure:
- Long Call (Highest Strike - OTM)
- 2x Short Calls (Middle Strike - OTM)
- Long Call (Lowest Strike - Further OTM/ITM) - "broken wing" is closer in

This is a neutral strategy with a directional bias. The "broken wing" creates an
unbalanced structure that can collect credit or reduce cost while maintaining defined risk.

Key Characteristics:
- Defined maximum risk
- Defined maximum profit
- Lower cost than standard butterfly
- Can be structured for credit in some cases
- Slightly bullish bias (profits if stock stays/rises to sweet spot)
- Benefits from low volatility at expiration

Best Used When:
- Expect stock to trade in narrow range near short strikes
- Want defined risk with lower capital
- Prefer higher probability over larger profit
- IV is moderate to high (sell more premium at short strikes)

Profit/Loss:
- Max Profit: At short call strike at expiration
- Max Loss: Either at long call strikes (difference in strikes - net premium)
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


class BrokenWingButterflyCallStrategy(BaseStrategy):
    """Broken Wing Butterfly Call - Unbalanced 3-leg call butterfly."""
    
    def __init__(self):
        super().__init__(
            strategy_id='bwb_call',
            strategy_name='bwb_call',
            display_name='Broken Wing Butterfly - Call',
            description='Risk-defined neutral strategy with unbalanced wings using calls. Lower cost and higher probability than standard butterfly, with slight bullish bias.',
            num_legs=3,
            complexity_level='advanced'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for BWB Call strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_dte': 30,
            'max_dte': 60,
            'short_call_delta_min': 0.25,
            'short_call_delta_max': 0.40,
            'lower_wing_width': 8.0,  # Width between low long call and short calls (% of stock) - broken wing
            'upper_wing_width': 5.0,  # Width between short calls and high long call (% of stock)
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
        if not (0 < full_params['short_call_delta_min'] < full_params['short_call_delta_max'] <= 0.50):
            return False, "Short call delta range must be between 0 and 0.50"
        
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
        Scan for Broken Wing Butterfly Call opportunities.
        
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
        
        # Step 3: Filter to CALL options only
        call_options = [opt for opt in dte_filtered_options if opt['type'] == 'CALL']
        tracker.add_step(
            name="CALL Filter",
            description="Filter to CALL options only",
            input_count=len(dte_filtered_options),
            passed_count=len(call_options)
        )
        
        # Step 4: Find suitable short calls (middle of butterfly)
        suitable_short_calls = []
        for opt in call_options:
            call_delta_abs = abs(opt.get('delta', 0))
            if (params['short_call_delta_min'] <= call_delta_abs <= params['short_call_delta_max'] and
                opt.get('volume', 0) >= params['min_volume'] and
                opt['strike'] > stock_price):
                suitable_short_calls.append(opt)
        
        tracker.add_step(
            name="Short Call Filter",
            description=f"Calls with delta {params['short_call_delta_min']}-{params['short_call_delta_max']}, volume >= {params['min_volume']}, OTM",
            input_count=len(call_options),
            passed_count=len(suitable_short_calls)
        )
        
        # Step 5: Build butterfly combinations
        butterfly_combos = []
        for short_call in suitable_short_calls:
            short_strike = short_call['strike']
            expiry_date = short_call['expiry_date']
            
            # Get all calls for this expiry
            expiry_calls = {opt['strike']: opt for opt in call_options 
                          if opt['expiry_date'] == expiry_date}
            
            # Calculate wing widths
            lower_width = stock_price * params['lower_wing_width'] / 100
            upper_width = stock_price * params['upper_wing_width'] / 100
            
            # Find low long call (broken wing - further from short)
            low_long_strike_target = short_strike - lower_width
            low_long_call = None
            min_diff = float('inf')
            for strike, call in expiry_calls.items():
                if strike < short_strike and call.get('volume', 0) >= params['min_volume']:
                    diff = abs(strike - low_long_strike_target)
                    if diff < min_diff:
                        min_diff = diff
                        low_long_call = call
            
            # Find high long call (smaller wing)
            high_long_strike_target = short_strike + upper_width
            high_long_call = None
            min_diff = float('inf')
            for strike, call in expiry_calls.items():
                if strike > short_strike and call.get('volume', 0) >= params['min_volume']:
                    diff = abs(strike - high_long_strike_target)
                    if diff < min_diff:
                        min_diff = diff
                        high_long_call = call
            
            if low_long_call and high_long_call:
                butterfly_combos.append({
                    'short_call': short_call,
                    'low_long_call': low_long_call,
                    'high_long_call': high_long_call,
                    'expiry_date': expiry_date,
                    'days_to_expiry': short_call['days_to_expiry']
                })
        
        tracker.add_step(
            name="Wing Matching",
            description="Matching lower and upper wing long calls to each short call",
            input_count=len(suitable_short_calls),
            passed_count=len(butterfly_combos)
        )
        
        # Step 6: Filter by credit/debit requirements
        credit_filtered = []
        for combo in butterfly_combos:
            low_long_debit = combo['low_long_call'].get('premium', 0)
            short_credit = combo['short_call'].get('premium', 0) * 2
            high_long_debit = combo['high_long_call'].get('premium', 0)
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
            short_call = combo['short_call']
            low_long_call = combo['low_long_call']
            high_long_call = combo['high_long_call']
            days_to_expiry = combo['days_to_expiry']
            time_to_expiry = days_to_expiry / 365.0
            
            short_strike = short_call['strike']
            low_long_strike = low_long_call['strike']
            high_long_strike = high_long_call['strike']
            net_credit_debit = combo['net_credit_debit']
            
            # Calculate wing widths and risk
            lower_wing_width_actual = short_strike - low_long_strike
            upper_wing_width_actual = high_long_strike - short_strike
            max_profit = upper_wing_width_actual + net_credit_debit
            max_loss_lower = lower_wing_width_actual - upper_wing_width_actual - net_credit_debit
            max_loss_upper = -net_credit_debit if net_credit_debit < 0 else 0
            max_loss = max(max_loss_lower, max_loss_upper)
            
            lower_breakeven = low_long_strike + max_loss_lower
            upper_breakeven = high_long_strike - max_profit
            
            position_iv = np.mean([
                low_long_call.get('iv', avg_iv),
                short_call.get('iv', avg_iv),
                high_long_call.get('iv', avg_iv)
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
            short_call = combo['short_call']
            low_long_call = combo['low_long_call']
            high_long_call = combo['high_long_call']
            expiry_date = combo['expiry_date']
            days_to_expiry = combo['days_to_expiry']
            time_to_expiry = days_to_expiry / 365.0
            
            short_strike = short_call['strike']
            low_long_strike = low_long_call['strike']
            high_long_strike = high_long_call['strike']
            
            low_long_debit = low_long_call.get('premium', 0)
            short_credit = short_call.get('premium', 0) * 2
            high_long_debit = high_long_call.get('premium', 0)
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
            
            avg_volume = (low_long_call.get('volume', 0) + short_call.get('volume', 0) * 2 + 
                         high_long_call.get('volume', 0)) / 4
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
                
                'low_long_call_strike': low_long_strike,
                'low_long_call_premium': low_long_debit,
                'low_long_call_delta': low_long_call.get('delta', 0),
                'low_long_call_iv': low_long_call.get('iv', avg_iv),
                'low_long_call_volume': low_long_call.get('volume', 0),
                
                'short_call_strike': short_strike,
                'short_call_premium': short_credit / 2,
                'short_call_delta': short_call.get('delta', 0),
                'short_call_iv': short_call.get('iv', avg_iv),
                'short_call_volume': short_call.get('volume', 0),
                'short_call_quantity': 2,
                
                'high_long_call_strike': high_long_strike,
                'high_long_call_premium': high_long_debit,
                'high_long_call_delta': high_long_call.get('delta', 0),
                'high_long_call_iv': high_long_call.get('iv', avg_iv),
                'high_long_call_volume': high_long_call.get('volume', 0),
                
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
        Calculate payoff diagram data for BWB Call position.
        
        Args:
            opportunity: Opportunity dictionary from scan()
            price_range: Optional list of stock prices to calculate payoff for
            
        Returns:
            Dictionary with payoff data for visualization
        """
        stock_price = opportunity['stock_price']
        
        # Extract position details
        low_strike = opportunity['low_long_call_strike']
        short_strike = opportunity['short_call_strike']
        high_strike = opportunity['high_long_call_strike']
        net_credit_debit = opportunity['net_credit_debit']
        
        # Generate price range if not provided
        if price_range is None:
            # Range from low strike - 10% to high strike + 10%
            price_min = low_strike * 0.90
            price_max = high_strike * 1.10
            price_range = np.linspace(price_min, price_max, 100)
        
        payoffs = []
        
        for price in price_range:
            # Low long call payoff (we bought it)
            if price > low_strike:
                low_call_payoff = (price - low_strike) - opportunity['low_long_call_premium']
            else:
                low_call_payoff = -opportunity['low_long_call_premium']
            
            # Short calls payoff (we sold 2, so multiply by 2)
            if price > short_strike:
                short_calls_payoff = -(price - short_strike) * 2 + opportunity['short_call_premium'] * 2
            else:
                short_calls_payoff = opportunity['short_call_premium'] * 2
            
            # High long call payoff (we bought it)
            if price > high_strike:
                high_call_payoff = (price - high_strike) - opportunity['high_long_call_premium']
            else:
                high_call_payoff = -opportunity['high_long_call_premium']
            
            # Total payoff
            total_payoff = low_call_payoff + short_calls_payoff + high_call_payoff
            
            payoffs.append({
                'stock_price': price,
                'payoff': total_payoff,
                'low_call_payoff': low_call_payoff,
                'short_calls_payoff': short_calls_payoff,
                'high_call_payoff': high_call_payoff
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
    print("Broken Wing Butterfly Call Strategy Module")
    print("=" * 60)
    
    # Initialize strategy
    strategy = BrokenWingButterflyCallStrategy()
    
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
        'low_long_call_strike': 97.0,
        'low_long_call_premium': 2.50,
        'short_call_strike': 105.0,
        'short_call_premium': 3.00,  # Per contract
        'short_call_quantity': 2,
        'high_long_call_strike': 110.0,
        'high_long_call_premium': 1.50,
        'net_credit_debit': 2.00,  # Credit: (3.00 * 2) - 2.50 - 1.50
        'is_credit': True,
        'lower_wing_width': 8.0,
        'upper_wing_width': 5.0,
        'max_profit': 7.0,  # 5.0 + 2.0
        'max_loss': 1.0,  # 8.0 - 5.0 - 2.0
        'lower_breakeven': 98.0,
        'upper_breakeven': 103.0
    }
    
    # Calculate payoff at specific prices
    test_prices = [92, 97, 105, 110, 115, 120]
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
    
    # At 92 (far below): loss limited by broken wing (flat)
    assert payoffs_list[0] > 0, "Should have stable payoff below lower strike"
    
    # At 97 (at low long call): payoff is same (flat wing)
    assert payoffs_list[1] == payoffs_list[0], "Should be flat below low long call"
    
    # At 105 (at short strike): should be at max profit
    assert payoffs_list[2] >= 7.0, "Should be at max profit at short strike"
    
    # At 110 (at high long call): approaching upper breakeven
    assert payoffs_list[3] > 0, "Should still be profitable at high strike"
    
    # At 115 (above high strike): payoff stable
    assert payoffs_list[4] == payoffs_list[3], "Should be flat above high long call"
    
    # At 120 (far above): loss capped
    assert payoffs_list[5] == payoffs_list[4], "Loss should be capped and flat"
    
    print("\n✓ Payoff calculation: PASS")
    
    print("\n" + "=" * 60)
    print("✅ All BWB Call tests passed!")
    print("=" * 60)
