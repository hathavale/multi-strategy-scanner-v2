"""
Base Strategy Class - Abstract interface for all options strategies.

All strategy implementations must inherit from this base class and implement
the required abstract methods. This ensures consistent interface across all
strategies for validation, scanning, and payoff calculations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.calculations import (
    get_stock_price,
    get_risk_free_rate,
    get_options_data,
    compute_avg_iv,
    prob_in_range,
    parse_options_chain,
    validate_strike_price,
    validate_expiration_date,
    validate_option_type,
    get_eastern_now
)


class BaseStrategy(ABC):
    """
    Abstract base class for all options strategies.
    
    Attributes:
        strategy_id (str): Unique identifier for the strategy
        strategy_name (str): Internal name for the strategy
        display_name (str): User-friendly display name
        description (str): Strategy description
        num_legs (int): Number of option legs in the strategy
        complexity_level (str): Complexity rating (beginner/intermediate/advanced)
    """
    
    def __init__(self, strategy_id: str, strategy_name: str, display_name: str,
                 description: str, num_legs: int, complexity_level: str = "intermediate"):
        """
        Initialize base strategy.
        
        Args:
            strategy_id: Unique identifier (e.g., 'pmcc')
            strategy_name: Internal name (e.g., 'pmcc')
            display_name: Display name (e.g., 'PMCC - Poor Man\'s Covered Call')
            description: Strategy description
            num_legs: Number of option legs
            complexity_level: Complexity rating
        """
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.display_name = display_name
        self.description = description
        self.num_legs = num_legs
        self.complexity_level = complexity_level
    
    @abstractmethod
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate strategy-specific parameters.
        
        Args:
            params: Dictionary containing strategy parameters
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if parameters are valid, False otherwise
            - error_message: None if valid, error description if invalid
        """
        pass
    
    @abstractmethod
    def scan(self, symbol: str, filter_criteria: Dict[str, Any], 
             api_key: str, session: Any) -> Optional[Dict[str, Any]]:
        """
        Scan for opportunities using this strategy.
        
        Args:
            symbol: Stock symbol to scan
            filter_criteria: Filter parameters (min/max values, ranges, etc.)
            api_key: Alpha Vantage API key
            session: Requests session for API calls
            
        Returns:
            Dictionary with scan results if opportunity found, None otherwise
            Result format:
            {
                'symbol': str,
                'stock_price': float,
                'strategy_id': str,
                'legs': List[Dict],  # Each leg with strike, expiry, type, price, delta, etc.
                'metrics': Dict,     # Max profit, max loss, breakeven, prob_profit, etc.
                'score': float,      # Overall strategy score/ranking
                'scan_timestamp': datetime
            }
        """
        pass
    
    @abstractmethod
    def calculate_payoff(self, stock_prices: List[float], legs: List[Dict[str, Any]],
                        initial_cost: float) -> List[float]:
        """
        Calculate payoff diagram values at expiration.
        
        Args:
            stock_prices: List of stock prices to calculate payoff for
            legs: List of option legs with strike, type, premium, quantity
            initial_cost: Net debit/credit for entering the position
            
        Returns:
            List of profit/loss values corresponding to each stock price
        """
        pass
    
    def calculate_breakeven(self, legs: List[Dict[str, Any]], 
                          initial_cost: float) -> List[float]:
        """
        Calculate breakeven points for the strategy.
        
        Args:
            legs: List of option legs
            initial_cost: Net debit/credit
            
        Returns:
            List of breakeven stock prices
        """
        # Default implementation - can be overridden by specific strategies
        # Find zero-crossings in payoff diagram
        stock_prices = []
        min_strike = min(leg['strike'] for leg in legs)
        max_strike = max(leg['strike'] for leg in legs)
        
        # Generate price range around strikes
        price_range = [
            min_strike - 20 + i for i in range(int(max_strike - min_strike + 40))
        ]
        
        payoffs = self.calculate_payoff(price_range, legs, initial_cost)
        
        breakevens = []
        for i in range(len(payoffs) - 1):
            # Check for sign change (zero crossing)
            if payoffs[i] * payoffs[i + 1] < 0:
                # Linear interpolation to find exact breakeven
                breakeven = price_range[i] + (price_range[i + 1] - price_range[i]) * \
                           abs(payoffs[i]) / (abs(payoffs[i]) + abs(payoffs[i + 1]))
                breakevens.append(round(breakeven, 2))
        
        return breakevens
    
    def calculate_max_profit(self, legs: List[Dict[str, Any]], 
                           initial_cost: float) -> float:
        """
        Calculate maximum profit for the strategy.
        
        Args:
            legs: List of option legs
            initial_cost: Net debit/credit
            
        Returns:
            Maximum profit (may be unlimited for some strategies)
        """
        # Default implementation - can be overridden
        min_strike = min(leg['strike'] for leg in legs)
        max_strike = max(leg['strike'] for leg in legs)
        
        # Check payoff at key points
        test_prices = [0, min_strike, max_strike, max_strike * 2]
        payoffs = self.calculate_payoff(test_prices, legs, initial_cost)
        
        max_profit = max(payoffs)
        return round(max_profit, 2)
    
    def calculate_max_loss(self, legs: List[Dict[str, Any]], 
                         initial_cost: float) -> float:
        """
        Calculate maximum loss for the strategy.
        
        Args:
            legs: List of option legs
            initial_cost: Net debit/credit
            
        Returns:
            Maximum loss (negative value)
        """
        # Default implementation - can be overridden
        min_strike = min(leg['strike'] for leg in legs)
        max_strike = max(leg['strike'] for leg in legs)
        
        # Check payoff at key points
        test_prices = [0, min_strike, max_strike, max_strike * 2]
        payoffs = self.calculate_payoff(test_prices, legs, initial_cost)
        
        max_loss = min(payoffs)
        return round(max_loss, 2)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get strategy metadata.
        
        Returns:
            Dictionary with strategy information
        """
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'display_name': self.display_name,
            'description': self.description,
            'num_legs': self.num_legs,
            'complexity_level': self.complexity_level
        }
    
    def get_current_price(self, symbol: str, api_key: str, session: Any) -> Optional[float]:
        """
        Get current stock price for a symbol.
        
        Args:
            symbol: Stock symbol
            api_key: Alpha Vantage API key
            session: Requests session for API calls
            
        Returns:
            Current stock price or None if unavailable
        """
        try:
            return get_stock_price(symbol, api_key, session)
        except Exception:
            return None
    
    def recalculate_metrics(self, legs: List[Dict[str, Any]], 
                           current_stock_price: float,
                           original_stock_price: float) -> Dict[str, Any]:
        """
        Recalculate strategy metrics based on current stock price.
        
        Args:
            legs: List of option legs with strike, type, premium, quantity
            current_stock_price: Current stock price
            original_stock_price: Original stock price when position was opened
            
        Returns:
            Dictionary with updated metrics
        """
        from datetime import datetime
        
        # Calculate net debit/credit from legs
        net_cost = 0
        for leg in legs:
            premium = leg.get('premium', 0)
            position = leg.get('position', 'long')
            quantity = leg.get('quantity', 1)
            
            if position == 'long':
                net_cost += premium * quantity * 100  # 100 shares per contract
            else:
                net_cost -= premium * quantity * 100
        
        # Calculate payoff at current price
        payoffs = self.calculate_payoff([current_stock_price], legs, net_cost)
        current_pnl = payoffs[0] if payoffs else 0
        
        # Calculate breakevens
        breakevens = self.calculate_breakeven(legs, net_cost)
        
        # Calculate max profit and loss
        max_profit = self.calculate_max_profit(legs, net_cost)
        max_loss = self.calculate_max_loss(legs, net_cost)
        
        # Calculate days to expiry for the earliest leg
        min_dte = None
        for leg in legs:
            expiry = leg.get('expiry')
            if expiry:
                try:
                    if isinstance(expiry, str):
                        expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
                    else:
                        expiry_date = expiry
                    dte = (expiry_date - get_eastern_now()).days
                    if min_dte is None or dte < min_dte:
                        min_dte = dte
                except:
                    pass
        
        # Calculate ROI
        roi = 0
        if abs(net_cost) > 0:
            roi = (max_profit / abs(net_cost)) * 100
        
        # Estimate probability of profit (simplified)
        prob_profit = 50  # Default
        if breakevens and current_stock_price:
            # Simple estimate based on position relative to breakeven
            if len(breakevens) == 1:
                distance_to_be = (breakevens[0] - current_stock_price) / current_stock_price * 100
                if distance_to_be > 0:
                    # Need stock to go up
                    prob_profit = max(20, 50 - distance_to_be * 2)
                else:
                    # Already above breakeven
                    prob_profit = min(80, 50 + abs(distance_to_be) * 2)
        
        return {
            'current_pnl': round(current_pnl, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(max_loss, 2),
            'breakeven': breakevens[0] if breakevens else None,
            'roi': round(roi, 2),
            'prob_profit': round(prob_profit, 2),
            'days_to_expiry': min_dte,
            'price_change_pct': round((current_stock_price - original_stock_price) / original_stock_price * 100, 2)
        }


# Test code
if __name__ == "__main__":
    print("Base Strategy Class Module")
    print("=" * 50)
    print("✓ Abstract base class defined")
    print("✓ Required methods: validate_parameters, scan, calculate_payoff")
    print("✓ Helper methods: calculate_breakeven, calculate_max_profit, calculate_max_loss")
    print("✓ Strategy info: get_strategy_info")
