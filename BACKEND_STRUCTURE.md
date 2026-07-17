# Backend Structure — Trippin' Travel Planner

> Canonical backend documentation generated from static analysis of the entire codebase.

---

## Table of Contents

1. [Backend Overview](#backend-overview)
2. [Technology Stack](#technology-stack)
3. [Folder Structure](#folder-structure)
4. [Request Lifecycle](#request-lifecycle)
5. [API Endpoints](#api-endpoints)
6. [Authentication System](#authentication-system)
7. [Database Design](#database-design)
8. [Redis Architecture](#redis-architecture)
9. [LangGraph Architecture](#langgraph-architecture)
10. [State Management](#state-management)
11. [Agent Architecture](#agent-architecture)
12. [Tool Architecture](#tool-architecture)
13. [External Integrations](#external-integrations)
14. [System Design Concepts](#system-design-concepts)
15. [Algorithms](#algorithms)
16. [Security](#security)
17. [Error Handling](#error-handling)
18. [Performance](#performance)
19. [Configuration](#configuration)
20. [Logging](#logging)
21. [Testing](#testing)
22. [Known Limitations](#known-limitations)
23. [Recommended Cleanup](#recommended-cleanup)
24. [Dependency Map](#dependency-map)
25. [Backend Summary](#backend-summary)

---

## Backend Overview

### Project Purpose

Trippin' is an AI-powered multi-agent travel planning system. A user provides a natural-language trip request (e.g., "Plan a trip from Miami to New York for a concert at Prudential Center on July 15, 2026"), and the system produces a comprehensive Markdown travel report containing flight options, hotel recommendations, weather forecasts, local attractions, and a day-by-day itinerary.

### Problem Being Solved

Planning a trip requires gathering data from multiple sources — flight search engines, hotel databases, weather services, local attraction databases, and web search. Trippin' automates this by coordinating specialized AI agents, each responsible for one domain, orchestrated through a state-machine workflow.

### High-Level Architecture

```
┌──────────────────────────────────────────────┐
│              Entry Points                     │
│   CLI (main.py)  ·  FastAPI REST (8080)      │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Request Parser + Validation         │
│   NL → JSON extraction (Groq LLM)            │
│   Missing-field detection before graph start  │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│         State Builder + DB Persistence        │
│   Normalize fields → TripPlannerState         │
│   Create Trip record in PostgreSQL            │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│      LangGraph Orchestration (StateGraph)     │
│   coordinator → supervisor → parallel agents  │
│   → search → local → itinerary → END          │
│   SQLite checkpointing after every node       │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              Response                          │
│   Markdown report + itinerary → client        │
│   Trip record updated in PostgreSQL           │
└──────────────────────────────────────────────┘
```

### Backend Responsibilities

- Accept trip requests via REST API or CLI
- Authenticate users via JWT
- Parse natural-language requests into structured fields
- Validate required fields before expensive operations
- Orchestrate 8 specialized AI agents via LangGraph
- Search flights (Kiwi MCP), hotels (Agentorist MCP), weather (LiveDataLink MCP), web (Tavily)
- Generate a formatted Markdown travel report
- Persist user data and trip records to PostgreSQL
- Checkpoint workflow state to SQLite for resumability
- Cache agent results in Redis
- Rate-limit API usage per user

---

## Technology Stack

| Technology | Version | Purpose | Where Used |
|---|---|---|---|
| **Python** | 3.13+ | Runtime | Everywhere |
| **FastAPI** | 0.138.0 | REST API framework | `backend/api/` |
| **LangGraph** | 1.2.6 | Multi-agent workflow orchestration | `graph/trip_graph.py` |
| **LangChain** | 1.3.11 | Agent construction (LLM + tools + prompt) | All agent files |
| **LangChain Groq** | 1.1.3 | Groq LLM integration | `config/models.py` |
| **Groq** | 0.37.1 | LLM provider (text generation, audio transcription) | `config/models.py` |
| **Tavily** | 0.7.26 | Web search API | `tools/tavily_search.py` |
| **MCP** | 1.28.0 | Model Context Protocol client for external tools | `tools/flight_tools.py`, `hotel_tools.py`, `weather_mcp_client.py` |
| **SQLAlchemy** | 2.0.51 | Async ORM for PostgreSQL | `database/` |
| **Alembic** | 1.18.5 | Database migrations | `alembic/` |
| **PostgreSQL** | — | Application data (users, trips) | `database/connection.py` |
| **SQLite** | — | LangGraph state checkpointing | `memory/sqlite_checkpoint.py` |
| **Redis** | — | Caching + rate limiting | `cache/`, `services/rate_limiter.py` |
| **Pydantic** | 2.13.4 | Request/response validation | `backend/api/schemas/` |
| **Pydantic Settings** | 2.14.2 | Environment variable loading | `config/settings.py` |
| **python-jose** | 3.5.0 | JWT token creation/verification | `auth/security.py` |
| **passlib + bcrypt** | 1.7.4 / 4.2.1 | Password hashing | `auth/security.py` |
| **uvicorn** | 0.49.0 | ASGI server | `backend/api/app.py` |
| **aiosqlite** | 0.22.1 | Async SQLite for checkpointing | `memory/sqlite_checkpoint.py` |
| **asyncpg** | 0.31.0 | Async PostgreSQL driver | `database/connection.py` |

---

## Folder Structure

```
trip_planner/
├── main.py                         # CLI entry point (argparse → plan_trip)
├── alembic.ini                     # Alembic config
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (gitignored)
├── .env.example                    # Template for .env
│
├── agents/                         # AI agent implementations
│   ├── __init__.py
│   ├── request_parser_agent.py     # NL → JSON extraction + validation helpers
│   ├── coordinator.py              # Validates required fields, initializes defaults
│   ├── supervisor_agent.py         # Builds execution plan, generates supervisor notes
│   ├── flight_agent.py             # Kiwi MCP flight search + LLM summary
│   ├── hotel_agent.py              # Agentorist hotel search + LLM summary
│   ├── weather_agent.py            # LiveDataLink weather + LLM summary
│   ├── search_agent.py             # Tavily web search + LLM summary
│   ├── local_agent.py              # Agentorist local discovery + LLM summary
│   ├── itinerary_agent.py          # Synthesizes all notes → itinerary + report
│   ├── report_formatter_agent.py   # Deterministic Markdown assembly (no LLM)
│   └── conversation_agent.py       # Multi-turn field collection helpers
│
├── auth/                           # Authentication
│   ├── __init__.py
│   ├── security.py                 # JWT creation, password hashing, token decode
│   ├── dependencies.py             # FastAPI dependency: get_current_active_user
│   └── oauth.py                    # OAuth2 scaffold (Google/GitHub — not wired)
│
├── backend/                        # FastAPI application
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       ├── app.py                  # create_app(), middleware, exception handlers
│       ├── log_config.py           # Structured logging with request ID
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── auth.py             # /auth/* endpoints
│       │   └── trips.py            # /trips/* endpoints (plan, stream, history, resume)
│       └── schemas/
│           ├── __init__.py
│           ├── request.py          # TripPlanRequest Pydantic model
│           ├── response.py         # TripPlanResponse, TripStateResponse, etc.
│           └── auth.py             # UserCreate, UserLogin, Token, etc.
│
├── cache/                          # Redis caching layer
│   ├── __init__.py
│   ├── redis_client.py             # Singleton async Redis client
│   ├── cache_service.py            # get/set/delete/exists/clear abstraction
│   ├── cache_keys.py               # Key generation + TTL constants
│   └── metrics.py                  # In-memory hit/miss/write counters
│
├── config/                         # Configuration
│   ├── __init__.py
│   ├── settings.py                 # pydantic-settings: all env vars
│   └── models.py                   # Groq LLM client, audio transcription
│
├── database/                       # PostgreSQL persistence
│   ├── __init__.py
│   ├── connection.py               # AsyncEngine, session factory, get_db
│   ├── models.py                   # SQLAlchemy ORM: User, Trip, RefreshToken
│   └── crud.py                     # All database operations
│
├── graph/                          # LangGraph definition
│   ├── __init__.py
│   └── trip_graph.py               # StateGraph construction + compilation
│
├── memory/                         # LangGraph checkpointing
│   ├── __init__.py
│   ├── sqlite_checkpoint.py        # AsyncSqliteSaver factory
│   └── trip_planner.db             # SQLite database file
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── trip_planner_service.py     # plan_trip(), resume_trip() — non-API entry
│   └── conversation_service.py     # Multi-turn conversation flow
│
├── state/                          # LangGraph state definition
│   ├── __init__.py
│   └── trip_state.py               # TripPlannerState TypedDict
│
├── tools/                          # External tool wrappers
│   ├── __init__.py
│   ├── flight_tools.py             # Kiwi MCP flight search
│   ├── hotel_tools.py              # Agentorist MCP hotel + local search
│   ├── weather_tools.py            # Weather data aggregation
│   ├── weather_mcp_client.py       # LiveDataLink MCP client (forecast, current, AQI)
│   └── tavily_search.py            # Tavily web search with retry
│
├── utils/                          # Shared utilities
│   ├── __init__.py
│   ├── error_categories.py         # Exception → user-friendly message classifier
│   └── file_utils.py               # Directory creation, file I/O, base64
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_state_builder.py       # Unit tests for build_trip_state
│   ├── test_trip_planner_service.py # Unit tests for plan_trip, resume_trip
│   ├── test_conversation_service.py # Unit tests for multi-turn conversation
│   ├── test_parallel_fanout.py     # Unit tests for graph routing
│   └── test_request_validation.py  # Unit tests for field validation
│
├── alembic/                        # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 17f9f6270f5b_initial_schema.py
│       ├── 2de810388b32_add_refresh_tokens_table.py
│       └── faee491064bb_add_oauth_fields.py
│
├── notebooks/                      # Jupyter notebooks (exploration)
├── recordings/                     # Audio recordings directory
└── logs/                           # Log output directory
```

---

## Request Lifecycle

### POST /trips/plan — Complete Trace

```
1. HTTP Request arrives
   ↓
2. _logging_middleware()
   - Generates request_id (uuid4 hex, 12 chars)
   - Sets request_id_var context variable
   - Starts timer
   [backend/api/app.py:19]
   ↓
3. FastAPI validates body as TripPlanRequest (Pydantic)
   - Checks sentence min_length=1 OR all structured fields present
   - Returns 422 if neither path is valid
   [backend/api/schemas/request.py:44]
   ↓
4. get_current_active_user() dependency
   - Extracts Bearer token from Authorization header
   - decode_token() → JWT verification with SECRET_KEY
   - get_user_by_id() → PostgreSQL lookup
   - Checks is_active
   [auth/dependencies.py:17]
   ↓
5. check_trip_failure_rate_limit(user_id)
   - Redis: checks if trip_failure_lock:{user_id} exists → 429 if locked
   [services/rate_limiter.py:86]
   ↓
6. check_trip_quota(user_id)
   - Redis: checks trip_success:{user_id} count vs daily limit → 429 if exceeded
   [services/rate_limiter.py:115]
   ↓
7. Request Parsing (if sentence provided)
   a. request_parser_agent(sentence)
      - Creates LangChain agent with Groq LLM (no tools)
      - System prompt instructs: extract 5 fields, ignore irrelevant text, return JSON only
      - Calls agent.invoke() → LLM call
      - _extract_json_payload() → extracts JSON from response
      - Normalizes all 5 fields via _normalize_text / _normalize_travelers
      - Returns dict with 5 keys
      [agents/request_parser_agent.py:113]
   b. validate_parsed_fields(parsed)
      - Checks origin, destination, venue, event_date for empty/None/whitespace
      - Returns list of missing field names
      [agents/request_parser_agent.py:94]
   c. If missing fields → return JSONResponse(400, {"success": false, "message": "..."})
      [backend/api/routes/trips.py:160]
   ↓
8. State Builder
   - build_trip_state(parsed)
   - Normalizes all fields, defaults travelers to 1 if None
   - Returns TripPlannerState dict with initial values
   [utils/state_builder.py:42]
   ↓
9. Database — Create Trip Record
   - create_trip(db, user_id, request_text, origin, destination, event_date, venue, travelers, thread_id)
   - Inserts into PostgreSQL with status="in_progress"
   [database/crud.py:33]
   ↓
10. LangGraph Invocation
    - graph.ainvoke(state, config={thread_id})
    - Thread ID = "{user_id}-{uuid4.hex}"
    [backend/api/routes/trips.py:193]
    ↓
11. Graph Execution (see LangGraph Architecture)
    ↓
12. Database — Update Trip Record
    - update_trip_status(db, trip_id, "completed", final_state=result)
    - Sets completed_at, final_report, flight_details, hotel_details, weather_details, errors
    [database/crud.py:47]
    ↓
13. Rate Limiting — Record Success
    - record_trip_success(user_id) → increments trip_success:{user_id}
    - reset_trip_failures(user_id) → clears failure counter
    [services/rate_limiter.py:121]
    ↓
14. Response
    - Returns TripPlanResponse(success=True, report, itinerary, destination, event_date, trip_id, thread_id)
    [backend/api/routes/trips.py:244]
    ↓
15. _logging_middleware() logs elapsed time, sets X-Request-ID header
```

### POST /trips/plan/stream — SSE Variant

Same as above through step 10, then:

```
11. graph.astream_events(state, config, version="v2")
    - Yields SSE events for each agent start/complete/fail
    - Event types: progress, error, done
    - Each event: "event: {type}\ndata: {json}\n\n"
    [backend/api/routes/trips.py:332]
    ↓
12. Final "done" event contains same payload as TripPlanResponse
```

---

## API Endpoints

### Auth Router (`/auth`)

| Method | Path | Auth | Input | Output | Status Codes |
|---|---|---|---|---|---|
| POST | `/auth/register` | None | `UserCreate` (email, password, full_name?) | `UserResponse` (id, email, full_name, created_at) | 201, 409, 422, 429 |
| POST | `/auth/login` | None | `UserLogin` (email, password) | `Token` (access_token, refresh_token, token_type, expires_in) | 200, 401, 422, 429 |
| POST | `/auth/refresh` | None | `TokenRefresh` (refresh_token) | `Token` | 200, 401 |
| GET | `/auth/me` | Bearer | — | `UserResponse` | 200, 401, 403 |
| POST | `/auth/logout` | Bearer | `TokenRefresh` | `{message}` | 200, 401 |

### Trip Router (`/trips`)

| Method | Path | Auth | Input | Output | Status Codes |
|---|---|---|---|---|---|
| GET | `/trips/health` | None | — | `HealthResponse` | 200 |
| POST | `/trips/plan` | Bearer | `TripPlanRequest` | `TripPlanResponse` or `JSONResponse(400)` | 200, 400, 422, 429, 500 |
| POST | `/trips/plan/stream` | Bearer | `TripPlanRequest` | `StreamingResponse` (SSE) | 200, 400, 422, 429 |
| GET | `/trips/history` | Bearer | limit, offset (query) | `list[TripHistoryItem]` | 200 |
| GET | `/trips/{identifier}` | Bearer | UUID or string | `TripDetailResponse` or `TripStateResponse` | 200, 403, 404 |
| POST | `/trips/{thread_id}/resume` | Bearer | thread_id (path) | `TripStateResponse` | 200, 403 |

### Request Schema — TripPlanRequest

```python
class TripPlanRequest(BaseModel):
    origin: str | None       # min_length=3, IATA code
    destination: str | None  # min_length=3, IATA code
    event_date: str | None   # pattern=^\d{4}-\d{2}-\d{2}$
    venue: str | None        # min_length=1
    sentence: str | None     # min_length=1, free-text NL request

    # Validator: either sentence OR all 4 structured fields required
```

### Response Schemas

| Schema | Fields |
|---|---|
| `TripPlanResponse` | success, report, itinerary, destination, event_date, trip_id?, thread_id? |
| `TripStateResponse` | thread_id, status, state (full dict) |
| `TripHistoryItem` | id, request_text, origin, destination, status, created_at, completed_at |
| `TripDetailResponse` | id, user_id, request_text, origin, destination, event_date, venue, travelers, status, final_report, flight_details, hotel_details, weather_details, thread_id, created_at, completed_at |
| `HealthResponse` | status |
| `Token` | access_token, refresh_token, token_type, expires_in |
| `UserResponse` | id, email, full_name, created_at |

---

## Authentication System

### JWT Flow

```
Register:
  POST /auth/register
  → hash_password(password) via bcrypt
  → create_user(db, email, hashed_password, full_name)
  → return UserResponse

Login:
  POST /auth/login
  → get_user_by_email(db, email)
  → verify_password(plain, hashed) via bcrypt
  → create_access_token({"sub": user_id}) → HS256, 30 min expiry
  → create_refresh_token({"sub": user_id}) → HS256, 7 day expiry
  → store_refresh_token(db, user_id, hash(refresh_token), expires_at)
  → return Token(access_token, refresh_token)

Refresh:
  POST /auth/refresh
  → decode_token(refresh_token) → verify JWT signature + type="refresh"
  → get_refresh_token_by_hash(db, hash(refresh_token))
  → Check: not revoked, not expired
  → create_access_token({"sub": user_id})
  → return Token (new access_token, same refresh_token)

Logout:
  POST /auth/logout
  → revoke_refresh_token(db, token_id) → sets revoked_at
```

### Token Details

| Property | Access Token | Refresh Token |
|---|---|---|
| Algorithm | HS256 | HS256 |
| Secret | `SECRET_KEY` from env | `SECRET_KEY` from env |
| Expiry | 30 minutes | 7 days |
| Claims | `sub` (user_id), `exp`, `type="access"` | `sub` (user_id), `exp`, `type="refresh"` |
| Storage | Client-side (Authorization header) | Database (hash stored) |

### Protected Routes

All `/trips/*` routes except `/trips/health` require Bearer authentication via `get_current_active_user()` dependency:

```
HTTPBearer() → extract token → decode_token(token) → payload["sub"] → get_user_by_id(db, UUID(user_id)) → check is_active
```

### Password Storage

- Hashing: `passlib.context.CryptContext(schemes=["bcrypt"])`
- Verification: `CryptContext.verify(plain, hashed)`

---

## Database Design

### ER Diagram

```mermaid
erDiagram
    users ||--o{ trips : "creates"
    users ||--o{ refresh_tokens : "owns"

    users {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        string oauth_provider
        string oauth_id
        datetime created_at
        datetime updated_at
    }

    trips {
        uuid id PK
        uuid user_id FK
        text request_text
        string origin
        string destination
        string event_date
        string venue
        integer travelers
        string status
        text final_report
        jsonb flight_details
        jsonb hotel_details
        jsonb weather_details
        jsonb errors
        string thread_id
        datetime created_at
        datetime completed_at
    }

    refresh_tokens {
        uuid id PK
        uuid user_id FK
        text token_hash
        datetime created_at
        datetime expires_at
        datetime revoked_at
        text device_name
        text ip_address
        datetime last_used_at
    }
```

### Tables

**users** — Application users

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default uuid_generate_v4() |
| email | String | UNIQUE, NOT NULL, indexed |
| hashed_password | String | NOT NULL |
| full_name | String | nullable |
| is_active | Boolean | default True |
| created_at | DateTime(tz) | default NOW() |
| updated_at | DateTime(tz) | on update NOW() |
| oauth_provider | String | nullable |
| oauth_id | String | nullable |

**trips** — Trip planning records

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default uuid_generate_v4() |
| user_id | UUID | FK → users.id, NOT NULL, indexed |
| request_text | Text | — |
| origin | String | — |
| destination | String | — |
| event_date | String | — |
| venue | String | — |
| travelers | Integer | default 1 |
| status | String | default "in_progress" |
| final_report | Text | nullable |
| flight_details | JSON | nullable |
| hotel_details | JSON | nullable |
| weather_details | JSON | nullable |
| errors | JSON | nullable |
| thread_id | String | nullable, indexed |
| created_at | DateTime(tz) | default NOW() |
| completed_at | DateTime(tz) | nullable |

**refresh_tokens** — JWT refresh token storage

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default uuid_generate_v4() |
| user_id | UUID | FK → users.id, NOT NULL, indexed |
| token_hash | Text | NOT NULL |
| created_at | DateTime(tz) | default NOW() |
| expires_at | DateTime(tz) | NOT NULL, indexed |
| revoked_at | DateTime(tz) | nullable, indexed |
| device_name | Text | nullable |
| ip_address | Text | nullable |
| last_used_at | DateTime(tz) | nullable |

### CRUD Operations

All operations are in `database/crud.py`:

| Function | Table | Operation |
|---|---|---|
| `create_user()` | users | INSERT |
| `get_user_by_email()` | users | SELECT WHERE email |
| `get_user_by_id()` | users | SELECT WHERE id |
| `update_user()` | users | UPDATE WHERE id |
| `create_trip()` | trips | INSERT |
| `update_trip_status()` | trips | UPDATE (status, final_state, completed_at) |
| `get_user_trips()` | trips | SELECT WHERE user_id, ORDER BY created_at DESC, LIMIT/OFFSET |
| `get_trip_by_id()` | trips | SELECT WHERE id |
| `get_trip_by_thread_id()` | trips | SELECT WHERE thread_id |
| `create_refresh_token()` | refresh_tokens | INSERT |
| `get_refresh_token_by_hash()` | refresh_tokens | SELECT WHERE token_hash |
| `revoke_refresh_token()` | refresh_tokens | UPDATE SET revoked_at |

---

## Redis Architecture

### Purpose

Redis serves two distinct purposes:
1. **Agent result caching** — avoids re-calling MCP tools for identical requests
2. **Rate limiting** — tracks login attempts, registration attempts, trip failures, and daily quotas

### Client

- Singleton async Redis client (`redis.asyncio.Redis`)
- Connection pool: max 10 connections, 2s connect timeout, 2s socket timeout
- Graceful failure: all operations return `None`/`0`/`False` on Redis unavailability (fail-open)

### Cache Keys

All keys use the prefix `tripplanner:`:

| Key Pattern | Purpose | TTL |
|---|---|---|
| `tripplanner:flight:{origin}:{destination}:{date}:{travelers}` | Flight search results | 600s (10 min) |
| `tripplanner:hotel:{destination}:{date}:{travelers}` | Hotel search results | 1200s (20 min) |
| `tripplanner:weather:{destination}:{date}` | Weather forecast | 3600s (60 min) |
| `tripplanner:search:{destination}:{venue}` | Web search results | 43200s (12 hours) |
| `tripplanner:itinerary:{destination}:{venue}:{date}` | Itinerary + report | 600s (10 min) |

### Rate Limit Keys

| Key Pattern | Purpose | TTL |
|---|---|---|
| `tripplanner:login:{email}` | Login failure counter | 25 hours |
| `tripplanner:login_lock:{email}` | Login lock flag | 25 hours |
| `tripplanner:register:{email}` | Registration failure counter | 24 hours |
| `tripplanner:register_lock:{email}` | Registration lock flag | 24 hours |
| `tripplanner:trip_failure:{user_id}` | Trip failure counter | 20 minutes |
| `tripplanner:trip_failure_lock:{user_id}` | Trip failure lock flag | 20 minutes |
| `tripplanner:trip_success:{user_id}` | Daily trip success counter | 24 hours |

### Cache Lifecycle

```
Agent starts
  → Check cache (GET)
  → If hit: return cached data, skip LLM + MCP
  → If miss: call MCP tool + LLM, then SET cache with TTL
```

### Cache Service API

| Function | Redis Command | Returns |
|---|---|---|
| `get(key)` | GET + JSON parse | value or None |
| `set(key, value, ttl)` | SET with JSON + EX | bool |
| `delete(key)` | DELETE | bool |
| `exists(key)` | EXISTS | bool |
| `expire(key, ttl)` | EXPIRE | bool |
| `ttl(key)` | TTL | int |
| `clear(namespace?)` | SCAN + DELETE | count |

### Cache Metrics

In-memory counters (thread-safe via Lock): hits, misses, writes, deletes, errors. No persistence — reset on restart.

---

## LangGraph Architecture

### Graph Definition

```mermaid
graph TD
    START --> coordinator_agent
    coordinator_agent --> supervisor_agent
    supervisor_agent -->|Send()| flight_agent
    supervisor_agent -->|Send()| hotel_agent
    supervisor_agent -->|Send()| weather_agent
    supervisor_agent -->|Send()| search_agent
    supervisor_agent -->|Send()| local_agent
    flight_agent --> itinerary_agent
    hotel_agent --> itinerary_agent
    weather_agent --> itinerary_agent
    search_agent --> itinerary_agent
    local_agent --> itinerary_agent
    itinerary_agent --> END
```

### Nodes

| Node | File | Function | LLM Call | Tools |
|---|---|---|---|---|
| coordinator_agent | `agents/coordinator.py` | `coordinator_agent()` | No (creates agent but doesn't call it) | None |
| supervisor_agent | `agents/supervisor_agent.py` | `supervisor_agent()` | Yes | None |
| flight_agent | `agents/flight_agent.py` | `flight_agent()` | Yes | None (calls MCP directly) |
| hotel_agent | `agents/hotel_agent.py` | `hotel_agent()` | Yes | None (calls MCP directly) |
| weather_agent | `agents/weather_agent.py` | `weather_agent()` | Yes | None (calls MCP directly) |
| search_agent | `agents/search_agent.py` | `search_agent()` | Yes | `search_web` (Tavily) |
| local_agent | `agents/local_agent.py` | `local_agent()` | Yes | `search_local_places` (Agentorist MCP) |
| itinerary_agent | `agents/itinerary_agent.py` | `itinerary_agent()` | Yes | None |

### Edges

| From | To | Type | Condition |
|---|---|---|---|
| START | coordinator_agent | Fixed | Always |
| coordinator_agent | supervisor_agent | Fixed | Always |
| supervisor_agent | flight/hotel/weather/search/local | Conditional | `execution_plan` flags |
| supervisor_agent | itinerary_agent | Conditional | If no agents enabled |
| flight_agent | itinerary_agent | Fixed | Always (fan-in) |
| hotel_agent | itinerary_agent | Fixed | Always (fan-in) |
| weather_agent | itinerary_agent | Fixed | Always (fan-in) |
| search_agent | itinerary_agent | Fixed | Always (fan-in) |
| local_agent | itinerary_agent | Fixed | Always (fan-in) |
| itinerary_agent | END | Fixed | Always |

### Execution Plan

The supervisor generates an `execution_plan` dict:

```python
{
    "run_flight_agent": True/False,
    "run_hotel_agent": True/False,
    "run_weather_agent": True/False,
    "run_search_agent": True/False,
    "run_local_agent": True/False,
}
```

Based on whether each agent's output already exists in state. The `_route_from_supervisor()` function reads this dict and returns `Send()` objects for enabled agents.

### Parallel Execution

Flight, hotel, weather, search, and local agents execute **concurrently** via LangGraph's `Send()` API. LangGraph manages the fan-out (supervisor → parallel agents) and fan-in (parallel agents → itinerary_agent).

### Checkpointing

- Every node execution is checkpointed to SQLite via `AsyncSqliteSaver`
- Thread ID format: `{user_id}-{uuid4.hex}` for API, `conversation_{uuid4.hex}` for conversations
- Enables resumption of failed workflows via `POST /trips/{thread_id}/resume`

### State Merging

LangGraph merges node return values into the global state. Each agent returns a partial dict (only changed fields). The `errors` field uses `Annotated[list[str], operator.add]` reducer — errors from parallel branches accumulate rather than overwrite.

---

## State Management

### TripPlannerState (TypedDict)

| Field | Type | Producer | Consumer |
|---|---|---|---|
| `origin` | str | request_parser / API input | flight_agent, coordinator, report |
| `destination` | str | request_parser / API input | flight, hotel, weather, search, local agents, report |
| `travelers` | int | request_parser / state_builder (default 1) | flight_agent, hotel_agent |
| `venue` | str | request_parser / API input | search_agent, local_agent, report |
| `event_date` | str | request_parser / API input | flight, hotel, weather agents, report |
| `flight_details` | dict | flight_agent | itinerary_agent |
| `flight_notes` | str | flight_agent | itinerary_agent, report |
| `flight_status` | str | flight_agent | supervisor |
| `hotel_details` | dict | hotel_agent | itinerary_agent |
| `hotel_notes` | str | hotel_agent | itinerary_agent, report |
| `hotel_status` | str | hotel_agent | supervisor |
| `weather_details` | dict | weather_agent | itinerary_agent |
| `weather_notes` | str | weather_agent | itinerary_agent, report |
| `weather_status` | str | weather_agent | supervisor |
| `search_results` | dict | search_agent | itinerary_agent |
| `search_notes` | str | search_agent | itinerary_agent, report |
| `search_status` | str | search_agent | supervisor |
| `itinerary` | str | itinerary_agent | API response |
| `final_report` | str | report_formatter_agent | API response, DB |
| `itinerary_status` | str | itinerary_agent | — |
| `supervisor_notes` | str | supervisor_agent | itinerary_agent |
| `status` | str | coordinator ("processing"), supervisor ("blocked"), itinerary ("completed"/"failed") | API response |
| `errors` | list[str] (reducer: add) | All agents | API response, DB |
| `flight_booking_link` | str | flight_agent | report |
| `hotel_booking_links` | list[str] (reducer: add) | hotel_agent | report |
| `hotel_price_details` | list[str] (reducer: add) | hotel_agent | supervisor |
| `recommended_flight_price` | float | flight_agent | — |
| `recommended_hotel_price` | float | — | — |
| `execution_plan` | dict | supervisor_agent | routing functions |
| `local_results` | dict | local_agent | — |
| `local_notes` | str | local_agent | — |
| `local_status` | str | local_agent | supervisor |

### Initial State (from build_trip_state)

```python
{
    "origin": "",
    "destination": "",
    "travelers": 1,
    "venue": "",
    "event_date": "",
    "errors": [],
    "flight_booking_link": "",
    "hotel_booking_links": [],
    "hotel_price_details": [],
    "recommended_flight_price": 0.0,
    "recommended_hotel_price": 0.0,
}
```

---

## Agent Architecture

### coordinator_agent

| Property | Value |
|---|---|
| File | `agents/coordinator.py` |
| Purpose | Validate required fields, initialize missing state defaults |
| LLM Call | No (creates agent but doesn't invoke it) |
| Tools | None |
| Required Fields | destination, venue, event_date |
| On Failure | Appends error strings to `errors` list |
| Sets | `status = "processing"`, initializes empty dicts for agent outputs |

### supervisor_agent

| Property | Value |
|---|---|
| File | `agents/supervisor_agent.py` |
| Purpose | Re-validate fields, build execution plan, generate supervisor summary |
| LLM Call | Yes (summarizes execution plan) |
| Tools | None |
| Required Fields | destination, venue, event_date |
| On Validation Failure | Sets `status = "blocked"`, still calls LLM before returning |
| Sets | `execution_plan`, `supervisor_notes`, `status` |

### flight_agent

| Property | Value |
|---|---|
| File | `agents/flight_agent.py` |
| Purpose | Search flights via Kiwi MCP, summarize with LLM |
| LLM Call | Yes (recommends best flight) |
| Tools | None (calls `search_flights()` directly) |
| Cache | `CacheKeys.flight(origin, destination, event_date, travelers)` — 10 min TTL |
| Output Fields | `flight_details`, `flight_notes`, `flight_status`, `flight_booking_link`, `recommended_flight_price` |
| On Failure | Sets `flight_status = "failed"`, classifies error |

### hotel_agent

| Property | Value |
|---|---|
| File | `agents/hotel_agent.py` |
| Purpose | Search hotels via Agentorist MCP, summarize with LLM |
| LLM Call | Yes (recommends hotels) |
| Tools | None (calls `search_hotels()` directly) |
| Cache | `CacheKeys.hotel(destination, event_date, travelers)` — 20 min TTL |
| Output Fields | `hotel_details`, `hotel_notes`, `hotel_status`, `hotel_booking_links`, `hotel_price_details` |
| On Failure | Sets `hotel_status = "failed"` |

### weather_agent

| Property | Value |
|---|---|
| File | `agents/weather_agent.py` |
| Purpose | Fetch weather forecast + air quality via LiveDataLink MCP, summarize with LLM |
| LLM Call | Yes (analyzes forecast) |
| Tools | None (calls `get_weather()` directly) |
| Cache | `CacheKeys.weather(destination, event_date)` — 60 min TTL |
| Output Fields | `weather_details`, `weather_notes`, `weather_status` |
| On Failure | Sets `weather_status = "failed"` |

### search_agent

| Property | Value |
|---|---|
| File | `agents/search_agent.py` |
| Purpose | Web search for destination research (attractions, restaurants, transport) |
| LLM Call | Yes (summarizes search results) |
| Tools | `search_web` (Tavily) — LLM decides when to call |
| Cache | `CacheKeys.search(destination, venue)` — 12 hour TTL |
| Output Fields | `search_results`, `search_notes`, `search_status` |
| On Failure | Sets `search_status = "failed"` |
| Special | Has `_SearchTraceHandler` for detailed execution tracing |

### local_agent

| Property | Value |
|---|---|
| File | `agents/local_agent.py` |
| Purpose | Local discovery via Agentorist MCP |
| LLM Call | Yes (decides if needed, summarizes) |
| Tools | `search_local_places` (Agentorist MCP) |
| Cache | None |
| Output Fields | `local_results`, `local_notes`, `local_status` |
| On Failure | Sets `local_status = "failed"` |

### itinerary_agent

| Property | Value |
|---|---|
| File | `agents/itinerary_agent.py` |
| Purpose | Synthesize all agent outputs into day-by-day itinerary + final report |
| LLM Call | Yes (creates itinerary) |
| Tools | None |
| Cache | `CacheKeys.itinerary(destination, venue, event_date)` — 10 min TTL |
| Output Fields | `itinerary`, `itinerary_notes`, `itinerary_status`, `final_report`, `status` |
| On Failure | Uses `_build_fallback_itinerary()` — concatenates raw agent notes |
| Special | Calls `report_formatter_agent()` at the end to assemble final report |

### report_formatter_agent

| Property | Value |
|---|---|
| File | `agents/report_formatter_agent.py` |
| Purpose | Deterministic Markdown report assembly — NO LLM |
| LLM Call | No |
| Tools | None |
| Input | Full state dict |
| Output | `{"final_report": "..."}` |
| Sections | Executive Summary, Trip Overview, Recommended Flight, Other Flights, Recommended Hotels, Additional Hotels, Weather Summary, Weather Details, Local Highlights, Restaurants, Transportation, Day-wise Itinerary, Quick Links, Next Steps |

### conversation_agent

| Property | Value |
|---|---|
| File | `agents/conversation_agent.py` |
| Purpose | Multi-turn field collection helpers (deterministic, no LLM) |
| Required Fields | origin, destination, event_date |
| Functions | `detect_missing_fields()`, `next_question()`, `conversation_status()` |

---

## Tool Architecture

### search_flights (Kiwi MCP)

| Property | Value |
|---|---|
| File | `tools/flight_tools.py` |
| Function | `search_flights(origin, destination, event_date, travelers)` |
| MCP Server | `settings.kiwi_mcp_server_url` |
| Tool Name | `search-flight` |
| Protocol | SSE or Streamable HTTP (auto-detected by URL) |
| Timeout | 20 seconds |
| Input Mapping | `origin→flyFrom`, `destination→flyTo`, `event_date→departureDate` (DD/MM/YYYY), `travelers→adults` |
| Output | `{status, provider, tool_used, data: {structured, content}, available_tools}` |
| Deduplication | Limits content to 5 items |

### search_hotels (Agentorist MCP)

| Property | Value |
|---|---|
| File | `tools/hotel_tools.py` |
| Function | `search_hotels(destination)` |
| MCP Server | `settings.agentorist_mcp_server_url` |
| Tool Name | `search` |
| Protocol | SSE or Streamable HTTP |
| Timeout | 20 seconds |
| Payload | `{vertical: "local", query: "best hotels", location: destination, agent_client: "TripPlanner"}` |
| Output | `{status, provider, data: {results: [...]}}` |
| Deduplication | Limits results to 5 |

### search_local_places (Agentorist MCP)

| Property | Value |
|---|---|
| File | `tools/hotel_tools.py` |
| Function | `search_local_places(destination, venue?)` |
| MCP Server | `settings.agentorist_mcp_server_url` |
| Tool Name | `search` |
| Payload | `{vertical: "local", query: "best places near {venue/destination}", location: destination}` |
| Output | Same as search_hotels |

### Weather Tools (LiveDataLink MCP)

| Function | File | MCP Tool | Timeout |
|---|---|---|---|
| `get_current_weather(location)` | `weather_mcp_client.py` | `weather_current` | 20s |
| `get_weather_forecast(location, days)` | `weather_mcp_client.py` | `weather_forecast` | 20s |
| `get_air_quality(location)` | `weather_mcp_client.py` | `air_quality` | 20s |
| `get_weather(destination, event_date)` | `weather_tools.py` | Aggregates above | — |

Weather logic:
- Calculates forecast days as `min(max((event_date - today).days, 1), 16)`
- Forecast is required — failure fails the whole request
- Air quality is optional — failure doesn't fail the request

### search_web (Tavily)

| Property | Value |
|---|---|
| File | `tools/tavily_search.py` |
| Function | `search_web(query, max_results=5)` |
| API | Tavily REST API |
| Retry | 3 attempts with linear backoff |
| Timeout | 15 seconds per attempt |
| Output | `{query, results: [...]}` |

---

## External Integrations

### Groq (LLM Provider)

- **Model**: `openai/gpt-oss-20b` (configurable via `GROQ_TEXT_MODEL`)
- **Temperature**: 0.2
- **Used by**: All agents that call LLM (request_parser, supervisor, flight, hotel, weather, search, local, itinerary)
- **Integration**: `langchain_groq.ChatGroq` via `config/models.py:get_text_llm()`
- **Also**: Audio transcription via `groq.audio.transcriptions.create()` with `whisper-large-v3`

### Kiwi (Flight Search)

- **MCP Server URL**: `settings.kiwi_mcp_server_url`
- **Tool**: `search-flight`
- **Input**: flyFrom, flyTo, departureDate, adults
- **Output**: Structured itineraries with price, duration, booking links

### Agentorist (Hotels + Local Discovery)

- **MCP Server URL**: `settings.agentorist_mcp_server_url`
- **Tool**: `search`
- **Used for**: Both hotel search and local place discovery
- **Differentiation**: `vertical: "local"` + different query strings

### LiveDataLink (Weather)

- **MCP Server URL**: `settings.weather_mcp_server_url`
- **Tools**: `weather_current`, `weather_forecast`, `air_quality`
- **Protocol**: Streamable HTTP only (not SSE)

### Tavily (Web Search)

- **API Key**: `settings.tavily_api_key`
- **Integration**: `tavily-python` SDK
- **Used by**: `search_agent` for destination research

### PostgreSQL

- **URL**: `settings.DATABASE_URL` (default: `postgresql+asyncpg://trippin_user:trippin_pass_2026@localhost:5432/trippin_db`)
- **Driver**: asyncpg
- **ORM**: SQLAlchemy async
- **Tables**: users, trips, refresh_tokens
- **Migrations**: Alembic

### Redis

- **Host**: `settings.redis_host` (default: localhost, forced to 127.0.0.1)
- **Port**: `settings.redis_port` (default: 6379)
- **DB**: `settings.redis_db` (default: 0)
- **Used for**: Caching + rate limiting
- **Fail-open**: All operations gracefully handle Redis unavailability

### SQLite

- **File**: `memory/trip_planner.db`
- **Purpose**: LangGraph state checkpointing only
- **Driver**: aiosqlite
- **Integration**: `langgraph-checkpoint-sqlite`

---

## System Design Concepts

### Agentic AI

Each agent is an autonomous unit that receives state, performs work (tool calls + LLM reasoning), and returns updated state. Agents decide independently whether to use tools (search_agent, local_agent) or always use tools (flight_agent, hotel_agent call MCP directly).

### Supervisor Pattern

The supervisor_agent acts as a coordinator that:
1. Validates state
2. Decides which agents to run (execution_plan)
3. Provides a summary of the plan
4. Returns early with `status="blocked"` if validation fails

### Orchestration

LangGraph's StateGraph orchestrates the entire workflow. The graph definition in `trip_graph.py` wires nodes and edges. The framework handles state passing, checkpointing, and parallel execution.

### State Machine

The workflow is a directed acyclic graph (DAG):
```
START → coordinator → supervisor → [parallel agents] → itinerary → END
```

Status transitions: `in_progress` → `processing` → `completed` | `failed` | `blocked`

### Workflow Engine

LangGraph serves as the workflow engine, providing:
- Node execution with state passing
- Conditional routing (supervisor → agents)
- Parallel fan-out via `Send()`
- Fan-in (all agents → itinerary)
- Checkpointing after every node

### Repository Pattern

`database/crud.py` encapsulates all database operations. No raw SQL in routes or services.

### Service Layer

- `services/trip_planner_service.py` — non-API entry point for trip planning
- `services/conversation_service.py` — multi-turn conversation flow
- `services/rate_limiter.py` — rate limiting logic

### Caching

Two-tier caching:
1. **Agent-level**: Each agent checks cache before calling MCP tools
2. **Cache service**: Abstracts Redis with metrics tracking

### Rate Limiting

Four rate limiters:
1. Login failure lockout (5 attempts → 25 hour lock)
2. Registration rate limit (5 attempts → 24 hour lock)
3. Trip failure lockout (3 failures → 20 minute lock)
4. Daily trip quota (2 successful trips per 24 hours)

### Streaming

SSE (Server-Sent Events) streaming via `POST /trips/plan/stream`:
- Progress events for each agent start/complete/fail
- Error events on graph failure
- Final "done" event with complete result

### Authentication

JWT-based with access + refresh token pattern. Access tokens for API calls (30 min), refresh tokens for token renewal (7 days, stored in DB).

### Checkpointing

LangGraph checkpoints state to SQLite after every node. Enables:
- Workflow resumption from last successful node
- State inspection mid-execution
- Multi-turn conversation persistence

### Graceful Degradation

- Redis unavailable → caching disabled, rate limiting disabled, requests pass through
- MCP tool failure → error classified, agent sets status="failed", other agents continue
- LLM failure → error classified, agent returns fallback text
- Individual agent failures don't block the workflow

### Error Classification

`utils/error_categories.py` classifies exceptions by type (rate limit, timeout, connection) and context (groq, mcp, flight, hotel, weather, search, local, graph) into user-friendly messages.

### Prompt Engineering

Every agent has a detailed system prompt defining its role, constraints, and output format. Prompts are inline strings (no template files). Key patterns:
- Request parser: "Return ONLY JSON, ignore irrelevant text"
- Hotel agent: "Never invent prices or booking URLs"
- Search agent: "Perform exactly ONE search_web call"
- Weather agent: "Use 'Not available' only for genuinely absent fields"

### Structured Output

LLM responses are parsed as JSON (request parser) or as Markdown text (all other agents). The request parser uses `_extract_json_payload()` which handles raw JSON, markdown code blocks, and embedded JSON.

---

## Algorithms

### Request Parsing (NL → JSON)

1. User provides free-text sentence
2. System prompt instructs LLM to extract 5 fields as JSON
3. User prompt wraps the sentence
4. LLM returns response
5. `_extract_json_payload()`:
   a. Try `json.loads(response)` directly
   b. Try regex for ```` ```json {...} ``` ````
   c. Try find first `{` and last `}` in text
   d. Try `json.loads()` on extracted substring
   e. Raise ValueError if no JSON found
6. Each field normalized: None→"", "null"→"", whitespace→""
7. `validate_parsed_fields()` checks 4 required fields for empty/None/whitespace

### Missing Field Detection

```python
REQUIRED_FIELDS = ("origin", "destination", "venue", "event_date")
for field in REQUIRED_FIELDS:
    if not value or not str(value).strip():
        missing.append(field)
```

### Rate Limiting (Login Example)

```
check_login_rate_limit(email):
  if redis.exists("tripplanner:login_lock:{email}"):
    raise 429

record_login_failure(email):
  count = redis.incr("tripplanner:login:{email}")
  if count == 1:
    redis.expire("tripplanner:login:{email}", 25h)
  if count >= 5:
    redis.set("tripplanner:login_lock:{email}", 1, ex=25h)

reset_login_failures(email):
  redis.delete("tripplanner:login:{email}", "tripplanner:login_lock:{email}")
```

### Execution Plan Generation

```
supervisor_agent builds execution_plan:
  run_flight_agent  = not bool(state.get("flight_details"))
  run_hotel_agent   = not bool(state.get("hotel_details"))
  run_weather_agent = not bool(state.get("weather_details"))
  run_search_agent  = not bool(state.get("search_results"))
  run_local_agent   = not bool(state.get("local_results"))
```

### Parallel Fan-Out

```
_route_from_supervisor(state):
  plan = state["execution_plan"]
  sends = []
  if plan["run_flight_agent"]:   sends.append(Send("flight_agent", state))
  if plan["run_hotel_agent"]:    sends.append(Send("hotel_agent", state))
  if plan["run_weather_agent"]:  sends.append(Send("weather_agent", state))
  if plan["run_search_agent"]:   sends.append(Send("search_agent", state))
  if plan["run_local_agent"]:    sends.append(Send("local_agent", state))
  if not sends: return "itinerary_agent"
  return sends
```

### Error Classification

```
classify_error(exc, context):
  if rate_limit detected AND context contains "groq":
    return "AI service quota exceeded"
  if timeout AND context contains "groq":
    return "AI service timeout"
  if connection/timeout AND context contains "mcp":
    return "Travel services unavailable"
  if context matches flight/hotel/weather/search/local:
    return domain-specific message
  return "Something went wrong"
```

### Report Formatting (Deterministic)

```
report_formatter_agent(state):
  sections = [
    executive_summary,     # from state fields
    trip_overview,         # table from state fields
    recommended_flight,    # parsed from flight_notes
    other_flights,         # parsed from flight_notes
    recommended_hotels,    # parsed from hotel_notes
    additional_hotels,     # parsed from hotel_notes
    weather_summary,       # extracted between headings from weather_notes
    weather_details,       # extracted between headings
    local_highlights,      # extracted between headings from search_notes
    restaurants,           # extracted between headings
    transportation,        # extracted between headings
    itinerary,             # from state["itinerary"]
    quick_links,           # collected from flight_booking_link + hotel_booking_links
    next_steps,            # static checklist
  ]
  return "\n\n---\n\n".join(non_empty_sections)
```

### Date Normalization (Conversation Service)

```
_normalize_event_date(text):
  1. Try YYYY-MM-DD regex
  2. Strip ordinal suffixes (st, nd, rd, th)
  3. Try strptime with 8 formats: %B %d %Y, %b %d %Y, %d/%m/%Y, etc.
  4. Try title-cased versions
  5. Fall back to request_parser_agent(text)
  6. Return None if all fail
```

---

## Security

### Authentication

- JWT tokens signed with `SECRET_KEY` (HS256)
- Access token: 30 min expiry
- Refresh token: 7 day expiry, stored as SHA-256 hash in DB
- Bearer token required for all `/trips/*` endpoints except health

### Authorization

- User can only access their own trips (`user_id` checked)
- Refresh token ownership verified before use
- Refresh token revocation on logout

### Secrets

- `SECRET_KEY`: loaded from `.env`, validated at startup (must not be placeholder)
- `GROQ_API_KEY`: loaded from `.env`
- `TAVILY_API_KEY`: loaded from `.env`
- `LANGCHAIN_API_KEY`: loaded from `.env`
- Database URL: loaded from `.env`
- All secrets in `.env` (gitignored)

### Password Storage

- bcrypt hashing via `passlib`
- No plaintext storage

### Rate Limiting

- Login: 5 attempts per email → 25 hour lockout
- Registration: 5 attempts per email → 24 hour lockout
- Trip failures: 3 per user → 20 minute lockout
- Daily trip quota: 2 successful trips per 24 hours

### CORS

- Allowed origins: `localhost:8080`, `127.0.0.1:8080`, `172.20.10.11:8080`
- Credentials allowed
- All methods and headers allowed

### Input Validation

- Pydantic models validate all API inputs
- Request parser validates empty input
- State builder validates travelers (positive integer)
- Tool callers validate required MCP fields

---

## Error Handling

### Layers

| Layer | Handler | Behavior |
|---|---|---|
| Pydantic validation | `_validation_error_handler` | Returns 422 with error details |
| HTTP exceptions | `_http_error_handler` | Returns status code with detail |
| Unhandled exceptions | `_global_error_handler` | Returns 500 generic message |
| Graph execution | `plan_trip` try/except | Returns TripPlanResponse(success=False) |
| Agent failures | Per-agent try/except | Sets status="failed", classifies error |
| MCP tool failures | Per-tool try/except | Returns error dict, doesn't raise |
| Redis failures | All cache/rate-limit ops | Fails open (returns None/0/False) |

### Error Classification

`classify_error(exc, context)` maps exceptions to user-friendly messages:

| Exception Type | Context | Message |
|---|---|---|
| RateLimitError | groq | "AI service quota exceeded" |
| TimeoutError | groq | "AI service timeout" |
| ConnectionError | mcp | "Travel services unavailable" |
| Any | flight | "Couldn't retrieve flight information" |
| Any | hotel | "Couldn't retrieve hotel information" |
| Any | weather | "Couldn't retrieve weather information" |
| Any | search | "Couldn't retrieve destination information" |
| Any | local | "Couldn't retrieve local recommendations" |
| Any | graph | "Couldn't generate travel itinerary" |
| Any | (default) | "Something went wrong" |

### Recovery Flow

1. Agent failure → error appended to `errors` list → other agents continue
2. Graph failure → trip record updated to "failed" → error message returned to client
3. Redis failure → operations silently skipped → request proceeds without caching/rate-limiting
4. MCP timeout → agent sets status="failed" → itinerary agent uses available data

---

## Performance

### Caching

- Flight results: 10 min TTL
- Hotel results: 20 min TTL
- Weather: 60 min TTL
- Search: 12 hour TTL
- Itinerary: 10 min TTL

### Async Execution

- All database operations: async (asyncpg)
- All MCP calls: async with 20s timeout
- All LLM calls: async via LangChain
- Graph execution: async (`graph.ainvoke()`, `graph.astream_events()`)

### Parallel Agents

Flight, hotel, weather, search, and local agents execute concurrently. Total time ≈ max(individual agent times) instead of sum.

### Lazy Initialization

- Graph built once per process on first request (`_GRAPH_INSTANCE` singleton)
- Redis client created once per process (`_client` singleton)

### Potential Bottlenecks

1. **LLM calls**: Each agent makes one LLM call (Groq). Total: ~6-7 LLM calls per trip.
2. **MCP connections**: Each MCP call opens a new connection (no connection pooling). Up to 5 MCP calls per trip.
3. **Sequential steps**: coordinator → supervisor → parallel → itinerary is sequential. No parallelism between these phases.
4. **SQLite checkpointing**: Every node writes to SQLite. Under load, this could serialize.

---

## Configuration

### Environment Variables

| Variable | Required | Default | Used By |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | `config/models.py` |
| `TAVILY_API_KEY` | Yes | — | `tools/tavily_search.py` |
| `LANGCHAIN_API_KEY` | No | — | `config/settings.py` |
| `LANGCHAIN_PROJECT` | No | "TripPlanner" | `config/settings.py` |
| `LANGCHAIN_TRACING` | No | True | `config/settings.py` |
| `LANGCHAIN_ENDPOINT` | No | "https://api.smith.langchain.com" | `config/settings.py` |
| `GROQ_TEXT_MODEL` | No | "openai/gpt-oss-20b" | `config/models.py` |
| `GROQ_TRANSCRIPTION_MODEL` | No | "whisper-large-v3" | `config/models.py` |
| `KIWI_MCP_SERVER_URL` | No | "https://mcp.kiwi.com" | `tools/flight_tools.py` |
| `WEATHER_PROVIDER` | No | "livedatalink" | `config/settings.py` |
| `WEATHER_MCP_SERVER_URL` | No | "https://livedatalink.ai/mcp" | `tools/weather_mcp_client.py` |
| `AGENTORIST_MCP_SERVER_URL` | No | "https://mcp.agentorist.com/mcp" | `tools/hotel_tools.py` |
| `DATABASE_URL` | No | "postgresql+asyncpg://trippin_user:trippin_pass_2026@localhost:5432/trippin_db" | `database/connection.py` |
| `SECRET_KEY` | Yes | — | `auth/security.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 | `auth/security.py` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | `auth/security.py` |
| `REDIS_HOST` | No | "localhost" | `config/settings.py` |
| `REDIS_PORT` | No | 6379 | `config/settings.py` |
| `REDIS_DB` | No | 0 | `config/settings.py` |
| `REDIS_PASSWORD` | No | "" | `config/settings.py` |
| `REDIS_DEFAULT_TTL` | No | 1800 | `config/settings.py` |
| `REDIS_ENABLED` | No | True | `config/settings.py` |
| `RATE_LIMIT_ENABLED` | No | True | `config/settings.py` |
| `LOGIN_MAX_ATTEMPTS` | No | 5 | `config/settings.py` |
| `LOGIN_LOCK_HOURS` | No | 25 | `config/settings.py` |
| `REGISTER_MAX_ATTEMPTS` | No | 5 | `config/settings.py` |
| `REGISTER_LOCK_HOURS` | No | 24 | `config/settings.py` |
| `TRIP_FAILURE_MAX_ATTEMPTS` | No | 3 | `config/settings.py` |
| `TRIP_FAILURE_LOCK_MINUTES` | No | 20 | `config/settings.py` |
| `TRIP_SUCCESS_DAILY_LIMIT` | No | 2 | `config/settings.py` |
| `TRIP_SUCCESS_WINDOW_HOURS` | No | 24 | `config/settings.py` |
| `RECORDINGS_DIR` | No | "recordings" | `config/settings.py` |
| `OUTPUTS_DIR` | No | "outputs" | `config/settings.py` |
| `LOGS_DIR` | No | "logs" | `config/settings.py` |

---

## Logging

### Strategy

- Python `logging` module via custom logger (`backend/api/log_config.py`)
- Format: `%(asctime)s | %(levelname)-8s | %(name)s | request=%(request_id)s | %(message)s`
- Level: INFO
- Output: stdout
- Request ID: generated per request via contextvars, injected via filter

### Debug Logging

- `DEBUG = False` flags in flight_agent, hotel_agent, supervisor_agent, flight_tools, hotel_tools
- When enabled: prints full state, MCP payloads, tool schemas
- Graph nodes print `[GRAPH] NODE ENTER/EXIT` with timing
- Agents print `[TIMER] agent_name START/END` with elapsed time
- Search agent has `_SearchTraceHandler` for detailed LLM/tool call tracing

### Weaknesses

- Debug output uses `print()`, not `logging`
- No structured JSON logging
- No log rotation
- No separate log files for different levels
- Debug flags are hardcoded, not configurable

---

## Testing

### Current Tests

| File | Tests | Coverage |
|---|---|---|
| `test_state_builder.py` | 3 | build_trip_state defaults, field population, invalid travelers |
| `test_trip_planner_service.py` | 2 | plan_trip graph invocation, resume_trip snapshot |
| `test_conversation_service.py` | 6 | missing origin/date, resume, complete flow, state corruption, date normalization |
| `test_parallel_fanout.py` | 8 | Routing logic, parallel execution, fan-in |
| `test_request_validation.py` | 11 | Field validation, message formatting, edge cases |

**Total: 30 tests, all passing**

### Testing Strategy

- Unit tests with mocked dependencies (LLM, graph, Redis, DB)
- No integration tests
- No network calls in tests
- Tests verify logic, not external behavior

### Limitations

- No API endpoint tests (no TestClient)
- No database integration tests
- No Redis integration tests
- No MCP integration tests
- No LLM response parsing tests with real data
- No performance/load tests

---

## Known Limitations

1. **LLM-dependent parsing**: Request parser relies on LLM returning valid JSON. Prompt improvements help but can't guarantee 100% compliance.
2. **No MCP connection pooling**: Each MCP call opens a new connection. Under load, this is inefficient.
3. **SQLite for checkpointing**: Single-file database limits concurrent writes. Should migrate to PostgreSQL for production.
4. **Duplicate validation**: coordinator and supervisor both check required fields.
5. **Debug output via print()**: Not using the logging framework for debug messages.
6. **OAuth not wired**: Google/GitHub OAuth scaffold exists but callback routes are not implemented.
7. **No token blacklisting**: Logout only revokes refresh tokens. Access tokens remain valid until expiry.
8. **No retry on MCP failures**: MCP tools have timeouts but no exponential backoff retry.
9. **Hardcoded CORS origins**: Only localhost origins allowed.
10. **No API versioning**: Single version (v2.0.0 in metadata, no URL prefix).
11. **report_formatter_agent is 575 lines**: Large single file with many helper functions.
12. `_make_route_after()` is defined but never called (dead code in `trip_graph.py`).

---

## Recommended Cleanup

### SAFE to Remove

| Item | File | Evidence |
|---|---|---|
| `_make_route_after()` | `graph/trip_graph.py:65-75` | Defined but never called. All routing goes through `_route_from_supervisor()`. |
| `auth/oauth.py` | `auth/oauth.py` | All functions raise `NotImplementedError` or are empty stubs. No routes import it. |
| `recommended_hotel_price` field | `state/trip_state.py:85` | Never set by any agent. Always 0.0. |
| `_DEPRECATED_STATE_KEYS` | `agents/supervisor_agent.py:11-15` | Filters keys that no longer exist in state. |
| Debug `print()` statements | Multiple agents | ~50+ print statements across agents. Should use logging or be removed. |
| `_LLM_CALL_COUNTER` | `config/models.py` | Debug counter, only used in timing wrapper prints. |
| `_timed_agenerate`/`_timed_generate` wrappers | `config/models.py:44-64` | Debug timing wrappers that monkey-patch LLM methods. |
| `_timed_aput` monkey-patch | `memory/sqlite_checkpoint.py:35-41` | Debug timing that patches `AsyncSqliteSaver.aput`. |
| `_SearchTraceHandler` | `agents/search_agent.py:17-99` | Debug tracing handler, only used when DEBUG=True. |
| `DEBUG` flags | `flight_agent.py:8`, `hotel_agent.py`, `supervisor_agent.py:8`, `flight_tools.py`, `hotel_tools.py` | Hardcoded False, never toggled in production. |
| `transcribe_audio()` | `config/models.py:69-89` | Audio transcription function. Never called from any route or service. |
| `get_groq_client()` | `config/models.py:64-68` | Only used by `transcribe_audio()`. |
| `file_utils.py` | `utils/file_utils.py` | `ensure_project_dirs()`, `save_text_output()`, `audio_to_base64()`, `get_latest_recording()` — none called from any route or service. Only used by debug scripts. |
| Root-level debug scripts | `diagnose_phase5.py`, `run_search_flights_diag.py`, `run_timing.py`, `test_parallel.py`, `verify_phase_a.py`, `verify_redis.py`, `_debug_agents.py`, `_debug_checkpointer.py`, `_debug_trace.py`, `_repro.py` | Standalone debug/diagnostic scripts, not imported by any production code. |
| `notebooks/` | `notebooks/` | Jupyter notebooks for exploration, not part of production. |
| `improve.txt` | `improve.txt` | Not imported, appears to be notes. |
| `result.md` | `result.md` | Not imported, appears to be output. |

### REVIEW REQUIRED

| Item | File | Evidence |
|---|---|---|
| `conversation_service.py` | `services/conversation_service.py` | Functional but not exposed via API routes. No route calls `start_conversation()` or `continue_conversation()`. May be intended for future use. |
| `data/` directory | `data/` | Contains `hotels_raw.json`, `weather_raw.json`. Not loaded by any production code. May be test data. |
| Duplicate `_last_message_content()` | 6 files | Identical function defined in `request_parser_agent.py`, `flight_agent.py`, `hotel_agent.py`, `weather_agent.py`, `search_agent.py`, `local_agent.py`, `itinerary_agent.py`. Could be extracted to a shared utility. |
| Duplicate `_serialize_tool_result()` | `flight_tools.py`, `hotel_tools.py` | Nearly identical MCP result serialization. Could be shared. |
| Duplicate `_log_exception_details()` | `flight_tools.py`, `hotel_tools.py`, `weather_mcp_client.py` | Identical traceback logging. Could be shared. |
| Duplicate `_list_tools_and_call()` | `flight_tools.py`, `hotel_tools.py` | Very similar MCP client connection logic. Could be generalized. |
| `services/conversation_service.py:_normalize_event_date()` | Same file | Complex date parsing that reimplements dateutil-like functionality. |

### DO NOT REMOVE

| Item | File | Evidence |
|---|---|---|
| `report_formatter_agent.py` | `agents/report_formatter_agent.py` | Core production code — deterministic report assembly. Called by `itinerary_agent`. |
| `error_categories.py` | `utils/error_categories.py` | Core production code — used by every agent and tool for error classification. |
| `cache/` | `cache/` | Core production code — used by all caching agents and rate limiter. |
| `rate_limiter.py` | `services/rate_limiter.py` | Core production code — protects API from abuse. |
| `sqlite_checkpoint.py` | `memory/sqlite_checkpoint.py` | Core production code — enables workflow resumption. |
| `test_*` files | `tests/` | Test suite — 30 passing tests. |

---

## Dependency Map

### Module Dependencies

```mermaid
graph TD
    backend/api/routes/trips.py --> agents/request_parser_agent
    backend/api/routes/trips.py --> utils/state_builder
    backend/api/routes/trips.py --> services/rate_limiter
    backend/api/routes/trips.py --> database/crud
    backend/api/routes/auth.py --> auth/security
    backend/api/routes/auth.py --> database/crud
    backend/api/routes/auth.py --> services/rate_limiter
    backend/api/app.py --> backend/api/routes/auth
    backend/api/app.py --> backend/api/routes/trips
    backend/api/app.py --> cache/redis_client
    backend/api/app.py --> database/connection

    services/trip_planner_service.py --> agents/request_parser_agent
    services/trip_planner_service.py --> utils/state_builder
    services/trip_planner_service.py --> graph/trip_graph

    services/conversation_service.py --> agents/request_parser_agent
    services/conversation_service.py --> agents/conversation_agent
    services/conversation_service.py --> services/trip_planner_service
    services/conversation_service.py --> utils/state_builder

    graph/trip_graph.py --> agents/coordinator
    graph/trip_graph.py --> agents/supervisor_agent
    graph/trip_graph.py --> agents/flight_agent
    graph/trip_graph.py --> agents/hotel_agent
    graph/trip_graph.py --> agents/weather_agent
    graph/trip_graph.py --> agents/search_agent
    graph/trip_graph.py --> agents/local_agent
    graph/trip_graph.py --> agents/itinerary_agent
    graph/trip_graph.py --> memory/sqlite_checkpoint

    agents/flight_agent --> tools/flight_tools
    agents/flight_agent --> cache/cache_service
    agents/hotel_agent --> tools/hotel_tools
    agents/hotel_agent --> cache/cache_service
    agents/weather_agent --> tools/weather_tools
    agents/weather_agent --> cache/cache_service
    agents/search_agent --> tools/tavily_search
    agents/search_agent --> cache/cache_service
    agents/local_agent --> tools/hotel_tools
    agents/itinerary_agent --> agents/report_formatter_agent
    agents/itinerary_agent --> cache/cache_service

    tools/flight_tools --> config/settings
    tools/hotel_tools --> config/settings
    tools/weather_mcp_client --> config/settings
    tools/weather_tools --> tools/weather_mcp_client
    tools/tavily_search --> config/settings

    agents/* --> config/models
    agents/* --> utils/error_categories

    cache/cache_service --> cache/redis_client
    cache/cache_service --> cache/metrics
    cache/redis_client --> config/settings
    services/rate_limiter --> cache/cache_keys
    services/rate_limiter --> cache/redis_client

    database/connection --> config/settings
    database/crud --> database/models
    database/crud --> auth/security
    auth/dependencies --> auth/security
    auth/dependencies --> database/crud
    auth/security --> config/settings
```

### Agent Dependencies

| Agent | Depends On |
|---|---|
| request_parser_agent | config/models (LLM) |
| coordinator | config/models (LLM, unused) |
| supervisor_agent | config/models (LLM), utils/error_categories |
| flight_agent | tools/flight_tools, cache/cache_service, config/models (LLM), utils/error_categories |
| hotel_agent | tools/hotel_tools, cache/cache_service, config/models (LLM), utils/error_categories |
| weather_agent | tools/weather_tools, cache/cache_service, config/models (LLM), utils/error_categories |
| search_agent | tools/tavily_search, cache/cache_service, config/models (LLM), utils/error_categories |
| local_agent | tools/hotel_tools, config/models (LLM), utils/error_categories |
| itinerary_agent | agents/report_formatter_agent, cache/cache_service, config/models (LLM), utils/error_categories |
| conversation_agent | (none — pure logic) |

---

## Backend Summary

### Why the Architecture Works

1. **Separation of concerns**: Each agent handles one domain. Tools handle external integrations. Services handle business logic. Routes handle HTTP.
2. **Parallel execution**: Flight, hotel, weather, search, and local agents run concurrently, reducing total execution time.
3. **Graceful degradation**: Individual agent failures don't block the workflow. Missing data is handled with fallbacks.
4. **Checkpointing**: SQLite enables workflow resumption without re-executing completed steps.
5. **Caching**: Repeated requests for the same trip details skip expensive MCP calls.
6. **Validation layers**: Pydantic validates API inputs. Request parser validates NL extraction. Coordinator/supervisor validate state before agents run.

### What Should NEVER Be Modified During Cleanup

| Component | Reason |
|---|---|
| `state/trip_state.py` | LangGraph state schema — changing it breaks the entire graph |
| `graph/trip_graph.py` node/edge structure | Graph topology — changing it breaks workflow execution |
| `database/models.py` table schemas | Production data — requires Alembic migration for changes |
| `auth/security.py` JWT logic | Security-critical — changes affect all authenticated endpoints |
| `config/settings.py` env var names | Contract with `.env` and deployment config |
| `tools/*/MCP tool names` | Contract with external MCP servers |
| `backend/api/schemas/response.py` response models | API contract with clients |
| `backend/api/schemas/request.py` request models | API contract with clients |

---

*Document generated from static analysis of all backend source files. Last updated: 2026-07-18.*
