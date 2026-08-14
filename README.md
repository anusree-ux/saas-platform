### Multi-tenant Event analytics SaaS platform
The platform accepts events from client applications through a REST API,processes them asynchronously using Celery and RabbitMQ, stores event data and hourly aggregate in a database, and pushes real-time updates to connected dashboards through Redis Pub/Sub and Websockets.

A client sends an event to the API:

Client Application
       |
       | POST /events/
       v
   FastAPI API
       |
       | enqueue task
       v
    RabbitMQ
       |
       | consume
       v
     Celery
       |
       +------> PostgreSQL
       |          |
       |          +--> Raw event
       |          +--> Aggregate
       |
       +------> Redis Pub/Sub
                    |
                    v
                WebSocket
                    |
                    v
              Live Dashboard

This architecture allows the API to return quickly while heavier event processing happens asynchronously.

## Key Features
# Multi-Tenant Architecture
Each tenant has its own API key and tenant identifier.
Events are associated with the authenticated tenant, preventing one tenant's event data from being mixed with another tenant's data.

# Asynchronous Event Processing
Events are accepted by the API and placed onto a message queue instead of being processed completely during the HTTP request.
The API returns:
{
  "id": "event-id",
  "status": "queued"
}
with HTTP status:
202 Accepted
Celery workers then process the queued events asynchronously.

# Idempotency
Clients provide an idempotency_key with each event.
If the same event is submitted multiple times with the same idempotency key, the event is processed only once.

For example:

Request 1:
idempotency_key = payment-123

Request 2:
idempotency_key = payment-123

The second request does not increment the aggregate again.
This protects the system from duplicate requests and retry-related double counting.

# Atomic Aggregation
The platform maintains aggregates for events.
The aggregation logic uses an atomic database update rather than a vulnerable:

read -> modify -> write

pattern.

This prevents concurrent workers from silently overwriting each other's increments.

For example, 20 concurrent events for the same event name should produce:

count = 20

rather than losing increments due to a race condition.

# Rate Limiting
The event ingestion endpoint uses a token-bucket rate limiter.

Requests that exceed the configured rate receive:

429 Too Many Requests

with a response indicating that the client should try again later.
This prevents a single client from overwhelming the API.

# Real-Time Updates
After an event is processed, the backend publishes an update through Redis Pub/Sub.

Connected dashboard clients receive the update through a WebSocket connection.

This allows newly processed events to appear in the dashboard without continuously polling for every individual event.

# Event Analytics
The platform exposes analytics endpoints that retrieve event aggregates over a time window.

Example:
GET /analytics/events?since=24h

## Architecture
                         ┌──────────────────────┐
                         │   Client / Dashboard │
                         └──────────┬───────────┘
                                    │
                         HTTP / WebSocket
                                    │
                                    v
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │                      │
                         │ Authentication       │
                         │ Validation           │
                         │ Rate Limiting        │
                         │ Event Ingestion      │
                         └───────┬───────┬──────┘
                                 │       │
                          enqueue│       │query
                                 │       │
                                 v       v
                         ┌──────────┐  ┌──────────┐
                         │ RabbitMQ │  │PostgreSQL│
                         └────┬─────┘  └──────────┘
                              │
                              │ consume
                              v
                       ┌───────────────┐
                       │    Celery     │
                       │    Worker     │
                       └───────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    v                     v
              ┌───────────┐        ┌──────────────┐
              │ PostgreSQL│        │ Redis Pub/Sub │
              │           │        └──────┬───────┘
              │ Events    │               │
              │ Aggregates│               │
              └───────────┘               v
                                    ┌──────────────┐
                                    │  WebSocket   │
                                    │   Clients    │
                                    └──────────────┘

## API Endpoints

The main API functionality currently includes:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/tenants/` | Create a new tenant |
| `POST` | `/events/` | Submit an event |
| `GET` | `/events/` | Retrieve events |
| `GET` | `/analytics/events?since=24h` | Retrieve event analytics |
| `WebSocket` | `/ws?api_key=<API_KEY>` | Receive real-time tenant updates |
| `GET` | `/docs` | Open the interactive Swagger API documentation |
| `GET` | `/openapi.json` | Retrieve the OpenAPI specification |

### Interactive API Documentation

The API can be explored locally through FastAPI's Swagger UI.

Once the application is running, open:

```text
http://127.0.0.1:8000/docs
