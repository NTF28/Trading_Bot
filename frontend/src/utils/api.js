const BASE = "http://127.0.0.1:8000";

export async function fetchAssets() {
  const res = await fetch(`${BASE}/api/assets`);
  return res.json();
}

export async function fetchCandles(asset, timeframe, n = 150) {
  const res = await fetch(`${BASE}/api/candles?asset=${asset}&timeframe=${timeframe}&n=${n}`);
  return res.json();
}

export async function fetchSignal(asset, timeframe) {
  const res = await fetch(`${BASE}/api/signal?asset=${asset}&timeframe=${timeframe}`);
  return res.json();
}