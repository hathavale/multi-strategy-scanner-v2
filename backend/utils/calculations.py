"""
Core utility functions for options calculations.
Extracted and standardized from Options-Analysis-Strategies.ipynb
"""

import numpy as np
from scipy.stats import norm
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pytz


# US Eastern timezone for stock market calculations
EASTERN_TZ = pytz.timezone('US/Eastern')


def get_eastern_now() -> datetime:
    """
    Get current datetime in US Eastern timezone.
    US stock markets operate on Eastern Time.
    
    Returns:
        datetime: Current time in US Eastern timezone (naive datetime for compatibility)
    """
    return datetime.now(EASTERN_TZ).replace(tzinfo=None)


def get_stock_price(symbol: str, api_key: str, session=None) -> Optional[float]:
    """
    Fetch real-time stock price from Alpha Vantage API.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        api_key: Your Alpha Vantage API key
        session: Optional requests.Session for connection reuse
        
    Returns:
        float: Real-time stock price or None if error
    """
    import requests
    
    print(f"📈 Calling get_stock_price for symbol: {symbol}")
    
    if session is None:
        session = requests.Session()
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': api_key,
            'entitlement': 'realtime'
        }
        
        print(f"📈 Alpha Vantage stock price request: {params}")
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if 'Error Message' in data or 'Note' in data or 'Information' in data:
            print(f"📈 ❌ API error in stock price response: {data}")
            return None
        
        # Extract real-time price
        price = data.get('Global Quote', {}).get('05. price', 0)
        final_price = float(price) if price else None
        print(f"📈 ✅ Stock price for {symbol}: {final_price}")
        return final_price
        
    except Exception as e:
        print(f"📈 ❌ Error fetching stock price for {symbol}: {e}")
        return None


def get_risk_free_rate(api_key: str, session=None) -> float:
    """
    Fetch current risk-free rate (3-month Treasury yield) from Alpha Vantage.
    
    Args:
        api_key: Your Alpha Vantage API key
        session: Optional requests.Session for connection reuse
        
    Returns:
        float: Risk-free rate as decimal (e.g., 0.05 for 5%) or default 0.05
    """
    import requests
    
    if session is None:
        session = requests.Session()
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TREASURY_YIELD',
            'interval': 'daily',
            'maturity': '3month',
            'apikey': api_key
        }
        
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data or 'Note' in data or 'Information' in data:
            return 0.05
        
        time_series = data.get('data', [])
        if time_series:
            return float(time_series[0]['value']) / 100
        
        return 0.05
        
    except Exception:
        return 0.05


def get_options_data(symbol: str, api_key: str, session=None) -> Optional[Dict]:
    """
    Fetch real-time options chain data from Alpha Vantage.
    
    Args:
        symbol: Stock ticker symbol
        api_key: Your Alpha Vantage API key
        session: Optional requests.Session for connection reuse
        
    Returns:
        dict: Options chain data or None if error
    """
    import requests
    
    print(f"📊 Calling get_options_data for symbol: {symbol}")
    
    if session is None:
        session = requests.Session()
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'REALTIME_OPTIONS',
            'symbol': symbol,
            'apikey': api_key,
            'require_greeks': 'true',
            'entitlement': 'realtime'
        }
        
        print(f"📊 Alpha Vantage options request: {params}")
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data or 'Note' in data or 'Information' in data:
            print(f"📊 ❌ API error in options response: {data}")
            return None
        
        # Log the count of options retrieved
        if 'data' in data:
            options_count = len(data['data'])
            print(f"📊 ✅ Retrieved {options_count} options contracts for {symbol}")
        else:
            print(f"📊 ⚠️ No 'data' field in options response for {symbol}")
            
        return data
        
    except Exception as e:
        print(f"📊 ❌ Error fetching options data for {symbol}: {e}")
        return None


def compute_avg_iv(options_data: Optional[Dict]) -> float:
    """
    Calculate average implied volatility from options chain.
    
    Args:
        options_data: Options chain data from Alpha Vantage
        
    Returns:
        float: Average IV as decimal (e.g., 0.30 for 30%) or 0.15 as fallback
    """
    if not options_data:
        return 0.15
    
    ivs = [
        float(opt.get('implied_volatility', 0)) 
        for opt in options_data.get('data', []) 
        if float(opt.get('implied_volatility', 0)) > 0
    ]
    
    return np.mean(ivs) if ivs else 0.15


