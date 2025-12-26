"""
Twisted Sister Strategy - 3-leg neutral income strategy (Reverse Jade Lizard).

Structure:
- Short Call (OTM)
- Short Put (OTM) 
- Long Put (Further OTM) - protects the short put

This is a bearish-neutral strategy that collects premium. The ideal scenario is when
the collected credit exceeds the width of the put spread, creating "no downside risk".

Key Characteristics:
- Defined risk on upside (short call)
- Undefined risk on downside UNLESS credit >= put spread width (ideal Twisted Sister)
- High probability of profit
- Benefits from time decay
- Neutral to slightly bearish bias

Best Used When:
- IV is elevated (collect more premium)
- Expect stock to stay neutral or fall slightly
- Want to collect income with reasonable risk
- Comfortable with assignment risk on short call

Profit/Loss:
- Max Profit: Total credit received (if stock between strikes)
- Max Loss (Upside): Call strike + total credit (if stock goes to infinity)
- Max Loss (Downside): Put spread width - total credit (if positive)
- Breakeven (Up): Call strike + total credit
- Breakeven (Down): Short put strike - total credit (if downside risk exists)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import BaseStrategy
from utils.calculations import (
    get_stock_price,
    get_risk_free_rate,
    get_options_data,
    compute_avg_iv,
    prob_in_range,
    parse_options_chain,
    get_eastern_now
)
from utils.pipeline_tracker import PipelineTracker


class TwistedSisterStrategy(BaseStrategy):
    """Twisted Sister - Short call + short put spread strategy (Reverse Jade Lizard)."""
    
    def __init__(self):
        super().__init__(
            strategy_id='twisted_sister',
            strategy_name='twisted_sister',
            display_name='Twisted Sister',
            description='Neutral income strategy: Short call + short put spread. Collects credit with defined upside risk and minimal/no downside risk when structured properly.',
            num_legs=3,
            complexity_level='advanced'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for Twisted Sister strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_dte': 30,
            'max_dte': 60,
            'call_delta_min': 0.15,
            'call_delta_max': 0.35,
            'short_put_delta_min': 0.15,
            'short_put_delta_max': 0.35,
            'spread_width_min': 2.0,  # Min % of stock price for put spread width (was 3.0, now 2.0 for more flexibility)
            'spread_width_max': 10.0,  # Max % of stock price (was 8.0, now 10.0)
            'min_credit': 0.50,  # Minimum net credit (was 1.00, now 0.50)
            'min_volume': 10,
            'max_spread_cost_ratio': 0.80,  # Long put can't cost more than 80% of short put (was 0.60, now 0.80)
            'prefer_no_downside_risk': False,  # Don't require no downside risk (was True, now False)
            # Scoring weights (must sum to 1.0)
            'weight_credit': 0.25,
            'weight_roc': 0.25,
            'weight_pop': 0.30,
            'weight_volume': 0.10,
            'weight_risk_bonus': 0.10
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
        
        # Validate delta ranges
        if not (0 < full_params['call_delta_min'] < full_params['call_delta_max'] <= 0.50):
            return False, "Call delta range must be between 0 and 0.50"
        if not (0 < full_params['short_put_delta_min'] < full_params['short_put_delta_max'] <= 0.50):
            return False, "Short put delta range must be between 0 and 0.50"
        
        # Validate spread width
        if full_params['spread_width_min'] <= 0 or full_params['spread_width_max'] <= 0:
            return False, "Spread width percentages must be positive"
        if full_params['spread_width_max'] < full_params['spread_width_min']:
            return False, "Max spread width must be greater than min spread width"
        
        # Validate credit and volume
        if full_params['min_credit'] <= 0:
            return False, "Minimum credit must be positive"
        if full_params['min_volume'] < 1:
            return False, "Minimum volume must be at least 1"
        
        # Validate spread cost ratio
        if not (0 < full_params['max_spread_cost_ratio'] <= 1.0):
            return False, "Spread cost ratio must be between 0 and 1.0"
        
        return True, None
    
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], 
             api_key: str, session: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Scan for Twisted Sister opportunities with pipeline tracking.
        
        Args:
            symbol: Stock ticker symbol
            filter_criteria: Dictionary of filter parameters
            api_key: Alpha Vantage API key
            session: Requests session for API calls
            
        Returns:
            List of opportunity dictionaries (top 10), sorted by score, or None if no opportunities found
        """
        # Merge with defaults
        defaults = self.get_default_parameters()
        params = {**defaults, **filter_criteria}
        
        # Validate parameters
        is_valid, error = self.validate_parameters(params)
        if not is_valid:
            print(f"❌ Invalid parameters: {error}")
            return None
        
        # Get market data
        stock_price = get_stock_price(symbol, api_key, session)
        if not stock_price:
            return None
        
        # Initialize pipeline tracker
        tracker = PipelineTracker(symbol, stock_price, self.strategy_id, self.display_name, filter_criteria)
        
        risk_free_rate = get_risk_free_rate(api_key, session)
        options_data = get_options_data(symbol, api_key, session)
        if not options_data:
            return None
        
        options_chain = parse_options_chain(options_data)
        if not options_chain:
            return None
        
        avg_iv = compute_avg_iv(options_data)
        current_date = get_eastern_now()
        
        # Count total options
        total_options = sum(len(opts) for opts in options_chain.values())
        tracker.add_step('Raw Options', f'Total options fetched for {symbol}', total_options, total_options)
        
        # Step 1: Filter by DTE
        dte_filtered_options = []
        for expiry_date, options in options_chain.items():
            days_to_expiry = (expiry_date - current_date).days
            if params['min_dte'] <= days_to_expiry <= params['max_dte']:
                for opt in options:
                    opt['expiry'] = expiry_date
                    opt['dte'] = days_to_expiry
                    dte_filtered_options.append(opt)
        tracker.add_step('DTE Filter', f"Days to expiry {params['min_dte']}-{params['max_dte']}", total_options, len(dte_filtered_options))
        
        # Step 2: Filter calls and puts
        suitable_calls = []
        suitable_puts = []
        for opt in dte_filtered_options:
            if opt.get('volume', 0) >= params['min_volume']:
                if opt['type'] == 'CALL' and opt['strike'] > stock_price:
                    call_delta = abs(opt.get('delta', 0))
                    if params['call_delta_min'] <= call_delta <= params['call_delta_max']:
                        suitable_calls.append(opt)
                elif opt['type'] == 'PUT' and opt['strike'] < stock_price:
                    put_delta = abs(opt.get('delta', 0))
                    if params['short_put_delta_min'] <= put_delta <= params['short_put_delta_max']:
                        suitable_puts.append(opt)
        tracker.add_step('Short Call Filter', f"OTM calls with delta {params['call_delta_min']}-{params['call_delta_max']}", len(dte_filtered_options), len(suitable_calls))
        tracker.add_step('Short Put Filter', f"OTM puts with delta {params['short_put_delta_min']}-{params['short_put_delta_max']}", len(dte_filtered_options), len(suitable_puts))
        
        # Step 3: Find valid combinations with long puts
        valid_combinations = []
        potential_combos = 0
        for call in suitable_calls:
            for short_put in suitable_puts:
                if call['expiry'] != short_put['expiry']:
                    continue
                potential_combos += 1
                
                max_long_strike = short_put['strike'] - (stock_price * params['spread_width_min'] / 100)
                min_long_strike = short_put['strike'] - (stock_price * params['spread_width_max'] / 100)
                
                for opt in dte_filtered_options:
                    if (opt['type'] == 'PUT' and 
                        opt['expiry'] == short_put['expiry'] and
                        min_long_strike <= opt['strike'] <= max_long_strike and
                        opt.get('volume', 0) >= params['min_volume']):
                        valid_combinations.append({
                            'call': call,
                            'short_put': short_put,
                            'long_put': opt
                        })
        tracker.add_step('Long Put Matching', f"Put spread width {params['spread_width_min']}-{params['spread_width_max']}% of stock", potential_combos, len(valid_combinations))
        
        # Step 4: Filter by credit requirement
        credit_filtered = []
        for combo in valid_combinations:
            total_credit = (combo['call'].get('premium', 0) + 
                          combo['short_put'].get('premium', 0) - 
                          combo['long_put'].get('premium', 0))
            if total_credit >= params['min_credit']:
                combo['total_credit'] = total_credit
                credit_filtered.append(combo)
        tracker.add_step('Credit Filter', f"Net credit ≥ ${params['min_credit']}", len(valid_combinations), len(credit_filtered))
        
        # Step 5: Filter by spread cost ratio
        ratio_filtered = []
        for combo in credit_filtered:
            short_put_credit = combo['short_put'].get('premium', 0)
            long_put_debit = combo['long_put'].get('premium', 0)
            if short_put_credit > 0:
                ratio = long_put_debit / short_put_credit
                if ratio <= params['max_spread_cost_ratio']:
                    ratio_filtered.append(combo)
        tracker.add_step('Spread Cost Ratio', f"Long put cost ≤ {params['max_spread_cost_ratio']*100}% of short put", len(credit_filtered), len(ratio_filtered))
        
        twisted_opportunities = []
        
        for combo in ratio_filtered:
            call = combo['call']
            short_put = combo['short_put']
            long_put = combo['long_put']
            days_to_expiry = call['dte']
            expiry_date = call['expiry']
            time_to_expiry = days_to_expiry / 365.0
            
            call_credit = call.get('premium', 0)
            short_put_credit = short_put.get('premium', 0)
            long_put_debit = long_put.get('premium', 0)
            total_credit = call_credit + short_put_credit - long_put_debit
            
            put_spread_width = short_put['strike'] - long_put['strike']
            max_downside_loss = put_spread_width - total_credit
            no_downside_risk = max_downside_loss <= 0
            
            if params['prefer_no_downside_risk'] and not no_downside_risk:
                continue
            
            max_profit = total_credit
            max_upside_loss = 999999.99
            
            upside_breakeven = call['strike'] + total_credit
            downside_breakeven = short_put['strike'] - total_credit if not no_downside_risk else 0
            
            capital_required = put_spread_width
            roc = (total_credit / capital_required * 100) if capital_required > 0 else 0
            annualized_roc = roc * (365 / days_to_expiry) if days_to_expiry > 0 else 0
            
            ivs = [call.get('iv', avg_iv), short_put.get('iv', avg_iv), long_put.get('iv', avg_iv)]
            position_iv = sum(ivs) / len(ivs)
            
            prob_max_profit = prob_in_range(short_put['strike'], call['strike'], stock_price, position_iv, risk_free_rate, time_to_expiry)
            prob_below_call_be = prob_in_range(0, upside_breakeven, stock_price, position_iv, risk_free_rate, time_to_expiry)
            
            if no_downside_risk:
                pop = prob_below_call_be
            else:
                prob_above_downside_be = 1 - prob_in_range(0, downside_breakeven, stock_price, position_iv, risk_free_rate, time_to_expiry)
                pop = prob_below_call_be * prob_above_downside_be
            
            credit_score = min(total_credit / 5.0, 1.0) * 100
            roc_score = min(annualized_roc / 50.0, 1.0) * 100
            pop_score = pop * 100
            downside_risk_bonus = 20 if no_downside_risk else 0
            avg_volume = (call.get('volume', 0) + short_put.get('volume', 0) + long_put.get('volume', 0)) / 3
            volume_score = min(avg_volume / 100, 1.0) * 100
            
            # Use configurable weights from params
            w_credit = params.get('weight_credit', 0.25)
            w_roc = params.get('weight_roc', 0.25)
            w_pop = params.get('weight_pop', 0.30)
            w_volume = params.get('weight_volume', 0.10)
            w_risk = params.get('weight_risk_bonus', 0.10)
            
            score = credit_score * w_credit + roc_score * w_roc + pop_score * w_pop + volume_score * w_volume + downside_risk_bonus * w_risk
            
            legs_data = [
                {'type': 'call', 'position': 'short', 'strike': call['strike'], 'expiry': expiry_date.isoformat(),
                 'premium': call_credit, 'delta': call.get('delta', 0), 'volume': call.get('volume', 0), 'dte': days_to_expiry},
                {'type': 'put', 'position': 'short', 'strike': short_put['strike'], 'expiry': expiry_date.isoformat(),
                 'premium': short_put_credit, 'delta': short_put.get('delta', 0), 'volume': short_put.get('volume', 0), 'dte': days_to_expiry},
                {'type': 'put', 'position': 'long', 'strike': long_put['strike'], 'expiry': expiry_date.isoformat(),
                 'premium': long_put_debit, 'delta': long_put.get('delta', 0), 'volume': long_put.get('volume', 0), 'dte': days_to_expiry}
            ]
            
            opportunity = {
                'symbol': symbol, 'stock_price': stock_price, 'strategy_type': self.strategy_id,
                'position_data': legs_data, 'legs': legs_data,
                'total_credit_debit': round(total_credit, 2), 'max_profit': round(max_profit, 2),
                'max_loss': round(max(max_upside_loss, max_downside_loss if not no_downside_risk else 0), 2),
                'breakeven_price': round(upside_breakeven, 2), 'roc_pct': round(roc, 2),
                'annualized_roc_pct': round(annualized_roc, 2), 'pop_pct': round(pop * 100, 2),
                'expiry_date': expiry_date.isoformat(), 'days_to_expiry': days_to_expiry,
                'metrics': {
                    'net_debit': round(-total_credit, 2), 'total_credit': round(total_credit, 2),
                    'put_spread_width': round(put_spread_width, 2), 'no_downside_risk': no_downside_risk,
                    'max_profit': round(max_profit, 2),
                    'max_loss': round(max(max_upside_loss, max_downside_loss if not no_downside_risk else 0), 2),
                    'max_upside_loss': round(max_upside_loss, 2),
                    'max_downside_loss': round(max_downside_loss if not no_downside_risk else 0, 2),
                    'breakeven': round(upside_breakeven, 2), 'upside_breakeven': round(upside_breakeven, 2),
                    'downside_breakeven': round(downside_breakeven, 2) if not no_downside_risk else None,
                    'capital_required': round(capital_required, 2), 'roi': round(roc, 2),
                    'annualized_roi': round(annualized_roc, 2), 'prob_max_profit': round(prob_max_profit * 100, 2),
                    'prob_profit': round(pop * 100, 2),
                    'risk_reward': round(max_profit / max(max_downside_loss if not no_downside_risk else 0.01, 0.01), 2)
                },
                'score': round(score, 2), 'scan_timestamp': get_eastern_now().isoformat()
            }
            twisted_opportunities.append(opportunity)
        
        tracker.add_step('Profitability Filter', 'Valid opportunities with positive metrics', len(ratio_filtered), len(twisted_opportunities))
        
        final_count = min(10, len(twisted_opportunities)) if twisted_opportunities else 0
        tracker.add_step('Final Selection', 'Top 10 opportunities by score', len(twisted_opportunities), final_count)
        
        tracker.finalize(final_count)
        
        if twisted_opportunities:
            twisted_opportunities.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n✅ Found {len(twisted_opportunities)} Twisted Sister opportunities")
            return twisted_opportunities[:10]
        else:
            print(f"\n❌ No Twisted Sister opportunities found matching all criteria")
            return None
    
    def calculate_payoff(self, stock_prices: List[float], legs: List[Dict[str, Any]],
                        initial_cost: float) -> List[float]:
        """
        Calculate Twisted Sister payoff at expiration.
        
        Twisted Sister = Short Call + Short Put + Long Put (lower strike)
        
        At expiration:
        - Short call: -(max(stock_price - call_strike, 0) - call_premium)
        - Short put: -(max(put_strike - stock_price, 0) - put_premium)
        - Long put: max(long_put_strike - stock_price, 0) - long_put_premium
        """
        payoffs = []
        
        # Extract legs by type and position
        short_call = next(leg for leg in legs if leg['type'] == 'call' and leg['position'] == 'short')
        short_put = next(leg for leg in legs if leg['type'] == 'put' and leg['position'] == 'short')
        long_put = next(leg for leg in legs if leg['type'] == 'put' and leg['position'] == 'long')
        
        call_strike = short_call['strike']
        short_put_strike = short_put['strike']
        long_put_strike = long_put['strike']
        
        for stock_price in stock_prices:
            # Short call payoff (we sold it, receive premium, pay out if ITM)
            if stock_price > call_strike:
                call_payoff = -(stock_price - call_strike) + short_call['premium']
            else:
                call_payoff = short_call['premium']
            
            # Short put payoff (we sold it, receive premium, pay out if ITM)
            if stock_price < short_put_strike:
                put_payoff = -(short_put_strike - stock_price) + short_put['premium']
            else:
                put_payoff = short_put['premium']
            
            # Long put payoff (we bought it, paid premium, receive value if ITM)
            if stock_price < long_put_strike:
                long_put_payoff = (long_put_strike - stock_price) - long_put['premium']
            else:
                long_put_payoff = -long_put['premium']
            
            # Total payoff
            total_payoff = call_payoff + put_payoff + long_put_payoff
            payoffs.append(round(total_payoff, 2))
        
        return payoffs


