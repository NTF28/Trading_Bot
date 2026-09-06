<div align="center">

<!-- Replace this with an actual screenshot of your dashboard -->
![QBOT Dashboard](https://raw.githubusercontent.com/NTF28/Trading_Bot/main/screenshot.png)

# ⚡ QBOT — Quotex Signal Engine

**Real-time binary options signal bot for Quotex.**
Multi-indicator analysis + XGBoost ML — one dashboard.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

</div>

---

## What it does

QBOT connects to Quotex via WebSocket, streams live candle data for any OTC or real market pair, runs it through a 6-indicator engine + a trained XGBoost model, and outputs a **CALL / PUT signal with a win probability %** — updated every minute.

```
Quotex WebSocket → Candle Store → Indicator Engine → Signal Engine → React Dashboard
                                        ↕
                              RSI · MACD · BB · EMA · Stoch · Patterns
                                        ↕
                               XGBoost ML (50% blend)
```

---

## Features

- 📡 **Live WebSocket feed** — real-time OHLCV candles from Quotex (OTC + real pairs)
- 🧠 **6-indicator fusion** — RSI, MACD, Bollinger Bands, EMA crossover, Stochastic, candlestick patterns
- 🤖 **XGBoost ML model** — trained on historical Quotex data, blended with indicator score
- 📊 **Live candlestick chart** — with EMA 9 + EMA 21 overlays
- 🔍 **Pair search** — searchable grid of all available assets
- 🕐 **Timezone selector** — local time analysis with hour/minute picker
- 📋 **Signal history** — per-pair log with timestamps and confidence
- 🧪 **Simulation mode** — works without credentials for development
- ✅ **Demo account safe** — uses Quotex practice account by default

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Data | PyQuotex (unofficial Quotex WebSocket client) |
| Indicators | pandas, pandas-ta |
| ML | XGBoost, scikit-learn |
| Frontend | React 18, Vite |
| Charts | lightweight-charts (TradingView) |
| Realtime | WebSocket (FastAPI ↔ React) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A free [Quotex](https://quotex.io) account

### 1. Clone

```bash
git clone https://github.com/NTF28/Trading_Bot.git
cd Trading_Bot
```

### 2. Backend

```bash
cd backend
pip install fastapi uvicorn websockets pandas pandas-ta xgboost scikit-learn numpy python-dotenv
pip install "pyquotex @ git+https://github.com/cleitonleonel/pyquotex.git"
```

Create your `.env`:
```bash
QUOTEX_EMAIL=your@email.com
QUOTEX_PASSWORD=yourpassword
QUOTEX_DEMO=true
```

Start:
```bash
uvicorn main:app --reload
```

### 3. Frontend

```bash
cd ../frontend
npm install
npm install lightweight-charts
npm run dev
```

Open **http://localhost:5173**

### 4. Train the ML model *(optional)*

```bash
cd backend
python models/train.py
```

Fetches 7 days of historical candles per asset and saves `models/xgb_model.pkl`. Signal engine auto-loads it on restart.

---

## How signals work

Each indicator votes **+1 (UP)**, **-1 (DOWN)**, or **0 (neutral)**:

| Indicator | Weight |
|---|---|
| MACD | 25% |
| RSI | 20% |
| EMA Crossover | 20% |
| Bollinger Bands | 15% |
| Stochastic | 10% |
| Candlestick Pattern | 10% |

Weighted score → sigmoid → win probability. Blended 50/50 with XGBoost output.
Signals below **60% probability** are suppressed as NEUTRAL.

---

## Configuration

Edit `backend/core/config.py`:

```python
MIN_WIN_PROBABILITY = 0.60   # Minimum % to fire a signal
ML_BLEND = 0.50              # 0 = pure indicators, 1 = pure ML
DEFAULT_TIMEFRAME = 60       # Candle size in seconds

OTC_ASSETS = [               # Add any Quotex OTC pair here
    "EURUSD_otc",
    "AUDCAD_otc",
    ...
]
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Connection status |
| `GET` | `/api/assets` | All available pairs |
| `GET` | `/api/signal?asset=EURUSD_otc&timeframe=60` | Current signal |
| `GET` | `/api/candles?asset=EURUSD_otc&timeframe=60&n=150` | Recent candles |
| `WS` | `/ws/signals` | Live signal stream |

---

## Project Structure

```
Trading_Bot/
├── backend/
│   ├── core/
│   │   ├── config.py          # Settings
│   │   ├── candle_store.py    # OHLCV rolling buffer
│   │   ├── indicators.py      # Technical indicator engine
│   │   ├── signal_engine.py   # Weighted vote + ML scorer
│   │   └── data_feed.py       # Quotex WebSocket connection
│   ├── models/
│   │   └── train.py           # XGBoost trainer
│   ├── main.py                # FastAPI server
│   └── .env                   # Credentials (never commit)
└── frontend/
    └── src/
        ├── App.jsx
        ├── components/
        │   └── CandleChart.jsx
        ├── hooks/
        │   └── useSignalSocket.js
        └── utils/
            └── api.js
```

---

## Disclaimer

This project is for **educational purposes only**. Binary options trading carries significant financial risk. Past signal accuracy does not guarantee future results. Never trade money you cannot afford to lose. The authors are not responsible for any financial losses.

---

<div align="center">

Built with 🤖 + ☕ &nbsp;|&nbsp; MIT License &nbsp;|&nbsp; PRs welcome

</div>
