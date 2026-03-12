"""
Bear Agent — aggregates all ANTI-trade evidence. Stress-tests the bull thesis.
Gives extra weight to contrarian signals, risk warnings, and regime mismatches.
"""
from .base import BaseAgent, Blackboard, DebateCase, Direction

import logging
logger = logging.getLogger(__name__)


class BearAgent(BaseAgent):
    name = "bear"

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        """Build bear case for every symbol, including counter-arguments."""
        bear_cases = {}

        agent_weights = blackboard.agent_weights or {}
        regime = blackboard.regime.get("primary")

        for symbol in candles_map.keys():
            risk_factors = []
            total_weighted_conviction = 0.0
            total_weight = 0.0

            # Gather SHORT signals + contrarian warnings
            for agent_name, agent_signals in blackboard.signals.items():
                if symbol not in agent_signals:
                    continue
                sig = agent_signals[symbol]
                if sig.direction != Direction.SHORT:
                    continue

                # Contrarian gets 1.5x weight in bear case
                weight = agent_weights.get(agent_name, 0.5)
                if agent_name == "contrarian":
                    weight *= 1.5

                total_weighted_conviction += sig.conviction * weight
                total_weight += weight
                risk_factors.append(f"{agent_name} ({sig.conviction:.0%}): {sig.reason}")

            # Check regime mismatch: if symbol has LONG signals in a BEAR regime
            from .base import Regime
            if regime in [Regime.TRENDING_BEAR, Regime.CRISIS, Regime.HIGH_VOLATILITY]:
                risk_factors.append(f"⚠ Hostile regime: {regime.value}")
                total_weighted_conviction += 0.2
                total_weight += 0.5

            if not risk_factors:
                continue

            avg_conviction = total_weighted_conviction / total_weight if total_weight > 0 else 0

            bear_cases[symbol] = DebateCase(
                symbol=symbol,
                conviction=round(min(avg_conviction, 0.95), 2),
                thesis=f"BEAR {symbol}: {len(risk_factors)} risk factors",
                risk_factors=risk_factors,
            )

        blackboard.bear_cases = bear_cases
        return {}
