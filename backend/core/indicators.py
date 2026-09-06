import pandas as pd
import pandas_ta as ta
import numpy as np
from dataclasses import dataclass, field


@dataclass
class IndicatorResult:
    # RSI
    rsi: float = float("nan")
    rsi_signal: int = 0           # +1 oversold, -1 overbought, 0 neutral

    # MACD
    macd: float = float("nan")
    macd_signal_line: float = float("nan")
    macd_histogram: float = float("nan")
    macd_signal: int = 0          # +1 bullish cross, -1 bearish cross, 0 neutral

    # Bollinger Bands
    bb_upper: float = float("nan")
    bb_mid: float = float("nan")
    bb_lower: float = float("nan")
    bb_signal: int = 0            # +1 near lower band, -1 near upper band, 0 mid

    # EMA crossover
    ema_fast: float = float("nan")
    ema_slow: float = float("nan")
    ema_signal: int = 0           # +1 fast > slow, -1 fast < slow

    # Stochastic
    stoch_k: float = float("nan")
    stoch_d: float = float("nan")
    stoch_signal: int = 0         # +1 oversold, -1 overbought, 0 neutral

    # Candlestick patterns
    pattern_signal: int = 0       # +1 bullish pattern, -1 bearish, 0 none
    pattern_name: str = ""

    def signals(self) -> list[int]:
        return [
            self.rsi_signal,
            self.macd_signal,
            self.bb_signal,
            self.ema_signal,
            self.stoch_signal,
            self.pattern_signal,
        ]

    def to_dict(self) -> dict:
        return {
            "rsi": round(self.rsi, 2) if not np.isnan(self.rsi) else None,
            "rsi_signal": self.rsi_signal,
            "macd": round(self.macd, 5) if not np.isnan(self.macd) else None,
            "macd_histogram": round(self.macd_histogram, 5) if not np.isnan(self.macd_histogram) else None,
            "macd_signal": self.macd_signal,
            "bb_upper": round(self.bb_upper, 5) if not np.isnan(self.bb_upper) else None,
            "bb_lower": round(self.bb_lower, 5) if not np.isnan(self.bb_lower) else None,
            "bb_signal": self.bb_signal,
            "ema_fast": round(self.ema_fast, 5) if not np.isnan(self.ema_fast) else None,
            "ema_slow": round(self.ema_slow, 5) if not np.isnan(self.ema_slow) else None,
            "ema_signal": self.ema_signal,
            "stoch_k": round(self.stoch_k, 2) if not np.isnan(self.stoch_k) else None,
            "stoch_d": round(self.stoch_d, 2) if not np.isnan(self.stoch_d) else None,
            "stoch_signal": self.stoch_signal,
            "pattern_signal": self.pattern_signal,
            "pattern_name": self.pattern_name,
        }


