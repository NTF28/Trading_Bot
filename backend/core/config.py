import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

class Settings:
    QUOTEX_EMAIL: str = os.getenv("QUOTEX_EMAIL", "")
    QUOTEX_PASSWORD: str = os.getenv("QUOTEX_PASSWORD", "")
    QUOTEX_DEMO: bool = os.getenv("QUOTEX_DEMO", "true").lower() == "true"

    # Candle settings
    DEFAULT_TIMEFRAME: int = 60          # seconds (1 minute)
    CANDLE_HISTORY_SECONDS: int = 7200   # 2 hours of history on startup
    MAX_CANDLES: int = 500               # rolling buffer size

    # Signal engine settings
    MIN_WIN_PROBABILITY: float = 0.60    # minimum to emit a signal
    SIGNAL_COOLDOWN_SEC: int = 30        # seconds between signals on same asset

    # Supported timeframes (seconds)
    TIMEFRAMES: list[int] = [60, 120, 180, 300, 900]

    # Assets to support (add/remove as needed)
    OTC_ASSETS: list[str] = [
        "NZDJPY_otc",
        "AUDCAD_otc", 
        "NZDCAD_otc",
        "AUDCHF_otc",
        "GBPUSD_otc",
        "USDINR_otc",
        "EURCAD_otc",
        "GBPJPY_otc",
    ]
    REAL_ASSETS: list[str] = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
    ]

settings = Settings()