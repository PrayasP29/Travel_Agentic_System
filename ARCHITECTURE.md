# Trippin' — System Architecture

## Overview

Trippin' is an AI-powered multi-agent travel planning system that converts a natural-language trip request into a structured, multi-section Markdown travel report. It coordinates specialized agents for flight search, hotel recommendations, weather analysis, destination research, and itinerary generation through a LangGraph-powered workflow. The system exposes a FastAPI REST API with JWT authentication and persists data to PostgreSQL (users/trips) and SQLite (workflow checkpointing).

## Tech Stack

| Component | Technology | Role |
|---|---|---|
| Workflow engine | **LangGraph** (StateGraph) | Multi-agent orchestration, parallel fan-out, checkpointing |
| Agent framework | **LangChain** (create_agent) | Agent construction (prompt + LLM + optional tools) |
| LLM provider | **Groq** (openai/gpt-oss-20b) | NL parsing, summarization, itinerary generation |
| Flight data | **Kiwi MCP Server** | Search-flight tool via Model Context Protocol |
| Hotel / Local data | **Agentorist MCP Server** | Search tool via MCP |
| Weather data | **LiveDataLink MCP Server** | weather_forecast, weather_current, air_quality |
| Web search | **Tavily API** | Destination research |
| API framework | **FastAPI** | REST endpoints, OpenAPI docs, middleware |
| Auth | **JWT** (access + refresh tokens) + **bcrypt** | User authentication |
| Database (app) | **PostgreSQL** (via SQLAlchemy async) | Users and trips records |
| Database (checkpoint) | **SQLite** (langgraph-checkpoint-sqlite) | LangGraph state snapshots |
| Migrations | **Alembic** | Schema version control |
| Validation | **Pydantic** | Request/response models |
| Testing | **unittest** (unit) + **pytest** (runner) | Mocked tests |

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Entry Points                           │
│   CLI (main.py)    FastAPI REST (backend/api/)           │
│                      :8080                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Service Layer                            │
│   trip_planner_service    conversation_service            │
│   (plan_trip, resume_trip) (multi-turn field collection) │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│             LangGraph Orchestration                      │
│   StateGraph[TripPlannerState] + SqliteSaver             │
│                                                          │
│   START → coordinator → supervisor                       │
│                              │                           │
│                    ┌─────────┼─────────┐                 │
│                    │  Send() │ Send()  │  Send()         │
│                    ▼         ▼         ▼                 │
│              flight    hotel     weather                 │
│              (Kiwi)  (Agentorist) (LiveDataLink)         │
│                    │         │         │                 │
│                    └─────────┼─────────┘                 │
│                              ▼                           │
│                      search (Tavily)                     │
│                              ▼                           │
│                      local (Agentorist)                  │
│                              ▼                           │
│                      itinerary → report_formatter        │
│                              │                           │
│                              ▼                           │
│                             END                          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Agents (8 graph nodes)                  │
│   coordinator │ supervisor │ flight │ hotel │ weather    │
│   search │ local │ itinerary │ report_formatter          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Tools Layer                             │
│   flight_tools (Kiwi MCP) │ hotel_tools (Agentorist)    │
│   weather_mcp_client + weather_tools (LiveDataLink)     │
│   tavily_search (Tavily REST API)                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Persistence (two databases)               │
│   PostgreSQL: users, trips (SQLAlchemy async)            │
│   SQLite: LangGraph state checkpoints (SqliteSaver)     │
└─────────────────────────────────────────────────────────┘
```

## Agent Pipeline

The system uses a **coordinator-supervisor** pattern with 8 LangGraph nodes:

| Node | Function | Purpose |
|---|---|---|
| `coordinator_agent` | `coordinator()` | Validate required fields, initialize defaults |
| `supervisor_agent` | `supervisor_agent()` | Validate, build execution plan, generate LLM notes |
| `flight_agent` | `flight_agent()` | Kiwi MCP flight search + LLM summary |
| `hotel_agent` | `hotel_agent()` | Agentorist hotel search + LLM summary |
| `weather_agent` | `weather_agent()` | LiveDataLink weather + LLM summary |
| `search_agent` | `search_agent()` | Tavily web search + LLM summary |
| `local_agent` | `local_agent()` | Agentorist local discovery + LLM summary |
| `itinerary_agent` | `itinerary_agent()` | Synthesize all notes, generate itinerary + report |

Every agent follows the same pattern: copy incoming state, wrap domain logic in try/except, write results back to state dict, append errors on failure, return updated dict. The LangGraph framework merges returned fields into the global state automatically.

## Parallel Execution

Flight, hotel, and weather agents execute **in parallel** via LangGraph's `Send()` API. The supervisor generates an `execution_plan` dict with boolean flags (`run_flight_agent`, `run_hotel_agent`, `run_weather_agent`). The `_route_from_supervisor()` function returns a list of `Send(node, state)` objects — one per enabled agent. LangGraph executes them concurrently.

After all parallel branches complete, they fan-in to `search_agent` (runs once). Then `local_agent` and `itinerary_agent` execute sequentially. If no parallel agents are enabled, the router skips directly to `search_agent`.

Errors are accumulated in `state["errors"]` as a list of strings. Individual agent failures do not block the workflow — later agents receive whatever data is available.

## Data Flow

```
User / HTTP Client
    │
    ▼
