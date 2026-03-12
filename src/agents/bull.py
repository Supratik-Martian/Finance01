"""
Bull Agent — aggregates all PRO-trade evidence.
Builds the bull thesis for each symbol from analyst agent signals.
"""
from .base import BaseAgent, Blackboard, DebateCase, Direction

import logging
logger = logging.getLogger(__name__)


class BullAgent(BaseAgent):
    name = "bull"

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        """Build bull case for every symbol that has LONG signals."""
        bull_cases = {}

        # Gather all agent weights
        agent_weights = blackboard.agent_weights or {}

        for symbol in candles_map.keys():
            supporting = []
            total_weighted_conviction = 0.0
            total_weight = 0.0

            for agent_name, agent_signals in blackboard.signals.items():
                if symbol not in agent_signals:
                    continue
                sig = agent_signals[symbol]
                if sig.direction != Direction.LONG:
                    continue

                weight = agent_weights.get(agent_name, 0.5)
                total_weighted_conviction += sig.conviction * weight
                total_weight += weight
                supporting.append(f"{agent_name} ({sig.conviction:.0%}): {sig.reason}")

            if not supporting:
                continue

            avg_conviction = total_weighted_conviction / total_weight if total_weight > 0 else 0

            bull_cases[symbol] = DebateCase(
                symbol=symbol,
                conviction=round(min(avg_conviction, 0.95), 2),
                thesis=f"BULL {symbol}: {len(supporting)} agents support LONG",
                supporting_agents=supporting,
            )

        blackboard.bull_cases = bull_cases
        return {}
