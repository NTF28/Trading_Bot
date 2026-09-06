from collections import deque
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from core.config import settings


@dataclass
class Candle:
    time: int        # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class CandleStore:
    """
    Rolling buffer of OHLCV candles per (asset, timeframe) pair.
    """

    def __init__(self, max_candles: int = settings.MAX_CANDLES):
        self.max_candles = max_candles
        self._store: dict[tuple[str, int], deque] = {}

    def _key(self, asset: str, timeframe: int) -> tuple[str, int]:
        return (asset, timeframe)

    def push(self, asset: str, timeframe: int, candle: Candle) -> None:
        key = self._key(asset, timeframe)
        if key not in self._store:
            self._store[key] = deque(maxlen=self.max_candles)
        buf = self._store[key]
        # Replace last candle if same timestamp (in-progress candle update)
        if buf and buf[-1].time == candle.time:
            buf[-1] = candle
        else:
            buf.append(candle)

    def get(self, asset: str, timeframe: int, n: Optional[int] = None) -> list:
        key = self._key(asset, timeframe)
        buf = self._store.get(key, deque())
        candles = list(buf)
        if n is not None:
            candles = candles[-n:]
        return candles

    def to_dataframe(self, asset: str, timeframe: int, n: Optional[int] = None) -> pd.DataFrame:
        candles = self.get(asset, timeframe, n)
        if not candles:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame([c.to_dict() for c in candles])
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")
        return df

    def has_enough_data(self, asset: str, timeframe: int, min_candles: int = 50) -> bool:
        return len(self.get(asset, timeframe)) >= min_candles

    def available_pairs(self) -> list:
        return list(self._store.keys())


# Singleton shared across the app
candle_store = CandleStore()