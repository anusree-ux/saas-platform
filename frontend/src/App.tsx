import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

type EventItem = {
  id: string;
  event_name: string;
  properties: Record<string, unknown>;
  occurred_at: string;
  received_at: string;
};

type AnalyticsEvent = {
  event_name: string;
  count: number;
};

type AnalyticsResponse = {
  since: string;
  total_events: number;
  events: AnalyticsEvent[];
};

type WebSocketEvent = {
  type: string;
  tenant_id: string;
  event_id: string;
  event_name: string;
  properties: Record<string, unknown>;
  occurred_at: string;
  received_at: string;
  count: number;
};

function App() {
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const [totalEvents, setTotalEvents] = useState(0);
  const [eventTypes, setEventTypes] = useState<AnalyticsEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState("user.login");
  const [latestCount, setLatestCount] = useState(0);

  const [events, setEvents] = useState<EventItem[]>([]);

  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  /*
   * Controls whether the application is allowed
   * to maintain a WebSocket connection.
   */
  const shouldReconnectRef = useRef(false);

  /*
   * Every WebSocket connection gets its own ID.
   *
   * This prevents an old WebSocket from triggering
   * reconnect logic after a newer WebSocket has been created.
   */
  const connectionIdRef = useRef(0);

  const API_BASE_URL = "http://127.0.0.1:8000";

  /*
   * Fetch analytics summary.
   */
  const fetchAnalytics = async () => {
    if (!apiKey) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/analytics/events?since=24h`,
        {
          headers: {
            "X-API-Key": apiKey,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Analytics request failed: ${response.status}`
        );
      }

      const data: AnalyticsResponse = await response.json();

      setTotalEvents(data.total_events);
      setEventTypes(data.events);

      /*
       * Make sure selected event still exists.
       */
      setSelectedEvent((currentSelected) => {
        if (data.events.length === 0) {
          return currentSelected;
        }

        const exists = data.events.some(
          (event) => event.event_name === currentSelected
        );

        return exists
          ? currentSelected
          : data.events[0].event_name;
      });

      /*
       * Keep latest count synchronized with the
       * currently selected event.
       */
      const selected = data.events.find(
        (event) => event.event_name === selectedEvent
      );

      if (selected) {
        setLatestCount(selected.count);
      }
    } catch (error) {
      console.error(
        "Failed to fetch analytics:",
        error
      );
    }
  };

  /*
   * Fetch recent events.
   */
  const fetchEvents = async () => {
    if (!apiKey) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/events/`,
        {
          headers: {
            "X-API-Key": apiKey,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Events request failed: ${response.status}`
        );
      }

      const data: EventItem[] = await response.json();

      setEvents(data.slice(0, 10));
    } catch (error) {
      console.error(
        "Failed to fetch events:",
        error
      );
    }
  };

  /*
   * Clear any scheduled reconnect.
   */
  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(
        reconnectTimerRef.current
      );

      reconnectTimerRef.current = null;
    }
  };

  /*
   * Close the current WebSocket.
   */
  const closeCurrentWebSocket = () => {
    const websocket = websocketRef.current;

    if (!websocket) {
      return;
    }

    websocketRef.current = null;

    /*
     * Prevent the socket's onclose handler from
     * starting another reconnect.
     */
    websocket.onclose = null;
    websocket.onerror = null;
    websocket.onmessage = null;
    websocket.onopen = null;

    if (
      websocket.readyState === WebSocket.OPEN ||
      websocket.readyState === WebSocket.CONNECTING
    ) {
      websocket.close(1000, "Client closing connection");
    }
  };

  /*
   * Schedule a reconnect.
   */
  const scheduleReconnect = (connectionId: number) => {
    if (!shouldReconnectRef.current) {
      return;
    }

    /*
     * If this connection is no longer the current
     * connection, don't reconnect.
     */
    if (connectionId !== connectionIdRef.current) {
      return;
    }

    clearReconnectTimer();

    console.log(
      "Reconnecting in 3 seconds..."
    );

    reconnectTimerRef.current =
      window.setTimeout(() => {
        reconnectTimerRef.current = null;

        /*
         * Check again before reconnecting.
         */
        if (
          shouldReconnectRef.current &&
          connectionId === connectionIdRef.current
        ) {
          connectWebSocket();
        }
      }, 3000);
  };

  /*
   * Connect to WebSocket.
   */
  const connectWebSocket = () => {
    if (!apiKey) {
      return;
    }

    if (!shouldReconnectRef.current) {
      return;
    }

    /*
     * Invalidate the previous connection.
     */
    connectionIdRef.current += 1;

    const connectionId =
      connectionIdRef.current;

    console.log(
      "Opening WebSocket connection..."
    );

    /*
     * Make sure only one WebSocket exists.
     */
    closeCurrentWebSocket();

    clearReconnectTimer();

    setConnecting(true);

    const websocket = new WebSocket(
      `ws://127.0.0.1:8000/ws?api_key=${encodeURIComponent(
        apiKey
      )}`
    );

    websocketRef.current = websocket;

    websocket.onopen = () => {
      /*
       * Ignore stale connections.
       */
      if (
        connectionId !== connectionIdRef.current
      ) {
        websocket.close();
        return;
      }

      console.log("WebSocket connected");

      setConnected(true);
      setConnecting(false);
    };

    websocket.onmessage = (event) => {
      /*
       * Ignore messages from stale connections.
       */
      if (
        connectionId !== connectionIdRef.current
      ) {
        return;
      }

      console.log(
        "WebSocket message:",
        event.data
      );

      try {
        const data: WebSocketEvent =
          JSON.parse(event.data);

        /*
         * Ignore non-event messages.
         */
        if (data.type !== "event") {
          return;
        }

        /*
         * The backend already calculated the aggregate.
         *
         * Do NOT increment it manually.
         */
        setEventTypes((previous) => {
          const exists = previous.some(
            (event) =>
              event.event_name ===
              data.event_name
          );

          if (!exists) {
            return [
              ...previous,
              {
                event_name: data.event_name,
                count: data.count,
              },
            ];
          }

          return previous.map((event) =>
            event.event_name === data.event_name
              ? {
                  ...event,
                  count: data.count,
                }
              : event
          );
        });

        /*
         * Update the selected event count.
         */
        setLatestCount((current) => {
          /*
           * Only replace the count if this is
           * the currently selected event.
           */
          if (
            data.event_name === selectedEvent
          ) {
            return data.count;
          }

          return current;
        });

        /*
         * Add the event to the recent events list.
         */
        const newEvent: EventItem = {
          id: data.event_id,
          event_name: data.event_name,
          properties: data.properties,
          occurred_at: data.occurred_at,
          received_at: data.received_at,
        };

        setEvents((previous) => {
          /*
           * Avoid duplicate events.
           */
          const filtered = previous.filter(
            (event) =>
              event.id !== newEvent.id
          );

          return [
            newEvent,
            ...filtered,
          ].slice(0, 10);
        });

        /*
         * Synchronize the total with the backend.
         *
         * We fetch the authoritative total rather
         * than doing previous + 1.
         */
        fetchAnalytics();
      } catch (error) {
        console.error(
          "Invalid WebSocket message:",
          error
        );
      }
    };

    websocket.onclose = (event) => {
      /*
       * Ignore stale WebSocket close events.
       */
      if (
        connectionId !== connectionIdRef.current
      ) {
        return;
      }

      console.log(
        `WebSocket disconnected. Code: ${event.code}`
      );

      setConnected(false);
      setConnecting(false);

      /*
       * Only reconnect if the application still
       * wants an active connection.
       */
      if (shouldReconnectRef.current) {
        scheduleReconnect(connectionId);
      }
    };

    websocket.onerror = (error) => {
      if (
        connectionId !== connectionIdRef.current
      ) {
        return;
      }

      console.error(
        "WebSocket error:",
        error
      );
    };
  };

  /*
   * Connect button.
   */
  const handleConnect = async () => {
    if (!apiKey) {
      return;
    }

    /*
     * Enable WebSocket lifecycle.
     */
    shouldReconnectRef.current = true;

    /*
     * Invalidate any previous connection.
     */
    connectionIdRef.current += 1;

    clearReconnectTimer();
    closeCurrentWebSocket();

    setConnected(false);
    setConnecting(true);

    /*
     * Load the current database state first.
     */
    await Promise.all([
      fetchAnalytics(),
      fetchEvents(),
    ]);

    /*
     * Open exactly one WebSocket.
     */
    connectWebSocket();
  };

  /*
   * Cleanup.
   */
  useEffect(() => {
    return () => {
      console.log(
        "Cleaning up WebSocket"
      );

      /*
       * Stop all future reconnects.
       */
      shouldReconnectRef.current = false;

      /*
       * Invalidate all existing connections.
       */
      connectionIdRef.current += 1;

      clearReconnectTimer();

      closeCurrentWebSocket();
    };
  }, []);

  const chartData = eventTypes.map(
    (event) => ({
      name: event.event_name,
      count: event.count,
    })
  );

  return (
    <div className="app">
      <div className="dashboard">

        <header className="header">
          <div>
            <h1>SaaS Event Monitor</h1>

            <p>
              Monitor your tenant event stream
              in real time
            </p>
          </div>

          <div className="connection-status">
            <span
              className={`status-dot ${
                connected
                  ? "connected"
                  : "disconnected"
              }`}
            />

            <span>
              {connected
                ? "WebSocket connected"
                : connecting
                ? "Connecting..."
                : "Disconnected"}
            </span>
          </div>
        </header>

        <section className="connection-card">
          <label htmlFor="api-key">
            API Key
          </label>

          <div className="api-input-row">
            <input
              id="api-key"
              type="password"
              placeholder="Enter your API key"
              value={apiKey}
              onChange={(event) =>
                setApiKey(
                  event.target.value
                )
              }
            />

            <button
              onClick={handleConnect}
              disabled={
                !apiKey || connecting
              }
            >
              {connecting
                ? "Connecting..."
                : "Connect"}
            </button>
          </div>
        </section>

        <section className="stats-grid">

          <div className="stat-card">
            <span>
              Total Events (24h)
            </span>

            <strong>
              {totalEvents}
            </strong>
          </div>

          <div className="stat-card">
            <span>
              Event Types
            </span>

            <strong>
              {eventTypes.length}
            </strong>
          </div>

          <div className="stat-card">
            <span>
              Latest Event Count
            </span>

            <strong>
              {latestCount}
            </strong>
          </div>

        </section>

        <section className="card">

          <div className="section-header">
            <div>
              <h2>
                Events by Type
              </h2>

              <p>
                Event distribution over the
                last 24 hours
              </p>
            </div>
          </div>

          {chartData.length > 0 ? (
            <div className="chart-container">
              <ResponsiveContainer
                width="100%"
                height={280}
              >
                <BarChart
                  data={chartData}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="name"
                  />

                  <YAxis
                    allowDecimals={false}
                  />

                  <Tooltip />

                  <Bar
                    dataKey="count"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="empty-state">
              No events found.
            </p>
          )}

          <div className="event-type-list">
            {eventTypes.map(
              (event) => (
                <button
                  key={
                    event.event_name
                  }
                  className={`event-type ${
                    selectedEvent ===
                    event.event_name
                      ? "selected"
                      : ""
                  }`}
                  onClick={() => {
                    setSelectedEvent(
                      event.event_name
                    );

                    setLatestCount(
                      event.count
                    );
                  }}
                >
                  <span>
                    {event.event_name}
                  </span>

                  <strong>
                    {event.count}
                  </strong>
                </button>
              )
            )}
          </div>

        </section>

        <section className="card">

          <div className="section-header">
            <div>
              <h2>
                Recent Events
              </h2>

              <p>
                Latest events received by
                your tenant
              </p>
            </div>

            <span className="event-count">
              {events.length} events
            </span>
          </div>

          {events.length === 0 ? (
            <p className="empty-state">
              No events found.
            </p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Properties</th>
                    <th>Occurred At</th>
                    <th>Received At</th>
                  </tr>
                </thead>

                <tbody>
                  {events.map(
                    (event) => (
                      <tr
                        key={event.id}
                      >
                        <td>
                          <strong>
                            {
                              event.event_name
                            }
                          </strong>
                        </td>

                        <td>
                          <code>
                            {JSON.stringify(
                              event.properties
                            )}
                          </code>
                        </td>

                        <td>
                          {new Date(
                            event.occurred_at
                          ).toLocaleString()}
                        </td>

                        <td>
                          {new Date(
                            event.received_at
                          ).toLocaleString()}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}

        </section>

      </div>
    </div>
  );
}

export default App;