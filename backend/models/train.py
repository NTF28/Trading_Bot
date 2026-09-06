"""
Model trainer — run this standalone to train the XGBoost model.
Usage: python backend/models/train.py
Requires a valid .env with Quotex credentials.
"""

import asyncio
import sys
import os
import pickle
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import settings
from core.indicators import indicator_engine, IndicatorResult

try:
    from pyquotex.stable_api import Quotex
    PYQUOTEX_AVAILABLE = True
except ImportError:
    PYQUOTEX_AVAILABLE = False

try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


def extract_features(df: pd.DataFrame) -> list[dict]:
    """
    Slide a window over the DataFrame, compute indicators at each step,
    and label: 1 if next candle closes higher, 0 if lower.
    """
    rows = []
    min_window = 50

    for i in range(min_window, len(df) - 1):
        window = df.iloc[:i].copy()
        result = indicator_engine.compute(window)

        # Skip if critical indicators are NaN
        if np.isnan(result.rsi) or np.isnan(result.macd_histogram):
            continue

        label = 1 if df["close"].iloc[i + 1] > df["close"].iloc[i] else 0

        rows.append({
            "rsi": result.rsi,
            "macd_histogram": result.macd_histogram if not np.isnan(result.macd_histogram) else 0,
            "bb_signal": result.bb_signal,
            "ema_signal": result.ema_signal,
            "stoch_k": result.stoch_k if not np.isnan(result.stoch_k) else 50,
            "stoch_d": result.stoch_d if not np.isnan(result.stoch_d) else 50,
            "rsi_signal": result.rsi_signal,
            "macd_signal": result.macd_signal,
            "pattern_signal": result.pattern_signal,
            "label": label,
        })

    return rows


async def fetch_training_data(assets: list[str], timeframe: int = 60) -> pd.DataFrame:
    """Fetch historical candles for all assets from Quotex."""
    if not PYQUOTEX_AVAILABLE:
        raise RuntimeError("PyQuotex not installed")

    client = Quotex(email=settings.QUOTEX_EMAIL, password=settings.QUOTEX_PASSWORD)
    await client.connect()

    all_rows = []
    for asset in assets:
        print(f"  Fetching {asset}...")
        try:
            candles = await client.get_historical_candles(
                asset=asset,
                amount_of_seconds=86400 * 7,  # 7 days of history
                period=timeframe,
                max_workers=3,
            )
            if not candles:
                print(f"  No data for {asset}, skipping")
                continue

            df = pd.DataFrame(candles)
            df = df.rename(columns={"time": "time", "open": "open", "close": "close",
                                     "high": "high", "low": "low"})
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("time").sort_index()

            rows = extract_features(df)
            all_rows.extend(rows)
            print(f"  {asset}: {len(rows)} training samples")
        except Exception as e:
            print(f"  Error on {asset}: {e}")

    await client.close()
    return pd.DataFrame(all_rows)


def train(data: pd.DataFrame) -> None:
    feature_cols = ["rsi", "macd_histogram", "bb_signal", "ema_signal",
                    "stoch_k", "stoch_d", "rsi_signal", "macd_signal", "pattern_signal"]

    X = data[feature_cols].values
    y = data["label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\n✅ Accuracy: {acc:.2%}")
    print(classification_report(y_test, preds, target_names=["DOWN", "UP"]))

    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    model_path = os.path.join(os.path.dirname(__file__), "xgb_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"✅ Model saved to {model_path}")


async def main():
    if not XGB_AVAILABLE:
        print("❌ XGBoost not installed")
        return
    if not PYQUOTEX_AVAILABLE:
        print("❌ PyQuotex not installed")
        return
    if not settings.QUOTEX_EMAIL:
        print("❌ QUOTEX_EMAIL not set in .env")
        return

    assets = settings.OTC_ASSETS[:3] + settings.REAL_ASSETS[:2]
    print(f"Fetching training data for: {assets}")
    data = await fetch_training_data(assets)

    if data.empty:
        print("❌ No training data collected")
        return

    print(f"\nTotal samples: {len(data)} | UP: {data['label'].sum()} | DOWN: {(data['label']==0).sum()}")
    train(data)


if __name__ == "__main__":
    asyncio.run(main())