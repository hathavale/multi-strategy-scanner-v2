"""
PMCC (Poor Man's Covered Call) Strategy Implementation.

A PMCC is a bullish strategy that mimics a covered call using options instead of stock:
- Buy a long-term deep ITM call option (LEAP) as a stock replacement
- Sell a short-term OTM call option to generate income

This is cheaper than buying 100 shares + selling a call, hence "Poor Man's" Covered Call.

Strategy Characteristics:
- Bullish directional bias
- 2 legs (long call + short call)
- Lower capital requirement than traditional covered call
- Limited profit potential, limited risk
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import BaseStrategy
from utils.calculations import (
    get_stock_price,
    get_risk_free_rate,
    get_options_data,
    parse_options_chain,
    calculate_time_to_expiry,
    calculate_delta,
    validate_strike_price,
    validate_expiration_date,
    get_eastern_now
)
from utils.pipeline_tracker import PipelineTracker


class PMCCStrategy(BaseStrategy):
    """
    PMCC - Poor Man's Covered Call strategy implementation.
    
    Entry Criteria:
    - Long call: Deep ITM (delta 0.70-0.90), 180+ days to expiry
    - Short call: OTM (delta 0.20-0.40), 30-45 days to expiry
    - Short call strike > Long call strike
    """
    
    def __init__(self):
        super().__init__(
            strategy_id='pmcc',
            strategy_name='pmcc',
            display_name='PMCC - Poor Man\'s Covered Call',
            description='Buy deep ITM long call (LEAP) and sell OTM short call for income',
            num_legs=2,
            complexity_level='intermediate'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for PMCC strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_long_delta': 0.60,
            'max_long_delta': 0.95,
            'min_short_delta': 0.15,
            'max_short_delta': 0.50,
            'min_long_dte': 150,
            'min_short_dte': 10,
            'max_short_dte': 60,
            'min_credit': 0.25,
            'min_volume': 0,
            # Scoring weights (must sum to 1.0)
            'weight_roi': 0.25,
            'weight_risk_reward': 0.20,
            'weight_premium': 0.15,
            'weight_long_delta': 0.20,
            'weight_short_delta': 0.20
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate PMCC-specific parameters.
        
        Expected params:
        - long_strike: Strike price for long call
        - long_expiry: Expiration date for long call
        - short_strike: Strike price for short call
        - short_expiry: Expiration date for short call
        - stock_price: Current stock price
        """
        required_fields = ['long_strike', 'long_expiry', 'short_strike', 'short_expiry', 'stock_price']
        
        # Check required fields
        for field in required_fields:
            if field not in params:
                return False, f"Missing required parameter: {field}"
        
        # Validate strikes
        if not validate_strike_price(params['long_strike'], params['stock_price']):
            return False, "Invalid long call strike price"
        
        if not validate_strike_price(params['short_strike'], params['stock_price']):
            return False, "Invalid short call strike price"
        
        # Short strike must be higher than long strike
        if params['short_strike'] <= params['long_strike']:
            return False, "Short call strike must be higher than long call strike"
        
        # Validate expiration dates
        if not validate_expiration_date(params['long_expiry']):
            return False, "Long call expiration date must be in the future"
        
        if not validate_expiration_date(params['short_expiry']):
            return False, "Short call expiration date must be in the future"
        
        # Long expiry must be later than short expiry
        if params['long_expiry'] <= params['short_expiry']:
            return False, "Long call expiration must be later than short call expiration"
        
        return True, None
    
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], 
             api_key: str, session: Any) -> Optional[Dict[str, Any]]:
        """
        Scan for PMCC opportunities with pipeline tracking.
        
        Filter criteria:
        - min_long_delta: Minimum delta for long call (default: 0.70)
        - max_long_delta: Maximum delta for long call (default: 0.90)
        - min_short_delta: Minimum delta for short call (default: 0.20)
        - max_short_delta: Maximum delta for short call (default: 0.40)
        - min_long_dte: Minimum days to expiry for long call (default: 180)
        - min_short_dte: Minimum days to expiry for short call (default: 30)
        - max_short_dte: Maximum days to expiry for short call (default: 45)
        - min_credit: Minimum credit from short call (default: 0.50)
        - min_volume: Minimum option volume (default: 10)
        """
        # Set default filter values
        min_long_delta = filter_criteria.get('min_long_delta', 0.70)
        max_long_delta = filter_criteria.get('max_long_delta', 0.90)
        min_short_delta = filter_criteria.get('min_short_delta', 0.20)
        max_short_delta = filter_criteria.get('max_short_delta', 0.40)
        min_long_dte = filter_criteria.get('min_long_dte', 180)
        min_short_dte = filter_criteria.get('min_short_dte', 30)
        max_short_dte = filter_criteria.get('max_short_dte', 45)
        min_credit = filter_criteria.get('min_credit', 0.50)
        min_volume = filter_criteria.get('min_volume', 10)
        
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
        
        # Parse options chain by expiration
        options_by_expiry = parse_options_chain(options_data)
        
        if not options_by_expiry:
            return None
        
        # Count total options across all expirations
        total_options = sum(len(opts) for opts in options_by_expiry.values())
        tracker.add_step('Raw Options', f'Total options fetched for {symbol}', total_options, total_options)
        
        # Step 1: Filter to CALL options only
        all_calls = []
        for expiry, options in options_by_expiry.items():
            for opt in options:
                if opt['type'] == 'CALL':
                    opt['expiry'] = expiry
                    all_calls.append(opt)
        tracker.add_step('CALL Filter', 'Filter to CALL options only', total_options, len(all_calls))
        
        # Step 2: Filter by minimum volume
        calls_with_volume = [c for c in all_calls if c['volume'] >= min_volume]
        tracker.add_step('Volume Filter', f'Minimum volume ≥ {min_volume}', len(all_calls), len(calls_with_volume))
        
        # Step 3: Separate Long Call candidates (LEAP - deep ITM, long-term)
        long_call_candidates = []
        for call in calls_with_volume:
            dte = (call['expiry'] - get_eastern_now()).days
            delta = call.get('delta', 0)
            is_itm = call['strike'] < stock_price
            is_long_term = dte >= min_long_dte
            is_delta_ok = min_long_delta <= delta <= max_long_delta
            
            if is_itm and is_long_term and is_delta_ok:
                call['dte'] = dte
                long_call_candidates.append(call)
        tracker.add_step('Long Call Filter', f'ITM, DTE ≥ {min_long_dte}, Delta {min_long_delta} to {max_long_delta}', len(calls_with_volume), len(long_call_candidates))
        
        # Step 4: Separate Short Call candidates (OTM, short-term)
        short_call_candidates = []
        for call in calls_with_volume:
            dte = (call['expiry'] - get_eastern_now()).days
            delta = call.get('delta', 0)
            is_short_term = min_short_dte <= dte <= max_short_dte
            is_delta_ok = min_short_delta <= delta <= max_short_delta
            
            if is_short_term and is_delta_ok:
                call['dte'] = dte
                short_call_candidates.append(call)
        tracker.add_step('Short Call Filter', f'DTE {min_short_dte}-{max_short_dte}, Delta {min_short_delta} to {max_short_delta}', len(calls_with_volume), len(short_call_candidates))
        
        # Step 5: Generate all valid combinations
        potential_combinations = len(long_call_candidates) * len(short_call_candidates)
        valid_combinations = []
        
        for long_call in long_call_candidates:
            for short_call in short_call_candidates:
                # Short strike must be higher than long strike
                if short_call['strike'] > long_call['strike']:
                    # Short expiry must be before long expiry
                    if short_call['expiry'] < long_call['expiry']:
                        valid_combinations.append({
                            'long_call': long_call,
                            'short_call': short_call
                        })
        tracker.add_step('Strike/Expiry Validation', 'Short strike > Long strike, Short expiry < Long expiry', potential_combinations, len(valid_combinations))
        
        # Step 6: Filter by minimum credit
        credit_filtered = []
        for combo in valid_combinations:
            if combo['short_call']['premium'] >= min_credit:
                credit_filtered.append(combo)
        tracker.add_step('Credit Filter', f'Short call premium ≥ ${min_credit}', len(valid_combinations), len(credit_filtered))
        
        # Step 7: Calculate metrics and filter profitable opportunities
        pmcc_opportunities = []
        for combo in credit_filtered:
            long_call = combo['long_call']
            short_call = combo['short_call']
            
            long_strike = long_call['strike']
            short_strike = short_call['strike']
            long_premium = long_call['premium']
            short_premium = short_call['premium']
            long_delta = long_call.get('delta', 0)
            short_delta = short_call.get('delta', 0)
            long_dte = long_call['dte']
            short_dte = short_call['dte']
            
            # Calculate position metrics
            net_debit = long_premium - short_premium
            max_profit = (short_strike - long_strike) - net_debit
            max_loss = net_debit
            
            if max_profit <= 0:
                continue
            
            # Calculate return metrics
            roi = (max_profit / net_debit) * 100 if net_debit > 0 else 0
            risk_reward = abs(max_profit / max_loss) if max_loss != 0 else 0
            
            # Breakeven
            breakeven = long_strike + net_debit
            
            # Calculate normalized score components (0-100 scale)
            roi_score = min(roi / 100.0, 1.0) * 100  # Cap ROI at 100%
            risk_reward_score = min(risk_reward / 3.0, 1.0) * 100  # Cap at 3:1
            premium_score = min(short_premium / 5.0, 1.0) * 100  # Cap at $5
            long_delta_score = (1 - abs(long_delta - 0.80)) * 100  # Target 0.80 delta
            short_delta_score = (1 - abs(short_delta - 0.30)) * 100  # Target 0.30 delta
            
            # Use configurable weights from filter_criteria
            w_roi = filter_criteria.get('weight_roi', 0.25)
            w_rr = filter_criteria.get('weight_risk_reward', 0.20)
            w_premium = filter_criteria.get('weight_premium', 0.15)
            w_long_delta = filter_criteria.get('weight_long_delta', 0.20)
            w_short_delta = filter_criteria.get('weight_short_delta', 0.20)
            
            score = (
                roi_score * w_roi +
                risk_reward_score * w_rr +
                premium_score * w_premium +
                long_delta_score * w_long_delta +
                short_delta_score * w_short_delta
            )
            
            legs_data = [
                {
                    'type': 'call',
                    'position': 'long',
                    'strike': long_strike,
                    'expiry': long_call['expiry'].isoformat(),
                    'premium': long_premium,
                    'delta': long_delta,
                    'volume': long_call['volume'],
                    'dte': long_dte
                },
                {
                    'type': 'call',
                    'position': 'short',
                    'strike': short_strike,
                    'expiry': short_call['expiry'].isoformat(),
                    'premium': short_premium,
                    'delta': short_delta,
                    'volume': short_call['volume'],
                    'dte': short_dte
                }
            ]
            
            opportunity = {
                'symbol': symbol,
                'stock_price': stock_price,
                'strategy_type': self.strategy_id,
                'position_data': legs_data,
                'legs': legs_data,
                'total_credit_debit': round(-net_debit, 2),
                'max_profit': round(max_profit, 2),
                'max_loss': round(max_loss, 2),
                'breakeven_price': round(breakeven, 2),
                'roc_pct': round(roi, 2),
                'annualized_roc_pct': round(roi * (365 / short_dte) if short_dte > 0 else 0, 2),
                'pop_pct': round((1 - short_delta) * 100, 2),
                'expiry_date': short_call['expiry'].isoformat(),
                'days_to_expiry': short_dte,
                'metrics': {
                    'net_debit': round(net_debit, 2),
                    'max_profit': round(max_profit, 2),
                    'max_loss': round(max_loss, 2),
                    'breakeven': round(breakeven, 2),
                    'roi': round(roi, 2),
                    'risk_reward': round(risk_reward, 2),
                    'prob_profit': round((1 - short_delta) * 100, 2)
                },
                'score': round(score, 2),
                'scan_timestamp': get_eastern_now().isoformat()
            }
            pmcc_opportunities.append(opportunity)
        
        tracker.add_step('Profitability Filter', 'Max profit > 0 (positive ROI)', len(credit_filtered), len(pmcc_opportunities))
        
        # Step 8: Sort and return top opportunities
        final_count = min(10, len(pmcc_opportunities)) if pmcc_opportunities else 0
        tracker.add_step('Final Selection', 'Top 10 opportunities by score', len(pmcc_opportunities), final_count)
        
        # Finalize and store pipeline data
        tracker.finalize(final_count)
        
        # Sort and return results
        if pmcc_opportunities:
            pmcc_opportunities.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n✅ Found {len(pmcc_opportunities)} PMCC opportunities")
            print(f"   Best score: {pmcc_opportunities[0]['score']:.2f}")
            print(f"   Returning top opportunities")
            return pmcc_opportunities[:10]
        else:
            print(f"\n❌ No PMCC opportunities found matching all criteria")
            return None
    
    def calculate_payoff(self, stock_prices: List[float], legs: List[Dict[str, Any]],
                        initial_cost: float) -> List[float]:
        """
        Calculate PMCC payoff at expiration.
        
        At expiration:
        - Long call: max(stock_price - long_strike, 0) - long_premium
        - Short call: -(max(stock_price - short_strike, 0) - short_premium)
        """
        payoffs = []
        
        long_leg = next(leg for leg in legs if leg['position'] == 'long')
        short_leg = next(leg for leg in legs if leg['position'] == 'short')
        
        long_strike = long_leg['strike']
        short_strike = short_leg['strike']
        
        for stock_price in stock_prices:
            # Long call payoff
            long_payoff = max(stock_price - long_strike, 0) - long_leg['premium']
            
            # Short call payoff (negative of intrinsic value minus premium received)
            short_payoff = -(max(stock_price - short_strike, 0) - short_leg['premium'])
            
            # Total payoff
            total_payoff = long_payoff + short_payoff
            payoffs.append(round(total_payoff, 2))
        
        return payoffs


