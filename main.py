"""
HYDRA-Lite Finance Agent — Main Entry Point.
Runs in PAPER TRADING mode by default (real prices, fake money).
Deployed to Railway, logs to Supabase, uses HYDRA multi-agent swarm.
"""
import os
import sys
import logging
import time
from datetime import datetime, time as dt_time

# Load .env if present (local dev only; Railway uses env vars directly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.broker import BrokerConnection
from src.strategies import ORBStrategy, VWAPMeanReversion, EMASupertrend
from src.ml_filter import MLSignalFilter
from src.agent import TradingAgent
from src.db import SupabaseLogger

# HYDRA agents
from src.agents import (
    RegimeDetector, MomentumAgent, MeanReversionAgent,
    BreakoutAgent, SentimentAgent, ContrarianAgent,
    BullAgent, BearAgent, RiskGuardianAgent, MetaOrchestrator,
)

# Create data directory
os.makedirs("data", exist_ok=True)

# ── Logging setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/agent.log", mode="a", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """Check if NSE is open (9:15 AM – 3:30 PM IST, Mon–Fri)."""
    now = datetime.now()
    if now.weekday() >= 5:  # Saturday/Sunday
        return False
    t = now.time()
    return dt_time(9, 0) <= t <= dt_time(15, 45)


def wait_for_market():
    """Sleep until market opens. Used on Railway to avoid wasting resources."""
    while not is_market_hours():
        now = datetime.now()
        print(f"\r  💤 Market closed | {now.strftime('%Y-%m-%d %H:%M:%S')} | "
              f"Waiting for 9:15 AM IST...", end="", flush=True)
        time.sleep(60)
    print()


def build_hydra(capital: float):
    """Construct the full HYDRA-Lite multi-agent pipeline."""
    # Layer 2: Regime Detection
    regime = RegimeDetector()

    # Layer 3: Strategy Agents (analysts)
    analysts = [
        MomentumAgent(),
        MeanReversionAgent(),
        BreakoutAgent(),
        SentimentAgent(),
        ContrarianAgent(),
    ]

    # Layer 4: Debate Agents
    bull = BullAgent()
    bear = BearAgent()

    # Layer 4a: Risk Guardian (absolute veto power)
    risk_guardian = RiskGuardianAgent(
        max_daily_drawdown=0.03,
        max_positions=3,
        max_stock_exposure_pct=0.10,
    )

    # Layer 5: Meta-Orchestrator (the brain)
    orchestrator = MetaOrchestrator(
        regime_agent=regime,
        analyst_agents=analysts,
        bull_agent=bull,
        bear_agent=bear,
        risk_guardian=risk_guardian,
        capital=capital,
    )

    return orchestrator


def main():
    # ────────── Configuration ──────────
    API_KEY    = os.getenv("KITE_API_KEY",    "paper_mode")
    API_SECRET = os.getenv("KITE_API_SECRET", "paper_mode")
    CAPITAL    = float(os.getenv("INITIAL_CAPITAL", "200000"))
    PAPER      = os.getenv("PAPER_TRADING", "true").lower() == "true"

    WATCHLIST = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "SBIN", "BHARTIARTL", "HINDUNILVR", "ITC", "KOTAKBANK",
        "TATAMOTORS", "AXISBANK", "BAJFINANCE", "MARUTI", "TITAN",
    ]

    # ────────── Initialize ──────────
    db_logger = SupabaseLogger()

    broker = BrokerConnection(API_KEY, API_SECRET,
                              paper_trading=PAPER, db_logger=db_logger)
    broker.authenticate()

    # Build HYDRA multi-agent swarm
    hydra = build_hydra(CAPITAL)

    # Vanilla strategies (kept as fallback, not used when HYDRA is active)
    strategies = [
        ORBStrategy(orb_minutes=15),
        VWAPMeanReversion(rsi_oversold=30, rsi_overbought=70),
        EMASupertrend(fast_ema=9, slow_ema=21),
    ]

    ml_filter = MLSignalFilter()

    agent = TradingAgent(
        broker=broker,
        capital=CAPITAL,
        watchlist=WATCHLIST,
        strategies=strategies,
        ml_filter=ml_filter,
        db_logger=db_logger,
        hydra_orchestrator=hydra,  # ← HYDRA brain enabled
    )

    # ────────── Run Loop ──────────
    while True:
        print("\n" + "=" * 60)
        print("  🐍 HYDRA-Lite Finance Agent")
        print(f"  Mode     : {'PAPER' if PAPER else 'LIVE'}")
        print(f"  Capital  : ₹{CAPITAL:,.0f}")
        print(f"  Supabase : {'✅ Connected' if db_logger.connected else '❌ CSV-only'}")
        print(f"  Brain    : HYDRA-Lite (10 agents)")
        print("=" * 60)

        wait_for_market()

        try:
            agent.start()
        except KeyboardInterrupt:
            agent.stop()
            break
        except Exception as e:
            logger.error(f"Agent crashed: {e}")
            agent.stop()

        print("\n  📅 Session ended. Will restart at next market open.")
        time.sleep(300)


if __name__ == "__main__":
    main()
