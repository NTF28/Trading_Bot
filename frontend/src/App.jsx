import React, { useState, useEffect, useRef } from "react";
import CandleChart from "./components/CandleChart";
import { useSignalSocket } from "./hooks/useSignalSocket";
import { fetchAssets, fetchCandles, fetchSignal } from "./utils/api";

const TIMEZONES = [
  { label: "UTC+0 — London (GMT)", offset: 0 },
  { label: "UTC+1 — Central Europe (CET)", offset: 60 },
  { label: "UTC+2 — Eastern Europe (EET)", offset: 120 },
  { label: "UTC+3 — Moscow (MSK)", offset: 180 },
  { label: "UTC+4 — Gulf (GST)", offset: 240 },
  { label: "UTC+5:30 — India (IST)", offset: 330 },
  { label: "UTC+6 — Bangladesh (BST)", offset: 360 },
  { label: "UTC+7 — Thailand (ICT)", offset: 420 },
  { label: "UTC+8 — Singapore (SGT)", offset: 480 },
  { label: "UTC+9 — Japan (JST)", offset: 540 },
  { label: "UTC-5 — Eastern US (EST)", offset: -300 },
  { label: "UTC-6 — Central US (CST)", offset: -360 },
  { label: "UTC-8 — Pacific US (PST)", offset: -480 },
];

const TIMEFRAMES = [
  { label: "1m", value: 60 },
  { label: "2m", value: 120 },
  { label: "3m", value: 180 },
  { label: "5m", value: 300 },
  { label: "15m", value: 900 },
];

function getLocalTime(offsetMinutes) {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const local = new Date(utc + offsetMinutes * 60000);
  return { h: local.getHours(), m: local.getMinutes(), s: local.getSeconds() };
}

