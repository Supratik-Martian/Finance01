"""
Contrarian Agent — The Skeptic.
Detects overextension and crowding. Always maintains minimum 5% weight.
HYDRA Principle P6: "Dissent is valuable."
"""
import numpy as np
from .base import BaseAgent, Blackboard, Regime, AgentSignal, Direction
from ..indicators import Indicators

import logging
logger = logging.getLogger(__name__)


class ContrarianAgent(BaseAgent):
    name = "contrarian"
    preferred_regimes = []  # works in all regimes
    anti_regimes = []

    def regime_fit(self, regime: Regime) -> float:
        """Contrarian always keeps minimum weight — insurance against groupthink."""
        return max(0.3, super().regime_fit(regime))

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        signals = {}

        for symbol, df in candles_map.items():
            if len(df) < 20:
                continue

            close = df['close']
            volume = df['volume'] if 'volume' in df.columns else None
            price = close.iloc[-1]

            rsi = Indicators.rsi(close, 14)
            rsi_val = rsi.iloc[-1] if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]) else 50

            # Count consecutive green/red candles
            green_streak = 0
            red_streak = 0
            for i in range(len(close) - 1, max(len(close) - 10, 0), -1):
                if close.iloc[i] > close.iloc[i - 1]:
                    if red_streak > 0:
                        break
                    green_streak += 1
                else:
                    if green_streak > 0:
                        break
                    red_streak += 1

            # Volume divergence (price up but volume declining = exhaustion)
            vol_declining = False
            if volume is not None and len(volume) > 5:
                recent_vol = volume.iloc[-3:].mean()
                prior_vol = volume.iloc[-6:-3].mean()
                vol_declining = recent_vol < prior_vol * 0.7

            atr = Indicators.atr(df['high'], df['low'], close, 14)
            atr_val = atr.iloc[-1] if len(atr) > 0 and not np.isnan(atr.iloc[-1]) else price * 0.02

            # ── Overbought fade (contrarian SHORT) ──
            if rsi_val > 78 and green_streak >= 4:
                conviction = 0.5
                if vol_declining:
                    conviction += 0.2  # exhaustion confirmation
                if green_streak >= 6:
                    conviction += 0.1

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.SHORT,
                    conviction=round(min(conviction, 0.80), 2),
                    entry_price=price,
                    stop_loss=price + 1.5 * atr_val,
                    target=price - 2 * atr_val,
                    reason=f"Contrarian SHORT: RSI={rsi_val:.0f}, {green_streak} green candles"
                           + (", vol exhaustion" if vol_declining else ""),
                    agent_name=self.name,
                )

            # ── Oversold bounce (contrarian LONG) ──
            elif rsi_val < 22 and red_streak >= 4:
                conviction = 0.5
                if vol_declining:
                    conviction += 0.15
                if red_streak >= 6:
                    conviction += 0.1

                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.LONG,
                    conviction=round(min(conviction, 0.75), 2),
                    entry_price=price,
                    stop_loss=price - 1.5 * atr_val,
                    target=price + 2 * atr_val,
                    reason=f"Contrarian LONG: RSI={rsi_val:.0f}, {red_streak} red candles"
                           + (", vol exhaustion" if vol_declining else ""),
                    agent_name=self.name,
                )

        # Check for crowding: if ALL other agents agree on a symbol, warn
        other_signals = {name: sigs for name, sigs in blackboard.signals.items()
                         if name != self.name}
        for symbol in candles_map:
            directions = []
            for agent_sigs in other_signals.values():
                if symbol in agent_sigs:
                    directions.append(agent_sigs[symbol].direction)
            if len(directions) >= 3 and len(set(directions)) == 1:
                logger.info(f"  ⚠️ CROWDING WARNING: {symbol} — all agents agree ({directions[0].value})")

        blackboard.signals[self.name] = signals
        return signals
