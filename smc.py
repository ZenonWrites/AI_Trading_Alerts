import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

# === Data Structure Classes ===
class TOD:
    """Time of Day structure"""
    def __init__(self, timeframe: str = None):
        self.timeframe = timeframe
        self.v = []  # value list
        
    def size(self):
        return len(self.v)
    
    def avg(self):
        return sum(self.v) / len(self.v) if self.v else 0
    
    def pop(self):
        return self.v.pop() if self.v else None
    
    def unshift(self, value):
        self.v.insert(0, value)
    
    def push(self, value):
        self.v.append(value)

class HTOD:
    """Hourly Time of Day structure"""
    def __init__(self, timeframe: str = None):
        self.timeframe = timeframe
        self.v = []  # value list
        
    def size(self):
        return len(self.v)
    
    def avg(self):
        return sum(self.v) / len(self.v) if self.v else 0
    
    def pop(self):
        return self.v.pop() if self.v else None
    
    def unshift(self, value):
        self.v.insert(0, value)
    
    def push(self, value):
        self.v.append(value)

class STOD:
    """Session Time of Day structure"""
    def __init__(self, timeframe: str = None):
        self.timeframe = timeframe
        self.v = []  # value list
        
    def size(self):
        return len(self.v)
    
    def avg(self):
        return sum(self.v) / len(self.v) if self.v else 0
    
    def pop(self):
        return self.v.pop() if self.v else None
    
    def unshift(self, value):
        self.v.insert(0, value)
    
    def push(self, value):
        self.v.append(value)

# === Helper Methods Framework ===
def add_element_tod(tod_array: List[TOD], timeframe: str, value: float, 
                   hour: int = None, minute: int = None, second: int = None) -> bool:
    """Add element to TOD array with timeframe checking"""
    timeframe_is_seconds = 's' in timeframe.lower()
    
    # Find or create TOD for this timeframe
    tod_item = None
    for item in tod_array:
        if item.timeframe == timeframe:
            tod_item = item
            break
    
    if tod_item is None:
        tod_item = TOD(timeframe)
        tod_array.append(tod_item)
    
    # Add value to the TOD
    tod_item.push(value)
    
    return True

def get_element_tod(tod_array: List[TOD], timeframe: str, index: int = 0) -> Optional[float]:
    """Get element from TOD array"""
    for item in tod_array:
        if item.timeframe == timeframe:
            if 0 <= index < len(item.v):
                return item.v[index]
            break
    return None

def add_element_htod(htod_array: List[HTOD], timeframe: str, value: float,
                    hour: int = None, minute: int = None, second: int = None) -> bool:
    """Add element to HTOD array with timeframe checking"""
    timeframe_is_seconds = 's' in timeframe.lower()
    
    # Find or create HTOD for this timeframe
    htod_item = None
    for item in htod_array:
        if item.timeframe == timeframe:
            htod_item = item
            break
    
    if htod_item is None:
        htod_item = HTOD(timeframe)
        htod_array.append(htod_item)
    
    # Add value to the HTOD
    htod_item.push(value)
    
    return True

def get_element_htod(htod_array: List[HTOD], timeframe: str, index: int = 0) -> Optional[float]:
    """Get element from HTOD array"""
    for item in htod_array:
        if item.timeframe == timeframe:
            if 0 <= index < len(item.v):
                return item.v[index]
            break
    return None

def add_element_stod(stod_array: List[STOD], timeframe: str, value: float,
                    hour: int = None, minute: int = None, second: int = None) -> bool:
    """Add element to STOD array with timeframe checking"""
    timeframe_is_seconds = 's' in timeframe.lower()
    
    # Find or create STOD for this timeframe
    stod_item = None
    for item in stod_array:
        if item.timeframe == timeframe:
            stod_item = item
            break
    
    if stod_item is None:
        stod_item = STOD(timeframe)
        stod_array.append(stod_item)
    
    # Add value to the STOD
    stod_item.push(value)
    
    return True

def get_element_stod(stod_array: List[STOD], timeframe: str, index: int = 0) -> Optional[float]:
    """Get element from STOD array"""
    for item in stod_array:
        if item.timeframe == timeframe:
            if 0 <= index < len(item.v):
                return item.v[index]
            break
    return None

