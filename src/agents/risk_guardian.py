"""
Risk Guardian Agent — has ABSOLUTE VETO POWER.
No trade executes if the Risk Guardian says no.
Checks drawdown, position limits, time rules, and crowding.
"""
from datetime import datetime, time as dt_time
from .base import BaseAgent, Blackboard, FinalDecision, OperatingMode

import logging
logger = logging.getLogger(__name__)


class RiskGuardianAgent(BaseAgent):
    name = "risk_guardian"

    def __init__(self, max_daily_drawdown: float = 0.03,
                 max_positions: int = 3,
                 max_stock_exposure_pct: float = 0.10,
                 no_entry_after: dt_time = dt_time(14, 30),
                 force_exit_at: dt_time = dt_time(15, 10)):
        super().__init__()
        self.max_daily_drawdown = max_daily_drawdown
        self.max_positions = max_positions
        self.max_stock_exposure_pct = max_stock_exposure_pct
        self.no_entry_after = no_entry_after
        self.force_exit_at = force_exit_at

    def validate_decisions(self, decisions: list[FinalDecision],
                           blackboard: Blackboard) -> list[FinalDecision]:
        """
        Final gatekeeper. Can VETO any trade.
        Returns filtered list with vetoed decisions marked.
        """
        capital = blackboard.portfolio.get("capital", 200000)
        open_positions = blackboard.portfolio.get("open_positions", {})
        daily_pnl = blackboard.portfolio.get("daily_pnl", 0.0)
        now = datetime.now().time()

        drawdown_pct = abs(daily_pnl / capital) if capital > 0 else 0

        # Update blackboard
        blackboard.risk_guardian["drawdown_pct"] = drawdown_pct

        # ── HARD STOP: flatten everything ──
        if drawdown_pct >= 0.05:
            logger.warning("🛑 RISK GUARDIAN: Drawdown > 5% — CRISIS MODE")
            blackboard.operating_mode = OperatingMode.CRISIS
            blackboard.risk_guardian["veto"] = True
            blackboard.risk_guardian["reason"] = "Drawdown > 5%: FLATTEN ALL"
            for d in decisions:
                d.vetoed = True
                d.veto_reason = "CRISIS: drawdown > 5%"
            return decisions

        # ── HALT new entries ──
        if drawdown_pct >= self.max_daily_drawdown:
            logger.warning(f"⚠️ RISK: Drawdown {drawdown_pct:.1%} > {self.max_daily_drawdown:.0%}")
            for d in decisions:
                d.vetoed = True
                d.veto_reason = f"Daily drawdown limit ({drawdown_pct:.1%})"
            return decisions

        # ── Time rules ──
        if now >= self.force_exit_at:
            for d in decisions:
                d.vetoed = True
                d.veto_reason = "Past force-exit time (15:10)"
            return decisions

        if now >= self.no_entry_after:
            for d in decisions:
                d.vetoed = True
                d.veto_reason = "No new entries after 14:30"
            return decisions

        # ── Per-decision checks ──
        for d in decisions:
            if d.vetoed:
                continue

            # Max positions
            if len(open_positions) >= self.max_positions:
                d.vetoed = True
                d.veto_reason = f"Max positions reached ({self.max_positions})"
                continue

            # Single stock exposure
            position_value = d.entry_price * d.quantity
            if capital > 0 and position_value / capital > self.max_stock_exposure_pct:
                d.vetoed = True
                d.veto_reason = f"Exposure {position_value / capital:.0%} > {self.max_stock_exposure_pct:.0%}"
                continue

            # Crowding: if ALL agents unanimously agree, reduce size 30%
            bull = blackboard.bull_cases.get(d.symbol)
            bear = blackboard.bear_cases.get(d.symbol)
            if bull and not bear:
                if len(bull.supporting_agents) >= 4:
                    d.quantity = max(1, int(d.quantity * 0.7))
                    d.reason += " [SIZE -30%: crowding risk]"
                    logger.info(f"  ⚠️ CROWDING: {d.symbol} — reduced size 30%")

        return decisions
