"""
Mean Reversion Agent — buys dips, sells rips.
Thrives in MEAN_REVERTING regimes.
"""
import numpy as np
from .base import BaseAgent, Blackboard, Regime, AgentSignal, Direction
from ..indicators import Indicators

import logging
logger = logging.getLogger(__name__)


class MeanReversionAgent(BaseAgent):
    name = "mean_reversion"
    preferred_regimes = [Regime.MEAN_REVERTING]
    anti_regimes = [Regime.TRENDING_BULL, Regime.TRENDING_BEAR, Regime.CRISIS]

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        signals = {}

        for symbol, df in candles_map.items():
            if len(df) < 20:
                continue

            close = df['close']
            high = df['high']
            low = df['low']
            price = close.iloc[-1]

            # VWAP
            vwap = Indicators.vwap(high, low, close,
                                    df['volume'] if 'volume' in df.columns else close * 0 + 1)
            vwap_val = vwap.iloc[-1] if len(vwap) > 0 and not np.isnan(vwap.iloc[-1]) else price

            # Bollinger Bands
            bb = Indicators.bollinger_bands(close, 20, 2.0)
            bb_upper = bb['upper'].iloc[-1]
            bb_lower = bb['lower'].iloc[-1]
            bb_mid = bb['middle'].iloc[-1]

            # RSI
            rsi = Indicators.rsi(close, 14)
            rsi_val = rsi.iloc[-1] if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]) else 50

            # Z-score from mean
            mean_20 = close.rolling(20).mean().iloc[-1]
            std_20 = close.rolling(20).std().iloc[-1]
            z_score = (price - mean_20) / std_20 if std_20 > 0 else 0

            atr = Indicators.atr(high, low, close, 14)
            atr_val = atr.iloc[-1] if len(atr) > 0 and not np.isnan(atr.iloc[-1]) else price * 0.02

            # ── LONG (oversold bounce) ──
            if (rsi_val < 30 and price < vwap_val and
                    price <= bb_lower * 1.005 and z_score < -1.5):

                conviction = min(0.9, abs(z_score) / 3.0)
                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.LONG,
                    conviction=round(conviction, 2),
                    entry_price=price,
                    stop_loss=price - 1.5 * atr_val,
                    target=bb_mid,  # revert to middle band
                    reason=f"MeanRev LONG: RSI={rsi_val:.0f}, Z={z_score:.1f}, below VWAP+BB",
                    agent_name=self.name,
                )

            # ── SHORT (overbought fade) ──
            elif (rsi_val > 70 and price > vwap_val and
                  price >= bb_upper * 0.995 and z_score > 1.5):

                conviction = min(0.9, abs(z_score) / 3.0)
                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.SHORT,
                    conviction=round(conviction, 2),
                    entry_price=price,
                    stop_loss=price + 1.5 * atr_val,
                    target=bb_mid,
                    reason=f"MeanRev SHORT: RSI={rsi_val:.0f}, Z={z_score:.1f}, above VWAP+BB",
                    agent_name=self.name,
                )

        blackboard.signals[self.name] = signals
        return signals
