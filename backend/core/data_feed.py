import asyncio
import logging
import time
from typing import Callable, Optional

from core.config import settings
from core.candle_store import candle_store, Candle

logger = logging.getLogger(__name__)

try:
    from pyquotex.stable_api import Quotex
    PYQUOTEX_AVAILABLE = True
except ImportError:
    PYQUOTEX_AVAILABLE = False
    logger.warning("PyQuotex not available — running in simulation mode")


class DataFeed:
    def __init__(self):
        self._client: Optional[object] = None
        self._connected = False
        self._subscriptions: set[tuple[str, int]] = set()
        self._callbacks: list[Callable] = []

    @property
    def connected(self) -> bool:
        return self._connected

    def on_candle(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    async def connect(self) -> bool:
        if not PYQUOTEX_AVAILABLE or not settings.QUOTEX_EMAIL or not settings.QUOTEX_PASSWORD:
            logger.info("Running in simulation mode")
            self._connected = True
            return True
        try:
            self._client = Quotex(
                email=settings.QUOTEX_EMAIL,
                password=settings.QUOTEX_PASSWORD,
            )
            check, reason = await self._client.connect()
            if check:
                self._connected = True
                if settings.QUOTEX_DEMO:
                    self._client.change_account("PRACTICE")
                logger.info("✅ Connected to Quotex")
            else:
                logger.warning(f"Quotex login failed: {reason} — using simulation")
                self._client = None
                self._connected = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e} — using simulation")
            self._client = None
            self._connected = True
            return True

    async def subscribe(self, asset: str, timeframe: int) -> None:
        key = (asset, timeframe)
        if key in self._subscriptions:
            return
        self._subscriptions.add(key)
        await self._load_history(asset, timeframe)
        if self._client:
            asyncio.create_task(self._stream_live(asset, timeframe))
        else:
            asyncio.create_task(self._simulate(asset, timeframe))

    async def _load_history(self, asset: str, timeframe: int) -> None:
        if not self._client:
            return
        try:
            candles = await self._client.get_historical_candles(
                asset=asset,
                amount_of_seconds=settings.CANDLE_HISTORY_SECONDS,
                period=timeframe,
                max_workers=3,
            )
            if not candles:
                logger.warning(f"No history returned for {asset} — check asset name")
                return
            for raw in candles:
                candle = Candle(
                    time=int(raw.get("time", 0)),
                    open=float(raw.get("open", 0)),
                    high=float(raw.get("high", 0)),
                    low=float(raw.get("low", 0)),
                    close=float(raw.get("close", 0)),
                )
                candle_store.push(asset, timeframe, candle)
            logger.info(f"✅ Loaded {len(candles)} candles for {asset}/{timeframe}s")
        except Exception as e:
            logger.warning(f"Could not load history for {asset}: {e}")

    async def _stream_live(self, asset: str, timeframe: int) -> None:
        """Stream live candles using start_realtime_candle + polling get_realtime_candles."""
        if not self._client:
            return
        try:
            # Start the real-time candle stream for this asset
            await self._client.start_realtime_candle(asset, period=timeframe)
            logger.info(f"Started realtime stream for {asset}/{timeframe}s")

            last_time = 0
            while (asset, timeframe) in self._subscriptions:
                await asyncio.sleep(1)  # poll every second
                try:
                    raw_candles = self._client.get_realtime_candles(asset)
                    if not raw_candles:
                        continue

                    # raw_candles is a dict {timeframe: {timestamp: candle}} or list
                    if isinstance(raw_candles, dict):
                        tf_data = raw_candles.get(timeframe, raw_candles.get(str(timeframe), {}))
                        if isinstance(tf_data, dict):
                            items = list(tf_data.values())
                        else:
                            items = tf_data if isinstance(tf_data, list) else []
                    elif isinstance(raw_candles, list):
                        items = raw_candles
                    else:
                        continue

                    for raw in items:
                        if not isinstance(raw, dict):
                            continue
                        ts = int(raw.get("time", raw.get("timestamp", 0)))
                        if ts <= last_time:
                            continue
                        candle = Candle(
                            time=ts,
                            open=float(raw.get("open", 0)),
                            high=float(raw.get("high", 0)),
                            low=float(raw.get("low", 0)),
                            close=float(raw.get("close", raw.get("price", 0))),
                        )
                        candle_store.push(asset, timeframe, candle)
                        await self._notify(asset, timeframe, candle)
                        last_time = ts

                except Exception as e:
                    logger.debug(f"Poll error for {asset}: {e}")

        except Exception as e:
            logger.error(f"Stream error for {asset}: {e}")
            await asyncio.sleep(5)
            if (asset, timeframe) in self._subscriptions:
                asyncio.create_task(self._stream_live(asset, timeframe))

    async def _simulate(self, asset: str, timeframe: int) -> None:
        """Simulation mode — synthetic candles for development without credentials."""
        import random
        logger.info(f"Simulating candles for {asset}/{timeframe}s")

        price = 1.1000 if "USD" in asset else 145.0
        ts = int(time.time()) - (settings.MAX_CANDLES * timeframe)

        for _ in range(settings.MAX_CANDLES):
            change = random.gauss(0, 0.0005)
            o = price
            c = price + change
            h = max(o, c) + abs(random.gauss(0, 0.0002))
            l = min(o, c) - abs(random.gauss(0, 0.0002))
            candle_store.push(asset, timeframe, Candle(
                time=ts, open=round(o,5), high=round(h,5),
                low=round(l,5), close=round(c,5)
            ))
            price = c
            ts += timeframe

        while (asset, timeframe) in self._subscriptions:
            await asyncio.sleep(timeframe)
            change = random.gauss(0, 0.0005)
            o = price
            c = price + change
            h = max(o, c) + abs(random.gauss(0, 0.0002))
            l = min(o, c) - abs(random.gauss(0, 0.0002))
            ts = int(time.time())
            candle = Candle(time=ts, open=round(o,5), high=round(h,5),
                            low=round(l,5), close=round(c,5))
            candle_store.push(asset, timeframe, candle)
            price = c
            await self._notify(asset, timeframe, candle)

    async def _notify(self, asset: str, timeframe: int, candle: Candle) -> None:
        for cb in self._callbacks:
            try:
                await cb(asset, timeframe, candle)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def unsubscribe(self, asset: str, timeframe: int) -> None:
        self._subscriptions.discard((asset, timeframe))

    async def disconnect(self) -> None:
        self._subscriptions.clear()
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
        self._connected = False


data_feed = DataFeed()