export default function App() {
  const [assets, setAssets] = useState({ otc: [], real: [] });
  const [search, setSearch] = useState("");
  const [asset, setAsset] = useState("EURUSD_otc");
  const [timeframe, setTimeframe] = useState(60);
  const [timezone, setTimezone] = useState(TIMEZONES[5]); // IST default
  const [analyzeHour, setAnalyzeHour] = useState(null);
  const [analyzeMin, setAnalyzeMin] = useState(null);
  const [currentTime, setCurrentTime] = useState(getLocalTime(330));
  const [initCandles, setInitCandles] = useState([]);
  const [initSignal, setInitSignal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [signalHistory, setSignalHistory] = useState([]);
  const [showChart, setShowChart] = useState(false);

  const { signal: liveSignal, candles: liveCandles, connected } = useSignalSocket(asset, timeframe);

  const candles = liveCandles.length > 0 ? liveCandles : initCandles;
  const signal = (() => {
    const s = liveSignal || initSignal;
    if (!s) return null;
    if (s.asset !== asset || s.timeframe !== timeframe) return null;
    return s;
  })();

  // Clock tick
  useEffect(() => {
    const t = setInterval(() => setCurrentTime(getLocalTime(timezone.offset)), 1000);
    return () => clearInterval(t);
  }, [timezone]);

  // Set default analyze time to now
  useEffect(() => {
    if (analyzeHour === null) {
      const t = getLocalTime(timezone.offset);
      setAnalyzeHour(t.h);
      setAnalyzeMin(t.m);
    }
  }, [timezone]);

  useEffect(() => {
    fetchAssets().then(setAssets).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    setInitCandles([]);
    setInitSignal(null);
    Promise.all([fetchCandles(asset, timeframe, 150), fetchSignal(asset, timeframe)])
      .then(([cr, sr]) => {
        setInitCandles(cr.candles || []);
        if (sr.status === "ok") setInitSignal(sr.signal);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, [asset, timeframe]);

  useEffect(() => {
    if (!liveSignal || liveSignal.direction === "NEUTRAL") return;
    if (liveSignal.asset !== asset || liveSignal.timeframe !== timeframe) return;
    setSignalHistory(p => [{ ...liveSignal, ts: new Date().toLocaleTimeString() }, ...p].slice(0, 15));
  }, [liveSignal]);

  useEffect(() => { setSignalHistory([]); }, [asset, timeframe]);

  const allAssets = [...(assets.otc || []), ...(assets.real || [])];
  const filtered = allAssets.filter(a => a.toLowerCase().includes(search.toLowerCase()));

  const handleGenerateSignal = () => {
    setShowChart(true);
    setLoading(true);
    fetchSignal(asset, timeframe).then(sr => {
      if (sr.status === "ok") setInitSignal(sr.signal);
      setLoading(false);
    });
    fetchCandles(asset, timeframe, 150).then(cr => setInitCandles(cr.candles || []));
  };

  const pad = n => String(n).padStart(2, "0");
  const timeStr = `${pad(currentTime.h)}:${pad(currentTime.m)}:${pad(currentTime.s)}`;
  const tzLabel = timezone.label.split("—")[0].trim();

  return (
    <div style={{ minHeight:"100vh", background:"#08090d", color:"#fff",
      fontFamily:"'Inter', system-ui, sans-serif", display:"flex", flexDirection:"column" }}>

      {/* Top bar */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"14px 28px", borderBottom:"1px solid #1a1d2e", background:"#0b0c14" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:32, height:32, borderRadius:8, background:"linear-gradient(135deg,#6c63ff,#3ecf8e)",
            display:"flex", alignItems:"center", justifyContent:"center", fontWeight:800, fontSize:14 }}>Q</div>
          <span style={{ fontWeight:700, fontSize:16, letterSpacing:0.5 }}>QBOT <span style={{ color:"#6c63ff", fontSize:12, fontWeight:400 }}>Signal Engine</span></span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ width:7, height:7, borderRadius:"50%", background: connected?"#3ecf8e":"#ff4d6d",
            boxShadow: connected?"0 0 8px #3ecf8e":"0 0 8px #ff4d6d" }} />
          <span style={{ fontSize:12, color: connected?"#3ecf8e":"#ff4d6d" }}>{connected?"LIVE":"OFFLINE"}</span>
          <span style={{ color:"#333", margin:"0 8px" }}>|</span>
          <span style={{ fontSize:12, color:"#888" }}>{tzLabel} · {timeStr}</span>
        </div>
      </div>

      <div style={{ display:"flex", flex:1, gap:0 }}>

        {/* LEFT PANEL — controls */}
        <div style={{ width:360, background:"#0b0c14", borderRight:"1px solid #1a1d2e",
          padding:"24px 20px", display:"flex", flexDirection:"column", gap:24, overflowY:"auto" }}>

          {/* Pair search */}
          <div>
            <label style={labelStyle}>Select Pair</label>
            <input
              placeholder="Search pairs..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ width:"100%", background:"#13141f", border:"1px solid #1e2035",
                borderRadius:10, padding:"10px 14px", color:"#fff", fontSize:13,
                outline:"none", marginBottom:10, boxSizing:"border-box" }}
            />
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, maxHeight:220, overflowY:"auto" }}>
              {filtered.map(a => (
                <button key={a} onClick={() => { setAsset(a); setShowChart(false); setSearch(""); }}
                  style={{ background: a===asset ? "#6c63ff22" : "#13141f",
                    border: a===asset ? "1px solid #6c63ff" : "1px solid #1e2035",
                    borderRadius:8, padding:"8px 10px", color: a===asset ? "#a89fff" : "#888",
                    fontSize:11, cursor:"pointer", textAlign:"center", fontWeight: a===asset?600:400,
                    transition:"all 0.15s", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                  {a.replace("_otc","").replace(/([A-Z]{3})([A-Z]{3})/,"$1/$2")}
                  {a.includes("_otc") && <span style={{ color:"#6c63ff", marginLeft:3, fontSize:9 }}>OTC</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Timeframe */}
          <div>
            <label style={labelStyle}>Timeframe</label>
            <div style={{ display:"flex", gap:6 }}>
              {TIMEFRAMES.map(tf => (
                <button key={tf.value} onClick={() => setTimeframe(tf.value)}
                  style={{ flex:1, background: tf.value===timeframe?"#6c63ff":"#13141f",
                    border: tf.value===timeframe?"1px solid #6c63ff":"1px solid #1e2035",
                    borderRadius:8, padding:"8px 0", color: tf.value===timeframe?"#fff":"#666",
                    fontSize:12, cursor:"pointer", fontWeight: tf.value===timeframe?700:400 }}>
                  {tf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Timezone */}
          <div>
            <label style={labelStyle}>Your Timezone</label>
            <select value={timezone.label}
              onChange={e => setTimezone(TIMEZONES.find(t => t.label === e.target.value))}
              style={{ width:"100%", background:"#13141f", border:"1px solid #1e2035",
                borderRadius:10, padding:"10px 14px", color:"#aaa", fontSize:12,
                outline:"none", cursor:"pointer", boxSizing:"border-box" }}>
              {TIMEZONES.map(tz => <option key={tz.label}>{tz.label}</option>)}
            </select>
          </div>

          {/* Analyze time */}
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
              <label style={labelStyle}>Analysis Time (Local)</label>
              <button onClick={() => { const t=getLocalTime(timezone.offset); setAnalyzeHour(t.h); setAnalyzeMin(t.m); }}
                style={{ background:"none", border:"none", color:"#6c63ff", fontSize:11, cursor:"pointer" }}>
                Use Now
              </button>
            </div>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:16,
              background:"#13141f", border:"1px solid #1e2035", borderRadius:10, padding:"16px" }}>
              <TimeSpinner value={analyzeHour??0} min={0} max={23} onChange={setAnalyzeHour} label="HOUR" />
              <span style={{ fontSize:28, color:"#6c63ff", fontWeight:700 }}>:</span>
              <TimeSpinner value={analyzeMin??0} min={0} max={59} onChange={setAnalyzeMin} label="MIN" />
            </div>
          </div>

          {/* Generate button */}
          <button onClick={handleGenerateSignal}
            style={{ width:"100%", padding:"14px", borderRadius:12,
              background:"linear-gradient(135deg,#6c63ff,#4f46e5)",
              border:"none", color:"#fff", fontSize:14, fontWeight:700,
              cursor:"pointer", letterSpacing:0.5, boxShadow:"0 4px 20px #6c63ff44",
              transition:"opacity 0.2s" }}
            onMouseOver={e => e.target.style.opacity=0.85}
            onMouseOut={e => e.target.style.opacity=1}>
            ⚡ Generate Signal
          </button>

          {/* Signal history */}
          {signalHistory.length > 0 && (
            <div>
              <label style={labelStyle}>History · {asset.replace("_otc","")}</label>
              <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                {signalHistory.map((s,i) => (
                  <div key={i} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    background:"#13141f", borderRadius:8, padding:"8px 12px",
                    border:`1px solid ${s.direction==="UP"?"#3ecf8e22":"#ff4d6d22"}` }}>
                    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                      <span style={{ color:s.direction==="UP"?"#3ecf8e":"#ff4d6d", fontSize:13 }}>
                        {s.direction==="UP"?"▲":"▼"}
                      </span>
                      <span style={{ color:s.direction==="UP"?"#3ecf8e":"#ff4d6d", fontWeight:700, fontSize:12 }}>
                        {s.direction==="UP"?"CALL":"PUT"}
                      </span>
                    </div>
                    <div style={{ textAlign:"right" }}>
                      <div style={{ fontSize:12, fontWeight:700, color:"#fff" }}>{s.probability}%</div>
                      <div style={{ fontSize:10, color:"#444" }}>{s.ts}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT — chart + signal */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {/* Signal result banner */}
          {showChart && signal && signal.direction !== "NEUTRAL" && (
            <div style={{ padding:"16px 24px", background:"#0e0f1a", borderBottom:"1px solid #1a1d2e" }}>
              <SignalBanner signal={signal} asset={asset} timeframe={timeframe}
                analyzeHour={analyzeHour} analyzeMin={analyzeMin} timezone={timezone} />
            </div>
          )}

          {/* Chart */}
          <div style={{ flex:1, padding:16, minHeight:0 }}>
            <div style={{ height:"100%", background:"#0e0f1a", border:"1px solid #1a1d2e",
              borderRadius:12, overflow:"hidden", position:"relative" }}>
              {!showChart ? (
                <div style={{ height:"100%", display:"flex", alignItems:"center", justifyContent:"center",
                  flexDirection:"column", gap:12, color:"#333" }}>
                  <div style={{ fontSize:40 }}>📈</div>
                  <div style={{ fontSize:14 }}>Select a pair and click Generate Signal</div>
                </div>
              ) : (
                <CandleChart candles={candles} signal={signal} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TimeSpinner({ value, min, max, onChange, label }) {
  const inc = () => onChange(v => v >= max ? min : v + 1);
  const dec = () => onChange(v => v <= min ? max : v - 1);
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6 }}>
      <button onClick={inc} style={spinBtn}>▲</button>
      <span style={{ fontSize:28, fontWeight:700, minWidth:40, textAlign:"center" }}>
        {String(value).padStart(2,"0")}
      </span>
      <button onClick={dec} style={spinBtn}>▼</button>
      <span style={{ fontSize:10, color:"#444", letterSpacing:1 }}>{label}</span>
    </div>
  );
}

function SignalBanner({ signal, asset, timeframe, analyzeHour, analyzeMin, timezone }) {
  const isUp = signal.direction === "UP";
  const color = isUp ? "#3ecf8e" : "#ff4d6d";
  const tfLabel = TIMEFRAMES.find(t => t.value === timeframe)?.label || `${timeframe}s`;
  const pairLabel = asset.replace("_otc","").replace(/([A-Z]{3})([A-Z]{3})/,"$1/$2");
  const isOtc = asset.includes("_otc");
  const tzShort = timezone.label.match(/\(([^)]+)\)/)?.[1] || "UTC";
  const pad = n => String(n).padStart(2,"0");

  return (
    <div style={{ display:"flex", alignItems:"center", gap:24, flexWrap:"wrap" }}>

      {/* Direction */}
      <div style={{ display:"flex", alignItems:"center", gap:14,
        background:`${color}12`, border:`1px solid ${color}44`,
        borderRadius:12, padding:"14px 20px" }}>
        <div style={{ fontSize:32, color }}>{isUp ? "▲" : "▼"}</div>
        <div>
          <div style={{ fontSize:10, color:"#666", letterSpacing:1, marginBottom:2 }}>SIGNAL DIRECTION</div>
          <div style={{ fontSize:22, fontWeight:800, color }}>{isUp ? "CALL / BUY" : "PUT / SELL"}</div>
        </div>
      </div>

      {/* Pair + time */}
      <div style={{ background:"#13141f", border:"1px solid #1e2035", borderRadius:12, padding:"14px 20px" }}>
        <div style={{ fontSize:10, color:"#666", letterSpacing:1, marginBottom:4 }}>PAIR</div>
        <div style={{ fontSize:18, fontWeight:700 }}>
          {pairLabel} {isOtc && <span style={{ color:"#6c63ff", fontSize:11 }}>OTC</span>}
        </div>
        <div style={{ fontSize:11, color:"#555", marginTop:2 }}>
          {pad(analyzeHour??0)}:{pad(analyzeMin??0)} ({tzShort}) · {tfLabel}
        </div>
      </div>

      {/* Probability */}
      <div style={{ flex:1, minWidth:200, background:"#13141f", border:"1px solid #1e2035", borderRadius:12, padding:"14px 20px" }}>
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
          <span style={{ fontSize:10, color:"#666", letterSpacing:1 }}>WIN PROBABILITY</span>
          <span style={{ fontSize:16, fontWeight:800, color }}>{signal.probability}%</span>
        </div>
        <div style={{ background:"#1a1d2e", borderRadius:6, height:6, overflow:"hidden" }}>
          <div style={{ width:`${signal.probability}%`, height:"100%", background:color,
            borderRadius:6, transition:"width 0.8s ease" }} />
        </div>
        <div style={{ display:"flex", justifyContent:"space-between", marginTop:6 }}>
          <span style={{ fontSize:10, color:"#333" }}>50%</span>
          <span style={{ fontSize:11, fontWeight:600,
            color: signal.confidence==="HIGH"?"#3ecf8e":signal.confidence==="MEDIUM"?"#f59e0b":"#888" }}>
            {signal.confidence} CONFIDENCE
          </span>
          <span style={{ fontSize:10, color:"#333" }}>95%</span>
        </div>
      </div>

      {/* Indicators mini */}
      <div style={{ background:"#13141f", border:"1px solid #1e2035", borderRadius:12, padding:"14px 20px" }}>
        <div style={{ fontSize:10, color:"#666", letterSpacing:1, marginBottom:8 }}>INDICATORS</div>
        {[
          ["RSI", signal.indicators?.rsi, signal.indicators?.rsi_signal],
          ["MACD", signal.indicators?.macd_histogram, signal.indicators?.macd_signal],
          ["EMA", null, signal.indicators?.ema_signal],
          ["Stoch", signal.indicators?.stoch_k, signal.indicators?.stoch_signal],
        ].map(([name, val, sig]) => (
          <div key={name} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:16, marginBottom:4 }}>
            <span style={{ fontSize:11, color:"#555", width:40 }}>{name}</span>
            <span style={{ fontSize:11, color:"#888" }}>{val != null ? Number(val).toFixed(2) : "—"}</span>
            <span style={{ fontSize:11, color: sig===1?"#3ecf8e":sig===-1?"#ff4d6d":"#444" }}>
              {sig===1?"▲":sig===-1?"▼":"—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const labelStyle = { fontSize:11, color:"#555", letterSpacing:1, textTransform:"uppercase",
  display:"block", marginBottom:8, fontWeight:600 };
const spinBtn = { background:"none", border:"none", color:"#6c63ff", fontSize:14,
  cursor:"pointer", padding:"2px 8px", borderRadius:4 };