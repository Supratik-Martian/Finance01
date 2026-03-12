import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
from .indicators import Indicators

warnings.filterwarnings('ignore')

class MLSignalFilter:
    """
    ML model to filter/enhance signals from technical strategies.
    Predicts probability that a trade will be profitable.
    """
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=20
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from OHLCV data"""
        features = pd.DataFrame(index=df.index)
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Price-based features
        features['returns_1'] = close.pct_change(1)
        features['returns_5'] = close.pct_change(5)
        features['returns_10'] = close.pct_change(10)
        
        # Volatility
        features['volatility_10'] = close.pct_change().rolling(10).std()
        features['volatility_20'] = close.pct_change().rolling(20).std()
        features['atr_norm'] = Indicators.atr(high, low, close, 14) / close
        
        # Momentum
        features['rsi'] = Indicators.rsi(close, 14)
        macd, signal, hist = Indicators.macd(close)
        features['macd_hist'] = hist
        features['macd_hist_change'] = hist.diff()
        
        # Trend
        features['ema_9_21_ratio'] = (
            Indicators.ema(close, 9) / Indicators.ema(close, 21)
        ) - 1
        features['price_vs_sma20'] = (
            close / Indicators.sma(close, 20)
        ) - 1
        
        # Volume
        features['volume_ratio'] = volume / volume.rolling(20).mean()
        features['volume_trend'] = volume.rolling(5).mean() / volume.rolling(20).mean()
        
        # Bollinger Band position
        upper, mid, lower = Indicators.bollinger_bands(close)
        bb_width = upper - lower
        features['bb_position'] = (close - lower) / bb_width.where(bb_width > 0, 1)
        features['bb_width_norm'] = bb_width / close
        
        # Candlestick features
        features['body_ratio'] = (close - df['open']) / (high - low).where(
            (high - low) > 0, 1
        )
        features['upper_shadow'] = (high - close.clip(lower=df['open'])) / (
            high - low
        ).where((high - low) > 0, 1)
        features['lower_shadow'] = (close.clip(upper=df['open']) - low) / (
            high - low
        ).where((high - low) > 0, 1)
        
        # Time features (intraday)
        features['hour'] = df.index.hour
        features['minute'] = df.index.minute
        features['minutes_from_open'] = (
            (df.index.hour - 9) * 60 + (df.index.minute - 15)
        )
        
        # Higher highs / lower lows
        features['hh'] = (high > high.shift(1)).astype(int).rolling(5).sum()
        features['ll'] = (low < low.shift(1)).astype(int).rolling(5).sum()
        
        self.feature_names = features.columns.tolist()
        return features
    
    def create_labels(self, df, forward_periods=6, min_return=0.003):
        """
        Label: 1 if price moves up by min_return within forward_periods
               0 otherwise
        """
        future_max = df['high'].rolling(forward_periods).max().shift(-forward_periods)
        future_min = df['low'].rolling(forward_periods).min().shift(-forward_periods)
        
        # For buy signals
        potential_gain = (future_max - df['close']) / df['close']
        potential_loss = (df['close'] - future_min) / df['close']
        
        # Profitable if gain > threshold and gain > loss
        labels = ((potential_gain > min_return) & 
                  (potential_gain > potential_loss * 1.5)).astype(int)
        
        return labels
    
    def train(self, historical_df: pd.DataFrame):
        features = self.extract_features(historical_df)
        labels = self.create_labels(historical_df)
        
        combined = pd.concat([features, labels.rename('target')], axis=1)
        combined.dropna(inplace=True)
        
        X = combined[self.feature_names]
        y = combined['target']
        
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            self.scaler.fit(X_train)
            X_train_scaled = self.scaler.transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            self.model.fit(X_train_scaled, y_train)
            score = self.model.score(X_val_scaled, y_val)
            scores.append(score)
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        print(f"ML Filter trained. Mean accuracy: {np.mean(scores):.4f}")
    
    def predict_confidence(self, df: pd.DataFrame) -> float:
        if not self.is_trained:
            return 0.5
        
        features = self.extract_features(df)
        latest = features.iloc[[-1]].dropna(axis=1)
        
        missing = set(self.feature_names) - set(latest.columns)
        for col in missing:
            latest[col] = 0
        latest = latest[self.feature_names]
        
        X_scaled = self.scaler.transform(latest)
        proba = self.model.predict_proba(X_scaled)[0][1]
        return proba
    
    def save(self, path="ml_filter"):
        joblib.dump(self.model, f"{path}_model.pkl")
        joblib.dump(self.scaler, f"{path}_scaler.pkl")
    
    def load(self, path="ml_filter"):
        self.model = joblib.load(f"{path}_model.pkl")
        self.scaler = joblib.load(f"{path}_scaler.pkl")
        self.is_trained = True
