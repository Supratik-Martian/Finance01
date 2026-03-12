"""
Momentum Agent — detects strong trends using dual momentum (absolute + relative).
Thrives in TRENDING_BULL and TRENDING_BEAR regimes.
"""
import numpy as np
from .base import BaseAgent, Blackboard, Regime, AgentSignal, Direction
from ..indicators import Indicators

import logging
logger = logging.getLogger(__name__)


class MomentumAgent(BaseAgent):
    name = "momentum"
    preferred_regimes = [Regime.TRENDING_BULL, Regime.TRENDING_BEAR]
    anti_regimes = [Regime.MEAN_REVERTING, Regime.CRISIS]

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        signals = {}

        for symbol, df in candles_map.items():
            if len(df) < 30:
                continue

            close = df['close']
            volume = df['volume'] if 'volume' in df.columns else None
            price = close.iloc[-1]

            # EMA crossover
            ema9 = close.ewm(span=9).mean()
            ema21 = close.ewm(span=21).mean()
            ema50 = close.ewm(span=50).mean() if len(close) >= 50 else ema21

            # ADX for trend strength
            adx = self._simple_adx(df, 14)

            # RSI
            rsi = Indicators.rsi(close, 14)
            rsi_val = rsi.iloc[-1] if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]) else 50

            # Volume confirmation
            vol_ok = True
            if volume is not None and len(volume) > 20:
                avg_vol = volume.rolling(20).mean().iloc[-1]
                vol_ok = volume.iloc[-1] > avg_vol * 0.8

            # ── LONG signal ──
            if (ema9.iloc[-1] > ema21.iloc[-1] and
                    price > ema50.iloc[-1] and
                    adx > 20 and
                    30 < rsi_val < 75 and
                    vol_ok):

                # Conviction based on trend strength
                conviction = min(1.0, (adx - 20) / 30)  # 20→0, 50→1
                conviction *= 0.5 + 0.5 * (rsi_val - 30) / 40  # boost for strong RSI

                atr = Indicators.atr(df['high'], df['low'], close, 14)
                atr_val = atr.iloc[-1] if len(atr) > 0 and not np.isnan(atr.iloc[-1]) else price * 0.02

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.LONG,
                    conviction=round(min(conviction, 0.95), 2),
                    entry_price=price,
                    stop_loss=price - 2 * atr_val,
                    target=price + 3 * atr_val,
                    reason=f"Momentum LONG: EMA9>EMA21, ADX={adx:.0f}, RSI={rsi_val:.0f}",
                    agent_name=self.name,
                )

            # ── SHORT signal ──
            elif (ema9.iloc[-1] < ema21.iloc[-1] and
                  price < ema50.iloc[-1] and
                  adx > 20 and
                  25 < rsi_val < 70 and
                  vol_ok):

                conviction = min(1.0, (adx - 20) / 30)
                conviction *= 0.5 + 0.5 * (70 - rsi_val) / 40

                atr = Indicators.atr(df['high'], df['low'], close, 14)
                atr_val = atr.iloc[-1] if len(atr) > 0 and not np.isnan(atr.iloc[-1]) else price * 0.02

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.SHORT,
                    conviction=round(min(conviction, 0.90), 2),
                    entry_price=price,
                    stop_loss=price + 2 * atr_val,
                    target=price - 3 * atr_val,
                    reason=f"Momentum SHORT: EMA9<EMA21, ADX={adx:.0f}, RSI={rsi_val:.0f}",
                    agent_name=self.name,
                )

        blackboard.signals[self.name] = signals
        return signals

    def _simple_adx(self, df, period=14) -> float:
        try:
            high, low, close = df['high'], df['low'], df['close']
            atr = Indicators.atr(high, low, close, period)
            if atr.iloc[-1] == 0:
                return 0
            plus_dm = high.diff().clip(lower=0)
            minus_dm = low.diff().abs().clip(lower=0)
            plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
            dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)) * 100
            adx = dx.rolling(period).mean()
            val = adx.iloc[-1]
            return val if not np.isnan(val) else 0
        except Exception:
            return 0
