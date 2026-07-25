# Trippin'

> Multi-agent travel planning backend that turns a trip request into a persisted Markdown travel report.

![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.138.0-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.6-1C3C3C)
![LangChain](https://img.shields.io/badge/LangChain-1.3.11-1C3C3C)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-asyncpg-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-cache%20%2B%20rate%20limits-DC382D?logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/tests-unit%20suite-blue)
![Last Updated](https://img.shields.io/badge/last%20updated-2026--07--26-informational)

Trippin' accepts a natural-language request such as:

```text
Plan a trip from Miami to New York for a concert at Prudential Center on yyyy-mm-dd.
```

It extracts structured trip fields, creates a trip record, runs a LangGraph workflow of specialist agents for flights, hotels, weather, destination research, local discovery, and itinerary generation, then returns a formatted Markdown report through a REST API or Server-Sent Events stream.

This repository contains the backend/API system. No frontend application, Dockerfile, or production deployment manifests are currently present in the codebase.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [System Flow](#system-flow)
- [API Surfaces](#api-surfaces)
- [Backend Architecture](#backend-architecture)
- [AI Agent Workflow](#ai-agent-workflow)
- [Streaming](#streaming)
- [Authentication](#authentication)
- [Database](#database)
- [Redis](#redis)
- [LangGraph](#langgraph)
- [Technology Stack](#technology-stack)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Error Handling](#error-handling)
- [Performance Optimizations](#performance-optimizations)
- [Security](#security)
- [Deployment Notes](#deployment-notes)
- [Development Workflow](#development-workflow)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Acknowledgements](#acknowledgements)
- [License](#license)
- [Contact](#contact)

## Overview

Trip planning requires stitching together several slow, independent data sources: flights, hotels, weather, venue context, restaurants, transit, and local recommendations. Trippin' models that work as a stateful multi-agent workflow instead of a single monolithic prompt.

The system is for API consumers, hackathon demos, engineers, and contributors who want a backend that can:

| Area | What Trippin' does |
|---|---|
| Problem | Reduces manual research across travel services into one trip-planning workflow. |
| Solution | Uses a FastAPI API and LangGraph state machine to coordinate specialist agents. |
| Output | Returns Markdown report text, itinerary text, trip metadata, and persisted history. |
| Users | Authenticated users with per-user trip history and protected trip access. |
| Persistence | Stores users/trips in PostgreSQL and workflow checkpoints in SQLite. |

## Features

| Category | Implemented capability |
|---|---|
| Request intake | Accepts either structured fields or a natural-language `sentence`. |
| Natural-language parsing | Groq-backed parser extracts `origin`, `destination`, `travelers`, `venue`, and `event_date`. |
| Authentication | Email/password registration, login, JWT access tokens, refresh tokens, `/auth/me`, and logout. |
| Trip planning | Creates a trip record, executes the graph, updates final status and report fields. |
| Multi-agent execution | Coordinator, supervisor, flight, hotel, weather, search, local, and itinerary nodes. |
| Live execution | `/trips/plan/stream` emits Server-Sent Events for agent progress and final result. |
| History | Authenticated users can list prior trips and fetch trip details. |
| Reports | Deterministic report formatter assembles final Markdown from state. |
| Resume | Thread checkpoints can be inspected and incomplete workflows can be resumed. |
| Caching | Redis-backed cache for flight, hotel, weather, search, and itinerary outputs. |
| Rate limiting | Redis-backed login, registration, trip-failure, and daily trip-quota limits. |
| Validation | Pydantic schemas plus parser/state validation before expensive graph execution. |

## Architecture

```mermaid
flowchart TD
    Client[HTTP client or CLI] --> API[FastAPI app]
    API --> Auth[JWT auth dependency]
    API --> RateLimit[Redis rate limiter]
    API --> Parser[Request parser agent]
    Parser --> StateBuilder[TripPlannerState builder]
    StateBuilder --> TripDB[(PostgreSQL users/trips)]
    StateBuilder --> Graph[LangGraph StateGraph]
    Graph --> Coordinator[Coordinator]
    Coordinator --> Supervisor[Supervisor]
    Supervisor --> Flight[Flight agent]
    Supervisor --> Hotel[Hotel agent]
    Supervisor --> Weather[Weather agent]
    Supervisor --> Search[Search agent]
    Supervisor --> Local[Local agent]
    Flight --> Itinerary[Itinerary agent]
    Hotel --> Itinerary
    Weather --> Itinerary
    Search --> Itinerary
    Local --> Itinerary
    Itinerary --> Formatter[Report formatter]
    Formatter --> TripDB
    Graph --> Checkpoints[(SQLite checkpoints)]
    Flight --> Redis[(Redis cache)]
    Hotel --> Redis
    Weather --> Redis
    Search --> Redis
    Itinerary --> Redis
```

## System Flow

```mermaid
sequenceDiagram
    participant U as User/API Client
    participant A as FastAPI
    participant R as Redis
    participant P as Parser
    participant D as PostgreSQL
    participant G as LangGraph
    participant C as SQLite Checkpoints

    U->>A: POST /trips/plan
    A->>A: Validate TripPlanRequest
    A->>A: Verify Bearer JWT
    A->>R: Check failure lock + daily quota
    alt sentence request
        A->>P: Extract structured trip fields
    end
    A->>D: Create trip status=in_progress
    A->>G: Invoke graph with thread_id
    G->>C: Save checkpoints after graph steps
    G->>G: Run specialist agents
    G-->>A: Final state
    A->>D: Update trip status=completed/failed
    A->>R: Record success or failure
    A-->>U: Report, itinerary, trip_id, thread_id
```

## API Surfaces

The FastAPI app is created in `backend/api/app.py`, includes Swagger docs at `/docs`, and registers `/auth` plus `/trips` routes.

### Authentication

| Method | Path | Auth | Purpose |
|---|---|---:|---|
| `POST` | `/auth/register` | No | Create a user with email, password, and optional full name. |
| `POST` | `/auth/login` | No | Issue access and refresh tokens. |
| `POST` | `/auth/refresh` | No | Issue a new access token from a valid refresh token. |
| `GET` | `/auth/me` | Yes | Return the current user profile. |
| `POST` | `/auth/logout` | Yes | Revoke the supplied refresh token if it belongs to the user. |

### Trips

| Method | Path | Auth | Purpose |
|---|---|---:|---|
| `GET` | `/trips/health` | No | Static API health response. |
| `POST` | `/trips/plan` | Yes | Run trip planning and return the final response. |
| `POST` | `/trips/plan/stream` | Yes | Run trip planning with SSE progress events. |
| `GET` | `/trips/history?limit=20&offset=0` | Yes | List authenticated user's trips. |
| `GET` | `/trips/{identifier}` | Yes | Return trip detail for a UUID, or checkpoint state for a thread id. |
| `POST` | `/trips/{thread_id}/resume` | Yes | Resume an incomplete checkpointed workflow. |

## Backend Architecture

| Layer | Files | Responsibility |
|---|---|---|
| API | `backend/api/app.py`, `backend/api/routes/` | FastAPI app factory, middleware, exception handlers, auth and trip endpoints. |
| Schemas | `backend/api/schemas/` | Pydantic request and response contracts. |
| Services | `services/` | Trip planning, checkpoint resume, conversation helpers, rate limiting. |
| Graph | `graph/trip_graph.py` | LangGraph topology and supervisor fan-out routing. |
| Agents | `agents/` | LLM/tool-backed domain workers and deterministic report formatting. |
| Tools | `tools/` | Kiwi MCP, Agentorist MCP, LiveDataLink MCP, and Tavily wrappers. |
| Auth | `auth/` | Password hashing, JWT creation/verification, user dependency. |
| Database | `database/`, `alembic/` | SQLAlchemy models, CRUD, async sessions, migrations. |
| Cache | `cache/` | Redis client, key builder, JSON cache abstraction, metrics counters. |
| State | `state/trip_state.py` | Shared LangGraph state schema and reducers. |

## AI Agent Workflow

```mermaid
graph LR
    START --> coordinator_agent
    coordinator_agent --> supervisor_agent
    supervisor_agent -->|Send if enabled| flight_agent
    supervisor_agent -->|Send if enabled| hotel_agent
    supervisor_agent -->|Send if enabled| weather_agent
    supervisor_agent -->|Send if enabled| search_agent
    supervisor_agent -->|Send if enabled| local_agent
    supervisor_agent -->|No enabled agents| itinerary_agent
    flight_agent --> itinerary_agent
    hotel_agent --> itinerary_agent
    weather_agent --> itinerary_agent
    search_agent --> itinerary_agent
    local_agent --> itinerary_agent
    itinerary_agent --> END
```

| Agent | Implementation | Responsibility |
|---|---|---|
| Request parser | `agents/request_parser_agent.py` | Converts free text into structured JSON fields. |
| Coordinator | `agents/coordinator.py` | Validates required state and initializes defaults. |
| Supervisor | `agents/supervisor_agent.py` | Builds `execution_plan` booleans and writes supervisor notes. |
| Flight | `agents/flight_agent.py` | Calls Kiwi MCP `search-flight`, normalizes flights, selects/summarizes options. |
| Hotel | `agents/hotel_agent.py` | Calls Agentorist MCP search for hotels and preserves ratings, addresses, price categories, and links. |
| Weather | `agents/weather_agent.py` | Calls LiveDataLink forecast/current/AQI tools and summarizes travel weather. |
| Search | `agents/search_agent.py` | Calls Tavily once for attractions, restaurants, transportation, and local tips. |
| Local | `agents/local_agent.py` | Calls Agentorist local discovery for nearby places. |
| Itinerary | `agents/itinerary_agent.py` | Synthesizes available notes into an itinerary and invokes report formatting. |
| Report formatter | `agents/report_formatter_agent.py` | Deterministically formats the final Markdown travel report. |
| Conversation helper | `agents/conversation_agent.py` | Detects missing fields and returns the next question for multi-turn flows. |

## Streaming

`POST /trips/plan/stream` returns `text/event-stream`.

The route emits:

| Event | Meaning |
|---|---|
| `progress` | Request received, node started, node completed, cache hit, or node failed. |
| `error` | Top-level graph failure. |
| `done` | Final report payload with `success`, `report`, `itinerary`, `trip_id`, and `thread_id`. |

The implementation reads LangGraph `astream_events(..., version="v2")` and maps graph node events to user-facing progress messages.

## Authentication

Authentication is JWT-based:

1. `POST /auth/register` hashes the password with bcrypt and creates a `User`.
2. `POST /auth/login` verifies credentials and returns an access token plus refresh token.
3. Protected endpoints use `get_current_active_user()` to decode the Bearer token and load the user from PostgreSQL.
4. `POST /auth/refresh` validates a hashed refresh token stored in PostgreSQL and returns a new access token.
5. `POST /auth/logout` revokes the submitted refresh token.

Access tokens default to 30 minutes. Refresh tokens default to 7 days.

## Database

Application data is stored in PostgreSQL through SQLAlchemy async sessions.

| Table | Model | Purpose |
|---|---|---|
| `users` | `User` | Account identity, password hash, active status, optional OAuth fields. |
| `refresh_tokens` | `RefreshToken` | Hashed refresh tokens, expiry, revocation, optional device/IP fields. |
| `trips` | `Trip` | Request text, origin, destination, venue, status, final report, agent details, errors, thread id, timestamps. |

Alembic migrations exist in `alembic/versions/`, while app startup also calls `create_tables()` via SQLAlchemy metadata.

## Redis

Redis is used for both caching and rate limiting. Redis operations are designed to fail open: if the Redis client is unavailable, cache and limiter helpers return without blocking the primary request.

| Namespace | TTL / Window | Purpose |
|---|---:|---|
| `tripplanner:flight:*` | 10 min | Flight search summaries. |
| `tripplanner:hotel:*` | 20 min | Hotel recommendations. |
| `tripplanner:weather:*` | 60 min | Weather summaries. |
| `tripplanner:search:*` | 12 hr | Destination research summaries. |
| `tripplanner:itinerary:*` | 10 min | Final itinerary/report state. |
| `tripplanner:login:*` | 25 hr | Failed login counters and locks. |
| `tripplanner:register:*` | 24 hr | Registration attempt counters and locks. |
| `tripplanner:trip_failure:*` | 20 min | Trip failure counters and locks. |
| `tripplanner:trip_success:*` | 24 hr | Daily successful trip quota. |

## LangGraph

`graph/trip_graph.py` compiles a `StateGraph[TripPlannerState]` with SQLite checkpointing from `memory.sqlite_checkpoint.get_checkpointer()`.

Key implementation details:

| Detail | Implementation |
|---|---|
| Checkpoint identity | API thread IDs are generated as `{user_id}-{uuid4.hex}`. |
| Parallel routing | `_route_from_supervisor()` returns `Send()` objects for enabled agent nodes. |
| Fan-in | Flight, hotel, weather, search, and local agents all point to `itinerary_agent`. |
| State updates | Node wrappers return only changed keys to avoid LangGraph parallel update conflicts. |
| Error reducer | `errors` uses `Annotated[list[str], operator.add]` so parallel branches accumulate errors. |

## Technology Stack

| Technology | Version / Source | Used for |
|---|---:|---|
| Python | 3.13+ | Runtime. |
| FastAPI | 0.138.0 | REST API and OpenAPI docs. |
| Uvicorn | 0.49.0 | ASGI server. |
| LangGraph | 1.2.6 | Stateful workflow orchestration. |
| LangChain | 1.3.11 | Agent construction. |
| LangChain Groq / Groq | 1.1.3 / 0.37.1 | LLM calls. |
| Tavily Python | 0.7.26 | Destination web search. |
| MCP | 1.28.0 | External tool protocol clients. |
| SQLAlchemy | 2.0.51 | Async ORM. |
| asyncpg | 0.31.0 | PostgreSQL driver. |
| Alembic | 1.18.5 | Database migrations. |
| aiosqlite | 0.22.1 | SQLite checkpoint persistence. |
| Redis | `redis` package in environment | Cache and rate limit backend. |
| Pydantic | 2.13.4 | Validation and API schemas. |
| pydantic-settings | 2.14.2 | Environment config. |
| python-jose | 3.5.0 | JWT encode/decode. |
| passlib + bcrypt | 1.7.4 / 4.2.1 | Password hashing. |

## Folder Structure

```text
trip_planner/
├── agents/                  # Request parser, graph agents, report formatter
├── alembic/                 # Database migration environment and versions
├── auth/                    # JWT, password hashing, auth dependencies
├── backend/api/             # FastAPI app, routes, schemas, logging
├── cache/                   # Redis client, cache service, keys, metrics
├── config/                  # Environment settings and Groq model factory
├── database/                # SQLAlchemy engine, models, CRUD helpers
├── docs/                    # Additional repository docs and audits
├── graph/                   # LangGraph StateGraph definition
├── memory/                  # SQLite checkpoint helper/database location
├── recordings/              # Runtime directory referenced by settings
├── services/                # Trip, conversation, and rate-limit services
├── state/                   # TripPlannerState TypedDict
├── tests/                   # Unit tests
├── tools/                   # MCP and Tavily integration wrappers
├── utils/                   # State builder, error categories, logging helpers
├── ARCHITECTURE.md          # Architecture notes
├── BACKEND_STRUCTURE.md     # Detailed backend analysis
├── alembic.ini              # Alembic config
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL with a database available for the app
- Redis if caching/rate limiting should be enabled
- Groq API key
- Tavily API key
- Network access to the configured MCP servers

### Clone and install

```bash
git clone <repository-url>
cd trip_planner
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Copy `.env.example` to `.env` and set real values:

```env
GROQ_API_KEY=...
TAVILY_API_KEY=...
SECRET_KEY=...
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trippin_db
REDIS_HOST=localhost
REDIS_PORT=6379
```

Generate a local secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Database

The repository includes Alembic migrations:

```bash
alembic upgrade head
```

The FastAPI startup hook also calls `create_tables()`, which creates missing SQLAlchemy tables from metadata.

### Run locally

```bash
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/trips/health`

### CLI

```bash
python main.py --request "Plan a trip from MIA to EWR on 2026-07-15 for a concert at Prudential Center"
```

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `GROQ_API_KEY` | Yes | empty | Required by `get_text_llm()`. |
| `TAVILY_API_KEY` | Yes for search | empty | Used by Tavily destination search. |
| `LANGCHAIN_API_KEY` | No | empty | Optional LangSmith tracing key. |
| `LANGCHAIN_PROJECT` | No | `TripPlanner` | LangSmith project name. |
| `LANGCHAIN_TRACING` | No | `true` | Sets `LANGCHAIN_TRACING_V2`. |
| `LANGCHAIN_ENDPOINT` | No | `https://api.smith.langchain.com` | LangSmith endpoint. |
| `GROQ_TEXT_MODEL` | No | `openai/gpt-oss-20b` | Chat model name. |
| `GROQ_TRANSCRIPTION_MODEL` | No | `whisper-large-v3` | Defined in settings; no active route uses transcription. |
| `KIWI_MCP_SERVER_URL` | No | `https://mcp.kiwi.com` | Flight MCP server. |
| `WEATHER_PROVIDER` | No | `livedatalink` | Weather provider label. |
| `WEATHER_MCP_SERVER_URL` | No | `https://livedatalink.ai/mcp` | Weather MCP server. |
| `AGENTORIST_MCP_SERVER_URL` | No | `https://mcp.agentorist.com/mcp` | Hotel/local MCP server. |
| `RECORDINGS_DIR` | No | `recordings` | Runtime directory setting. |
| `OUTPUTS_DIR` | No | `outputs` | Runtime directory setting. |
| `LOGS_DIR` | No | `logs` | Runtime directory setting. |
| `DATABASE_URL` | Yes | PostgreSQL local placeholder in code | SQLAlchemy async database URL. |
| `SECRET_KEY` | Yes | empty | JWT signing key; app raises if missing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime. |
| `GOOGLE_CLIENT_ID` | No | empty | Present in `.env.example`; no active OAuth routes. |
| `GOOGLE_CLIENT_SECRET` | No | empty | Present in `.env.example`; no active OAuth routes. |
| `GITHUB_CLIENT_ID` | No | empty | Present in `.env.example`; no active OAuth routes. |
| `GITHUB_CLIENT_SECRET` | No | empty | Present in `.env.example`; no active OAuth routes. |
| `REDIS_HOST` | No | `localhost` | Redis host. |
| `REDIS_PORT` | No | `6379` | Redis port. |
| `REDIS_DB` | No | `0` | Redis DB index. |
| `REDIS_PASSWORD` | No | empty | Redis password. |
| `REDIS_DEFAULT_TTL` | No | `1800` | Default cache TTL. |
| `REDIS_ENABLED` | No | `true` | Enables Redis client creation. |
| `RATE_LIMIT_ENABLED` | No | `true` | Enables Redis-backed rate limits. |
| `LOGIN_MAX_ATTEMPTS` | No | `5` | Failed login attempts before lock. |
| `LOGIN_LOCK_HOURS` | No | `25` | Login lock duration. |
| `REGISTER_MAX_ATTEMPTS` | No | `5` | Registration attempts before lock. |
| `REGISTER_LOCK_HOURS` | No | `24` | Registration lock duration. |
| `TRIP_FAILURE_MAX_ATTEMPTS` | No | `3` | Failed trips before lock. |
| `TRIP_FAILURE_LOCK_MINUTES` | No | `20` | Trip failure lock duration. |
| `TRIP_SUCCESS_DAILY_LIMIT` | No | `2` | Daily successful trip quota. |
| `TRIP_SUCCESS_WINDOW_HOURS` | No | `24` | Quota window. |

## Usage

1. Start PostgreSQL and Redis.
2. Start the API with Uvicorn.
3. Register a user.
4. Login and store the returned access token.
5. Call `/trips/plan` or `/trips/plan/stream`.
6. Fetch `/trips/history` or `/trips/{trip_id}` to review persisted runs.

Example structured request:

```bash
curl -X POST http://127.0.0.1:8000/trips/plan \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d "{\"origin\":\"MIA\",\"destination\":\"EWR\",\"event_date\":\"2026-07-15\",\"venue\":\"Prudential Center\"}"
```

Example natural-language request:

```bash
curl -X POST http://127.0.0.1:8000/trips/plan \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d "{\"sentence\":\"Plan a trip from MIA to EWR on 2026-07-15 for a concert at Prudential Center\"}"
```

## Error Handling

| Layer | Behavior |
|---|---|
| Pydantic | Returns `422` validation errors for invalid request shape. |
| Missing parsed fields | Returns `400` with a message asking for required fields. |
| Auth | Returns `401` for invalid credentials/tokens and `403` for inactive/unauthorized access. |
| Rate limits | Returns `429` when Redis counters indicate lockout or quota exhaustion. |
| Graph failure | Marks trip `failed`, records failure, and returns a classified user-facing message. |
| Agent failure | Appends an error and preserves available state so downstream agents can continue. |
| Tool failure | Tool wrappers return normalized error dictionaries instead of raising where possible. |
| Cache failure | Redis cache helpers log warnings and fail open. |

## Performance Optimizations

- LangGraph `Send()` fan-out allows enabled specialist agents to run concurrently.
- Redis caches expensive agent outputs with domain-specific TTLs.
- Tavily client is cached and blocking Tavily calls run in an executor.
- Graph construction is lazy and cached per process in route/service modules.
- Report formatting is deterministic and does not require an additional LLM call.
- Tool responses are trimmed in several wrappers to reduce state size.

## Security

| Control | Implementation |
|---|---|
| Password storage | bcrypt via `passlib`. |
| Access tokens | HS256 JWT with `type=access` and expiry. |
| Refresh tokens | HS256 JWT with `type=refresh`; SHA-256 hash stored in DB with revocation timestamp. |
| Protected routes | `/trips/*` except `/trips/health` require current active user. |
| Authorization | Trip UUID lookups verify `trip.user_id == current_user.id`. |
| Input validation | Pydantic request schemas and explicit parsed-field validation. |
| CORS | Allows `http://localhost:5173` and `http://localhost:8080` with credentials. |

## Deployment Notes

No Dockerfile, compose file, frontend build, CI workflow, or hosted deployment manifests are currently included. A production deployment should provide:

- ASGI server process for `backend.api.app:app`
- Managed PostgreSQL
- Managed Redis or Redis disabled with `REDIS_ENABLED=false`
- Secure `SECRET_KEY`
- Real API keys for Groq and Tavily
- Network access to configured MCP servers
- CORS origins adjusted in `backend/api/app.py`
- Migration strategy using Alembic instead of relying only on startup `create_tables()`

## Development Workflow

Run tests:

```bash
python -m unittest
```

or:

```bash
python -m pytest tests/
```

Useful checks:

```bash
python -m py_compile backend/api/app.py graph/trip_graph.py services/trip_planner_service.py
git status --short
```

When contributing, keep changes scoped to the relevant layer, update tests for behavior changes, and avoid committing `.env`, generated cache files, local databases, or virtual environments.

## Known Limitations

These are verified from the repository state:

| Limitation | Evidence |
|---|---|
| No frontend pages are present | No `package.json`, React/Vite source, or frontend directory exists in the tracked file list. |
| No Docker/deployment config is present | No Dockerfile, compose file, or deployment manifests are present. |
| Health check is shallow | `/trips/health` always returns `{"status":"healthy"}` and does not check PostgreSQL, Redis, or MCP servers. |
| CORS origins are hardcoded | `backend/api/app.py` allows only localhost origins. |
| OAuth env vars exist but OAuth routes are not wired | `.env.example` includes Google/GitHub vars; active auth routes are register/login/refresh/me/logout. |
| Access tokens are not revoked on logout | Logout revokes refresh tokens; access tokens remain valid until expiry. |
| Refresh tokens are reused on refresh | `/auth/refresh` returns the same refresh token with a new access token. |
| Redis rate-limit increment and expiry are separate operations | `_incr_with_ttl()` calls `incr()` then `expire()` on first creation. |
| SQLite checkpointing may constrain concurrent writes | LangGraph checkpoints are stored through a SQLite checkpointer. |
| `create_tables()` runs on startup | Startup creates metadata tables even though Alembic migrations exist. |
| Several graph singletons exist | `_GRAPH_INSTANCE` appears in route and service modules. |

## Roadmap

Roadmap items are derived from existing architecture and limitations:

- Add production deployment assets once the target runtime is chosen.
- Move CORS origins into environment-driven settings.
- Upgrade `/trips/health` to check PostgreSQL, Redis, and key external providers.
- Rotate refresh tokens on `/auth/refresh`.
- Add access-token revocation or shorter-lived access-token strategy if logout enforcement is required.
- Make Redis rate-limit counter updates atomic.
- Consolidate duplicate graph singleton creation.
- Evaluate PostgreSQL-backed LangGraph checkpointing for higher concurrency.
- Add API integration tests with FastAPI `TestClient` or async HTTP client.
- Add frontend or document the expected API client contract if a UI is added later.

## Acknowledgements

Trippin' is built on FastAPI, LangGraph, LangChain, Groq, Tavily, Model Context Protocol, SQLAlchemy, Alembic, PostgreSQL, Redis, Pydantic, python-jose, passlib, and Uvicorn.

## License

No repository-level license file is currently present. The FastAPI OpenAPI metadata declares MIT, but a `LICENSE` file should be added before treating the project as formally licensed for open-source distribution.

## Contact

- Repository metadata in `backend/api/app.py`: `https://github.com/anomalyco/Travel_Agentic_System`
- Use GitHub Issues and Discussions in the repository for bugs, questions, and contributor coordination.
