"""
Sentiment Agent — scores news headlines from yfinance for each symbol.
Uses keyword-based financial sentiment scoring with novelty detection.
"""
import hashlib
import logging
from .base import BaseAgent, Blackboard, Regime, AgentSignal, Direction

logger = logging.getLogger(__name__)

# Financial keyword dictionaries
POSITIVE_WORDS = {
    'surge', 'surges', 'rally', 'rallies', 'beat', 'beats', 'upgrade',
    'upgraded', 'profit', 'profits', 'growth', 'soar', 'soars', 'gain',
    'gains', 'bullish', 'outperform', 'buy', 'strong', 'record', 'high',
    'boost', 'boosts', 'rise', 'rises', 'positive', 'recovery', 'rebound',
    'dividend', 'expansion', 'breakout', 'innovation', 'partnership',
}

NEGATIVE_WORDS = {
    'crash', 'crashes', 'plunge', 'plunges', 'downgrade', 'downgraded',
    'loss', 'losses', 'decline', 'declines', 'bearish', 'sell', 'weak',
    'fall', 'falls', 'drop', 'drops', 'negative', 'fraud', 'probe',
    'investigation', 'lawsuit', 'penalty', 'fine', 'default', 'bankruptcy',
    'warning', 'risk', 'debt', 'layoff', 'layoffs', 'recession', 'slump',
    'miss', 'misses', 'underperform', 'cut', 'slash',
}


class SentimentAgent(BaseAgent):
    name = "sentiment"
    preferred_regimes = [Regime.MEAN_REVERTING, Regime.TRENDING_BULL]
    anti_regimes = []

    def __init__(self):
        super().__init__()
        self._seen_headlines = set()  # novelty tracking

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        signals = {}

        for symbol in candles_map.keys():
            try:
                score, confidence, headlines = self._score_symbol(symbol)
            except Exception:
                continue

            if abs(score) < 0.3 or confidence < 0.2:
                continue  # not strong enough

            price = candles_map[symbol]['close'].iloc[-1]
            atr_pct = price * 0.02  # rough 2% ATR estimate

            if score > 0.3:
                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.LONG,
                    conviction=round(min(score * confidence, 0.80), 2),
                    entry_price=price,
                    stop_loss=price - atr_pct,
                    target=price + 1.5 * atr_pct,
                    reason=f"Sentiment LONG: score={score:.2f}, {len(headlines)} headlines",
                    agent_name=self.name,
                )
            elif score < -0.3:
                signals[symbol] = AgentSignal(
                    symbol=symbol,
                    direction=Direction.SHORT,
                    conviction=round(min(abs(score) * confidence, 0.75), 2),
                    entry_price=price,
                    stop_loss=price + atr_pct,
                    target=price - 1.5 * atr_pct,
                    reason=f"Sentiment SHORT: score={score:.2f}, {len(headlines)} headlines",
                    agent_name=self.name,
                )

        blackboard.signals[self.name] = signals
        return signals

    def _score_symbol(self, symbol: str) -> tuple:
        """Fetch news from yfinance and score headlines."""
        import yfinance as yf

        ticker = yf.Ticker(f"{symbol}.NS")
        try:
            news = ticker.news or []
        except Exception:
            news = []

        if not news:
            return 0.0, 0.0, []

        total_score = 0
        novel_count = 0
        headlines = []

        for article in news[:10]:  # last 10 articles
            title = article.get('title', '') or ''
            headline_hash = hashlib.md5(title.lower().encode()).hexdigest()

            # Novelty check
            novelty = 1.0
            if headline_hash in self._seen_headlines:
                novelty = 0.3  # repeat = 70% decay
            self._seen_headlines.add(headline_hash)

            # Score
            words = set(title.lower().split())
            pos = len(words & POSITIVE_WORDS)
            neg = len(words & NEGATIVE_WORDS)
            raw_score = (pos - neg) / max(pos + neg, 1)

            total_score += raw_score * novelty
            novel_count += novelty
            headlines.append(title)

        if novel_count == 0:
            return 0.0, 0.0, headlines

        avg_score = total_score / novel_count
        confidence = min(1.0, novel_count / 5)  # more headlines = more confident

        return avg_score, confidence, headlines
