import { useEffect, useRef, useState, useCallback } from "react";

export function useSignalSocket(asset, timeframe) {
  const ws = useRef(null);
  const [signal, setSignal] = useState(null);
  const [candles, setCandles] = useState([]);
  const [connected, setConnected] = useState(false);
  const pendingSubscribe = useRef({ asset, timeframe });

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN ||
        ws.current?.readyState === WebSocket.CONNECTING) return;

    const socket = new WebSocket("ws://127.0.0.1:8000/ws/signals");
    ws.current = socket;

    socket.onopen = () => {
      setConnected(true);
      // Send subscribe once connection is confirmed open
      socket.send(JSON.stringify({
        type: "subscribe",
        asset: pendingSubscribe.current.asset,
        timeframe: pendingSubscribe.current.timeframe,
      }));
    };

    socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "signal") setSignal(msg.data);
        if (msg.type === "candle") {
          setCandles((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.time === msg.data.time) {
              updated[updated.length - 1] = msg.data;
            } else {
              updated.push(msg.data);
              if (updated.length > 300) updated.shift();
            }
            return updated;
          });
        }
      } catch (err) {
        console.error("WS parse error", err);
      }
    };

    socket.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };

    socket.onerror = () => socket.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  // When asset/timeframe changes, update the pending ref and send if open
  useEffect(() => {
    pendingSubscribe.current = { asset, timeframe };
    setCandles([]);
    setSignal(null);
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "subscribe", asset, timeframe }));
    }
  }, [asset, timeframe]);

  return { signal, candles, connected };
}