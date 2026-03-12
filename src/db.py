"""
Supabase logger — writes orders, trades, heartbeats, and session data.
Falls back to CSV if Supabase is unreachable.
"""
import os
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import supabase
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    logger.warning("supabase package not installed — CSV-only mode")


class SupabaseLogger:
    def __init__(self):
        self.client: Client | None = None
        self.session_id: str | None = None

        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")

        if HAS_SUPABASE and url and key:
            try:
                self.client = create_client(url, key)
                logger.info("✅ Supabase connected")
            except Exception as e:
                logger.error(f"Supabase init failed: {e}")
                self.client = None
        else:
            logger.info("Supabase credentials not set — CSV-only mode")

    @property
    def connected(self) -> bool:
        return self.client is not None

    # ─── Session ────────────────────────────────

    def start_session(self, initial_capital: float) -> str | None:
        if not self.connected:
            return None
        try:
            result = self.client.table("trading_sessions").insert({
                "initial_capital": initial_capital,
                "status": "running",
            }).execute()
            self.session_id = result.data[0]["id"]
            logger.info(f"Session started: {self.session_id}")
            return self.session_id
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return None

    def end_session(self, final_capital: float, total_pnl: float,
                    total_trades: int, win_rate: float):
        if not self.connected or not self.session_id:
            return
        try:
            self.client.table("trading_sessions").update({
                "ended_at": datetime.now().isoformat(),
                "final_capital": final_capital,
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "status": "stopped",
            }).eq("id", self.session_id).execute()
        except Exception as e:
            logger.error(f"Failed to end session: {e}")

    # ─── Orders ─────────────────────────────────

    def log_order(self, symbol: str, side: str, qty: int, price: float,
                  order_type: str = "MARKET", tag: str = "", status: str = "EXECUTED"):
        row = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": float(price) if price else 0,
            "order_type": order_type,
            "tag": tag,
            "status": status,
        }
        if self.connected and self.session_id:
            try:
                row["session_id"] = self.session_id
                self.client.table("orders").insert(row).execute()
            except Exception as e:
                logger.error(f"Supabase order log failed: {e}")
                self._csv_fallback("data/orders_fallback.csv", row)
        else:
            self._csv_fallback("data/orders_fallback.csv", row)

    # ─── Trades ─────────────────────────────────

    def log_trade(self, symbol: str, side: str, qty: int,
                  entry_price: float, exit_price: float,
                  gross_pnl: float, costs: float, net_pnl: float,
                  entry_time: str, reason: str = "", agent: str = ""):
        row = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_pnl": gross_pnl,
            "costs": costs,
            "net_pnl": net_pnl,
            "entry_time": entry_time,
            "exit_time": datetime.now().isoformat(),
            "reason": reason,
            "strategy_agent": agent,
        }
        if self.connected and self.session_id:
            try:
                row["session_id"] = self.session_id
                self.client.table("trades").insert(row).execute()
            except Exception as e:
                logger.error(f"Supabase trade log failed: {e}")
                self._csv_fallback("data/trades_fallback.csv", row)
        else:
            self._csv_fallback("data/trades_fallback.csv", row)

    # ─── Heartbeat ──────────────────────────────

    def log_heartbeat(self, open_positions: int, daily_pnl: float,
                      capital: float, regime: str = "UNKNOWN",
                      operating_mode: str = "NORMAL",
                      watchlist_prices: dict = None):
        if not self.connected or not self.session_id:
            return
        try:
            import json
            self.client.table("agent_heartbeat").insert({
                "session_id": self.session_id,
                "open_positions": open_positions,
                "daily_pnl": daily_pnl,
                "capital": capital,
                "regime": regime,
                "operating_mode": operating_mode,
                "watchlist_prices": json.dumps(watchlist_prices or {}),
            }).execute()
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

    # ─── Agent Scores ───────────────────────────

    def log_agent_scores(self, scores: list[dict]):
        """scores = [{"agent_name": "momentum", "rolling_sharpe": 1.2, ...}]"""
        if not self.connected or not self.session_id:
            return
        try:
            rows = [{**s, "session_id": self.session_id} for s in scores]
            self.client.table("agent_scores").insert(rows).execute()
        except Exception as e:
            logger.error(f"Agent scores log failed: {e}")

    # ─── CSV Fallback ───────────────────────────

    def _csv_fallback(self, path: str, row: dict):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_exists = os.path.exists(path)
        try:
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            logger.error(f"CSV fallback failed: {e}")
