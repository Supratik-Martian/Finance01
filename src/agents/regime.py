"""
Regime Detection Agent — the most important agent in HYDRA.
Classifies current market conditions using ADX, Hurst exponent, and volatility.
"""
import numpy as np
from .base import BaseAgent, Blackboard, Regime
from ..indicators import Indicators

import logging
logger = logging.getLogger(__name__)


class RegimeDetector(BaseAgent):
    name = "regime"
    preferred_regimes = []  # meta-agent, works in all regimes
    anti_regimes = []

    def analyze(self, candles_map: dict, blackboard: Blackboard) -> dict:
        # Use the first available symbol with enough data as market proxy
        regime_votes = []

        for symbol, df in candles_map.items():
            if len(df) < 30:
                continue

            close = df['close']
            high = df['high']
            low = df['low']

            # 1. ADX regime
            adx_val = self._calc_adx(high, low, close, 14)
            ema20 = close.ewm(span=20).mean().iloc[-1]
            ema50 = close.ewm(span=50).mean().iloc[-1] if len(close) >= 50 else ema20
            price = close.iloc[-1]

            if adx_val > 25:
                if price > ema20 > ema50:
                    regime_votes.append(Regime.TRENDING_BULL)
                elif price < ema20 < ema50:
                    regime_votes.append(Regime.TRENDING_BEAR)
                else:
                    regime_votes.append(Regime.TRENDING_BULL if price > ema20 else Regime.TRENDING_BEAR)
            else:
                regime_votes.append(Regime.MEAN_REVERTING)

            # 2. Volatility check
            atr = Indicators.atr(high, low, close, 14)
            if len(atr) > 0:
                atr_pct = atr.iloc[-1] / price * 100
                if atr_pct > 3.0:  # High vol threshold for Indian stocks
                    regime_votes.append(Regime.HIGH_VOLATILITY)

            # 3. Hurst exponent (trending vs mean-reverting)
            hurst = self._calc_hurst(close.values[-50:]) if len(close) >= 50 else 0.5
            if hurst > 0.6:
                regime_votes.append(Regime.TRENDING_BULL if price > ema20 else Regime.TRENDING_BEAR)
            elif hurst < 0.4:
                regime_votes.append(Regime.MEAN_REVERTING)

            break  # use first symbol with enough data as proxy

        # Ensemble vote
        if not regime_votes:
            blackboard.regime["primary"] = Regime.UNKNOWN
            blackboard.regime["confidence"] = 0.0
            return {}

        # Count votes
        from collections import Counter
        vote_counts = Counter(regime_votes)
        total = len(regime_votes)
        primary = vote_counts.most_common(1)[0][0]
        confidence = vote_counts[primary] / total

        probs = {r.value: vote_counts.get(r, 0) / total for r in Regime}

        blackboard.regime = {
            "primary": primary,
            "confidence": round(confidence, 2),
            "probabilities": probs,
            "stability": confidence,
        }

        logger.info(f"  🏛️ Regime: {primary.value} (confidence: {confidence:.0%})")
        return {}

    def _calc_adx(self, high, low, close, period=14) -> float:
        """Simplified ADX calculation."""
        try:
            plus_dm = high.diff().clip(lower=0)
            minus_dm = low.diff().abs().clip(lower=0)

            atr = Indicators.atr(high, low, close, period)
            if atr.iloc[-1] == 0:
                return 0

            plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

            dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)) * 100
            adx = dx.rolling(period).mean()

            val = adx.iloc[-1]
            return val if not np.isnan(val) else 0
        except Exception:
            return 0

    def _calc_hurst(self, ts: np.ndarray) -> float:
        """Hurst exponent: >0.5 trending, <0.5 mean-reverting, =0.5 random."""
        try:
            n = len(ts)
            if n < 20:
                return 0.5
            lags = range(2, min(20, n // 2))
            tau = [np.std(np.subtract(ts[lag:], ts[:-lag])) for lag in lags]
            tau = [t for t in tau if t > 0]
            if len(tau) < 2:
                return 0.5
            poly = np.polyfit(np.log(list(range(2, 2 + len(tau)))), np.log(tau), 1)
            return poly[0]
        except Exception:
            return 0.5