POST /trips/plan  {"sentence": "..."} or {"origin": "...", "destination": "...", ...}
    │
    ▼
JWT Auth → get_current_active_user() → user_id from token
    │
    ▼
Request Parser (if sentence provided): Groq LLM extracts structured fields
    │
    ▼
State Builder: normalize values, build TripPlannerState
    │
    ▼
Create Trip record in PostgreSQL (status=in_progress)
    │
    ▼
LangGraph invocation with thread_id = "{user_id}-{uuid4.hex}"
    │
    ├── coordinator_agent → supervisor_agent
    │       │
    │       ▼  Send() fan-out
    │   flight / hotel / weather (parallel)
    │       │
    │       ▼  fan-in
    │   search → local → itinerary → report_formatter
    │
    ▼
Update Trip record in PostgreSQL (status=completed, final_state=result)
    │
    ▼
Return TripPlanResponse with report, itinerary, trip_id, thread_id
```

## API Layer

The FastAPI application is built via a factory pattern (`create_app()` in `backend/api/app.py`). Routes are organized under two routers:

### Auth Routes (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create account (email, password, name) |
| POST | `/auth/login` | None | Authenticate, receive JWT access + refresh tokens |
| POST | `/auth/refresh` | None | Exchange refresh token for new access token |
| GET | `/auth/me` | Bearer token | Get current user profile |
| POST | `/auth/logout` | Bearer token | Invalidate session |

### Trip Routes (`/trips`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/trips/health` | None | Health check |
| POST | `/trips/plan` | Bearer token | Plan a new trip (saves to PostgreSQL) |
| GET | `/trips/history` | Bearer token | List user's trips (paginated) |
| GET | `/trips/{trip_id}` | Bearer token | Full trip detail with report |
| POST | `/trips/{thread_id}/resume` | Bearer token | Resume incomplete workflow |
| GET | `/trips/{identifier}` | Bearer token | Trip detail (UUID) or thread state (string) |

### Middleware Stack

1. **Logging Middleware** — Assigns `request_id` (uuid4 hex), measures elapsed time, logs method/path/status/duration, sets `X-Request-ID` response header.
2. **CORS Middleware** — Allows localhost origins with credentials.
3. **Exception Handlers** — 422 (validation), variable (HTTPException), 500 (unhandled).

## Database Layer

Two separate persistence systems serve different purposes:

### PostgreSQL (Application Data)

Tables: `users` and `trips` managed via SQLAlchemy async ORM with Alembic migrations.

**users** — `id` (UUID), `email` (unique), `hashed_password`, `full_name`, `is_active`, `oauth_provider`, `oauth_id`, `created_at`, `updated_at`.

**trips** — `id` (UUID), `user_id` (FK → users), `request_text`, `origin`, `destination`, `event_date`, `venue`, `travelers`, `status`, `final_report`, `flight_details` (JSON), `hotel_details` (JSON), `weather_details` (JSON), `errors` (JSON), `thread_id`, `created_at`, `completed_at`.

### SQLite (LangGraph Checkpointing)

Managed by `langgraph.checkpoint.sqlite.SqliteSaver` in `memory/sqlite_checkpoint.py`. After every graph node execution, LangGraph persists the full `TripPlannerState` to `memory/trip_planner.db`. This enables:

- **Resumability** — failed workflows resume from last checkpoint
- **State inspection** — mid-execution state via `get_state()`
- **Multi-turn conversations** — state saved across user interactions

## Authentication

JWT-based authentication using access tokens (30 min expiry) and refresh tokens (7 days). Tokens are signed with `SECRET_KEY` from environment config.

**Flow:**
1. User registers via `POST /auth/register` — password hashed with bcrypt
2. User logs in via `POST /auth/login` — receives `access_token` + `refresh_token`
3. Protected endpoints use `get_current_active_user()` dependency — decodes Bearer token, looks up user in PostgreSQL, returns `User` model
4. Token refresh via `POST /auth/refresh` — validates refresh token, issues new access token

OAuth2 social login scaffold (Google, GitHub) is defined in `auth/oauth.py` but not yet wired to callback endpoints.

## Performance

The parallel fan-out via `Send()` reduces total execution time. Instead of running flight → hotel → weather sequentially (3× latency of slowest MCP call), they execute concurrently. The fan-in after parallel agents uses LangGraph's built-in wait-for-all-branches semantics — `search_agent` runs only after all parallel branches complete.

Key optimizations:
- **Lazy graph construction** — the `StateGraph` is built once per process on first request
- **Shared state merging** — LangGraph merges partial node updates; no redundant serialization
- **Deterministic report formatting** — `report_formatter_agent` uses zero LLM calls

## Future Work

- Weather MCP fix (Streamable HTTP reliability improvements)
- Token blacklisting for logout enforcement
- Social login (wire Google/GitHub OAuth callbacks)
- PostgreSQL for LangGraph checkpointing (replace SQLite `SqliteSaver` with `PostgresSaver`)
- Retry layer with exponential backoff for MCP tools
- Abstract provider interfaces for swappable backends
- Live integration tests against real API endpoints
