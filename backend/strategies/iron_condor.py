"""
Iron Condor Strategy - 4-leg credit strategy combining call and put spreads.

Structure:
- Sell Put (Lower Strike - OTM)
- Buy Put (Lowest Strike - Further OTM)
- Sell Call (Upper Strike - OTM)
- Buy Call (Highest Strike - Further OTM)

This is a neutral, income-generating strategy that profits from low volatility.
The iron condor combines a short put spread and a short call spread.

Key Characteristics:
- Net credit received upfront
- Defined maximum risk
- Defined maximum profit (net credit)
- Profits if stock stays between short strikes at expiration
- Benefits from time decay and decreasing volatility
- Two breakeven points (one on each side)

Best Used When:
- Expect stock to trade in narrow range
- IV is moderate to high (sell premium)
- Want defined risk with income
- Neutral market outlook
- Low volatility expected at expiration

Profit/Loss:
- Max Profit: Net credit received (if stock expires between short strikes)
- Max Loss: Width of wider spread - net credit
- Breakevens: Short strikes ± net credit
- Profit Zone: Between breakeven points
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


class IronCondorStrategy(BaseStrategy):
    """Iron Condor - 4-leg neutral credit strategy with defined risk."""
    
    def __init__(self):
        super().__init__(
            strategy_id='iron_condor',
            strategy_name='iron_condor',
            display_name='Iron Condor',
            description='Neutral credit strategy combining OTM put and call spreads. Profits from low volatility and time decay within a range.',
            num_legs=4,
            complexity_level='intermediate'
        )
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for Iron Condor strategy.
        
        Returns:
            Dictionary with default filter criteria
        """
        return {
            'min_dte': 30,
            'max_dte': 60,
            'short_put_delta_min': 0.15,
            'short_put_delta_max': 0.30,
            'short_call_delta_min': 0.15,
            'short_call_delta_max': 0.30,
            'put_spread_width_min': 3.0,  # Minimum width of put spread (% of stock price)
            'put_spread_width_max': 10.0,  # Maximum width of put spread (% of stock price)
            'call_spread_width_min': 3.0,  # Minimum width of call spread (% of stock price)
            'call_spread_width_max': 10.0,  # Maximum width of call spread (% of stock price)
            'min_credit': 0.50,  # Minimum net credit to receive (per share)
            'min_credit_to_risk_ratio': 0.25,  # Credit should be at least 25% of max risk
            'max_risk_per_contract': 500,  # Maximum risk per contract
            'min_volume': 10,
            'min_prob_profit': 0.45,  # Minimum 45% probability of profit
            'prefer_balanced': True,  # Prefer balanced wing widths
            # Scoring weights (must sum to 1.0)
            'weight_credit_to_risk': 0.30,
            'weight_pop': 0.30,
            'weight_credit_amount': 0.20,
            'weight_volume': 0.10,
            'weight_balanced': 0.10
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate strategy-specific parameters.
        
        Args:
            params: Dictionary of strategy parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Merge with defaults
        full_params = self.get_default_parameters()
        full_params.update(params)
        
        # Validate DTE range
        if full_params['min_dte'] < 0 or full_params['max_dte'] < full_params['min_dte']:
            return False, "Invalid DTE range"
        
        # Validate delta ranges
        if not (0 < full_params['short_put_delta_max'] <= 0.50):
            return False, "Short put delta max must be between 0 and 0.50"
        
        if not (0 < full_params['short_call_delta_max'] <= 0.50):
            return False, "Short call delta max must be between 0 and 0.50"
        
        # Validate spread widths
        if full_params['put_spread_width_min'] <= 0 or full_params['put_spread_width_max'] <= full_params['put_spread_width_min']:
            return False, "Invalid put spread width range"
        
        if full_params['call_spread_width_min'] <= 0 or full_params['call_spread_width_max'] <= full_params['call_spread_width_min']:
            return False, "Invalid call spread width range"
        
        # Validate credit requirements
        if full_params['min_credit'] < 0:
            return False, "Minimum credit must be non-negative"
        
        if not (0 <= full_params['min_credit_to_risk_ratio'] <= 1.0):
            return False, "Credit to risk ratio must be between 0 and 1"
        
        # Validate probability
        if not (0 <= full_params['min_prob_profit'] <= 1.0):
            return False, "Probability of profit must be between 0 and 1"
        
        # Validate scoring weights sum to 1.0
        weight_sum = (full_params['weight_credit_to_risk'] + 
                     full_params['weight_pop'] + 
                     full_params['weight_credit_amount'] +
                     full_params['weight_volume'] +
                     full_params['weight_balanced'])
        
        if not (0.99 <= weight_sum <= 1.01):
            return False, f"Scoring weights must sum to 1.0 (currently {weight_sum:.2f})"
        
        return True, None
    
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], 
             api_key: str, session=None) -> Optional[List[Dict[str, Any]]]:
        """
        Scan for Iron Condor opportunities.
        
        The scan finds combinations of OTM put spreads and call spreads that:
        1. Are in the same expiration
        2. Have appropriate deltas (15-30 delta for short strikes)
        3. Generate sufficient credit
        4. Have acceptable risk/reward ratio
        5. Meet probability requirements
        
        Args:
            symbol: Stock ticker symbol
            filter_criteria: Dictionary of filter parameters
            api_key: Alpha Vantage API key
            session: Optional requests.Session for connection reuse
            
        Returns:
            List of Iron Condor opportunities (sorted by score) or None if none found
        """
        # Merge filter criteria with defaults
        params = self.get_default_parameters()
        params.update(filter_criteria)
        
        # Validate parameters
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            print(f"❌ Invalid parameters: {error_msg}")
            return None
        
        # Step 1: Fetch market data
        print(f"\n🔍 Scanning Iron Condor opportunities for {symbol}")
        print(f"   DTE range: {params['min_dte']}-{params['max_dte']} days")
        print(f"   Short delta range: {params['short_put_delta_min']:.2f}-{params['short_put_delta_max']:.2f}")
        
        stock_price = get_stock_price(symbol, api_key, session)
        if not stock_price:
            return None
        
        # Initialize pipeline tracker after we have stock_price
        tracker = PipelineTracker(
            symbol=symbol,
            stock_price=stock_price,
            strategy_name=self.strategy_id,
            strategy_display_name=self.display_name,
            filter_criteria=params
        )
        
        options_data = get_options_data(symbol, api_key, session)
        if not options_data:
            tracker.finalize(0)
            return []
        
        risk_free_rate = get_risk_free_rate(api_key, session)
        avg_iv = compute_avg_iv(options_data)
        
        # Step 2: Parse options chain
        options_chain = parse_options_chain(options_data)
        if not options_chain:
            tracker.finalize(0)
            return []
        
        # Count total raw options from API
        total_raw_options = sum(len(opts) for opts in options_chain.values())
        total_expirations = len(options_chain)
        
        tracker.add_step('Market Data', f'Retrieved {total_raw_options} options contracts', total_raw_options, total_raw_options)
        tracker.add_step('Parse Options', f'Grouped into {total_expirations} expirations', total_raw_options, total_expirations)
        
        # Step 3: Filter by expiration (DTE range)
        valid_expirations = []
        now = get_eastern_now()
        
        for expiry, opts in options_chain.items():
            dte = (expiry - now).days
            if params['min_dte'] <= dte <= params['max_dte']:
                valid_expirations.append((expiry, opts, dte))
        
        tracker.add_step('DTE Filter', f"{params['min_dte']}-{params['max_dte']} days", total_expirations, len(valid_expirations))
        
        if not valid_expirations:
            tracker.finalize(0)
            return []
        
        # Step 4: Find Iron Condor combinations
        condor_candidates = []
        
        for expiry, opts, dte in valid_expirations:
            # Separate calls and puts
            calls = [o for o in opts if o['type'] == 'CALL']
            puts = [o for o in opts if o['type'] == 'PUT']
            
            # Filter by volume
            calls = [c for c in calls if c['volume'] >= params['min_volume']]
            puts = [p for p in puts if p['volume'] >= params['min_volume']]
            
            # Find put spread candidates (sell higher strike, buy lower strike)
            put_spreads = []
            for i, short_put in enumerate(puts):
                # Short put should be OTM with delta in range
                if not (params['short_put_delta_min'] <= abs(short_put['delta']) <= params['short_put_delta_max']):
                    continue
                if short_put['strike'] >= stock_price:  # Must be OTM
                    continue
                
                # Find long put (lower strike, further OTM)
                for long_put in puts[i+1:]:
                    if long_put['strike'] >= short_put['strike']:
                        continue
                    
                    spread_width_pct = (short_put['strike'] - long_put['strike']) / stock_price * 100
                    if params['put_spread_width_min'] <= spread_width_pct <= params['put_spread_width_max']:
                        put_credit = short_put['premium'] - long_put['premium']
                        if put_credit > 0:  # Must be credit
                            put_spreads.append({
                                'short_put': short_put,
                                'long_put': long_put,
                                'credit': put_credit,
                                'width': short_put['strike'] - long_put['strike'],
                                'width_pct': spread_width_pct
                            })
            
            # Find call spread candidates (sell lower strike, buy higher strike)
            call_spreads = []
            for i, short_call in enumerate(calls):
                # Short call should be OTM with delta in range
                if not (params['short_call_delta_min'] <= abs(short_call['delta']) <= params['short_call_delta_max']):
                    continue
                if short_call['strike'] <= stock_price:  # Must be OTM
                    continue
                
                # Find long call (higher strike, further OTM)
                for long_call in calls:
                    if long_call['strike'] <= short_call['strike']:
                        continue
                    
                    spread_width_pct = (long_call['strike'] - short_call['strike']) / stock_price * 100
                    if params['call_spread_width_min'] <= spread_width_pct <= params['call_spread_width_max']:
                        call_credit = short_call['premium'] - long_call['premium']
                        if call_credit > 0:  # Must be credit
                            call_spreads.append({
                                'short_call': short_call,
                                'long_call': long_call,
                                'credit': call_credit,
                                'width': long_call['strike'] - short_call['strike'],
                                'width_pct': spread_width_pct
                            })
            
            # Combine put spreads with call spreads to form iron condors
            for ps in put_spreads:
                for cs in call_spreads:
                    # Ensure short strikes don't overlap
                    if ps['short_put']['strike'] >= cs['short_call']['strike']:
                        continue
                    
                    total_credit = ps['credit'] + cs['credit']
                    max_risk = max(ps['width'], cs['width'])
                    credit_to_risk = total_credit / max_risk if max_risk > 0 else 0
                    
                    # Filter by credit requirements
                    if total_credit < params['min_credit']:
                        continue
                    if credit_to_risk < params['min_credit_to_risk_ratio']:
                        continue
                    if max_risk * 100 > params['max_risk_per_contract']:  # Convert to dollars per contract
                        continue
                    
                    condor_candidates.append({
                        'expiry': expiry,
                        'dte': dte,
                        'put_spread': ps,
                        'call_spread': cs,
                        'total_credit': total_credit,
                        'max_risk': max_risk,
                        'credit_to_risk': credit_to_risk
                    })
        
        tracker.add_step(
            'Spread Combination', 
            'Find valid put and call spreads: (1) OTM put spreads (sell higher, buy lower) with deltas and widths in range, (2) OTM call spreads (sell lower, buy higher) with deltas and widths in range, (3) Combine non-overlapping spreads meeting credit and risk requirements', 
            len(valid_expirations), 
            len(condor_candidates)
        )
        
        if not condor_candidates:
            tracker.finalize(0)
            return []
        
        # Step 5: Calculate probability of profit
        prob_filtered = []
        
        for candidate in condor_candidates:
            # Get time to expiry for this candidate's expiration
            time_to_expiry = candidate['dte'] / 365.0
            
            # Breakeven points
            lower_breakeven = candidate['put_spread']['short_put']['strike'] - candidate['total_credit']
            upper_breakeven = candidate['call_spread']['short_call']['strike'] + candidate['total_credit']
            
            # Probability of staying between breakevens
            pop = prob_in_range(lower_breakeven, upper_breakeven, stock_price, avg_iv, risk_free_rate, time_to_expiry)
            
            if pop >= params['min_prob_profit']:
                candidate['pop'] = pop
                candidate['lower_breakeven'] = lower_breakeven
                candidate['upper_breakeven'] = upper_breakeven
                prob_filtered.append(candidate)
        
        tracker.add_step('Probability Filter', f"POP >= {params['min_prob_profit']*100:.0f}%", len(condor_candidates), len(prob_filtered))
        
        if not prob_filtered:
            tracker.finalize(0)
            return []
        
        # Step 6: Score and rank opportunities
        iron_condor_opportunities = []
        
        for candidate in prob_filtered:
            ps = candidate['put_spread']
            cs = candidate['call_spread']
            
            # Calculate volume score (min of all legs)
            min_volume = min(
                ps['short_put']['volume'],
                ps['long_put']['volume'],
                cs['short_call']['volume'],
                cs['long_call']['volume']
            )
            volume_score = min(min_volume / 100, 1.0)  # Normalize to 0-1
            
            # Calculate balanced score (prefer similar put and call spread widths)
            width_diff = abs(ps['width_pct'] - cs['width_pct'])
            balanced_score = max(0, 1 - (width_diff / 10))  # Penalty for >10% difference
            
            # Calculate total score
            score = (
                params['weight_credit_to_risk'] * (candidate['credit_to_risk'] * 100) +
                params['weight_pop'] * (candidate['pop'] * 100) +
                params['weight_credit_amount'] * (candidate['total_credit'] * 10) +
                params['weight_volume'] * (volume_score * 100) +
                params['weight_balanced'] * (balanced_score * 100)
            )
            
            # Build legs data
            legs_data = [
                {
                    'type': 'put',
                    'position': 'short',
                    'strike': ps['short_put']['strike'],
                    'expiry': candidate['expiry'].isoformat(),
                    'premium': ps['short_put']['premium'],
                    'delta': ps['short_put']['delta'],
                    'volume': ps['short_put']['volume'],
                    'dte': candidate['dte']
                },
                {
                    'type': 'put',
                    'position': 'long',
                    'strike': ps['long_put']['strike'],
                    'expiry': candidate['expiry'].isoformat(),
                    'premium': ps['long_put']['premium'],
                    'delta': ps['long_put']['delta'],
                    'volume': ps['long_put']['volume'],
                    'dte': candidate['dte']
                },
                {
                    'type': 'call',
                    'position': 'short',
                    'strike': cs['short_call']['strike'],
                    'expiry': candidate['expiry'].isoformat(),
                    'premium': cs['short_call']['premium'],
                    'delta': cs['short_call']['delta'],
                    'volume': cs['short_call']['volume'],
                    'dte': candidate['dte']
                },
                {
                    'type': 'call',
                    'position': 'long',
                    'strike': cs['long_call']['strike'],
                    'expiry': candidate['expiry'].isoformat(),
                    'premium': cs['long_call']['premium'],
                    'delta': cs['long_call']['delta'],
                    'volume': cs['long_call']['volume'],
                    'dte': candidate['dte']
                }
            ]
            
            # ROI calculation
            roi = (candidate['total_credit'] / candidate['max_risk'] * 100) if candidate['max_risk'] > 0 else 0
            annualized_roi = roi * (365 / candidate['dte']) if candidate['dte'] > 0 else 0
            
            opportunity = {
                'symbol': symbol,
                'stock_price': stock_price,
                'strategy_type': self.strategy_id,
                'position_data': legs_data,
                'legs': legs_data,
                'total_credit_debit': round(candidate['total_credit'], 2),
                'max_profit': round(candidate['total_credit'], 2),
                'max_loss': round(candidate['max_risk'] - candidate['total_credit'], 2),
                'breakeven_price': round((candidate['lower_breakeven'] + candidate['upper_breakeven']) / 2, 2),
                'roc_pct': round(roi, 2),
                'annualized_roc_pct': round(annualized_roi, 2),
                'pop_pct': round(candidate['pop'] * 100, 2),
                'expiry_date': candidate['expiry'].isoformat(),
                'days_to_expiry': candidate['dte'],
                'metrics': {
                    'net_credit': round(candidate['total_credit'], 2),
                    'max_profit': round(candidate['total_credit'], 2),
                    'max_risk': round(candidate['max_risk'], 2),
                    'max_loss': round(candidate['max_risk'] - candidate['total_credit'], 2),
                    'lower_breakeven': round(candidate['lower_breakeven'], 2),
                    'upper_breakeven': round(candidate['upper_breakeven'], 2),
                    'profit_range_width': round(candidate['upper_breakeven'] - candidate['lower_breakeven'], 2),
                    'credit_to_risk': round(candidate['credit_to_risk'], 3),
                    'roi': round(roi, 2),
                    'annualized_roi': round(annualized_roi, 2),
                    'prob_profit': round(candidate['pop'] * 100, 2),
                    'put_spread_width': round(ps['width'], 2),
                    'call_spread_width': round(cs['width'], 2),
                    'min_volume': min_volume
                },
                'score': round(score, 2),
                'scan_timestamp': get_eastern_now().isoformat()
            }
            
            iron_condor_opportunities.append(opportunity)
        
        tracker.add_step('Scoring', 'Calculate and rank opportunities', len(prob_filtered), len(iron_condor_opportunities))
        
        # Sort and return top opportunities
        iron_condor_opportunities.sort(key=lambda x: x['score'], reverse=True)
        final_count = min(10, len(iron_condor_opportunities))
        tracker.finalize(final_count)
        
        if iron_condor_opportunities:
            print(f"\n✅ Found {len(iron_condor_opportunities)} Iron Condor opportunities")
            print(f"   Best score: {iron_condor_opportunities[0]['score']:.2f}")
            print(f"   Best credit/risk: {iron_condor_opportunities[0]['metrics']['credit_to_risk']:.3f}")
            return iron_condor_opportunities[:10]
        else:
            print(f"\n❌ No Iron Condor opportunities found")
            return []
    
    def calculate_payoff(self, stock_prices: List[float], legs: List[Dict[str, Any]],
                        initial_cost: float) -> List[float]:
        """
        Calculate Iron Condor payoff at expiration.
        
        At expiration:
        - Short put: -(max(short_put_strike - stock_price, 0) - premium)
        - Long put: max(long_put_strike - stock_price, 0) - premium
        - Short call: -(max(stock_price - short_call_strike, 0) - premium)
        - Long call: max(stock_price - long_call_strike, 0) - premium
        """
        payoffs = []
        
        # Identify legs
        short_put = next(leg for leg in legs if leg['type'] == 'put' and leg['position'] == 'short')
        long_put = next(leg for leg in legs if leg['type'] == 'put' and leg['position'] == 'long')
        short_call = next(leg for leg in legs if leg['type'] == 'call' and leg['position'] == 'short')
        long_call = next(leg for leg in legs if leg['type'] == 'call' and leg['position'] == 'long')
        
        for stock_price in stock_prices:
            # Put spread payoff
            short_put_payoff = -(max(short_put['strike'] - stock_price, 0) - short_put['premium'])
            long_put_payoff = max(long_put['strike'] - stock_price, 0) - long_put['premium']
            
            # Call spread payoff
            short_call_payoff = -(max(stock_price - short_call['strike'], 0) - short_call['premium'])
            long_call_payoff = max(stock_price - long_call['strike'], 0) - long_call['premium']
            
            # Total payoff
            total_payoff = short_put_payoff + long_put_payoff + short_call_payoff + long_call_payoff
            payoffs.append(round(total_payoff, 2))
        
        return payoffs


# Test code
if __name__ == "__main__":
    print("Iron Condor Strategy Module")
    print("=" * 50)
    
    strategy = IronCondorStrategy()
    print(f"Strategy: {strategy.display_name}")
    print(f"Complexity: {strategy.complexity_level}")
    print(f"Number of legs: {strategy.num_legs}")
    print(f"\nDefault Parameters:")
    for key, value in strategy.get_default_parameters().items():
        print(f"  {key}: {value}")
