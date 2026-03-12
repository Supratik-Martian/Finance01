from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import pandas as pd
from .indicators import Indicators

class Signal(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0

@dataclass
class TradeSignal:
    symbol: str
    signal: Signal
    confidence: float  # 0 to 1
    entry_price: float
    stop_loss: float
    target: float
    quantity: int
    reason: str
    timestamp: datetime

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradeSignal]:
        pass

# ─── Strategy 1: VWAP + RSI Mean Reversion ───
class VWAPMeanReversion(BaseStrategy):
    """
    Buy when price < VWAP and RSI < 30 (oversold near value)
    Sell when price > VWAP and RSI > 70 (overbought above value)
    """
    def __init__(self, rsi_oversold=30, rsi_overbought=70, 
                 risk_reward=2.0, risk_pct=0.01):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.risk_reward = risk_reward
        self.risk_pct = risk_pct
    
    def generate_signal(self, df, symbol) -> Optional[TradeSignal]:
        if len(df) < 20:
            return None
            
        close = df['close']
        vwap = Indicators.vwap(df['high'], df['low'], close, df['volume'])
        rsi = Indicators.rsi(close, 14)
        atr = Indicators.atr(df['high'], df['low'], close, 14)
        
        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_vwap = vwap.iloc[-1]
        current_atr = atr.iloc[-1]
        
        if current_rsi < self.rsi_oversold and current_price < current_vwap * 0.998:
            sl = current_price - (2 * current_atr)
            tp = current_price + (2 * current_atr * self.risk_reward)
            return TradeSignal(
                symbol=symbol, signal=Signal.BUY,
                confidence=min((self.rsi_oversold - current_rsi) / 30, 1.0),
                entry_price=current_price, stop_loss=sl, target=tp,
                quantity=0,  # calculated by risk manager
                reason=f"VWAP Reversion: RSI={current_rsi:.1f}, "
                       f"Price below VWAP by {((current_vwap-current_price)/current_price)*100:.2f}%",
                timestamp=datetime.now()
            )
        
        if current_rsi > self.rsi_overbought and current_price > current_vwap * 1.002:
            sl = current_price + (2 * current_atr)
            tp = current_price - (2 * current_atr * self.risk_reward)
            return TradeSignal(
                symbol=symbol, signal=Signal.SELL,
                confidence=min((current_rsi - self.rsi_overbought) / 30, 1.0),
                entry_price=current_price, stop_loss=sl, target=tp,
                quantity=0,
                reason=f"VWAP Reversion: RSI={current_rsi:.1f}, "
                       f"Price above VWAP by {((current_price-current_vwap)/current_price)*100:.2f}%",
                timestamp=datetime.now()
            )
        
        return None


# ─── Strategy 2: Opening Range Breakout (ORB) ───
class ORBStrategy(BaseStrategy):
    """
    Classic intraday strategy for Indian markets.
    Define range in first N minutes, trade breakout.
    """
    def __init__(self, orb_minutes=15, atr_multiplier=1.5):
        self.orb_minutes = orb_minutes
        self.atr_multiplier = atr_multiplier
        self.orb_high = {}
        self.orb_low = {}
        self.orb_set = {}
    
    def generate_signal(self, df, symbol) -> Optional[TradeSignal]:
        if len(df) < 5:
            return None
        
        market_open = df.index[0].replace(hour=9, minute=15)
        orb_end = market_open + pd.Timedelta(minutes=self.orb_minutes)
        
        # Define ORB range
        if symbol not in self.orb_set:
            orb_data = df[df.index <= orb_end]
            if len(orb_data) >= 3:  # enough candles
                self.orb_high[symbol] = orb_data['high'].max()
                self.orb_low[symbol] = orb_data['low'].min()
                self.orb_set[symbol] = True
            else:
                return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        orb_range = self.orb_high[symbol] - self.orb_low[symbol]
        
        # Breakout above ORB high
        if (current['close'] > self.orb_high[symbol] and 
            prev['close'] <= self.orb_high[symbol] and
            current['volume'] > df['volume'].rolling(10).mean().iloc[-1] * 1.5):
            
            sl = self.orb_low[symbol]
            tp = current['close'] + (orb_range * 2)
            
            return TradeSignal(
                symbol=symbol, signal=Signal.BUY,
                confidence=0.7,
                entry_price=current['close'], stop_loss=sl, target=tp,
                quantity=0,
                reason=f"ORB Breakout UP: Range={orb_range:.2f}, Volume surge confirmed",
                timestamp=datetime.now()
            )
        
        # Breakdown below ORB low
        if (current['close'] < self.orb_low[symbol] and 
            prev['close'] >= self.orb_low[symbol] and
            current['volume'] > df['volume'].rolling(10).mean().iloc[-1] * 1.5):
            
            sl = self.orb_high[symbol]
            tp = current['close'] - (orb_range * 2)
            
            return TradeSignal(
                symbol=symbol, signal=Signal.SELL,
                confidence=0.7,
                entry_price=current['close'], stop_loss=sl, target=tp,
                quantity=0,
                reason=f"ORB Breakout DOWN: Range={orb_range:.2f}",
                timestamp=datetime.now()
            )
        
        return None

# ─── Strategy 3: EMA Crossover + Supertrend Confirmation ───
class EMASupertrend(BaseStrategy):
    def __init__(self, fast_ema=9, slow_ema=21, st_period=10, st_mult=3):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.st_period = st_period
        self.st_mult = st_mult
    
    def generate_signal(self, df, symbol) -> Optional[TradeSignal]:
        if len(df) < self.slow_ema + 5:
            return None
        
        close = df['close']
        ema_fast = Indicators.ema(close, self.fast_ema)
        ema_slow = Indicators.ema(close, self.slow_ema)
        st, direction = Indicators.supertrend(
            df['high'], df['low'], close, 
            self.st_period, self.st_mult
        )
        
        # Bullish: fast EMA crosses above slow + supertrend bullish
        if (ema_fast.iloc[-1] > ema_slow.iloc[-1] and 
            ema_fast.iloc[-2] <= ema_slow.iloc[-2] and
            direction.iloc[-1] == 1):
            
            return TradeSignal(
                symbol=symbol, signal=Signal.BUY,
                confidence=0.65,
                entry_price=close.iloc[-1],
                stop_loss=st.iloc[-1],
                target=close.iloc[-1] + 2 * (close.iloc[-1] - st.iloc[-1]),
                quantity=0,
                reason="EMA crossover + Supertrend bullish",
                timestamp=datetime.now()
            )
        
        # Bearish
        if (ema_fast.iloc[-1] < ema_slow.iloc[-1] and 
            ema_fast.iloc[-2] >= ema_slow.iloc[-2] and
            direction.iloc[-1] == -1):
            
            return TradeSignal(
                symbol=symbol, signal=Signal.SELL,
                confidence=0.65,
                entry_price=close.iloc[-1],
                stop_loss=st.iloc[-1],
                target=close.iloc[-1] - 2 * (st.iloc[-1] - close.iloc[-1]),
                quantity=0,
                reason="EMA crossover + Supertrend bearish",
                timestamp=datetime.now()
            )
        
        return None