# === Trading Strategy Class ===
class SMCDiscountStrategy:
    """SMC Discount + Bullish Engulfing + Volume Strategy"""
    
    def __init__(self, lookback: int = 30, min_volume: int = 100000, 
                 tp_percent: float = 5.0, sl_percent: float = 2.0):
        self.lookback = lookback
        self.min_volume = min_volume
        self.tp_percent = tp_percent
        self.sl_percent = sl_percent
        
        # Track recent buy signals
        self.buy_signals = []
        self.max_signals = 5
        
    def highest(self, data: List[float], period: int) -> float:
        """Calculate highest value over period"""
        if len(data) < period:
            return max(data) if data else 0
        return max(data[-period:])
    
    def lowest(self, data: List[float], period: int) -> float:
        """Calculate lowest value over period"""
        if len(data) < period:
            return min(data) if data else 0
        return min(data[-period:])
    
    def is_in_discount_zone(self, high_data: List[float], low_data: List[float], 
                           close_price: float) -> bool:
        """Check if price is in discount zone (below midline)"""
        hh = self.highest(high_data, self.lookback)
        ll = self.lowest(low_data, self.lookback)
        midline = (hh + ll) / 2
        return close_price < midline
    
    def get_midline(self, high_data: List[float], low_data: List[float]) -> float:
        """Calculate midline (50% level)"""
        hh = self.highest(high_data, self.lookback)
        ll = self.lowest(low_data, self.lookback)
        return (hh + ll) / 2
    
    def is_bullish_engulfing(self, open_prices: List[float], close_prices: List[float]) -> bool:
        """Check for bullish engulfing pattern"""
        if len(open_prices) < 2 or len(close_prices) < 2:
            return False
        
        # Previous candle was bearish
        prev_bearish = close_prices[-2] < open_prices[-2]
        
        # Current candle is bullish
        curr_bullish = close_prices[-1] > open_prices[-1]
        
        # Current candle engulfs previous candle
        engulfed = (open_prices[-1] < close_prices[-2] and 
                   close_prices[-1] > open_prices[-2])
        
        return prev_bearish and curr_bullish and engulfed
    
    def volume_condition_met(self, volume: float) -> bool:
        """Check if volume condition is met"""
        return volume > self.min_volume
    
    def generate_buy_signal(self, high_data: List[float], low_data: List[float],
                           open_prices: List[float], close_prices: List[float],
                           volume: float, timestamp: datetime = None) -> bool:
        """Generate buy signal based on all conditions"""
        if len(close_prices) < 2:
            return False
        
        current_close = close_prices[-1]
        
        # Check all conditions
        in_discount = self.is_in_discount_zone(high_data, low_data, current_close)
        bullish_engulfing = self.is_bullish_engulfing(open_prices, close_prices)
        volume_ok = self.volume_condition_met(volume)
        
        buy_signal = in_discount and bullish_engulfing and volume_ok
        
        if buy_signal:
            self.log_buy_signal(current_close, volume, timestamp)
        
        return buy_signal
    
    def calculate_tp_sl(self, entry_price: float) -> tuple:
        """Calculate take profit and stop loss levels"""
        tp = entry_price * (1 + self.tp_percent / 100)
        sl = entry_price * (1 - self.sl_percent / 100)
        return tp, sl
    
    def log_buy_signal(self, price: float, volume: float, timestamp: datetime = None):
        """Log buy signal to recent signals list"""
        if timestamp is None:
            timestamp = datetime.now()
        
        signal = {
            'time': timestamp.strftime('%Y-%m-%d'),
            'price': f"{price:.2f}",
            'volume': str(int(volume))
        }
        
        self.buy_signals.append(signal)
        
        # Keep only the last 5 signals
        if len(self.buy_signals) > self.max_signals:
            self.buy_signals.pop(0)
    
    def get_recent_signals(self) -> List[Dict[str, str]]:
        """Get list of recent buy signals"""
        return self.buy_signals.copy()
    
    def print_signals_table(self):
        """Print recent signals in table format"""
        print("\n=== Recent Buy Signals ===")
        print(f"{'Time':<12} {'Price':<10} {'Volume':<15}")
        print("-" * 40)
        
        for signal in self.buy_signals:
            print(f"{signal['time']:<12} {signal['price']:<10} {signal['volume']:<15}")

# === Example Usage ===
def example_usage():
    """Example of how to use the converted strategy"""
    
    # Initialize strategy
    strategy = SMCDiscountStrategy(
        lookback=30,
        min_volume=100000,
        tp_percent=5.0,
        sl_percent=2.0
    )
    
    # Example data (in real usage, this would come from your data source)
    high_data = [100, 105, 102, 108, 110, 107, 112, 115, 113, 118]
    low_data = [95, 98, 96, 102, 105, 103, 107, 110, 108, 113]
    open_prices = [98, 103, 99, 105, 108, 105, 109, 112, 111, 115]
    close_prices = [102, 101, 104, 107, 106, 109, 114, 111, 116, 117]
    volume = 150000
    
    # Generate buy signal
    buy_signal = strategy.generate_buy_signal(
        high_data, low_data, open_prices, close_prices, volume
    )
    
    if buy_signal:
        entry_price = close_prices[-1]
        tp, sl = strategy.calculate_tp_sl(entry_price)
        
        print(f"Buy Signal Generated!")
        print(f"Entry Price: {entry_price}")
        print(f"Take Profit: {tp:.2f}")
        print(f"Stop Loss: {sl:.2f}")
        print(f"Midline: {strategy.get_midline(high_data, low_data):.2f}")
    
    # Display recent signals
    strategy.print_signals_table()
    
    # Example of using the data structures
    tod_array = []
    htod_array = []
    stod_array = []
    
    # Add elements
    add_element_tod(tod_array, "1h", 100.5, hour=9, minute=30)
    add_element_htod(htod_array, "1h", 200.5, hour=10, minute=15)
    add_element_stod(stod_array, "1h", 300.5, hour=11, minute=0)
    
    # Get elements
    tod_value = get_element_tod(tod_array, "1h", 0)
    htod_value = get_element_htod(htod_array, "1h", 0)
    stod_value = get_element_stod(stod_array, "1h", 0)
    
    print(f"\nData Structure Values:")
    print(f"TOD Value: {tod_value}")
    print(f"HTOD Value: {htod_value}")
    print(f"STOD Value: {stod_value}")

if __name__ == "__main__":
    example_usage()