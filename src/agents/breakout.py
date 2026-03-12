"""
Breakout Agent — detects range breakouts with volume confirmation.
Thrives at regime transitions (MEAN_REVERTING → TRENDING).
"""
import numpy as np
from .base import BaseAgent, Blackboard, Regime, AgentSignal, Direction
from ..indicators import Indicators

import logging
logger = logging.getLogger(__name__)


class BreakoutAgent(BaseAgent):
    name = "breakout"
    preferred_regimes = [Regime.MEAN_REVERTING]  # breakouts happen FROM ranges
    anti_regimes = [Regime.CRISIS]

    def __init__(self, orb_minutes: int = 15):
        super().__init__()
        self.orb_minutes = orb_minutes

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        signals = {}

        for symbol, df in candles_map.items():
            if len(df) < 20:
                continue

            close = df['close']
            high = df['high']
            low = df['low']
            volume = df['volume'] if 'volume' in df.columns else None
            price = close.iloc[-1]

            # Donchian Channel (20-period high/low)
            donchian_high = high.rolling(20).max().iloc[-1]
            donchian_low = low.rolling(20).min().iloc[-1]
            donchian_range = donchian_high - donchian_low

            if donchian_range <= 0:
                continue

            # Volume surge check
            vol_surge = False
            if volume is not None and len(volume) > 20:
                avg_vol = volume.rolling(20).mean().iloc[-1]
                vol_surge = volume.iloc[-1] > avg_vol * 1.5

            atr = Indicators.atr(high, low, close, 14)
            atr_val = atr.iloc[-1] if len(atr) > 0 and not np.isnan(atr.iloc[-1]) else price * 0.02

            # ── Upside breakout ──
            if price > donchian_high * 0.998 and vol_surge:
                conviction = 0.6
                if price > donchian_high:
                    conviction += 0.15
                # Higher conviction if ADX is rising (regime transition to trending)
                regime = blackboard.regime.get("primary", Regime.UNKNOWN)
                if regime in [Regime.TRENDING_BULL]:
                    conviction += 0.1

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.LONG,
                    conviction=round(min(conviction, 0.90), 2),
                    entry_price=price,
                    stop_loss=donchian_low + donchian_range * 0.4,
                    target=price + 2 * atr_val,
                    reason=f"Breakout LONG: price={price:.0f} > Donchian {donchian_high:.0f}, vol surge",
                    agent_name=self.name,
                )

            # ── Downside breakout ──
            elif price < donchian_low * 1.002 and vol_surge:
                conviction = 0.55
                if price < donchian_low:
                    conviction += 0.15

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.SHORT,
                    conviction=round(min(conviction, 0.85), 2),
                    entry_price=price,
                    stop_loss=donchian_high - donchian_range * 0.4,
                    target=price - 2 * atr_val,
                    reason=f"Breakout SHORT: price={price:.0f} < Donchian {donchian_low:.0f}, vol surge",
                    agent_name=self.name,
                )

        blackboard.signals[self.name] = signals
        return signals