def prob_in_range(low: float, high: float, spot: float, iv: float, 
                  r: float, t: float) -> float:
    """
    Calculate probability that stock price will be in range [low, high] at time t.
    Uses Black-Scholes log-normal distribution.
    
    Args:
        low: Lower bound of price range
        high: Upper bound of price range
        spot: Current stock price
        iv: Implied volatility (annualized, as decimal)
        r: Risk-free rate (as decimal)
        t: Time to expiration (in years)
        
    Returns:
        float: Probability as decimal (0.0 to 1.0)
    """
    if t == 0:
        return 1.0 if low < spot < high else 0.0
    
    sigma = iv * np.sqrt(t)
    
    # Handle boundary conditions
    if low <= 0:
        d2_low = np.inf
    else:
        d2_low = (np.log(spot / low) + (r - 0.5 * iv**2) * t) / sigma
    
    if high == np.inf:
        d2_high = -np.inf
    else:
        d2_high = (np.log(spot / high) + (r - 0.5 * iv**2) * t) / sigma
    
    return norm.cdf(d2_low) - norm.cdf(d2_high)


def parse_options_chain(options_data: Optional[Dict]) -> Dict[datetime, List[Dict]]:
    """
    Parse Alpha Vantage options chain into structured format grouped by expiration.
    
    Args:
        options_data: Raw options data from Alpha Vantage
        
    Returns:
        dict: Options grouped by expiration date
              {datetime: [{'strike': float, 'type': str, 'premium': float, ...}, ...]}
    """
    from collections import defaultdict
    
    print(f"🔧 Calling parse_options_chain")
    
    if not options_data:
        print(f"🔧 ❌ No options data provided to parse")
        return defaultdict(list)
    
    chain = defaultdict(list)
    total_options = len(options_data.get('data', []))
    parsed_count = 0
    skipped_count = 0
    
    print(f"🔧 Processing {total_options} raw options from Alpha Vantage")
    
    for opt in options_data.get('data', []):
        try:
            exp = datetime.strptime(opt['expiration'], '%Y-%m-%d')
            strike = float(opt['strike'])
            opt_type = opt['type'].upper()
            bid = float(opt.get('bid', 0))
            ask = float(opt.get('ask', 0))
            premium = (bid + ask) / 2
            iv = float(opt.get('implied_volatility', 0))
            delta = float(opt.get('delta', 0))
            volume = float(opt.get('volume', 0))
            oi = float(opt.get('open_interest', 0))
            
            chain[exp].append({
                'strike': strike,
                'type': opt_type,
                'premium': premium,
                'bid': bid,
                'ask': ask,
                'iv': iv,
                'delta': delta,
                'volume': volume,
                'open_interest': oi
            })
            parsed_count += 1
        except (KeyError, ValueError) as e:
            # Skip malformed option data
            skipped_count += 1
            continue
    
    expiration_count = len(chain)
    print(f"🔧 ✅ Parsed {parsed_count} options, skipped {skipped_count}, grouped into {expiration_count} expirations")
    
    return chain


def calculate_days_to_expiry(expiry_date: datetime) -> int:
    """
    Calculate days to expiration from current date (Eastern Time).
    
    Args:
        expiry_date: Expiration date
        
    Returns:
        int: Days to expiration
    """
    return (expiry_date - get_eastern_now()).days


def calculate_time_to_expiry(expiry_date: datetime) -> float:
    """
    Calculate time to expiration in years.
    
    Args:
        expiry_date: Expiration date
        
    Returns:
        float: Time to expiration in years
    """
    days = calculate_days_to_expiry(expiry_date)
    return days / 365.0


def black_scholes_price(S: float, K: float, T: float, r: float, 
                        sigma: float, option_type: str) -> float:
    """
    Calculate Black-Scholes option price.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
        
    Returns:
        float: Option price
    """
    if T <= 0:
        if option_type.lower() == 'call':
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price


def calculate_delta(S: float, K: float, T: float, r: float, 
                    sigma: float, option_type: str) -> float:
    """
    Calculate option delta (rate of change of option price with respect to stock price).
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
        
    Returns:
        float: Delta value
    """
    if T <= 0:
        if option_type.lower() == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    if option_type.lower() == 'call':
        delta = norm.cdf(d1)
    else:  # put
        delta = norm.cdf(d1) - 1
    
    return delta


