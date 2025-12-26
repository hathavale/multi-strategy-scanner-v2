"""
Synthetic Long Strategy Implementation.

A Synthetic Long mimics owning 100 shares of stock using options:
- Buy at-the-money (ATM) call option
- Sell at-the-money (ATM) put option

This creates a position with similar P/L profile to owning stock but requires less capital.

Strategy Characteristics:
- Bullish directional bias
- 2 legs (long call + short put)
- Similar risk/reward to owning stock
- Unlimited profit potential, substantial downside risk
- Net credit or small debit depending on strikes
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
    validate_strike_price,
    validate_expiration_date,
    get_eastern_now
)
from utils.pipeline_tracker import PipelineTracker


class SyntheticLongStrategy(BaseStrategy):
    """
    Synthetic Long strategy implementation.
    
    Entry Criteria:
    - Long call: ATM (delta 0.45-0.55), same strike as short put
    - Short put: ATM (delta -0.45 to -0.55), same strike as long call
    - Same expiration date for both legs
    - Total delta close to 1.0 (mimics 100 shares)
    """
    
    def __init__(self):
        super().__init__(
            strategy_id='synthetic_long',
            strategy_name='synthetic_long',
            display_name='Synthetic Long',
            description='Long call + short put at same strike to mimic stock ownership',
            num_legs=2,
            complexity_level='beginner'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for Synthetic Long strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_dte': 30,
            'max_dte': 90,
            'max_strike_distance': 0.05,
            'min_volume': 10,
            'min_delta': 0.90,
            'max_cost': 2.00,
            # Scoring weights (must sum to 1.0)
            'weight_cost': 0.30,
            'weight_delta': 0.35,
            'weight_strike_proximity': 0.20,
            'weight_volume': 0.15
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate Synthetic Long parameters.
        
        Expected params:
        - strike: Strike price for both options
        - expiry: Expiration date for both options
        - stock_price: Current stock price
        """
        required_fields = ['strike', 'expiry', 'stock_price']
        
        # Check required fields
        for field in required_fields:
            if field not in params:
                return False, f"Missing required parameter: {field}"
        
        # Validate strike
        if not validate_strike_price(params['strike'], params['stock_price']):
            return False, "Invalid strike price"
        
        # Validate expiration date
        if not validate_expiration_date(params['expiry']):
            return False, "Expiration date must be in the future"
        
        # Strike should be close to stock price (within 10%)
        strike_ratio = params['strike'] / params['stock_price']
        if not (0.90 <= strike_ratio <= 1.10):
            return False, "Strike should be at or near the money (within 10% of stock price)"
        
        return True, None
    
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], 
             api_key: str, session: Any) -> Optional[Dict[str, Any]]:
        """
        Scan for Synthetic Long opportunities with pipeline tracking.
        
        Filter criteria:
        - min_dte: Minimum days to expiry (default: 30)
        - max_dte: Maximum days to expiry (default: 90)
        - max_strike_distance: Max distance from ATM in % (default: 5%)
        - min_volume: Minimum option volume (default: 10)
        - min_delta: Minimum combined delta (default: 0.90)
        - max_cost: Maximum net cost (default: 2.00, prefer credit or small debit)
        """
        # Set default filter values
        min_dte = filter_criteria.get('min_dte', 30)
        max_dte = filter_criteria.get('max_dte', 90)
        max_strike_distance = filter_criteria.get('max_strike_distance', 0.05)  # 5%
        min_volume = filter_criteria.get('min_volume', 10)
        min_delta = filter_criteria.get('min_delta', 0.90)
        max_cost = filter_criteria.get('max_cost', 2.00)
        
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
        
        # Count total options
        total_options = sum(len(opts) for opts in options_by_expiry.values())
        tracker.add_step('Raw Options', f'Total options fetched for {symbol}', total_options, total_options)
        
        # Step 1: Filter by DTE
        dte_filtered = []
        for expiry, options in options_by_expiry.items():
            dte = (expiry - get_eastern_now()).days
            if min_dte <= dte <= max_dte:
                for opt in options:
                    opt['expiry'] = expiry
                    opt['dte'] = dte
                    dte_filtered.append(opt)
        tracker.add_step('DTE Filter', f'Days to expiry {min_dte}-{max_dte}', total_options, len(dte_filtered))
        
        # Step 2: Group options by strike and filter pairs with both call and put
        strikes_by_expiry = {}
        for opt in dte_filtered:
            key = (opt['expiry'], opt['strike'])
            if key not in strikes_by_expiry:
                strikes_by_expiry[key] = {'call': None, 'put': None, 'expiry': opt['expiry'], 'strike': opt['strike'], 'dte': opt['dte']}
            if opt['type'] == 'CALL':
                strikes_by_expiry[key]['call'] = opt
            else:
                strikes_by_expiry[key]['put'] = opt
        
        pairs = [v for v in strikes_by_expiry.values() if v['call'] and v['put']]
        tracker.add_step('Call/Put Pairs', 'Strikes with both call and put options', len(dte_filtered), len(pairs))
        
        # Step 3: Filter by ATM proximity
        atm_pairs = [p for p in pairs if abs(p['strike'] - stock_price) / stock_price <= max_strike_distance]
        tracker.add_step('ATM Filter', f'Strike within {max_strike_distance*100}% of stock price', len(pairs), len(atm_pairs))
        
        # Step 4: Filter by volume
        volume_filtered = [p for p in atm_pairs if p['call']['volume'] >= min_volume and p['put']['volume'] >= min_volume]
        tracker.add_step('Volume Filter', f'Minimum volume ≥ {min_volume}', len(atm_pairs), len(volume_filtered))
        
        # Step 5: Filter by delta (ATM options)
        delta_filtered = []
        for p in volume_filtered:
            call_delta = p['call'].get('delta', 0)
            put_delta = p['put'].get('delta', 0)
            if 0.35 <= call_delta <= 0.65 and -0.65 <= put_delta <= -0.35:
                delta_filtered.append(p)
        tracker.add_step('Delta Filter', 'ATM delta range (0.35-0.65)', len(volume_filtered), len(delta_filtered))
        
        # Step 6: Filter by cost and combined delta
        synthetic_opportunities = []
        for p in delta_filtered:
            call_premium = p['call']['premium']
            put_premium = p['put']['premium']
            call_delta = p['call'].get('delta', 0)
            put_delta = p['put'].get('delta', 0)
            
            net_cost = call_premium - put_premium
            if net_cost > max_cost:
                continue
            
            combined_delta = call_delta - put_delta
            if combined_delta < min_delta:
                continue
            
            strike = p['strike']
            expiry = p['expiry']
            dte = p['dte']
            strike_distance = abs(strike - stock_price) / stock_price
            
            breakeven = strike + net_cost
            
            # Calculate normalized score components (0-100 scale)
            cost_score = min((max_cost - net_cost) / max_cost, 1.0) * 100 if max_cost > 0 else 100
            delta_score = min(combined_delta / 1.0, 1.0) * 100  # Target delta of 1.0
            strike_proximity_score = (1 - strike_distance) * 100
            volume_score = min(min(p['call']['volume'], p['put']['volume']) / 500, 1.0) * 100
            
            # Use configurable weights from filter_criteria
            w_cost = filter_criteria.get('weight_cost', 0.30)
            w_delta = filter_criteria.get('weight_delta', 0.35)
            w_strike = filter_criteria.get('weight_strike_proximity', 0.20)
            w_volume = filter_criteria.get('weight_volume', 0.15)
            
            score = (
                cost_score * w_cost +
                delta_score * w_delta +
                strike_proximity_score * w_strike +
                volume_score * w_volume
            )
            
            max_profit_value = 999999
            max_loss_value = strike + net_cost
            roi_estimate = ((strike * 0.10) / max(net_cost, 0.01)) * 100 if net_cost > 0 else 0
            
            legs_data = [
                {'type': 'call', 'position': 'long', 'strike': strike, 'expiry': expiry.isoformat(),
                 'premium': call_premium, 'delta': call_delta, 'volume': p['call']['volume'], 'dte': dte},
                {'type': 'put', 'position': 'short', 'strike': strike, 'expiry': expiry.isoformat(),
                 'premium': put_premium, 'delta': put_delta, 'volume': p['put']['volume'], 'dte': dte}
            ]
            
            opportunity = {
                'symbol': symbol, 'stock_price': stock_price, 'strategy_type': self.strategy_id,
                'position_data': legs_data, 'legs': legs_data,
                'total_credit_debit': round(-net_cost, 2), 'max_profit': max_profit_value,
                'max_loss': round(max_loss_value, 2), 'breakeven_price': round(breakeven, 2),
                'roc_pct': round(roi_estimate, 2),
                'annualized_roc_pct': round(roi_estimate * (365 / dte) if dte > 0 else 0, 2),
                'pop_pct': 50.0, 'expiry_date': expiry.isoformat(), 'days_to_expiry': dte,
                'metrics': {
                    'net_cost': round(net_cost, 2), 'net_debit': round(net_cost, 2),
                    'max_profit': max_profit_value, 'max_loss': round(max_loss_value, 2),
                    'breakeven': round(breakeven, 2), 'combined_delta': round(combined_delta, 2),
                    'roi': round(roi_estimate, 2), 'risk_reward': 999, 'prob_profit': 50.0
                },
                'score': round(score, 2), 'scan_timestamp': get_eastern_now().isoformat()
            }
            synthetic_opportunities.append(opportunity)
        
        tracker.add_step('Cost/Delta Filter', f'Net cost ≤ ${max_cost}, combined delta ≥ {min_delta}', len(delta_filtered), len(synthetic_opportunities))
        
        # Final selection
        final_count = min(10, len(synthetic_opportunities)) if synthetic_opportunities else 0
        tracker.add_step('Final Selection', 'Top 10 opportunities by score', len(synthetic_opportunities), final_count)
        
        # Finalize pipeline
        tracker.finalize(final_count)
        
        if synthetic_opportunities:
            synthetic_opportunities.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n✅ Found {len(synthetic_opportunities)} Synthetic Long opportunities")
            return synthetic_opportunities[:10]
        else:
            print(f"\n❌ No Synthetic Long opportunities found matching all criteria")
            return None
    
    def calculate_payoff(self, stock_prices: List[float], legs: List[Dict[str, Any]],
                        initial_cost: float) -> List[float]:
        """
        Calculate Synthetic Long payoff at expiration.
        
        At expiration:
        - Long call: max(stock_price - strike, 0) - call_premium
        - Short put: -(max(strike - stock_price, 0) - put_premium)
        
        Combined payoff moves 1:1 with stock price above/below strike.
        """
        payoffs = []
        
        call_leg = next(leg for leg in legs if leg['type'] == 'call')
        put_leg = next(leg for leg in legs if leg['type'] == 'put')
        
        strike = call_leg['strike']  # Same strike for both
        
        for stock_price in stock_prices:
            # Long call payoff
            call_payoff = max(stock_price - strike, 0) - call_leg['premium']
            
            # Short put payoff
            put_payoff = -(max(strike - stock_price, 0) - put_leg['premium'])
            
            # Total payoff
            total_payoff = call_payoff + put_payoff
            payoffs.append(round(total_payoff, 2))
        
        return payoffs


