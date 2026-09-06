import React, { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts";

export default function CandleChart({ candles, signal }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const emaFastRef = useRef(null);
  const emaSlowRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0e0f1a" }, textColor: "#555" },
      grid: { vertLines: { color: "#13141f" }, horzLines: { color: "#13141f" } },
      crosshair: { mode: 1,
        vertLine: { color: "#6c63ff44", labelBackgroundColor: "#6c63ff" },
        horzLine: { color: "#6c63ff44", labelBackgroundColor: "#6c63ff" },
      },
      rightPriceScale: { borderColor: "#1a1d2e", textColor: "#555" },
      timeScale: { borderColor: "#1a1d2e", timeVisible: true, secondsVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 400,
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#3ecf8e", downColor: "#ff4d6d",
      borderUpColor: "#3ecf8e", borderDownColor: "#ff4d6d",
      wickUpColor: "#3ecf8e88", wickDownColor: "#ff4d6d88",
    });

    const emaFast = chart.addSeries(LineSeries, {
      color: "#6c63ff", lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });
    const emaSlow = chart.addSeries(LineSeries, {
      color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = candleSeries;
    emaFastRef.current = emaFast;
    emaSlowRef.current = emaSlow;

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight || 400);
    });
    ro.observe(containerRef.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !candles?.length) return;
    const sorted = [...candles].sort((a, b) => a.time - b.time);
    try {
      seriesRef.current.setData(sorted.map(c => ({
        time: c.time, open: c.open, high: c.high, low: c.low, close: c.close,
      })));

      const ema = (arr, period) => {
        const k = 2 / (period + 1);
        let e = arr[0];
        return arr.map((v, i) => { e = i === 0 ? v : v * k + e * (1 - k); return e; });
      };
      const closes = sorted.map(c => c.close);
      const fast = ema(closes, 9);
      const slow = ema(closes, 21);

      emaFastRef.current?.setData(sorted.map((c, i) => ({ time: c.time, value: parseFloat(fast[i].toFixed(5)) })).slice(9));
      emaSlowRef.current?.setData(sorted.map((c, i) => ({ time: c.time, value: parseFloat(slow[i].toFixed(5)) })).slice(21));
    } catch (e) { console.warn("Chart error:", e.message); }
  }, [candles]);

  const isUp = signal?.direction === "UP";
  const color = isUp ? "#3ecf8e" : "#ff4d6d";

  return (
    <div style={{ position:"relative", width:"100%", height:"100%" }}>
      <div ref={containerRef} style={{ width:"100%", height:"100%" }} />

      {/* Legend */}
      <div style={{ position:"absolute", top:12, left:12, display:"flex", gap:14, pointerEvents:"none" }}>
        {[["#3ecf8e","Bullish"], ["#ff4d6d","Bearish"], ["#6c63ff","EMA 9"], ["#f59e0b","EMA 21"]].map(([c,l]) => (
          <div key={l} style={{ display:"flex", alignItems:"center", gap:4 }}>
            <div style={{ width: l.startsWith("EMA")?14:8, height: l.startsWith("EMA")?2:8,
              background:c, borderRadius:2 }} />
            <span style={{ color:"#444", fontSize:10 }}>{l}</span>
          </div>
        ))}
      </div>

      {/* Signal overlay */}
      {signal && signal.direction !== "NEUTRAL" && (
        <div style={{ position:"absolute", top:12, right:12, pointerEvents:"none",
          background:`${color}15`, border:`1px solid ${color}55`,
          borderRadius:8, padding:"8px 16px", backdropFilter:"blur(4px)" }}>
          <span style={{ color, fontWeight:800, fontSize:14 }}>
            {isUp ? "▲ CALL" : "▼ PUT"} &nbsp; {signal.probability}%
          </span>
        </div>
      )}
    </div>
  );
}