def calculate_breakeven(legs: List[Dict], strategy_type: str) -> float:
    """
    Calculate breakeven price for a multi-leg options position.
    
    Args:
        legs: List of position legs with 'strike', 'premium', 'position' (1=long, -1=short)
        strategy_type: Type of strategy for specific breakeven logic
        
    Returns:
        float: Breakeven price
    """
    # This is strategy-specific and should be implemented in each strategy module
    # Generic implementation for simple strategies
    total_debit = sum(leg['premium'] * leg['position'] for leg in legs)
    
    if strategy_type in ['call_debit_spread', 'put_debit_spread']:
        # For spreads, breakeven = lower_strike + net_debit (calls) or higher_strike - net_debit (puts)
        pass
    
    # Placeholder - will be overridden by strategy-specific implementations
    return 0.0


def format_currency(value: float, decimals: int = 2) -> str:
    """
    Format value as currency string.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        str: Formatted currency string
    """
    return f"${value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format value as percentage string.
    
    Args:
        value: Numeric value (as decimal, e.g., 0.15 for 15%)
        decimals: Number of decimal places
        
    Returns:
        str: Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not symbol:
        return False
    
    # Basic validation: 1-5 uppercase letters
    return len(symbol) >= 1 and len(symbol) <= 5 and symbol.isalpha() and symbol.isupper()


def validate_strike(strike: float, stock_price: float) -> bool:
    """
    Validate strike price is reasonable relative to stock price.
    
    Args:
        strike: Strike price
        stock_price: Current stock price
        
    Returns:
        bool: True if valid, False otherwise
    """
    if strike <= 0:
        return False
    
    # Strike should be within reasonable range (10% to 500% of stock price)
    ratio = strike / stock_price
    return 0.1 <= ratio <= 5.0


def validate_premium(premium: float) -> bool:
    """
    Validate option premium is reasonable.
    
    Args:
        premium: Option premium
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Premium should be positive and less than $1000 per share
    return 0 < premium < 1000


def validate_strike_price(strike: float, stock_price: float = None) -> bool:
    """
    Validate strike price is reasonable.
    
    Args:
        strike: Strike price to validate
        stock_price: Optional current stock price for relative validation
        
    Returns:
        bool: True if valid, False otherwise
    """
    if strike <= 0:
        return False
    
    # If stock price provided, check strike is within reasonable range
    if stock_price is not None:
        # Strike should be within 0.5x to 2x of stock price
        if strike < stock_price * 0.5 or strike > stock_price * 2:
            return False
    
    return True


def validate_expiration_date(expiry_date: datetime) -> bool:
    """
    Validate expiration date is in the future (Eastern Time).
    
    Args:
        expiry_date: Expiration date to validate
        
    Returns:
        bool: True if valid (future date), False otherwise
    """
    return expiry_date > get_eastern_now()


def validate_option_type(option_type: str) -> bool:
    """
    Validate option type is 'call' or 'put'.
    
    Args:
        option_type: Option type string
        
    Returns:
        bool: True if valid, False otherwise
    """
    return option_type.lower() in ['call', 'put']


if __name__ == "__main__":
    # Example usage
    print("Options Calculations Utility Module")
    print("====================================")
    
    # Test probability calculation
    spot = 100
    iv = 0.30
    r = 0.05
    t = 30/365  # 30 days
    
    prob = prob_in_range(95, 105, spot, iv, r, t)
    print(f"\nProbability stock stays between $95-$105: {format_percentage(prob)}")
    
    # Test Black-Scholes
    call_price = black_scholes_price(100, 105, t, r, iv, 'call')
    put_price = black_scholes_price(100, 95, t, r, iv, 'put')
    print(f"Call price (105 strike): {format_currency(call_price)}")
    print(f"Put price (95 strike): {format_currency(put_price)}")
    
    # Test delta
    call_delta = calculate_delta(100, 105, t, r, iv, 'call')
    put_delta = calculate_delta(100, 95, t, r, iv, 'put')
    print(f"Call delta (105 strike): {call_delta:.3f}")
    print(f"Put delta (95 strike): {put_delta:.3f}")
