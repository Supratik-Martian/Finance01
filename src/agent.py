"""
Main Trading Agent — Orchestrator.
Connects real market data → strategies → risk manager → paper/live broker.
Saves all trades to CSV + Supabase with timestamps and P&L.
Supports HYDRA-Lite multi-agent swarm via MetaOrchestrator.
"""
import time as time_module
import csv
import os
import logging
from datetime import datetime
from .broker import BrokerConnection
from .data_stream import MarketDataStream
from .strategies import Signal, TradeSignal
from .risk_manager import RiskManager
from .ml_filter import MLSignalFilter
from .indicators import Indicators
from .db import SupabaseLogger

logger = logging.getLogger(__name__)


class TradingAgent:
    def __init__(self, broker: BrokerConnection, capital: float,
                 watchlist: list, strategies: list,
                 ml_filter: MLSignalFilter = None,
                 db_logger: SupabaseLogger = None,
                 hydra_orchestrator=None):

        self.broker = broker
        self.capital = capital
        self.watchlist = watchlist
        self.strategies = strategies
        self.ml_filter = ml_filter
        self.risk_mgr = RiskManager(capital)
        self.db = db_logger or SupabaseLogger()
        self.hydra = hydra_orchestrator  # MetaOrchestrator or None
        self.data_stream = None
        self.running = False

        # State
        self.candle_interval = 5   # minutes
        self.last_signal_time = {}
        self.min_signal_gap = 300  # seconds between signals for same stock
        self._heartbeat_counter = 0
        self._last_hydra_run = 0   # timestamp of last HYDRA cycle
        self._hydra_interval = 60  # seconds between HYDRA cycles

        # Token map: simple integer tokens for each symbol
        self.token_map = {1000 + i: sym for i, sym in enumerate(watchlist)}

        logger.info("=" * 60)
        logger.info(f"  Agent initialized | Capital: ₹{capital:,.0f}")
        logger.info(f"  Mode: {'PAPER' if broker.paper_trading else 'LIVE'}")
        logger.info(f"  Brain: {'HYDRA-Lite' if hydra_orchestrator else 'Vanilla'}")
        logger.info(f"  Watchlist: {', '.join(watchlist)}")
        logger.info("=" * 60)

    def start(self):
        """Main loop"""
        print("\n" + "=" * 60)
        print("  🚀 TRADING AGENT STARTED")
        print(f"  Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Mode : {'PAPER TRADING' if self.broker.paper_trading else 'LIVE'}")
        print("=" * 60 + "\n")

        self.running = True

        # Start Supabase session
        self.db.start_session(self.capital)

        # Create data stream
        self.data_stream = MarketDataStream(
            broker=self.broker,
            watchlist=self.watchlist,
            token_map=self.token_map,
            paper_trading=self.broker.paper_trading,
        )
        self.data_stream.on_data(self._on_tick)

        # Let broker access data stream for live prices
        self.broker.data_stream = self.data_stream

        self.data_stream.start()

        print("  ⏳ Waiting for market data to arrive (first batch in ~30s)...\n")

        # Main monitoring loop
        try:
            while self.running:
                self._check_positions()
                self._check_force_exit()
                self._log_status_line()
                self._send_heartbeat()
                time_module.sleep(5)
        except KeyboardInterrupt:
            self.stop()

    def _on_tick(self, ticks):
        """Called when new data arrives"""
        # ── HYDRA Mode: run full multi-agent cycle ──
        if self.hydra:
            now_ts = datetime.now().timestamp()
            if now_ts - self._last_hydra_run >= self._hydra_interval:
                self._last_hydra_run = now_ts
                self._run_hydra_cycle()
            return

        # ── Vanilla Mode: old strategy-per-tick evaluation ──
        for tick in ticks:
            token = tick['instrument_token']
            symbol = self.token_map.get(token)
            if not symbol:
                continue

            candles = self.data_stream.build_candles(token, self.candle_interval)

            if candles is None or len(candles) < 5:
                continue

            # Rate limit signals
            now = datetime.now().timestamp()
            if symbol in self.last_signal_time:
                if now - self.last_signal_time[symbol] < self.min_signal_gap:
                    continue

            self._evaluate_strategies(candles, symbol)

    def _run_hydra_cycle(self):
        """Run the full HYDRA multi-agent decision cycle."""
        from .agents.base import Direction

        # Build candle maps for all symbols with enough data
        candles_map = {}
        for token, symbol in self.token_map.items():
            candles = self.data_stream.build_candles(token, self.candle_interval)
            if candles is not None and len(candles) >= 10:
                candles_map[symbol] = candles

        if not candles_map:
            return

        logger.info(f"\n{'─' * 50}")
        logger.info(f"  🐉 HYDRA CYCLE | {len(candles_map)} stocks | {datetime.now().strftime('%H:%M:%S')}")

        # Run the orchestrator (it handles all agents internally)
        decisions = self.hydra.run_cycle(
            candles_map=candles_map,
            open_positions=dict(self.risk_mgr.open_positions),
            daily_pnl=self.risk_mgr.daily_pnl,
        )

        # Execute approved decisions
        for decision in decisions:
            side = "BUY" if decision.direction == Direction.LONG else "SELL"
            emoji = "🟢" if side == "BUY" else "🔴"

            print(f"\n{emoji} HYDRA {side} {decision.symbol}")
            print(f"  Conviction : {decision.conviction:.0%}")
            print(f"  Entry      : ₹{decision.entry_price:.2f}")
            print(f"  Stop Loss  : ₹{decision.stop_loss:.2f}")
            print(f"  Target     : ₹{decision.target:.2f}")
            print(f"  Qty        : {decision.quantity}")
            print(f"  Reason     : {decision.reason}")

            order_id = self.broker.place_order(
                symbol=decision.symbol, qty=decision.quantity,
                side=side, order_type="MARKET", tag="hydra"
            )

            if order_id:
                self.risk_mgr.open_positions[decision.symbol] = {
                    'side': side,
                    'qty': decision.quantity,
                    'entry': decision.entry_price,
                    'stop_loss': decision.stop_loss,
                    'target': decision.target,
                    'order_id': order_id,
                    'sl_order_id': None,
                    'timestamp': datetime.now(),
                }
                print(f"  ✅ Order {order_id}")

    def _evaluate_strategies(self, candles, symbol):
        can_trade, reason = self.risk_mgr.can_trade()
        if not can_trade:
            return

        signals = []
        for strategy in self.strategies:
            try:
                signal = strategy.generate_signal(candles, symbol)
                if signal:
                    signals.append(signal)
            except Exception:
                pass   # strategy may fail on thin data, skip

        if not signals:
            return

        best_signal = max(signals, key=lambda s: s.confidence)

        # ML filter
        if self.ml_filter and self.ml_filter.is_trained:
            ml_conf = self.ml_filter.predict_confidence(candles)
            old = best_signal.confidence
            best_signal.confidence = 0.6 * old + 0.4 * ml_conf
            logger.info(f"  ML: {old:.2f} → {best_signal.confidence:.2f}")

        valid, _ = self.risk_mgr.validate_signal(best_signal)
        if not valid:
            logger.info(f"  ❌ {symbol} rejected by risk manager.")
            return

        qty = self.risk_mgr.calculate_position_size(best_signal)
        if qty <= 0:
            return

        best_signal.quantity = qty
        self._execute_signal(best_signal)
        self.last_signal_time[symbol] = datetime.now().timestamp()

    def _execute_signal(self, signal: TradeSignal):
        side = "BUY" if signal.signal == Signal.BUY else "SELL"
        emoji = "🟢" if side == "BUY" else "🔴"

        print(f"\n{emoji} {side} {signal.symbol}")
        print(f"  Reason     : {signal.reason}")
        print(f"  Entry      : ₹{signal.entry_price:.2f}")
        print(f"  Stop Loss  : ₹{signal.stop_loss:.2f}")
        print(f"  Target     : ₹{signal.target:.2f}")
        print(f"  Qty        : {signal.quantity}")
        print(f"  Confidence : {signal.confidence:.2f}")

        order_id = self.broker.place_order(
            symbol=signal.symbol, qty=signal.quantity,
            side=side, order_type="MARKET", tag="entry"
        )

        if order_id:
            sl_side = "SELL" if side == "BUY" else "BUY"
            sl_order_id = self.broker.place_order(
                symbol=signal.symbol, qty=signal.quantity,
                side=sl_side, order_type="SL",
                trigger_price=signal.stop_loss,
                price=signal.stop_loss * (0.999 if sl_side == "SELL" else 1.001),
                tag="stoploss"
            )

            self.risk_mgr.open_positions[signal.symbol] = {
                'side': side,
                'qty': signal.quantity,
                'entry': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'target': signal.target,
                'order_id': order_id,
                'sl_order_id': sl_order_id,
                'timestamp': datetime.now(),
            }

            self.risk_mgr.record_trade(signal, signal.quantity, signal.entry_price)
            print(f"  ✅ Order {order_id}")

    def _check_positions(self):
        positions = list(self.risk_mgr.open_positions.items())
        if not positions:
            return

        for symbol, pos in positions:
            price = self.data_stream.get_ltp(symbol)
            if price <= 0:
                continue

            pnl_pct = (
                (price - pos['entry']) / pos['entry'] * 100
                if pos['side'] == 'BUY'
                else (pos['entry'] - price) / pos['entry'] * 100
            )

            # Target hit
            if ((pos['side'] == 'BUY' and price >= pos['target']) or
                    (pos['side'] == 'SELL' and price <= pos['target'])):
                print(f"\n🎯 TARGET HIT: {symbol} ₹{price:.2f}  (+{pnl_pct:.2f}%)")
                self._close_position(symbol, price, "target_hit")
                continue

            # Stop loss hit
            if ((pos['side'] == 'BUY' and price <= pos['stop_loss']) or
                    (pos['side'] == 'SELL' and price >= pos['stop_loss'])):
                print(f"\n💥 STOP LOSS: {symbol} ₹{price:.2f}  ({pnl_pct:+.2f}%)")
                self._close_position(symbol, price, "sl_hit")
                continue

            # Trailing stop update (if enough candles)
            token = {v: k for k, v in self.token_map.items()}.get(symbol)
            if token and token in self.data_stream.candles:
                c = self.data_stream.candles[token]
                if len(c) > 14:
                    try:
                        atr_val = Indicators.atr(c['high'], c['low'], c['close'], 14).iloc[-1]
                        if str(atr_val) != 'nan':
                            self.risk_mgr.update_trailing_stop(symbol, price, atr_val)
                    except Exception:
                        pass

    def _close_position(self, symbol, price, reason):
        if symbol not in self.risk_mgr.open_positions:
            return

        pos = self.risk_mgr.open_positions[symbol]
        close_side = "SELL" if pos['side'] == "BUY" else "BUY"

        self.broker.place_order(
            symbol=symbol, qty=pos['qty'],
            side=close_side, order_type="MARKET", tag=reason
        )

        if not self.broker.paper_trading and pos.get('sl_order_id'):
            try:
                self.broker.kite.cancel_order(variety="regular", order_id=pos['sl_order_id'])
            except Exception:
                pass

        # Log trade to Supabase before removing from open_positions
        entry_time = pos.get('timestamp', datetime.now()).isoformat()
        gross_pnl = (price - pos['entry']) * pos['qty']
        if pos['side'] == 'SELL':
            gross_pnl = -gross_pnl
        turnover = (pos['entry'] + price) * pos['qty']
        costs = 40.0 + turnover * 0.0003
        net_pnl = gross_pnl - costs

        self.db.log_trade(
            symbol=symbol, side=pos['side'], qty=pos['qty'],
            entry_price=pos['entry'], exit_price=price,
            gross_pnl=gross_pnl, costs=costs, net_pnl=net_pnl,
            entry_time=entry_time, reason=reason,
        )

        self.risk_mgr.close_position_record(symbol, price)
        del self.risk_mgr.open_positions[symbol]

    def _check_force_exit(self):
        if self.risk_mgr.should_force_exit():
            if self.risk_mgr.open_positions:
                print("\n⏰ FORCE EXIT — Market closing soon")
                for sym in list(self.risk_mgr.open_positions.keys()):
                    price = self.data_stream.get_ltp(sym)
                    if price <= 0:
                        price = self.risk_mgr.open_positions[sym]['entry']
                    self._close_position(sym, price, "force_exit")
                self.broker.square_off_all()

    def _log_status_line(self):
        """Periodic one-liner to show the agent is alive."""
        n_pos = len(self.risk_mgr.open_positions)
        n_signals = self.risk_mgr.trades_today
        prices_known = len(self.data_stream.latest_prices) if self.data_stream else 0
        if prices_known > 0:
            sample = list(self.data_stream.latest_prices.items())[:3]
            price_str = "  ".join(f"{s}: ₹{p:.2f}" for s, p in sample)
            print(
                f"\r  📊 Prices({prices_known}) | "
                f"Trades: {n_signals} | Open: {n_pos} | "
                f"P&L: ₹{self.risk_mgr.daily_pnl:+,.2f} | "
                f"{price_str}",
                end="", flush=True
            )

    def _send_heartbeat(self):
        """Send heartbeat to Supabase every ~30s (every 6 loops × 5s)"""
        self._heartbeat_counter += 1
        if self._heartbeat_counter % 6 != 0:
            return
        
        regime_str = "UNKNOWN"
        mode_str = "NORMAL"
        if self.hydra:
            reg = self.hydra.blackboard.regime.get("primary")
            regime_str = reg.value if hasattr(reg, 'value') else str(reg)
            mode = self.hydra.blackboard.operating_mode
            mode_str = mode.value if hasattr(mode, 'value') else str(mode)

        prices = dict(self.data_stream.latest_prices) if self.data_stream else {}
        self.db.log_heartbeat(
            open_positions=len(self.risk_mgr.open_positions),
            daily_pnl=self.risk_mgr.daily_pnl,
            capital=self.risk_mgr.capital,
            regime=regime_str,
            operating_mode=mode_str,
            watchlist_prices=prices,
        )

    def stop(self):
        print("\n\n🛑 Shutting down agent...")
        self.running = False
        if self.data_stream:
            self.data_stream.stop()
        self._check_force_exit()
        self.broker.square_off_all()
        self._save_trade_log()
        self._print_daily_summary()

        # End Supabase session
        closed = [t for t in self.risk_mgr.trade_log if t.get('exit') is not None]
        wins = sum(1 for t in closed if t.get('pnl', 0) > 0)
        win_rate = (wins / len(closed) * 100) if closed else 0
        self.db.end_session(
            final_capital=self.risk_mgr.capital,
            total_pnl=self.risk_mgr.daily_pnl,
            total_trades=self.risk_mgr.trades_today,
            win_rate=win_rate,
        )

    def _save_trade_log(self):
        if not self.risk_mgr.trade_log:
            return
        os.makedirs("data", exist_ok=True)
        path = f"data/trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            keys = self.risk_mgr.trade_log[0].keys()
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in self.risk_mgr.trade_log:
                    writer.writerow({k: str(v) for k, v in row.items()})
            print(f"  📁 Trade log saved: {path}")
        except Exception as e:
            logger.error(f"Failed to save trade log: {e}")

    def _print_daily_summary(self):
        print("\n" + "=" * 60)
        print("  📋 DAILY SUMMARY")
        print("=" * 60)
        print(f"  Total Trades : {self.risk_mgr.trades_today}")
        print(f"  P&L          : ₹{self.risk_mgr.daily_pnl:+,.2f}")
        ret = (self.risk_mgr.daily_pnl / self.risk_mgr.initial_capital) * 100
        print(f"  Return       : {ret:+.2f}%")
        print(f"  Capital      : ₹{self.risk_mgr.capital:,.2f}")

        if self.risk_mgr.trade_log:
            closed = [t for t in self.risk_mgr.trade_log if t.get('exit') is not None]
            wins = sum(1 for t in closed if t.get('pnl', 0) > 0)
            if closed:
                print(f"  Win Rate     : {wins / len(closed) * 100:.1f}% ({wins}/{len(closed)})")
        print("=" * 60)
