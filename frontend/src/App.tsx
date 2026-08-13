import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(false);
  const [count, setCount] = useState(0);
  const [connecting, setConnecting] = useState(false);

  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(false);

  const connectWebSocket = () => {
    if (!apiKey) return;

    shouldReconnectRef.current = true;
    setConnecting(true);

    const websocket = new WebSocket(
      `ws://127.0.0.1:8000/ws?api_key=${encodeURIComponent(apiKey)}`
    );

    websocketRef.current = websocket;

    websocket.onopen = () => {
      console.log("WebSocket connected");
      setConnected(true);
      setConnecting(false);
    };

    websocket.onmessage = (event) => {
      console.log("WebSocket message:", event.data);

      try {
        const data = JSON.parse(event.data);
        setCount(data.count);
      } catch (error) {
        console.error("Invalid WebSocket message:", error);
      }
    };

    websocket.onclose = () => {
      console.log("WebSocket disconnected");

      setConnected(false);
      setConnecting(false);

      if (shouldReconnectRef.current) {
        console.log("Reconnecting in 3 seconds...");

        reconnectTimerRef.current = window.setTimeout(() => {
          connectWebSocket();
        }, 3000);
      }
    };

    websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  };

  const handleConnect = () => {
    if (websocketRef.current) {
      websocketRef.current.close();
    }

    connectWebSocket();
  };

  useEffect(() => {
    return () => {
      shouldReconnectRef.current = false;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      websocketRef.current?.close();
    };
  }, []);

  return (
    <div className="app">
      <div className="card">
        <h1>SaaS Event Monitor</h1>

        <p className="subtitle">
          Connect to your tenant event stream
        </p>

        <label htmlFor="api-key">API Key</label>

        <input
          id="api-key"
          type="password"
          placeholder="Enter your API key"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
        />

        <button onClick={handleConnect} disabled={!apiKey || connecting}>
          {connecting ? "Connecting..." : "Connect"}
        </button>

        <div className="status">
          <span
            className={`status-dot ${
              connected ? "connected" : "disconnected"
            }`}
          ></span>

          <span>
            {connected
              ? "Connected"
              : connecting
              ? "Connecting..."
              : "Disconnected"}
          </span>
        </div>

        {connected && (
          <div className="count">
            <p>Latest Event Count</p>
            <strong>{count}</strong>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;