# Test code
if __name__ == '__main__':
    print("=" * 60)
    print("Twisted Sister Strategy Module")
    print("=" * 60)
    
    # Initialize strategy
    strategy = TwistedSisterStrategy()
    
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
    
    # Invalid parameters - bad delta
    invalid_params = valid_params.copy()
    invalid_params['call_delta_min'] = 0.60
    is_valid, error = strategy.validate_parameters(invalid_params)
    assert not is_valid, "Should reject call delta > 0.50"
    print("  ✓ Delta validation: PASS")
    
    print("\n✓ Parameter validation: PASS")
    
    # Test payoff calculation with mock data
    print("\n✓ Testing payoff calculation...")
    
    mock_opportunity = {
        'symbol': 'SPY',
        'stock_price': 100.0,
        'short_call_strike': 105.0,
        'short_call_premium': 2.50,
        'short_put_strike': 95.0,
        'short_put_premium': 2.00,
        'long_put_strike': 90.0,
        'long_put_premium': 0.50,
        'total_credit': 4.00,  # 2.50 + 2.00 - 0.50
        'put_spread_width': 5.0,
        'max_profit': 4.00,
        'max_downside_loss': 1.0,  # 5 - 4
        'max_upside_loss': float('inf'),
        'upside_breakeven': 109.0,
        'downside_breakeven': 91.0,
        'no_downside_risk': False
    }
    
    # Calculate payoff at specific prices
    test_prices = [85, 90, 95, 100, 105, 115]
    payoff_data = strategy.calculate_payoff(mock_opportunity, test_prices)
    
    print("\n  Payoff calculation test:")
    print(f"  Max Profit: ${payoff_data['max_profit']:.2f}")
    print(f"  Upside BE: ${payoff_data['upside_breakeven']:.2f}")
    print(f"  Downside BE: ${payoff_data['downside_breakeven']:.2f}" if payoff_data['downside_breakeven'] else "  Downside BE: None (no downside risk)")
    
    for payoff_point in payoff_data['payoffs']:
        price = payoff_point['stock_price']
        pl = payoff_point['payoff']
        print(f"  Stock @ ${price:.0f}: P/L = ${pl:.1f}")
    
    # Verify payoff characteristics
    payoffs_list = [p['payoff'] for p in payoff_data['payoffs']]
    
    # At 85 (below long put): loss should be capped
    assert abs(payoffs_list[0] - payoffs_list[1]) < 1, "Loss should be capped below long put"
    
    # At 90 (at long put): long put starts protecting
    assert payoffs_list[1] < 0, "Should have small loss at long put strike"
    
    # At 95 (at short put): approaching max profit zone
    assert payoffs_list[2] > 0, "Should profit at short put strike"
    
    # At 100 (between strikes): should be at/near max profit
    assert payoffs_list[3] >= 3.0, "Should be near max profit between strikes"
    
    # At 105 (at short call): still at max profit
    assert payoffs_list[4] >= 3.0, "Should still be near max profit at short call"
    
    # At 115 (above short call): losses start accumulating
    assert payoffs_list[5] < payoffs_list[4], "Should lose money above short call"
    
    print("\n✓ Payoff calculation: PASS")
    
    print("\n" + "=" * 60)
    print("✅ All Twisted Sister tests passed!")
    print("=" * 60)