# Test code
if __name__ == "__main__":
    print("Synthetic Long Strategy Module")
    print("=" * 50)
    
    strategy = SyntheticLongStrategy()
    info = strategy.get_strategy_info()
    
    print(f"Strategy: {info['display_name']}")
    print(f"ID: {info['strategy_id']}")
    print(f"Legs: {info['num_legs']}")
    print(f"Complexity: {info['complexity_level']}")
    print(f"Description: {info['description']}")
    
    # Test parameter validation
    test_params = {
        'strike': 100,
        'expiry': get_eastern_now() + timedelta(days=45),
        'stock_price': 100
    }
    
    is_valid, error = strategy.validate_parameters(test_params)
    print(f"\n✓ Parameter validation: {'PASS' if is_valid else 'FAIL'}")
    if error:
        print(f"  Error: {error}")
    
    # Test payoff calculation (should be linear like owning stock)
    stock_prices = [80, 90, 100, 110, 120]
    test_legs = [
        {'type': 'call', 'position': 'long', 'strike': 100, 'premium': 3.00},
        {'type': 'put', 'position': 'short', 'strike': 100, 'premium': 2.80}
    ]
    
    payoffs = strategy.calculate_payoff(stock_prices, test_legs, 0.20)
    print("\n✓ Payoff calculation test (should be linear):")
    for price, payoff in zip(stock_prices, payoffs):
        print(f"  Stock @ ${price}: P/L = ${payoff}")
