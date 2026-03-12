"""
Real-time market data stream for NSE stocks.
Uses yfinance for REAL price data (free, no API key needed).
Supports both live Kite ticker and free yfinance polling modes.
"""
import pandas as pd
from collections import defaultdict, deque
from datetime import datetime
import threading
import time
import logging

logger = logging.getLogger(__name__)


class MarketDataStream:
    """
    Streams real NSE market data using yfinance (free) or Kite WebSocket (paid).
    In paper trading mode, uses yfinance to fetch real 1-minute candles
    and simulates a tick-by-tick feed from them.
    """

    def __init__(self, broker, watchlist: list, token_map: dict, paper_trading=True):
        self.broker = broker
        self.watchlist = watchlist          # list of symbol strings like "RELIANCE"
        self.token_map = token_map          # {token_int: "SYMBOL"}
        self.reverse_map = {v: k for k, v in token_map.items()}  # {"SYMBOL": token_int}
        self.paper_trading = paper_trading

        self.tick_data = defaultdict(lambda: deque(maxlen=50000))
        self.candles = defaultdict(lambda: pd.DataFrame())
        self.latest_prices = {}             # {"SYMBOL": float}  — always up to date
        self.callbacks = []
        self._stop_event = threading.Event()

        if not self.paper_trading and hasattr(broker, 'kite') and broker.kite:
            from kiteconnect import KiteTicker
            tokens = list(token_map.keys())
            self.ticker = KiteTicker(
                broker.kite.api_key,
                broker.kite.access_token
            )
            self._setup_kite_ticker(tokens)
        else:
            self.ticker = None
            logger.info("Using yfinance for REAL NSE market data (paper trading mode).")

    # ──────────── Kite WebSocket (paid, real-time) ────────────

    def _setup_kite_ticker(self, tokens):
        self.ticker.on_ticks = self._on_kite_ticks
        self.ticker.on_connect = lambda ws, res: (
            ws.subscribe(tokens),
            ws.set_mode(ws.MODE_FULL, tokens),
            logger.info(f"Kite WS connected. Subscribed to {len(tokens)} instruments.")
        )
        self.ticker.on_close = lambda ws, code, reason: logger.warning(
            f"Kite WS closed: {code} - {reason}"
        )

    def _on_kite_ticks(self, ws, ticks):
        for tick in ticks:
            token = tick['instrument_token']
            symbol = self.token_map.get(token, "UNKNOWN")
            ts = tick.get('exchange_timestamp', datetime.now())
            ltp = tick['last_price']

            self.latest_prices[symbol] = ltp
            self.tick_data[token].append({
                'timestamp': ts,
                'ltp': ltp,
                'volume': tick.get('volume_traded', 0),
                'buy_qty': tick.get('total_buy_quantity', 0),
                'sell_qty': tick.get('total_sell_quantity', 0),
                'oi': tick.get('oi', 0),
                'bid': tick.get('depth', {}).get('buy', [{'price': ltp}])[0]['price'],
                'ask': tick.get('depth', {}).get('sell', [{'price': ltp}])[0]['price'],
            })

        for cb in self.callbacks:
            cb(ticks)

    # ──────────── yfinance polling (free, real prices) ────────────

    def _yf_symbols(self):
        """Convert NSE symbols to yfinance format: RELIANCE → RELIANCE.NS"""
        return {s: f"{s}.NS" for s in self.watchlist}

    def _fetch_intraday_yf(self):
        """
        Fetch the latest 1-minute candles for all watchlist stocks.
        yfinance gives ~15-20 min delayed data for NSE during market hours,
        but the PRICES ARE REAL — not random.
        """
        import yfinance as yf

        yf_map = self._yf_symbols()
        yf_tickers = list(yf_map.values())

        try:
            # Download 1-day of 1-min data for all tickers in one batch call
            data = yf.download(
                tickers=yf_tickers,
                period="1d",
                interval="1m",
                group_by="ticker",
                progress=False,
                threads=True,
            )

            if data.empty:
                logger.warning("yfinance returned empty data. Market may be closed.")
                return None

            return data
        except Exception as e:
            logger.error(f"yfinance fetch error: {e}")
            return None

    def _yf_polling_loop(self):
        """
        Background thread: polls yfinance every 30 seconds for fresh 1-min candles
        and feeds them into the tick pipeline.
        """
        yf_map = self._yf_symbols()
        seen_timestamps = defaultdict(set)  # track which candles we've already processed

        logger.info("yfinance polling thread started. Fetching real NSE data every 30s...")

        while not self._stop_event.is_set():
            try:
                raw = self._fetch_intraday_yf()
                if raw is None or raw.empty:
                    time.sleep(30)
                    continue

                for nse_sym, yf_sym in yf_map.items():
                    token = self.reverse_map.get(nse_sym)
                    if token is None:
                        continue

                    # Extract single-ticker DataFrame
                    try:
                        if len(yf_map) == 1:
                            df = raw.copy()
                        else:
                            df = raw[yf_sym].copy()
                    except (KeyError, TypeError):
                        continue

                    if df.empty:
                        continue

                    # Flatten columns if MultiIndex
                    if hasattr(df.columns, 'levels'):
                        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

                    df.dropna(subset=["Close"], inplace=True)
                    if df.empty:
                        continue

                    # Process only NEW candles (ones we haven't seen yet)
                    for ts, row in df.iterrows():
                        ts_key = str(ts)
                        if ts_key in seen_timestamps[nse_sym]:
                            continue
                        seen_timestamps[nse_sym].add(ts_key)

                        ltp = float(row["Close"])
                        vol = int(row.get("Volume", 0))
                        self.latest_prices[nse_sym] = ltp

                        self.tick_data[token].append({
                            'timestamp': pd.Timestamp(ts),
                            'ltp': ltp,
                            'volume': vol,
                            'buy_qty': 0,
                            'sell_qty': 0,
                            'oi': 0,
                            'bid': ltp - 0.05,
                            'ask': ltp + 0.05,
                        })

                    # Build candles immediately after ingesting
                    self.build_candles(token, interval_minutes=5)

                    # Fire callbacks with a lightweight tick list
                    latest_ltp = self.latest_prices.get(nse_sym, 0)
                    if latest_ltp > 0:
                        pseudo_tick = [{
                            'instrument_token': token,
                            'last_price': latest_ltp,
                            'exchange_timestamp': datetime.now(),
                            'volume_traded': 0,
                            'total_buy_quantity': 0,
                            'total_sell_quantity': 0,
                        }]
                        for cb in self.callbacks:
                            cb(pseudo_tick)

            except Exception as e:
                logger.error(f"yfinance polling error: {e}")

            # Poll every 30 seconds
            self._stop_event.wait(30)

    # ──────────── Candle building ────────────

    def build_candles(self, token, interval_minutes=5):
        """Convert tick data to OHLCV candles"""
        if not self.tick_data[token]:
            return pd.DataFrame()

        df = pd.DataFrame(list(self.tick_data[token]))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        if len(df) < 2:
            return pd.DataFrame()

        candles = df['ltp'].resample(f'{interval_minutes}min').ohlc()

        if 'volume' in df.columns:
            candles['volume'] = df['volume'].resample(
                f'{interval_minutes}min'
            ).sum()
        else:
            candles['volume'] = 1000

        candles.dropna(subset=['close'], inplace=True)

        if candles.empty:
            return pd.DataFrame()

        self.candles[token] = candles
        return candles

    # ──────────── Start / stop ────────────

    def start(self):
        """Start streaming in a background thread"""
        if self.ticker:
            t = threading.Thread(target=self.ticker.connect, kwargs={"threaded": True})
            t.daemon = True
            t.start()
        else:
            t = threading.Thread(target=self._yf_polling_loop, daemon=True)
            t.start()

    def stop(self):
        self._stop_event.set()

    def on_data(self, callback):
        self.callbacks.append(callback)

    def get_ltp(self, symbol: str) -> float:
        """Return the latest known price for a symbol."""
        return self.latest_prices.get(symbol, 0.0)
