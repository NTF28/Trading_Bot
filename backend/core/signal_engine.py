import numpy as np
import pickle
import os
from dataclasses import dataclass
from typing import Optional
from core.indicators import IndicatorResult, indicator_engine
from core.candle_store import candle_store
from core.config import settings

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


@dataclass
class Signal:
    asset: str
    timeframe: int
    direction: str          # "UP" | "DOWN" | "NEUTRAL"
    probability: float      # 0.0 – 1.0
    confidence: str         # "HIGH" | "MEDIUM" | "LOW"
    indicators: dict
    weighted_score: float   # raw score before ML blend
    ml_probability: Optional[float] = None
    pattern: str = ""

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "probability": round(self.probability * 100, 1),
            "confidence": self.confidence,
            "weighted_score": round(self.weighted_score, 3),
            "ml_probability": round(self.ml_probability * 100, 1) if self.ml_probability is not None else None,
            "pattern": self.pattern,
            "indicators": self.indicators,
        }


class SignalEngine:
    """
    Combines indicator votes (weighted scoring) with an XGBoost model
    to produce a directional signal with win probability.
    """

    # Indicator weights — tune these based on backtesting results
    WEIGHTS = {
        "rsi":     0.20,
        "macd":    0.25,
        "bb":      0.15,
        "ema":     0.20,
        "stoch":   0.10,
        "pattern": 0.10,
    }

    # How much to blend ML vs weighted score (0 = pure weighted, 1 = pure ML)
    ML_BLEND = 0.50

    MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/xgb_model.pkl")

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if XGB_AVAILABLE and os.path.exists(self.MODEL_PATH):
            with open(self.MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

    def _weighted_score(self, result: IndicatorResult) -> float:
        """Returns a score between -1 (strong DOWN) and +1 (strong UP)."""
        signals = {
            "rsi":     result.rsi_signal,
            "macd":    result.macd_signal,
            "bb":      result.bb_signal,
            "ema":     result.ema_signal,
            "stoch":   result.stoch_signal,
            "pattern": result.pattern_signal,
        }
        score = sum(self.WEIGHTS[k] * v for k, v in signals.items())
        return score

    def _score_to_probability(self, score: float) -> tuple[str, float]:
        """
        Converts weighted score [-1, 1] to (direction, win_probability).
        Uses a sigmoid-like curve so extreme scores give higher probability.
        """
        # Sigmoid scaled to [0.5, 0.95]
        prob_up = 1 / (1 + np.exp(-score * 6))
        if prob_up >= 0.5:
            return "UP", prob_up
        else:
            return "DOWN", 1 - prob_up

    def _ml_probability(self, result: IndicatorResult) -> Optional[float]:
        """Run XGBoost model if available. Returns P(UP) as float."""
        if self.model is None or not XGB_AVAILABLE:
            return None
        features = np.array([[
            result.rsi if not np.isnan(result.rsi) else 50,
            result.macd_histogram if not np.isnan(result.macd_histogram) else 0,
            result.bb_signal,
            result.ema_signal,
            result.stoch_k if not np.isnan(result.stoch_k) else 50,
            result.stoch_d if not np.isnan(result.stoch_d) else 50,
            result.rsi_signal,
            result.macd_signal,
            result.pattern_signal,
        ]])
        try:
            prob = float(self.model.predict_proba(features)[0][1])
            return prob
        except Exception:
            return None

    def _blend(self, weighted_prob: float, ml_prob: Optional[float]) -> float:
        if ml_prob is None:
            return weighted_prob
        return (1 - self.ML_BLEND) * weighted_prob + self.ML_BLEND * ml_prob

    def _confidence_label(self, probability: float) -> str:
        if probability >= 0.72:
            return "HIGH"
        elif probability >= 0.62:
            return "MEDIUM"
        return "LOW"

    def generate(self, asset: str, timeframe: int) -> Optional[Signal]:
        """Main entry point — returns a Signal or None if not enough data."""
        if not candle_store.has_enough_data(asset, timeframe, min_candles=50):
            return None

        df = candle_store.to_dataframe(asset, timeframe)
        result = indicator_engine.compute(df)

        weighted_score = self._weighted_score(result)
        direction, weighted_prob = self._score_to_probability(weighted_score)

        ml_prob_raw = self._ml_probability(result)
        # ML probability is always P(UP), so flip for DOWN direction
        if ml_prob_raw is not None and direction == "DOWN":
            ml_prob_for_blend = 1 - ml_prob_raw
        else:
            ml_prob_for_blend = ml_prob_raw

        final_prob = self._blend(weighted_prob, ml_prob_for_blend)

        # Suppress weak signals
        if final_prob < settings.MIN_WIN_PROBABILITY:
            direction = "NEUTRAL"

        return Signal(
            asset=asset,
            timeframe=timeframe,
            direction=direction,
            probability=final_prob,
            confidence=self._confidence_label(final_prob),
            indicators=result.to_dict(),
            weighted_score=weighted_score,
            ml_probability=ml_prob_raw,
            pattern=result.pattern_name,
        )


# Singleton
signal_engine = SignalEngine()