class IndicatorEngine:
    """
    Computes technical indicators from a pandas OHLCV DataFrame.
    All indicators return a directional signal: +1 (UP), -1 (DOWN), 0 (neutral).
    """

    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    EMA_FAST = 9
    EMA_SLOW = 21

    BB_PERIOD = 20
    BB_STD = 2.0

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    STOCH_K = 14
    STOCH_D = 3
    STOCH_SMOOTH = 3
    STOCH_OVERSOLD = 20
    STOCH_OVERBOUGHT = 80

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        result = IndicatorResult()
        if df is None or len(df) < 30:
            return result

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ── RSI ──────────────────────────────────────────────────────────────
        rsi_series = ta.rsi(close, length=self.RSI_PERIOD)
        if rsi_series is not None and not rsi_series.empty:
            result.rsi = float(rsi_series.iloc[-1])
            if result.rsi <= self.RSI_OVERSOLD:
                result.rsi_signal = 1
            elif result.rsi >= self.RSI_OVERBOUGHT:
                result.rsi_signal = -1

        # ── MACD ─────────────────────────────────────────────────────────────
        macd_df = ta.macd(close, fast=self.MACD_FAST, slow=self.MACD_SLOW, signal=self.MACD_SIGNAL)
        if macd_df is not None and not macd_df.empty:
            cols = macd_df.columns.tolist()
            result.macd = float(macd_df[cols[0]].iloc[-1])
            result.macd_signal_line = float(macd_df[cols[1]].iloc[-1])
            result.macd_histogram = float(macd_df[cols[2]].iloc[-1])
            # Signal on histogram direction change
            if len(macd_df) >= 2:
                prev_hist = float(macd_df[cols[2]].iloc[-2])
                curr_hist = result.macd_histogram
                if prev_hist < 0 and curr_hist > prev_hist:
                    result.macd_signal = 1
                elif prev_hist > 0 and curr_hist < prev_hist:
                    result.macd_signal = -1

        # ── Bollinger Bands ───────────────────────────────────────────────────
        bb_df = ta.bbands(close, length=self.BB_PERIOD, std=self.BB_STD)
        if bb_df is not None and not bb_df.empty:
            cols = bb_df.columns.tolist()
            result.bb_lower = float(bb_df[cols[0]].iloc[-1])
            result.bb_mid = float(bb_df[cols[1]].iloc[-1])
            result.bb_upper = float(bb_df[cols[2]].iloc[-1])
            price = float(close.iloc[-1])
            band_range = result.bb_upper - result.bb_lower
            if band_range > 0:
                pos = (price - result.bb_lower) / band_range
                if pos <= 0.15:
                    result.bb_signal = 1
                elif pos >= 0.85:
                    result.bb_signal = -1

        # ── EMA Crossover ─────────────────────────────────────────────────────
        ema_fast = ta.ema(close, length=self.EMA_FAST)
        ema_slow = ta.ema(close, length=self.EMA_SLOW)
        if ema_fast is not None and ema_slow is not None:
            result.ema_fast = float(ema_fast.iloc[-1])
            result.ema_slow = float(ema_slow.iloc[-1])
            if len(ema_fast) >= 2 and len(ema_slow) >= 2:
                prev_fast = float(ema_fast.iloc[-2])
                prev_slow = float(ema_slow.iloc[-2])
                # Golden cross / death cross
                if prev_fast <= prev_slow and result.ema_fast > result.ema_slow:
                    result.ema_signal = 1
                elif prev_fast >= prev_slow and result.ema_fast < result.ema_slow:
                    result.ema_signal = -1
                elif result.ema_fast > result.ema_slow:
                    result.ema_signal = 1
                else:
                    result.ema_signal = -1

        # ── Stochastic ────────────────────────────────────────────────────────
        stoch_df = ta.stoch(high, low, close, k=self.STOCH_K, d=self.STOCH_D, smooth_k=self.STOCH_SMOOTH)
        if stoch_df is not None and not stoch_df.empty:
            cols = stoch_df.columns.tolist()
            result.stoch_k = float(stoch_df[cols[0]].iloc[-1])
            result.stoch_d = float(stoch_df[cols[1]].iloc[-1])
            if result.stoch_k <= self.STOCH_OVERSOLD and result.stoch_d <= self.STOCH_OVERSOLD:
                result.stoch_signal = 1
            elif result.stoch_k >= self.STOCH_OVERBOUGHT and result.stoch_d >= self.STOCH_OVERBOUGHT:
                result.stoch_signal = -1

        # ── Candlestick Patterns ──────────────────────────────────────────────
        result.pattern_signal, result.pattern_name = self._detect_patterns(df)

        return result

    def _detect_patterns(self, df: pd.DataFrame) -> tuple[int, str]:
        """Detect basic candlestick patterns on the last 2 candles."""
        if len(df) < 2:
            return 0, ""

        o, h, l, c = (
            df["open"].values,
            df["high"].values,
            df["low"].values,
            df["close"].values,
        )

        curr_o, curr_h, curr_l, curr_c = o[-1], h[-1], l[-1], c[-1]
        prev_o, prev_h, prev_l, prev_c = o[-2], h[-2], l[-2], c[-2]

        body = abs(curr_c - curr_o)
        total_range = curr_h - curr_l or 0.0001
        upper_wick = curr_h - max(curr_o, curr_c)
        lower_wick = min(curr_o, curr_c) - curr_l

        # Doji — body very small vs range
        if body / total_range < 0.1:
            return 0, "doji"

        # Hammer (bullish) — small body at top, long lower wick
        if lower_wick > body * 2 and upper_wick < body * 0.5 and curr_c > curr_o:
            return 1, "hammer"

        # Shooting star (bearish) — small body at bottom, long upper wick
        if upper_wick > body * 2 and lower_wick < body * 0.5 and curr_c < curr_o:
            return -1, "shooting_star"

        # Bullish engulfing
        prev_bearish = prev_c < prev_o
        curr_bullish = curr_c > curr_o
        if prev_bearish and curr_bullish and curr_o < prev_c and curr_c > prev_o:
            return 1, "bullish_engulfing"

        # Bearish engulfing
        prev_bullish = prev_c > prev_o
        curr_bearish = curr_c < curr_o
        if prev_bullish and curr_bearish and curr_o > prev_c and curr_c < prev_o:
            return -1, "bearish_engulfing"

        # Pin bar (bullish) — rejection of lows
        if lower_wick > total_range * 0.6 and body < total_range * 0.3:
            return 1, "pin_bar_bullish"

        # Pin bar (bearish) — rejection of highs
        if upper_wick > total_range * 0.6 and body < total_range * 0.3:
            return -1, "pin_bar_bearish"

        return 0, ""


# Singleton
indicator_engine = IndicatorEngine()