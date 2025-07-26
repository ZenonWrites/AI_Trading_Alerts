import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import ta

def check_buy_signal(df):
    """
    Smart Money Concepts buy signal detection based on bullish BOS/CHoCH
    
    Args:
        df: pandas DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
    
    Returns:
        bool: True if buy signal detected on latest bar
    """
    if len(df) < 100:  # Need sufficient data
        return False
    
    # Calculate ATR for volatility filtering
    df_copy = df.copy()
    df_copy['atr'] = ta.volatility.average_true_range(df_copy['High'], df_copy['Low'], df_copy['Close'], window=14)
    
    # Parameters (matching Pine Script defaults)
    swing_length = 50
    internal_length = 5
    
    # Find swing highs and lows using rolling windows
    def find_pivots(series, window, pivot_type='high'):
        """Find pivot points in price series"""
        pivots = pd.Series(index=series.index, dtype=float)
        
        for i in range(window, len(series) - window):
            if pivot_type == 'high':
                if series.iloc[i] == series.iloc[i-window:i+window+1].max():
                    pivots.iloc[i] = series.iloc[i]
            else:  # low
                if series.iloc[i] == series.iloc[i-window:i+window+1].min():
                    pivots.iloc[i] = series.iloc[i]
        
        return pivots.dropna()
    
    # Find swing structure pivots
    swing_highs = find_pivots(df_copy['High'], swing_length//2, 'high')
    swing_lows = find_pivots(df_copy['Low'], swing_length//2, 'low')
    
    # Find internal structure pivots  
    internal_highs = find_pivots(df_copy['High'], internal_length//2, 'high')
    internal_lows = find_pivots(df_copy['Low'], internal_length//2, 'low')
    
    def detect_structure_break(df, highs, lows, structure_type='swing'):
        """Detect BOS and CHoCH patterns"""
        if len(highs) < 2 or len(lows) < 2:
            return pd.Series(index=df.index, dtype=bool).fillna(False)
        
        signals = pd.Series(index=df.index, dtype=bool).fillna(False)
        
        # Get recent pivots
        recent_highs = highs.tail(10) if len(highs) >= 10 else highs
        recent_lows = lows.tail(10) if len(lows) >= 10 else lows
        
        # Determine current trend based on pivot sequence
        all_pivots = pd.concat([recent_highs, recent_lows]).sort_index()
        
        if len(all_pivots) < 3:
            return signals
        
        # Track trend state
        current_trend = 0  # 0 = neutral, 1 = bullish, -1 = bearish
        last_significant_high = None
        last_significant_low = None
        
        for i in range(len(df)):
            current_close = df['Close'].iloc[i]
            
            # Update last significant levels
            for pivot_time, pivot_value in recent_highs.items():
                if pivot_time <= df.index[i] and (last_significant_high is None or pivot_value > last_significant_high):
                    last_significant_high = pivot_value
            
            for pivot_time, pivot_value in recent_lows.items():
                if pivot_time <= df.index[i] and (last_significant_low is None or pivot_value < last_significant_low):
                    last_significant_low = pivot_value
            
            if last_significant_high is None:
                continue
                
            # Check for bullish structure break (price breaks above recent high)
            if current_close > last_significant_high:
                # Determine if this is BOS or CHoCH
                if current_trend == -1:  # Was bearish, now breaking bullish = CHoCH
                    signals.iloc[i] = True
                elif current_trend == 0:  # Was neutral, now bullish = BOS
                    signals.iloc[i] = True
                
                current_trend = 1  # Now bullish
            
            # Update trend if breaking below significant low
            elif last_significant_low is not None and current_close < last_significant_low:
                current_trend = -1  # Now bearish
        
        return signals
    
    # Detect swing structure breaks
    swing_bullish_signals = detect_structure_break(df_copy, swing_highs, swing_lows, 'swing')
    
    # Detect internal structure breaks  
    internal_bullish_signals = detect_structure_break(df_copy, internal_highs, internal_lows, 'internal')
    
    # Additional filters
    def apply_confluence_filter(signals, df):
        """Apply confluence filter similar to Pine Script"""
        filtered_signals = signals.copy()
        
        for i in range(1, len(df)):
            if signals.iloc[i]:
                # Check if current bar is bullish
                current_bar_bullish = (df['High'].iloc[i] - max(df['Close'].iloc[i], df['Open'].iloc[i])) > \
                                    (min(df['Close'].iloc[i], df['Open'].iloc[i]) - df['Low'].iloc[i])
                
                if not current_bar_bullish:
                    filtered_signals.iloc[i] = False
        
        return filtered_signals
    
    # Apply confluence filter to internal signals
    internal_bullish_signals = apply_confluence_filter(internal_bullish_signals, df_copy)
    
    # Order block detection (simplified)
    def detect_order_blocks(df, pivot_highs, pivot_lows):
        """Detect order block formations"""
        ob_signals = pd.Series(index=df.index, dtype=bool).fillna(False)
        
        # Look for demand zones (bullish order blocks)
        for i in range(50, len(df)):
            # Find recent swing low
            recent_lows_before_i = pivot_lows[pivot_lows.index <= df.index[i]]
            if len(recent_lows_before_i) == 0:
                continue
                
            last_swing_low = recent_lows_before_i.iloc[-1]
            last_swing_low_idx = recent_lows_before_i.index[-1]
            
            # Check if price is breaking above this level after finding support
            if df['Close'].iloc[i] > last_swing_low and df['Low'].iloc[i-1] <= last_swing_low:
                ob_signals.iloc[i] = True
        
        return ob_signals
    
    # Detect order block signals
    swing_ob_signals = detect_order_blocks(df_copy, swing_highs, swing_lows)
    internal_ob_signals = detect_order_blocks(df_copy, internal_highs, internal_lows)
    
    # Equal highs/lows detection (simplified)
    def detect_equal_levels(highs, lows, threshold_multiplier=0.1):
        """Detect equal highs and lows"""
        eq_signals = pd.Series(index=df_copy.index, dtype=bool).fillna(False)
        atr = df_copy['atr'].mean()
        threshold = threshold_multiplier * atr
        
        # Check for equal lows (bullish signal)
        recent_lows = lows.tail(5) if len(lows) >= 5 else lows
        for i, (time1, low1) in enumerate(recent_lows.items()):
            for time2, low2 in recent_lows.iloc[i+1:].items():
                if abs(low1 - low2) < threshold:
                    # Equal lows found - potential bullish signal
                    if time2 in eq_signals.index:
                        eq_signals.loc[time2] = True
        
        return eq_signals
    
    equal_level_signals = detect_equal_levels(swing_highs, swing_lows)
    
    # Combine all bullish signals
    combined_signals = (
        swing_bullish_signals | 
        internal_bullish_signals | 
        swing_ob_signals | 
        internal_ob_signals |
        equal_level_signals
    )
    
    # Additional trend filter - only buy in overall uptrend
    df_copy['ema_20'] = ta.trend.ema_indicator(df_copy['Close'], window=20)
    df_copy['ema_50'] = ta.trend.ema_indicator(df_copy['Close'], window=50)
    
    trend_bullish = df_copy['ema_20'] > df_copy['ema_50']
    
    # Final signal with trend filter
    final_signals = combined_signals & trend_bullish
    
    # Return True if signal detected on latest bar
    if len(final_signals) > 0:
        return bool(final_signals.iloc[-1])
    
    return False


# Example usage:
def example_usage():
    """Example of how to use the function with yfinance data"""
    import yfinance as yf
    
    # Download data
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="6mo", interval="1d")
    
    # Rename columns to match expected format
    df = df.rename(columns={
        'Open': 'Open',
        'High': 'High', 
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume'
    })
    
    # Check for buy signal
    buy_signal = check_buy_signal(df)
    print(f"Buy signal detected: {buy_signal}")
    
    return buy_signal

# Uncomment to test:
# example_usage()