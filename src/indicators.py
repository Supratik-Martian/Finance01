import pandas as pd

class Indicators:
    """Vectorized technical indicators for speed"""
    
    @staticmethod
    def ema(series, period):
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(series, period):
        return series.rolling(window=period).mean()
    
    @staticmethod
    def rsi(series, period=14):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(series, fast=12, slow=26, signal=9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(series, period=20, std_dev=2):
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    @staticmethod
    def atr(high, low, close, period=14):
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def vwap(high, low, close, volume):
        typical_price = (high + low + close) / 3
        cumulative_tp_vol = (typical_price * volume).cumsum()
        cumulative_vol = volume.cumsum()
        return cumulative_tp_vol / cumulative_vol
    
    @staticmethod
    def supertrend(high, low, close, period=10, multiplier=3):
        atr = Indicators.atr(high, low, close, period)
        hl2 = (high + low) / 2
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=int)
        
        if len(close) > 0:
            supertrend.iloc[0] = upper_band.iloc[0]
            direction.iloc[0] = 1
            
            for i in range(1, len(close)):
                if close.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1  # Bullish
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1  # Bearish
                
        return supertrend, direction
    
    @staticmethod
    def order_flow_imbalance(buy_qty, sell_qty):
        """Order flow imbalance ratio"""
        total = buy_qty + sell_qty
        return (buy_qty - sell_qty) / total.where(total > 0, 1)
