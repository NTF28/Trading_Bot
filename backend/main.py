import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.data_feed import data_feed
from core.signal_engine import signal_engine
from core.candle_store import candle_store, Candle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def on_new_candle(asset: str, timeframe: int, candle: Candle):
    signal = signal_engine.generate(asset, timeframe)
    if signal and signal.direction != "NEUTRAL":
        await manager.broadcast({"type": "signal", "data": signal.to_dict()})
    await manager.broadcast({
        "type": "candle",
        "data": {"asset": asset, "timeframe": timeframe, **candle.to_dict()},
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting data feed...")
    await data_feed.connect()
    data_feed.on_candle(on_new_candle)
    default_asset = settings.OTC_ASSETS[0]
    await data_feed.subscribe(default_asset, settings.DEFAULT_TIMEFRAME)
    logger.info(f"Subscribed to {default_asset} @ {settings.DEFAULT_TIMEFRAME}s")
    yield
    logger.info("Shutting down...")
    await data_feed.disconnect()


app = FastAPI(title="Quotex Signal Bot", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/assets")
def get_assets():
    return {"otc": settings.OTC_ASSETS, "real": settings.REAL_ASSETS, "timeframes": settings.TIMEFRAMES}


@app.get("/api/signal")
async def get_signal(asset: str = Query(...), timeframe: int = Query(60)):
    await data_feed.subscribe(asset, timeframe)
    if not candle_store.has_enough_data(asset, timeframe, min_candles=50):
        return {"status": "loading", "message": "Collecting candle data..."}
    signal = signal_engine.generate(asset, timeframe)
    if not signal:
        return {"status": "loading", "message": "Not enough data yet"}
    return {"status": "ok", "signal": signal.to_dict()}


@app.get("/api/candles")
async def get_candles(asset: str = Query(...), timeframe: int = Query(60), n: int = Query(100)):
    await data_feed.subscribe(asset, timeframe)
    candles = candle_store.get(asset, timeframe, n=n)
    return {"asset": asset, "timeframe": timeframe, "candles": [c.to_dict() for c in candles]}


@app.post("/api/subscribe")
async def subscribe(asset: str = Query(...), timeframe: int = Query(60)):
    all_assets = settings.OTC_ASSETS + settings.REAL_ASSETS
    if asset not in all_assets:
        raise HTTPException(status_code=400, detail=f"Unknown asset: {asset}")
    await data_feed.subscribe(asset, timeframe)
    return {"status": "subscribed", "asset": asset, "timeframe": timeframe}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "connected": data_feed.connected,
        "pairs": [f"{a}/{t}s" for a, t in candle_store.available_pairs()],
    }


@app.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info(f"WS client connected. Total: {len(manager.active)}")
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                data = json.loads(msg)
                if data.get("type") == "subscribe":
                    asset = data.get("asset", settings.OTC_ASSETS[0])
                    timeframe = int(data.get("timeframe", settings.DEFAULT_TIMEFRAME))
                    await data_feed.subscribe(asset, timeframe)
                    await websocket.send_json({"type": "subscribed", "asset": asset, "timeframe": timeframe})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WS client disconnected. Remaining: {len(manager.active)}")