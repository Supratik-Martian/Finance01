"""
Meta-Orchestrator — the brain of HYDRA-Lite.
Dynamic agent weighting, bull/bear debate resolution, operating mode selection.
"""
from .base import (
    BaseAgent, Blackboard, Regime, OperatingMode,
    FinalDecision, Direction,
)

import logging
logger = logging.getLogger(__name__)


class MetaOrchestrator:
    """
    NOT a BaseAgent — this is the conductor.
    Holds all agent references. Caller just passes data, gets decisions.
    """

    def __init__(self, regime_agent, analyst_agents: list[BaseAgent],
                 bull_agent, bear_agent,
                 risk_guardian, capital: float = 200000):
        self.regime_agent = regime_agent
        self.analysts = analyst_agents  # momentum, mean_rev, breakout, sentiment, contrarian
        self.bull_agent = bull_agent
        self.bear_agent = bear_agent
        self.risk_guardian = risk_guardian
        self.capital = capital
        self.blackboard = Blackboard()

    def run_cycle(self, candles_map: dict,
                  open_positions: dict, daily_pnl: float) -> list[FinalDecision]:
        """
        Full HYDRA decision cycle:
        1. Clear → 2. Regime → 3. Weights → 4. Analysts →
        5. Bull/Bear debate → 6. Resolve → 7. Risk Guardian
        """
        self.blackboard.clear_signals()
        self.blackboard.portfolio = {
            "open_positions": open_positions,
            "daily_pnl": daily_pnl,
            "capital": self.capital,
        }

        # 1. Regime Detection
        self.regime_agent.analyze(candles_map, self.blackboard)
        regime = self.blackboard.regime.get("primary", Regime.UNKNOWN)

        # 2. Dynamic agent weights
        self._compute_agent_weights(regime)

        # 3. Operating mode
        self._select_operating_mode(daily_pnl)

        if self.blackboard.operating_mode in [OperatingMode.CRISIS, OperatingMode.DEFENSIVE]:
            logger.info(f"  🛡️ Mode: {self.blackboard.operating_mode.value} — no new trades")
            return []

        # 4. Analyst agents
        for agent in self.analysts:
            try:
                agent.analyze(candles_map, self.blackboard)
            except Exception as e:
                logger.error(f"  Agent {agent.name} failed: {e}")

        # 5. Bull/Bear debate
        self.bull_agent.analyze(candles_map, self.blackboard)
        self.bear_agent.analyze(candles_map, self.blackboard)

        # 6. Resolve → decisions
        decisions = self._resolve_debate(candles_map)

        # 7. Risk Guardian (can veto)
        decisions = self.risk_guardian.validate_decisions(decisions, self.blackboard)

        approved = [d for d in decisions if not d.vetoed]

        for d in decisions:
            status = "✅" if not d.vetoed else f"❌ {d.veto_reason}"
            logger.info(f"  {d.symbol} {d.direction.value} conv={d.conviction:.0%} → {status}")

        return approved

    def _compute_agent_weights(self, regime: Regime):
        """Dynamic weighting: regime_fit × rolling_accuracy × base_weight"""
        weights = {}
        for agent in self.analysts:
            fit = agent.regime_fit(regime)
            accuracy = agent.rolling_accuracy
            base = 1.0

            # Contrarian always keeps minimum 5% allocation (HYDRA P6)
            if agent.name == "contrarian":
                base = max(0.3, base)

            weight = fit * accuracy * base
            weights[agent.name] = round(max(0.05, weight), 2)

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total, 2) for k, v in weights.items()}

        self.blackboard.agent_weights = weights
        logger.info(f"  ⚖️ Agent weights: {weights}")

    def _select_operating_mode(self, daily_pnl: float):
        """Set operating mode based on drawdown, regime, and confidence."""
        drawdown_pct = abs(daily_pnl / self.capital) if self.capital > 0 else 0
        regime = self.blackboard.regime.get("primary", Regime.UNKNOWN)
        confidence = self.blackboard.regime.get("confidence", 0)

        if drawdown_pct >= 0.04 or regime == Regime.CRISIS:
            self.blackboard.operating_mode = OperatingMode.CRISIS
        elif drawdown_pct >= 0.02 or regime == Regime.HIGH_VOLATILITY:
            self.blackboard.operating_mode = OperatingMode.DEFENSIVE
        elif drawdown_pct >= 0.01 or confidence < 0.4:
            self.blackboard.operating_mode = OperatingMode.CAUTIOUS
        elif confidence > 0.7 and regime in [Regime.TRENDING_BULL, Regime.MEAN_REVERTING]:
            self.blackboard.operating_mode = OperatingMode.AGGRESSIVE
        else:
            self.blackboard.operating_mode = OperatingMode.NORMAL

        logger.info(f"  🎚️ Mode: {self.blackboard.operating_mode.value}")

    def _resolve_debate(self, candles_map: dict) -> list[FinalDecision]:
        """
        For each symbol with a bull or bear case, resolve the debate.
        net_conviction = bull - bear → determines direction and size.
        """
        decisions = []
        mode = self.blackboard.operating_mode

        all_symbols = set(self.blackboard.bull_cases.keys()) | set(self.blackboard.bear_cases.keys())

        for symbol in all_symbols:
            bull = self.blackboard.bull_cases.get(symbol)
            bear = self.blackboard.bear_cases.get(symbol)

            bull_conv = bull.conviction if bull else 0.0
            bear_conv = bear.conviction if bear else 0.0
            net = bull_conv - bear_conv

            # Skip if already in position
            if symbol in self.blackboard.portfolio["open_positions"]:
                continue

            # Decision thresholds
            if net > 0.3:
                direction = Direction.LONG
                conviction = net
            elif net > 0.0:
                direction = Direction.LONG
                conviction = net * 0.5  # reduced conviction
            elif net < -0.3:
                direction = Direction.SHORT
                conviction = abs(net) * 0.8  # shorts need more conviction
            else:
                continue  # ABSTAIN: too uncertain

            # Get entry details from best supporting signal
            entry, sl, target = self._get_best_entry(symbol, direction)
            if entry <= 0:
                if symbol in candles_map:
                    entry = candles_map[symbol]['close'].iloc[-1]
                else:
                    continue

            # Position sizing based on mode
            qty = self._size_position(entry, conviction, mode)
            if qty <= 0:
                continue

            reason_parts = []
            if bull:
                reason_parts.append(f"Bull({bull_conv:.0%})")
            if bear:
                reason_parts.append(f"Bear({bear_conv:.0%})")
            reason_parts.append(f"Net={net:+.0%}")

            decisions.append(FinalDecision(
                symbol=symbol,
                direction=direction,
                conviction=round(conviction, 2),
                quantity=qty,
                entry_price=entry,
                stop_loss=sl if sl > 0 else entry * (0.98 if direction == Direction.LONG else 1.02),
                target=target if target > 0 else entry * (1.03 if direction == Direction.LONG else 0.97),
                reason=" | ".join(reason_parts),
            ))

        return decisions

    def _get_best_entry(self, symbol: str, direction: Direction):
        """Find the best entry/SL/target from the supporting agent signals."""
        best_conv = 0
        entry, sl, target = 0, 0, 0

        for agent_name, sigs in self.blackboard.signals.items():
            if symbol not in sigs:
                continue
            sig = sigs[symbol]
            if sig.direction == direction and sig.conviction > best_conv:
                best_conv = sig.conviction
                entry = sig.entry_price
                sl = sig.stop_loss
                target = sig.target

        return entry, sl, target

    def _size_position(self, price: float, conviction: float,
                       mode: OperatingMode) -> int:
        """Kelly-inspired position sizing with mode adjustment."""
        if price <= 0:
            return 0

        # Base: risk 2% of capital per trade
        risk_pct = 0.02 * conviction

        # Mode multiplier
        mode_mult = {
            OperatingMode.AGGRESSIVE: 1.3,
            OperatingMode.NORMAL: 1.0,
            OperatingMode.CAUTIOUS: 0.5,
            OperatingMode.DEFENSIVE: 0.0,
            OperatingMode.CRISIS: 0.0,
        }.get(mode, 1.0)

        position_value = self.capital * risk_pct * mode_mult
        qty = int(position_value / price)
        return max(0, qty)