# Test code
if __name__ == "__main__":
    print("PMCC Strategy Module")
    print("=" * 50)
    
    strategy = PMCCStrategy()
    info = strategy.get_strategy_info()
    
    print(f"Strategy: {info['display_name']}")
    print(f"ID: {info['strategy_id']}")
    print(f"Legs: {info['num_legs']}")
    print(f"Complexity: {info['complexity_level']}")
    print(f"Description: {info['description']}")
    
    # Test parameter validation
    test_params = {
        'long_strike': 90,
        'long_expiry': get_eastern_now() + timedelta(days=200),
        'short_strike': 105,
        'short_expiry': get_eastern_now() + timedelta(days=35),
        'stock_price': 100
    }
    
    is_valid, error = strategy.validate_parameters(test_params)
    print(f"\n✓ Parameter validation: {'PASS' if is_valid else 'FAIL'}")
    if error:
        print(f"  Error: {error}")
    
    # Test payoff calculation
    stock_prices = [80, 90, 100, 105, 110, 120]
    test_legs = [
        {'position': 'long', 'strike': 90, 'premium': 12.50},
        {'position': 'short', 'strike': 105, 'premium': 2.50}
    ]
    
    payoffs = strategy.calculate_payoff(stock_prices, test_legs, 10.00)
    print("\n✓ Payoff calculation test:")
    for price, payoff in zip(stock_prices, payoffs):
        print(f"  Stock @ ${price}: P/L = ${payoff}")
        
        