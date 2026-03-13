"""
Broker connection layer.
- Paper Trading: records orders locally, uses real prices from data stream.
- Live Trading: routes through Kite Connect API to NSE.
"""
import logging
import uuid
import csv
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class BrokerConnection:
    def __init__(self, api_key, api_secret, paper_trading=True, db_logger=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper_trading = paper_trading
        self.data_stream = None  # will be set by agent after creation
        self.db = db_logger      # SupabaseLogger instance

        if not self.paper_trading:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=api_key)
        else:
            self.kite = None
            logger.info("═" * 50)
            logger.info("  PAPER TRADING MODE — NO REAL MONEY AT RISK")
            logger.info("═" * 50)

        self.paper_orders = []       # full order history
        self.paper_positions = {}    # {symbol: {side, qty, entry_price}}

    def authenticate(self, request_token=None):
        if self.paper_trading:
            logger.info("Paper auth OK.")
            return {"access_token": "paper_trading_token"}

        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        self.kite.set_access_token(data["access_token"])
        logger.info("Kite authenticated.")
        return data

    def get_instruments(self, exchange="NSE"):
        if self.paper_trading:
            return {}   # agent builds its own token map for paper mode
        return {i['tradingsymbol']: i for i in self.kite.instruments(exchange)}

    # ──────── Price queries ────────

    def get_ltp(self, symbols: list) -> dict:
        """
        Returns {key: {"last_price": float}} for each symbol.
        In paper mode, pulls real prices from the yfinance data stream.
        """
        if self.paper_trading:
            result = {}
            for s in symbols:
                # s could be "NSE:RELIANCE" or just "RELIANCE"
                clean = s.replace("NSE:", "")
                price = 0.0
                if self.data_stream:
                    price = self.data_stream.get_ltp(clean)
                result[s] = {"last_price": price}
            return result

        return self.kite.ltp(symbols)

    # ──────── Order management ────────

    def place_order(self, symbol, qty, side, order_type="MARKET",
                    price=None, trigger_price=None, tag="algo"):
        """Place an order. Paper mode records it locally."""
        if self.paper_trading:
            order_id = str(uuid.uuid4())[:8]

            # For MARKET orders in paper mode, use the current real price
            exec_price = price
            if order_type == "MARKET" and self.data_stream:
                live = self.data_stream.get_ltp(symbol)
                if live > 0:
                    exec_price = live

            order = {
                "id": order_id,
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "price": exec_price,
                "trigger": trigger_price,
                "tag": tag,
                "status": "EXECUTED" if order_type == "MARKET" else "PENDING",
            }
            self.paper_orders.append(order)
            self._save_orders_csv()

            # Log to Supabase
            if self.db:
                self.db.log_order(
                    symbol=symbol, side=side, qty=qty,
                    price=exec_price or 0, order_type=order_type,
                    tag=tag, status=order["status"]
                )

            logger.info(
                f"[PAPER] {side} {qty}x {symbol} @ ₹{exec_price or '?':.2f} "
                f"({tag}) → {order_id}"
            )
            return order_id

        # ── Live Kite order ──
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=(
                    self.kite.TRANSACTION_TYPE_BUY if side == "BUY"
                    else self.kite.TRANSACTION_TYPE_SELL
                ),
                quantity=qty,
                product=self.kite.PRODUCT_MIS,
                order_type=getattr(self.kite, f"ORDER_TYPE_{order_type}"),
                price=price,
                trigger_price=trigger_price,
                tag=tag
            )
            logger.info(f"Order placed: {order_id}")
            return order_id
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None

    def get_positions(self):
        if self.paper_trading:
            return []
        return self.kite.positions()["day"]

    def square_off_all(self):
        if self.paper_trading:
            logger.info("[PAPER] All positions squared off.")
            return

        positions = self.get_positions()
        for pos in positions:
            if pos["quantity"] != 0:
                side = "SELL" if pos["quantity"] > 0 else "BUY"
                self.place_order(
                    symbol=pos["tradingsymbol"],
                    qty=abs(pos["quantity"]),
                    side=side,
                    tag="squareoff"
                )

    # ──────── CSV persistence ────────

    def _save_orders_csv(self):
        os.makedirs("data", exist_ok=True)
        path = "data/paper_orders.csv"
        fieldnames = ["id", "timestamp", "symbol", "qty", "side",
                      "type", "price", "trigger", "tag", "status"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.paper_orders)
        except Exception as e:
            logger.error(f"Failed to write orders CSV: {e}")
