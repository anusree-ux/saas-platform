import { useState } from "react";
import "./App.css";

function App() {
  const [apiKey, setApiKey] = useState("");

  const handleConnect = () => {
    console.log("API key submitted:", apiKey);
  };

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

        <button onClick={handleConnect} disabled={!apiKey}>
          Connect
        </button>

        <div className="status">
          <span className="status-dot disconnected"></span>
          <span>Disconnected</span>
        </div>
      </div>
    </div>
  );
}

export default App;