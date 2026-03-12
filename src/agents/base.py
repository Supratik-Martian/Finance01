"""
HYDRA-Lite Agent Base Classes & Blackboard.
All agents implement BaseAgent and communicate through the Blackboard.
"""
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class Regime(Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    CRISIS = "CRISIS"
    UNKNOWN = "UNKNOWN"


class OperatingMode(Enum):
    NORMAL = "NORMAL"
    CAUTIOUS = "CAUTIOUS"
    DEFENSIVE = "DEFENSIVE"
    CRISIS = "CRISIS"
    AGGRESSIVE = "AGGRESSIVE"


@dataclass
class AgentSignal:
    """Signal produced by an analyst agent."""
    symbol: str
    direction: Direction
    conviction: float           # 0.0 – 1.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0
    reason: str = ""
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateCase:
    """Bull or Bear case for a symbol."""
    symbol: str
    conviction: float           # 0.0 – 1.0
    thesis: str                 # human-readable reasoning
    supporting_agents: list = field(default_factory=list)
    risk_factors: list = field(default_factory=list)


@dataclass
class FinalDecision:
    """Output of the Meta-Orchestrator."""
    symbol: str
    direction: Direction
    conviction: float
    quantity: int = 0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0
    reason: str = ""
    vetoed: bool = False
    veto_reason: str = ""


class Blackboard:
    """
    Shared state for all agents. Dictionary-based, auditable.
    Each agent reads from and writes to this board.
    """
    def __init__(self):
        self.regime = {
            "primary": Regime.UNKNOWN,
            "confidence": 0.0,
            "probabilities": {},
            "stability": 0.0,
        }
        self.signals = {}          # {agent_name: {symbol: AgentSignal}}
        self.bull_cases = {}       # {symbol: DebateCase}
        self.bear_cases = {}       # {symbol: DebateCase}
        self.risk_guardian = {
            "veto": False,
            "reason": "",
            "drawdown_pct": 0.0,
        }
        self.decisions = []        # [FinalDecision, ...]
        self.operating_mode = OperatingMode.NORMAL
        self.agent_weights = {}    # {agent_name: float}
        self.portfolio = {
            "open_positions": {},
            "daily_pnl": 0.0,
            "capital": 0.0,
        }

    def clear_signals(self):
        """Reset per-cycle state."""
        self.signals.clear()
        self.bull_cases.clear()
        self.bear_cases.clear()
        self.decisions.clear()
        self.risk_guardian["veto"] = False
        self.risk_guardian["reason"] = ""


class BaseAgent:
    """All HYDRA agents implement this interface."""

    name: str = "base"
    preferred_regimes: list = []
    anti_regimes: list = []

    def __init__(self):
        self._hit_history = []  # rolling accuracy: True=hit, False=miss
        self._max_history = 30

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        """
        Run analysis. Write results to blackboard.
        candles_map = {symbol: DataFrame with OHLCV columns}
        Returns dict of signals keyed by symbol.
        """
        raise NotImplementedError

    def regime_fit(self, regime: Regime) -> float:
        """How well does the current regime suit this agent? 0.0 – 1.0"""
        if regime in self.anti_regimes:
            return 0.1
        if regime in self.preferred_regimes:
            return 1.0
        return 0.5  # neutral

    def record_outcome(self, was_profitable: bool):
        """Track rolling accuracy."""
        self._hit_history.append(was_profitable)
        if len(self._hit_history) > self._max_history:
            self._hit_history.pop(0)

    @property
    def rolling_accuracy(self) -> float:
        if not self._hit_history:
            return 0.5  # prior: assume 50%
        return sum(self._hit_history) / len(self._hit_history)

    @property
    def rolling_sharpe_proxy(self) -> float:
        """Simple proxy: accuracy-based, centered at 0."""
        return (self.rolling_accuracy - 0.5) * 4  # maps 0.5→0, 0.75→1, 1.0→2

    def self_assess(self) -> dict:
        return {
            "agent_name": self.name,
            "rolling_sharpe": round(self.rolling_sharpe_proxy, 2),
            "win_rate": round(self.rolling_accuracy * 100, 1),
            "total_signals": len(self._hit_history),
        }
