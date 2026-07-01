# Trip Planner Backend — Architecture Document

## 1. Project Overview

### Purpose

The Trip Planner is an **AI-powered multi-agent travel planning system** that converts a natural-language trip request into a structured, multi-section Markdown travel report. It consolidates flight search, hotel recommendations, weather forecasting, destination research, and itinerary generation into a single automated pipeline.

### Overall Architecture

The system follows a **layered, event-driven, shared-state architecture**:

```
┌─────────────────────────────────────────────────────┐
│                   Entry Points                       │
│   CLI (main.py)   FastAPI REST (backend/api/)        │
│   Python API (services/)                             │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Service Layer (services/)                │
│   Trip Planning, Conversation Management, Resumption │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              LangGraph Orchestration (graph/)         │
│   StateGraph with conditional routing + checkpointing │
└───┬───────┬───────┬───────┬───────┬───────┬─────────┘
    │       │       │       │       │       │
┌───▼───┐ ┌─▼────┐ ┌▼─────┐ ┌▼─────┐ ┌▼─────┐ ┌▼──────┐
│Super- │ │Flight│ │Hotel │ │Weath-│ │Search│ │Itiner-│
│visor  │ │Agent │ │Agent │ │Agent │ │Agent │ │ary Ag.│
└───────┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
             │        │        │        │        │
    ┌────────▼────────▼────────▼────────▼────────▼────┐
    │                   Tool Layer (tools/)            │
    │  Kiwi MCP │ Agentorist MCP │ LiveDataLink MCP   │
    │  Tavily API │ Groq LLM                          │
    └─────────────────────────────────────────────────┘
```

### Technologies

| Category | Technology | Role |
|---|---|---|
| Workflow engine | **LangGraph** (StateGraph) | Multi-agent orchestration, state merging, checkpointing |
| Agent framework | **LangChain** (create_agent) | Agent construction (prompt + LLM + optional tools) |
| LLM provider | **Groq** (openai/gpt-oss-20b) | Natural language parsing, summarization, itinerary generation |
| Flight data | **Kiwi MCP Server** | Search-flight tool via Model Context Protocol |
| Hotel / Local data | **Agentorist MCP Server** | Search tool via MCP |
| Weather data | **LiveDataLink MCP Server** | weather_forecast, weather_current, air_quality tools via MCP |
| Web search | **Tavily API** | Destination research |
| API framework | **FastAPI** | REST endpoints, OpenAPI docs, middleware |
| Persistence | **SQLite** (langgraph-checkpoint-sqlite) | Graph state checkpointing |
| Validation | **Pydantic** / **pydantic-settings** | Request/response models, environment config |
| Logging | **Python logging** + ContextVars | Per-request correlation IDs |
| Testing | **unittest** | Unit tests with mocks |
| Deployment | **Uvicorn** + **Procfile** | ASGI server, Heroku-ready |

### Design Philosophy

1. **Shared state paradigm** — Every LangGraph node receives the complete `TripPlannerState` dict and returns a partial update. The framework merges updates automatically.
2. **Separation of concerns** — Each specialist agent owns exactly one domain (flights, hotels, weather, search, itinerary).
3. **Graceful degradation** — Individual agent failures are recorded in `errors[]` without blocking the workflow. The graph continues executing subsequent agents.
4. **Deterministic report generation** — The final report formatter uses no LLM; it assembles Markdown directly from state fields using string manipulation.
5. **Conditional execution** — The supervisor generates an execution plan that allows skipping agents whose data is already present (e.g., on resume).

### Architectural Style

**Multi-agent orchestration with a coordinator-supervisor pattern.** The system uses a hierarchical agent architecture:
- A **coordinator** validates initial state
- A **supervisor** plans execution and generates context
- **Specialist agents** execute domain tasks in a configurable order
- The **itinerary agent** synthesizes all outputs and triggers report generation

---

## 2. Folder Structure

```
trip_planner/
│
├── main.py                              # CLI entry point
├── Procfile                             # Heroku deployment command
├── runtime.txt                          # Python version for Heroku
├── requirements.txt                     # Python dependencies
├── requirements.md                      # Detailed dependency documentation
├── README.md                            # Project documentation
├── SYSTEM_DESIGN.md                     # System design document
├── result.md                            # Sample execution output
│
├── agents/                              # LangChain agent definitions
│   ├── __init__.py
│   ├── conversation_agent.py            # Deterministic field-missing detection
│   ├── coordinator.py                   # Initial state validation (graph node)
│   ├── flight_agent.py                  # Kiwi MCP flight search + LLM summary
│   ├── hotel_agent.py                   # Agentorist MCP hotel search + LLM summary
│   ├── itinerary_agent.py               # Synthesizes all notes into itinerary
│   ├── local_agent.py                   # Agentorist local discovery (graph node)
│   ├── report_formatter_agent.py        # Deterministic markdown assembly (no LLM)
│   ├── request_parser_agent.py          # NL → structured fields via Groq
│   ├── search_agent.py                  # Tavily web search + LLM summary
│   ├── supervisor_agent.py              # Orchestration, validation, planning
│   └── weather_agent.py                 # LiveDataLink weather + LLM summary
│
├── backend/                             # FastAPI web layer
│   └── api/
│       ├── __init__.py
│       ├── app.py                       # Application factory, middleware, handlers
│       ├── log_config.py                # Structured logging with request IDs
│       ├── routes/
│       │   ├── __init__.py
│       │   └── trips.py                 # REST endpoints (plan, state, resume)
│       └── schemas/
│           ├── __init__.py
│           ├── request.py               # TripPlanRequest model
│           └── response.py              # HealthResponse, TripPlanResponse, TripStateResponse
│
├── config/                              # Configuration management
│   ├── __init__.py
│   ├── models.py                        # Groq LLM and transcription clients
│   └── settings.py                      # Pydantic-settings from .env
│
├── data/                                # Cached MCP/API responses
│   ├── .gitkeep
│   ├── README.md
│   ├── hotels_raw.json                  # Sample Agentorist response
│   └── weather_raw.json                 # Sample LiveDataLink response
│
├── graph/                               # LangGraph workflow definition
│   ├── __init__.py
│   └── trip_graph.py                    # StateGraph with 8 nodes + conditional routing
│
├── logs/                                # Log output directory
│
├── memory/                              # State persistence
│   ├── __init__.py
│   ├── sqlite_checkpoint.py             # SqliteSaver configuration
│   └── trip_planner.db                  # SQLite checkpoint database (auto-created)
│
├── notebooks/                           # Jupyter notebooks
│   ├── final_report.txt
│   ├── mcp_connection_test.ipynb
│   ├── report.txt
│   ├── trip_planner.db
│   └── trip_planner.ipynb
│
├── recordings/                          # Audio recording directory
│
├── services/                            # Public API surface
│   ├── __init__.py
│   ├── conversation_service.py          # Multi-turn field collection
│   └── trip_planner_service.py          # plan_trip(), resume_trip()
│
├── state/                               # Data types
│   ├── __init__.py
│   └── trip_state.py                    # TripPlannerState TypedDict
│
├── tests/                               # Unit tests (unittest)
│   ├── __init__.py
│   ├── test_conversation_service.py     # Multi-turn conversation flows
│   ├── test_state_builder.py            # State construction tests
│   └── test_trip_planner_service.py     # Service entry point tests
│
├── tools/                               # External service integrations
│   ├── __init__.py
│   ├── flight_tools.py                  # Kiwi MCP client (SSE + Streamable HTTP)
│   ├── hotel_tools.py                   # Agentorist MCP client
│   ├── tavily_search.py                 # Tavily REST API client
│   ├── weather_mcp_client.py            # LiveDataLink MCP client (low-level)
│   └── weather_tools.py                 # Weather logic wrapper
│
└── utils/                               # Shared utilities
    ├── __init__.py
    ├── file_utils.py                    # File I/O, directory management, base64
    └── state_builder.py                 # TripPlannerState construction
```

### Folder Responsibilities

| Folder | Purpose | Contents |
|---|---|---|
| `agents/` | **All LangChain agent functions** invoked as LangGraph nodes or as pre/post-processing helpers. Each agent is a pure function that receives state dict and returns state dict. | 11 agent modules covering coordinator, supervisor, flight, hotel, weather, search, local, itinerary, report formatting, request parsing, conversation helpers |
| `backend/api/` | **FastAPI web application** — the REST API layer that exposes trip planning, state inspection, and workflow resumption over HTTP. | Application factory (`app.py`), logging config, router (`routes/trips.py`), Pydantic schemas (`schemas/request.py`, `schemas/response.py`) |
| `config/` | **Environment and model configuration.** Loads settings from `.env` via `pydantic-settings` and provides initialized LLM clients. | Settings loader, Groq text/transcription model factories |
| `graph/` | **LangGraph workflow definition** — builds the `StateGraph`, registers all nodes, defines edges and conditional routing, compiles with SQLite checkpointing. | Single module `trip_graph.py` |
| `memory/` | **State persistence layer** — configures `SqliteSaver` for LangGraph checkpointing. The resulting `.db` file stores full state snapshots after every node execution. | Checkpointer factory, SQLite database file |
| `services/` | **Public-facing service layer** — orchestrates parsing, state building, and graph invocation. Used by both the CLI entry point and the FastAPI router. | Trip planning service (`plan_trip`, `resume_trip`), conversation service (`start_conversation`, `continue_conversation`, `resume_conversation`) |
| `state/` | **Data type definitions** — the single `TripPlannerState` TypedDict that flows through every LangGraph node. | State type definition with 30+ fields |
| `tools/` | **External integration wrappers** — MCP clients for Kiwi, Agentorist, and LiveDataLink, plus the Tavily REST client. Each tool handles async→sync bridging, timeout management, error serialization, and result normalization. | 5 tool modules |
| `utils/` | **Shared utilities** used across multiple layers. | State builder (`build_trip_state`), file utilities (`save_text_output`, `read_text_file`, `audio_to_base64`) |
| `tests/` | **Unit test suite** using Python's `unittest` framework with mocked dependencies. | 3 test files covering state building, trip planning service, conversation service |
| `data/` | **Cached external responses** for offline development and debugging. | Sample JSON responses from Agentorist and LiveDataLink |

---

## 3. High-Level Architecture

### Layered Architecture

```
Layer 0: Entry Points
  CLI (main.py) │ FastAPI (backend/api/) │ Direct Python import
        │                │                        │
Layer 1: Services ───────┼────────────────────────┘
  trip_planner_service.py │ conversation_service.py
        │
Layer 2: LangGraph Orchestration
  graph/trip_graph.py  ←──  StateGraph[ TripPlannerState ]
        │
        ├── Layer 2a: Agents (agents/)
        │     coordinator_agent (validates state)
        │     supervisor_agent (plans execution)
        │     flight_agent (flight search + summary)
        │     hotel_agent (hotel search + summary)
        │     weather_agent (weather + summary)
        │     search_agent (web search + summary)
        │     local_agent (local discovery + summary)
        │     itinerary_agent (synthesis + report trigger)
        │     report_formatter_agent (deterministic markdown)
        │
        ├── Layer 2b: Tools (tools/)
        │     flight_tools.py  ──→ Kiwi MCP Server
        │     hotel_tools.py   ──→ Agentorist MCP Server
        │     weather_mcp_client.py + weather_tools.py ──→ LiveDataLink MCP Server
        │     tavily_search.py ──→ Tavily API
        │
        └── Layer 2c: Checkpointing (memory/)
              sqlite_checkpoint.py ──→ SQLite DB
                    │
Layer 3: Configuration (config/)
  settings.py (.env) │ models.py (Groq LLM)
```

### Layer Descriptions

**Entry Points Layer** — Three ways to invoke the system:
1. **CLI** (`main.py`): `python main.py --request "..."` parses args and calls `plan_trip()`.
2. **FastAPI** (`backend/api/`): REST endpoints at `/api/trips/plan`, `/api/trips/{thread_id}`, `/api/trips/{thread_id}/resume`, `/api/trips/health`.
3. **Python API** (`services/`): `plan_trip()`, `resume_trip()`, `start_conversation()`, `continue_conversation()` can be imported directly.

**Service Layer** — Orchestrates the end-to-end workflow:
- `trip_planner_service.plan_trip()`: Parses request → builds state → invokes graph → returns result dict.
- `trip_planner_service.resume_trip()`: Loads persisted state by `thread_id` from the checkpointer.
- `conversation_service`: Multi-turn state machine for collecting missing fields (origin, destination, event_date) through back-and-forth user interaction.

**LangGraph Orchestration Layer** — The core workflow engine:
- Defines a `StateGraph[TripPlannerState]` with 8 registered node functions.
- Uses conditional edges based on the supervisor's `execution_plan` dict to determine which agents run.
- Compiles with a `SqliteSaver` checkpointer that persists state after every node execution.
- Each node is a Python function decorated with debug print wrappers.

**Agent Layer** — Domain-specialized LLM agents:
- Each agent follows the pattern: copy state → wrap in try/except → execute domain logic → write results to state dict → return updated dict.
- Agents use `langchain.agents.create_agent()` with either zero tools (for pure LLM summarization) or one tool (for search_agent, local_agent).
- The `report_formatter_agent` is unique: it uses no LLM, assembling Markdown via deterministic string manipulation.

**Tool Layer** — External integration adapters:
- MCP clients connect to remote servers via SSE (Server-Sent Events) or Streamable HTTP transport, initialize sessions, list tools, and call specific tools.
- All MCP tools use `asyncio` internally but bridge to synchronous code via a `_run_coroutine()` helper that spawns a daemon thread with a new event loop.
- The Tavily client is a straightforward REST API wrapper with retry logic (3 attempts).

**MCP Layer** — Three MCP server integrations:
- **Kiwi** (`tools/flight_tools.py`): Tool name `search-flight`. Supports SSE and Streamable HTTP. Returns structured flight data.
- **Agentorist** (`tools/hotel_tools.py`): Tool name `search`. Supports SSE and Streamable HTTP. Returns structured local business results.
- **LiveDataLink** (`tools/weather_mcp_client.py`): Tools `weather_current`, `weather_forecast`, `air_quality`. Streamable HTTP only. Returns plain text.

**External APIs** — Two non-MCP integrations:
- **Groq** (`config/models.py`): REST API for LLM completions (via `langchain-groq` `ChatGroq`) and audio transcription (via native `groq` client with Whisper model).
- **Tavily** (`tools/tavily_search.py`): REST API for web search with 3-attempt retry and configurable max results.

**State Layer** — The `TripPlannerState` TypedDict (~30 fields) is the single source of truth. Every node reads from it and writes to it. Fields are organized by domain (origin/destination, flight_*, hotel_*, weather_*, search_*, itinerary, booking info, status, errors, execution plan).

**Report Generation Layer** — `report_formatter_agent` in `agents/report_formatter_agent.py`:
- Pure Python string assembly — no LLM calls.
- Parses `flight_notes`, `hotel_notes`, `weather_notes`, `search_notes` using regex to extract structured sections.
- Produces a Markdown document with sections: Executive Summary, Trip Overview, Recommended Flight, Other Available Flights, Recommended Hotels, Additional Hotel Options, Weather Summary, Weather Details, Local Highlights, Restaurants, Transportation, Day-wise Itinerary, Quick Links, Next Steps.

---

## 4. Complete Request Flow

```
User / HTTP Client
        │
        │ POST /api/trips/plan  {"sentence": "Plan a trip from MIA to EWR on 2026-07-15..."}
        │         OR  {"origin": "MIA", "destination": "EWR", ...}
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI (backend/api/routes/trips.py)                          │
│  1. Logging middleware assigns request_id (uuid4 hex[:12])       │
│  2. CORS middleware checks origin headers                        │
│  3. RequestValidationError handler catches schema issues         │
│  4. Request body parsed into TripPlanRequest Pydantic model      │
│  5. model_validator ensures sentence XOR all structured fields   │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  TripPlanRequest Validation                                     │
│  ├─ If body.sentence is provided: use natural language path      │
│  └─ Else: use structured fields from body directly               │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Branch A: Natural Language Parsing (agents/request_parser)      │
│  1. Call request_parser_agent(sentence)                          │
│  2. LangChain agent (create_agent) with Groq LLM                 │
│  3. System prompt: "Extract structured details... Return JSON"   │
│  4. LLM returns JSON with keys: origin, destination, travelers,  │
│     venue, event_date                                            │
│  5. _extract_json_payload() handles markdown code blocks,        │
│     raw JSON, and nested responses                               │
│  6. Normalize each field (trim, handle null/none/unknown)        │
│  7. Return structured dict                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Branch B: Structured Fields (no parsing needed)                 │
│  Simply create dict from body.origin, .destination, .event_date, │
│  .venue                                                          │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  State Builder (utils/state_builder.py)                          │
│  1. _normalize_text(): trim, treat null/none/unknown as empty    │
│  2. _normalize_travelers(): handle string, float, int, default 1 │
│  3. build_trip_state(): assemble TripPlannerState dict with      │
│     origin, destination, travelers, venue, event_date,           │
│     empty errors[], empty booking fields                         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  LangGraph Invocation (graph/trip_graph.py)                      │
│  1. state = build_trip_state(parsed)                             │
│  2. thread_id = "api_trip_" + uuid4.hex                          │
│  3. graph.invoke(state, config={thread_id})                       │
│  4. StateGraph[TripPlannerState] begins execution                │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────────┐
  │  START ──→ coordinator_agent                      │
  │  - Validates destination, venue, event_date        │
  │  - Initializes defaults (flight_details={}, etc.)  │
  │  - Sets status = "processing"                      │
  │  - SQLite checkpoint after execution               │
  └──────────────────────┬───────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  coordinator_agent ──→ supervisor_agent            │
  │  - Validates required fields (dest, venue, date)   │
  │  - Initializes all domain field defaults           │
  │  - Builds execution_plan: which agents to run      │
  │    (based on whether domain data already exists)   │
  │  - Calls LLM to generate supervisor_notes           │
  │  - Sets status = "blocked" if validation fails     │
  │  - SQLite checkpoint after execution               │
  └──────────────────────┬───────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────┐
  │  _route_from_supervisor() via Send() API          │
  │  - Checks execution_plan for each parallel agent  │
  │  - Returns list of Send(node, state) for enabled  │
  │    agents (flight, hotel, weather)                │
  │  - If none enabled → routes directly to           │
  │    search_agent (string)                          │
  └──────────────────────┬───────────────────────────┘
                          │
            ┌─────────────┼─────────────┐      (or ──► search_agent)
            ▼             ▼             ▼
  ┌──────────────┐ ┌──────────┐ ┌──────────────┐
  │ flight_agent │ │hotel_ag. │ │ weather_ag.  │
  │   (parallel) │ │(parallel)│ │  (parallel)  │
  │              │ │          │ │              │
  │ search_fl-   │ │search_   │ │ get_weather  │
  │ ights(Kiwi)  │ │hotels(Ag)│ │ (LiveDataLn) │
  │              │ │          │ │              │
  │ LLM summary  │ │LLM sum.  │ │ LLM summary  │
  └───────┬──────┘ └────┬─────┘ └──────┬───────┘
          │             │              │
          └─────────────┼──────────────┘
                        │  (fan-in: all three converge)
                        ▼
  ┌──────────────────────────────────────────────────┐
  │  search_agent / local_agent (sequential, with     │
  │  skip support via _make_route_after)              │
  │  - search_agent: Tavily web search + LLM summary  │
  │  - local_agent: Agentorist MCP + LLM summary      │
  └──────────────────────┬───────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────┐
  │  itinerary_agent                                   │
  │  - Takes all agent notes (flight, hotel, weather,  │
  │    search) plus supervisor_notes                   │
  │  - Calls LLM to synthesize day-by-day itinerary    │
  │  - Calls report_formatter_agent() internally       │
  │    - Determinisic Markdown assembly, no LLM        │
  │  - Sets status = "completed" or "failed"           │
  │  - SQLite checkpoint after execution               │
  └──────────────────────┬───────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────────┐
  │  itinerary_agent ──→ END                           │
  │  Graph returns final state dict with final_report  │
  └──────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Response Assembly (backend/api/routes/trips.py)                 │
│  1. result = graph.invoke() returns TripPlannerState dict        │
│  2. Extract final_report, itinerary, status from result          │
│  3. Handle failures: log error, return error TripPlanResponse    │
│  4. Return TripPlanResponse(success=True, report=markdown,       │
│     itinerary=text, destination=..., event_date=...)              │
│  5. Logging middleware records elapsed_ms, status_code           │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
User / HTTP Client receives JSON response with markdown report
```

---

## 5. FastAPI Architecture

### Application Factory (`backend/api/app.py:96-143`)

The `create_app()` function constructs the FastAPI application:

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Trip Planner API", version="2.0.0", ...)
    # Middleware
    app.middleware("http")(_logging_middleware)
    app.add_middleware(CORSMiddleware, ...)
    # Exception handlers
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _global_error_handler)
    # Router
    app.include_router(trips_router)
    return app

app = create_app()  # Module-level instance for uvicorn
```

### Middleware

**Logging Middleware** (`app.py:18-43`):
- Generates a unique `request_id` (12 hex chars from uuid4) for every request.
- Stores it in `request.state.request_id` and a `contextvars.ContextVar` for log injection.
- Records wall-clock time before and after request processing.
- Logs method, path, status_code, and elapsed_ms on completion.
- Handles unhandled exceptions by logging the traceback and re-raising.
- Sets `X-Request-ID` response header for correlation.

**CORS Middleware** (`app.py:126-136`):
- Allow origins: `http://localhost:8080`, `http://127.0.0.1:8080`, `http://172.20.10.11:8080`
- allow_credentials=True, allow_methods=["*"], allow_headers=["*"]

### Exception Handlers

| Handler | Exception | Status | Response |
|---|---|---|---|
| `_validation_error_handler` | `RequestValidationError` | 422 | `{"detail": [validation errors]}` |
| `_http_error_handler` | `HTTPException` | Variable | `{"detail": exc.detail}` |
| `_global_error_handler` | `Exception` | 500 | `{"detail": "An internal error occurred..."}` |

All handlers log a warning with method, path, and error details.

### Routers

The single router `trips_router` is defined in `routes/trips.py` at prefix `/api/trips` with tag `"Trip Planning"`.

### Dependency Injection

No FastAPI `Depends` usage. The graph instance is lazily initialized via a module-level singleton pattern:

```python
def _get_graph():
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        from graph.trip_graph import build_trip_graph
        _GRAPH_INSTANCE = build_trip_graph()
    return _GRAPH_INSTANCE
```

This avoids circular imports and ensures the graph is built once and reused across requests.

### Startup Sequence

There is no explicit `@app.on_event("startup")` handler. The graph is built lazily on first request. The application can be started with:
```
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
```
Or via the Heroku `Procfile`:
```
web: uvicorn backend.api.app:app --host 0.0.0.0 --port $PORT
```

---

## 6. Configuration System

### Settings Loading (`config/settings.py`)

Uses `pydantic-settings` BaseSettings to load from `.env`:

```python
class Settings(BaseSettings):
    groq_api_key: str = ""
    tavily_api_key: str = ""
    langchain_api_key: str = ""
    langchain_project: str = "TripPlanner"
    langchain_tracing: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    groq_text_model: str = "openai/gpt-oss-20b"
    groq_transcription_model: str = "whisper-large-v3"
    kiwi_mcp_server_url: str = "https://mcp.kiwi.com"
    weather_provider: str = "livedatalink"
    weather_mcp_server_url: str = "https://livedatalink.ai/mcp"
    agentorist_mcp_server_url: str = "https://mcp.agentorist.com/mcp"
    recordings_dir: str = "recordings"
    outputs_dir: str = "outputs"
    logs_dir: str = "logs"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

The `.env` file path is resolved as `PROJECT_ROOT / ".env"` where `PROJECT_ROOT` is the parent of `config/`.

### Caching

`get_settings()` is wrapped with `@lru_cache(maxsize=None)` so settings are loaded once per process. Side effects: the function also sets `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT`, and `LANGCHAIN_API_KEY` environment variables for LangSmith tracing.

### Complete Configuration Options

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | `""` | API key for Groq LLM and transcription |
| `TAVILY_API_KEY` | For search | `""` | API key for Tavily web search |
| `LANGCHAIN_API_KEY` | No | `""` | LangSmith tracing API key |
| `LANGCHAIN_PROJECT` | No | `"TripPlanner"` | LangSmith project name |
| `LANGCHAIN_TRACING` | No | `true` | Enable LangSmith tracing |
| `LANGCHAIN_ENDPOINT` | No | `"https://api.smith.langchain.com"` | LangSmith endpoint |
| `GROQ_TEXT_MODEL` | No | `"openai/gpt-oss-20b"` | Groq chat model |
| `GROQ_TRANSCRIPTION_MODEL` | No | `"whisper-large-v3"` | Groq audio model |
| `KIWI_MCP_SERVER_URL` | For flights | `"https://mcp.kiwi.com"` | Kiwi MCP server |
| `WEATHER_PROVIDER` | No | `"livedatalink"` | Weather provider label |
| `WEATHER_MCP_SERVER_URL` | For weather | `"https://livedatalink.ai/mcp"` | LiveDataLink MCP server |
| `AGENTORIST_MCP_SERVER_URL` | For hotels | `"https://mcp.agentorist.com/mcp"` | Agentorist MCP server |
| `RECORDINGS_DIR` | No | `"recordings"` | Audio recording directory |
| `OUTPUTS_DIR` | No | `"outputs"` | Text output directory |
| `LOGS_DIR` | No | `"logs"` | Log directory |

### Model Helpers (`config/models.py`)

- `get_text_llm()`: Returns `ChatGroq(api_key, model=groq_text_model, temperature=0.2)` — used by all agents.
- `get_groq_client()`: Returns native `Groq(api_key)` — used for audio transcription.
- `transcribe_audio(audio_path)`: Reads binary audio file, sends to Groq Whisper API, returns transcribed text. Handles `FileNotFoundError`, `OSError`, and `APIError`.

---

## 7. LangGraph Architecture

### Graph Construction (`graph/trip_graph.py`)

The graph is built in `build_trip_graph()`:

```python
def build_trip_graph():
    graph = StateGraph(TripPlannerState)
    
    # Register all 8 nodes with debug wrappers
    graph.add_node("coordinator_agent", coordinator_agent)
    graph.add_node("supervisor_agent", supervisor_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("search_agent", search_agent)
    graph.add_node("local_agent", local_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    
    # Fixed edges
    graph.add_edge(START, "coordinator_agent")
    graph.add_edge("coordinator_agent", "supervisor_agent")
    graph.add_edge("itinerary_agent", END)

    # Supervisor → parallel fan-out via Send()
    # Returns list of Send() for enabled parallel agents,
    # or "search_agent" string to skip to sequential chain.
    graph.add_conditional_edges("supervisor_agent",
        _route_from_supervisor, _ALL_AGENT_ROUTES)

    # Fan-in: all parallel agents converge to search_agent
    graph.add_edge("flight_agent", "search_agent")
    graph.add_edge("hotel_agent", "search_agent")
    graph.add_edge("weather_agent", "search_agent")

    # Sequential chain after fan-in (with skip support)
    graph.add_conditional_edges("search_agent",
        _make_route_after("search_agent"), _ALL_AGENT_ROUTES)
    graph.add_conditional_edges("local_agent",
        _make_route_after("local_agent"), _ALL_AGENT_ROUTES)

    checkpointer = get_checkpointer()
    return graph.compile(checkpointer=checkpointer)
```

### Nodes (8 total)

| Node | Function | Purpose |
|---|---|---|
| `coordinator_agent` | `coordinator()` | Validate required fields, initialize defaults |
| `supervisor_agent` | `supervisor_agent()` | Validate, build execution plan, generate notes |
| `flight_agent` | `flight_agent()` | Search Kiwi MCP, summarize with LLM |
| `hotel_agent` | `hotel_agent()` | Search Agentorist MCP, summarize with LLM |
| `weather_agent` | `weather_agent()` | Get LiveDataLink weather, summarize with LLM |
| `search_agent` | `search_agent()` | Tavily search, summarize with LLM |
| `local_agent` | `local_agent()` | Agentorist local search, summarize with LLM |
| `itinerary_agent` | `itinerary_agent()` | Synthesize all notes, generate report |

### Edges

**Fixed edges:**
- `START → coordinator_agent` — Always first.
- `coordinator_agent → supervisor_agent` — Always second.
- `itinerary_agent → END` — Always last.

**Conditional edges from supervisor (parallel fan-out via Send()):**
- Function: `_route_from_supervisor(state)`
- Logic: Iterates through `_PARALLEL_AGENTS = ["flight_agent", "hotel_agent", "weather_agent"]` and checks `state["execution_plan"][f"run_{agent}"]`.
- Returns a **list of Send(node, state)** objects — one per enabled agent. LangGraph executes these in parallel.
- If none of the three are enabled, returns the string `"search_agent"` (skip directly to sequential chain).

**Fan-in: parallel agents converge to search_agent:**
- `flight_agent → search_agent` (add_edge)
- `hotel_agent → search_agent` (add_edge)
- `weather_agent → search_agent` (add_edge)
- search_agent runs only once, after ALL parallel branches complete. If a branch did not run (agent disabled), its edge does not block the fan-in.

**Sequential chain after fan-in (with skip support):**
- Function: `_make_route_after(agent_name)` — creates a closure that scans the remaining sequential agents.
- Used for `search_agent` and `local_agent`. Returns `"itinerary_agent"` when no more need to run.

### Execution Lifecycle

```
START
  │
  ▼
coordinator_agent  ──→  supervisor_agent
                              │
                              ▼
              ┌── _route_from_supervisor() (Send) ──┐
              │              │              │       │
         (flight OK)  (hotel OK)  (weather OK)  (none)
              │              │              │       │
         ┌────┘              │              └────┐  │
         ▼                   ▼                   ▼  │
  flight_agent         hotel_agent        weather  │
   (parallel)          (parallel)         (par.)   │
         │                   │                   │  │
         └───────────────────┼───────────────────┘  │
                             │ (fan-in)             │
                             ▼                      │
                       search_agent ◄────────────────┘
                             │
                             ▼ (conditional)
                       local_agent ──→ itinerary_agent ──→ END
```

### Routing Map

```
_ALL_AGENT_ROUTES = {
    "flight_agent":   "flight_agent",
    "hotel_agent":    "hotel_agent",
    "weather_agent":  "weather_agent",
    "search_agent":   "search_agent",
    "local_agent":    "local_agent",
    "itinerary_agent": "itinerary_agent",
}
```

Every routing function must return one of these keys. The dictionary maps return values to registered node names (in this case they are identical).

### Checkpointing

The graph is compiled with `checkpointer=SqliteSaver` from `memory/sqlite_checkpoint.py`. After every node execution, LangGraph automatically persists the full state to the SQLite database.

---

## 8. State Management

### TripPlannerState (`state/trip_state.py`)

Defined as a `TypedDict` with 30 fields:

```python
class TripPlannerState(TypedDict):
    # ── Input fields ──
    origin: str               # Departure city/airport
    destination: str          # Arrival city/area
    travelers: int            # Number of travelers
    venue: str                # Venue or event location
    event_date: str           # Event date in YYYY-MM-DD
    
    # ── Flight agent ──
    flight_details: dict      # Raw flight search response
    flight_notes: str         # Formatted flight info + LLM summary
    flight_status: str        # "completed" | "failed"
    
    # ── Hotel agent ──
    hotel_details: dict       # Raw hotel search response
    hotel_notes: str          # Formatted hotel info + LLM summary
    hotel_status: str         # "completed" | "failed"
    
    # ── Weather agent ──
    weather_details: dict     # Raw weather response
    weather_notes: str        # LLM weather summary
    weather_status: str       # "completed" | "failed"
    
    # ── Search agent ──
    search_results: dict      # Raw Tavily search response
    search_notes: str         # LLM search summary
    search_status: str        # "completed" | "failed"
    
    # ── Local agent ──
    local_results: dict       # Raw Agentorist local response
    local_notes: str          # LLM local summary
    local_status: str         # "completed" | "failed"
    
    # ── Itinerary ──
    itinerary: str            # Generated day-by-day itinerary
    itinerary_status: str     # "completed" | "failed"
    
    # ── Supervisor ──
    supervisor_notes: str     # LLM summary of the plan
    execution_plan: dict      # Which agents to run (flags)
    
    # ── Booking / pricing ──
    flight_booking_link: str       # Selected flight booking URL
    hotel_booking_links: list[str]  # All hotel booking URLs
    hotel_price_details: list[str]  # Structured hotel price info
    recommended_flight_price: float  # Selected flight price
    recommended_hotel_price: float   # (deprecated)
    
    # ── Workflow ──
    status: str               # overall workflow status
    errors: list[str]         # accumulated error messages
    final_report: str         # Final Markdown travel report
```

### Field Lifecycle

| Field | Producer | Consumer | Lifecycle |
|---|---|---|---|
| `origin`, `destination`, `travelers`, `venue`, `event_date` | Request parser / user | All agents | Set once at start, read-only downstream |
| `execution_plan` | Supervisor | Graph routing functions | Set by supervisor, consumed by conditional edges |
| `supervisor_notes` | Supervisor | Itinerary agent, report | Set by supervisor LLM |
| `flight_details`, `flight_notes`, `flight_status` | Flight agent | Itinerary agent, report | Set by flight_agent node |
| `hotel_details`, `hotel_notes`, `hotel_status` | Hotel agent | Itinerary agent, report | Set by hotel_agent node |
| `weather_details`, `weather_notes`, `weather_status` | Weather agent | Itinerary agent, report | Set by weather_agent node |
| `search_results`, `search_notes`, `search_status` | Search agent | Itinerary agent, report | Set by search_agent node |
| `local_results`, `local_notes`, `local_status` | Local agent | Itinerary agent, report | Set by local_agent node |
| `itinerary`, `itinerary_status` | Itinerary agent | Report formatter | Set by itinerary_agent node |
| `final_report` | Report formatter | API response | Last field set, returned to caller |
| `status` | Multiple nodes | API response | Progresses: collecting → processing → completed/failed/blocked |
| `errors` | All nodes | API response, debugging | Accumulated across all nodes |
| Booking fields | Flight/hotel agents | Report formatter | Set during flight and hotel agent execution |

### State Evolution

1. **Initial state** — Created by `build_trip_state()` with only input fields, empty errors, zero booking fields.
2. **coordinator_agent** — Adds domain field defaults, sets `status = "processing"`.
3. **supervisor_agent** — Adds `execution_plan` dict, `supervisor_notes`, default empty dicts for all domains, may set `status = "blocked"` if validation fails.
4. **Each specialist agent** — Overwrites its domain fields (e.g., `flight_details`, `flight_notes`, `flight_status`).
5. **itinerary_agent** — Sets `itinerary`, `final_report`, `status = "completed"` or `"failed"`.

### Error Handling Pattern

Each agent copies `errors = list(state.get("errors") or [])`, appends error messages on failure, and writes back `state["errors"] = errors`. Errors are never cleared, only appended.

---

## 9. Supervisor Agent (`agents/supervisor_agent.py`)

### Purpose

The supervisor is the **orchestrator** of the multi-agent workflow. It validates input, initializes state defaults, builds the execution plan, and generates contextual notes for downstream agents.

### Responsibilities

1. **Validate required fields** — Checks that `destination`, `venue`, and `event_date` are present. If any are missing, appends validation errors and sets status to `"blocked"`.
2. **Initialize default state** — Ensures every domain field exists (even if empty) to prevent KeyError in downstream agents.
3. **Build execution plan** — Generates a dict with boolean flags `run_flight_agent`, `run_hotel_agent`, `run_weather_agent`, `run_search_agent`, `run_local_agent`. Each flag is `True` if the corresponding domain data is not already present in state (enables conditional skipping on resume).
4. **Generate supervisor notes** — Uses Groq LLM to analyze the trip request and current state, producing a textual summary that explains why the execution plan makes sense and calls out any missing details.
5. **State sanitization** — Removes deprecated keys (`recommended_hotel_price`, `hotel_price`, `hotel_price_details_numeric`) before passing state to the LLM to avoid confusing the model with stale numeric data.

### Inputs

- Full `TripPlannerState` dict

### Outputs

- `supervisor_notes` (str) — LLM-generated contextual summary
- `execution_plan` (dict) — `{"run_flight_agent": bool, "run_hotel_agent": bool, ...}`
- Domain defaults — All domain fields initialized to `{}` or `""`
- `status` — May be set to `"blocked"` on validation failure, `"degraded"` on LLM failure

### LLM Usage

- Model: `ChatGroq` with `openai/gpt-oss-20b`
- System prompt: Provides context about the multi-agent trip planner, instructions on summarizing hotel info using price categories (not numeric prices).
- User prompt: Includes the execution plan, hotel summary (built from structured price details), and full sanitized state.

### Interaction with Graph

The supervisor's `execution_plan` is consumed by the conditional routing functions `_route_from_supervisor` and `_make_route_after` to determine which agent to execute next.

### Failure Handling

If the LLM call fails, the supervisor:
- Appends `"supervisor planning failed: {error}"` to `errors[]`
- Sets `supervisor_notes` to a fallback string
- Sets `status = "degraded"`
- Continues execution (does not block)

---

## 10. Every Specialist Agent

### 10.1 Request Parser Agent (`agents/request_parser_agent.py`)

**Purpose:** Extracts structured trip fields from natural language input.

**Not a graph node** — called before graph execution by the API route and service layer.

**Inputs:** `user_request: str` (e.g., "I want to fly from Mumbai to Delhi on 2026-07-15 for a concert at the Dome.")

**Outputs:** `dict` with keys `origin`, `destination`, `travelers`, `venue`, `event_date` (normalized strings, `None` → `""`)

**Process:**
1. Creates a LangChain `create_agent` with Groq LLM and no tools.
2. System prompt: "You are a request parsing agent. Extract structured details... Return only JSON..."
3. Invokes agent with `"Extract the trip details and respond with JSON only.\n\nrequest: {user_request}"`.
4. `_extract_json_payload()` extracts JSON from the response using three strategies: direct `json.loads()`, markdown code block regex extraction, or finding `{...}` boundaries.
5. Each field is normalized: trimmed, with `none`/`null`/`n/a`/`unknown` converted to empty string.
6. `_normalize_travelers()` handles string digits, word numbers (one-ten), floats, booleans.

**LLM usage:** Yes — one call per request.
**Tools used:** None.
**Failure handling:** Raises `ValueError` on empty input or unparseable JSON.

---

### 10.2 Coordinator Agent (`agents/coordinator.py`)

**Purpose:** Validates required inputs and initializes missing state fields.

**Graph node:** Position 1 (START → coordinator_agent).

**Inputs:** Full `TripPlannerState` (initial state).

**Outputs:**
- Validation errors for `destination`, `venue`, `event_date`
- Initialized default dicts for all domain fields
- `status = "processing"`

**LLM usage:** Creates an LLM agent but does not actually invoke it (the agent object is constructed but `invoke()` is never called). This appears to be a placeholder for future use.

**Failure handling:** Appends error strings to `errors[]` for missing required fields.

**Note:** The coordinator creates an LLM agent but never calls it — currently a no-op skeleton that only validates fields.

---

### 10.3 Supervisor Agent (already covered in Section 9)

---

### 10.4 Flight Agent (`agents/flight_agent.py`)

**Purpose:** Search for flights via Kiwi MCP, parse results, select the best option, and generate a structured recommendation.

**Graph node:** Position 2-6 (conditional routing after supervisor).

**Inputs from state:** `origin`, `destination`, `event_date`, `travelers`.

**Outputs to state:**
- `flight_details` (dict) — Raw Kiwi MCP response
- `flight_notes` (str) — Formatted flight information with LLM recommendation
- `flight_status` (str) — `"completed"` or `"failed"`
- `flight_booking_link` (str) — Booking URL of selected flight
- `recommended_flight_price` (float) — Price of selected flight

**Process:**
1. Calls `tools/flight_tools.search_flights(origin, destination, event_date, travelers)`.
2. If search fails (status != "success"), sets `flight_status = "failed"` and returns.
3. `parse_flight_data()` extracts the JSON flight list from the MCP response's `content[]` array.
4. Limits to first 5 flights.
5. Builds a text summary of available flights for the LLM.
6. Extracts default booking link and price from the first flight.
7. Creates a LangChain agent with Groq LLM and no tools.
8. System prompt: "You are a flight planning agent... select the best option... Output summary MUST contain exactly these fields in markdown: Recommended Flight, Route, Departure, Arrival, Price, Booking Link."
9. LLM response is post-processed: extracts first URL from response for `flight_booking_link`, parses price with regex.
10. `_format_flight_notes()` builds the final structured notes by iterating over the parsed flight list, deduplicating, and formatting each flight with route, times, duration, price, booking link, and layover info.

**LLM usage:** Yes — one call to select the best flight and generate recommendation text.
**Tools used:** `search_flights()` (Kiwi MCP).
**Failure handling:** Catches all exceptions, appends error, sets status to `"failed"`.

---

### 10.5 Hotel Agent (`agents/hotel_agent.py`)

**Purpose:** Search for hotels via Agentorist MCP, extract structured results, and generate LLM-powered recommendations.

**Graph node:** Position 2-6 (conditional routing).

**Inputs from state:** `destination`, `venue`, `event_date`, `travelers`, optional `budget` and `hotel_preferences`.

**Outputs to state:**
- `hotel_details` (dict) — Raw Agentorist response
- `hotel_notes` (str) — Structured hotel info with LLM recommendations
- `hotel_status` (str) — `"completed"` or `"failed"`
- `hotel_booking_links` (list[str]) — All booking URLs found
- `hotel_price_details` (list[dict]) — Structured data: `{hotel, price_category, rating}`

**Process:**
1. Calls `tools/hotel_tools.search_hotels(destination)`.
2. If search fails, returns early with `hotel_status = "failed"`.
3. Extracts `results` array from MCP response, iterates to collect booking links and price details.
4. Builds a structured MCP summary block with hotel names, ratings, price categories, addresses, and links.
5. Creates a LangChain agent with strict instructions: "Only use information that exists in the provided MCP data. Do not invent hotel prices. Do not convert price categories into nightly rates."
6. LLM generates recommendations based on reputation, location, venue proximity, and traveler preferences.
7. `_format_hotel_notes()` produces the final structured notes by iterating results, deduplicating by name+address, formatting each hotel with name, rating, address, price category, booking link, and notes.

**LLM usage:** Yes — one call to generate hotel recommendations from the MCP data.
**Tools used:** `search_hotels()` (Agentorist MCP).
**Failure handling:** Catches all exceptions, appends error, sets status to `"failed"`.

---

### 10.6 Weather Agent (`agents/weather_agent.py`)

**Purpose:** Fetch weather forecast and air quality data via LiveDataLink MCP, then generate a structured LLM summary covering forecast, historical expectations, air quality, and travel advice.

**Graph node:** Position 2-6 (conditional routing).

**Inputs from state:** `destination`, `event_date`.

**Outputs to state:**
- `weather_details` (dict) — Combined weather result (forecast + optional air quality)
- `weather_notes` (str) — LLM weather summary in structured markdown
- `weather_status` (str) — `"completed"` or `"failed"`

**Process:**
1. Calls `tools/weather_tools.get_weather(destination, event_date)`.
2. If no date provided, falls back to current weather only.
3. If weather fails, returns early with `weather_status = "failed"`.
4. Creates a LangChain agent with a detailed system prompt specifying the exact markdown output structure (Forecast Summary, Historical Expectations, Air Quality, Travel Advice).
5. The prompt includes instructions for handling dates beyond the 16-day forecast range by providing historical climate expectations.

**LLM usage:** Yes — one call to analyze and summarize weather data.
**Tools used:** `get_weather()` (wraps LiveDataLink MCP tools).
**Failure handling:** Catches exceptions, appends error, sets status to `"failed"`.

---

### 10.7 Search Agent (`agents/search_agent.py`)

**Purpose:** Perform destination research via Tavily web search, extracting attractions, restaurants, transportation options, and local tips.

**Graph node:** Position 2-6 (conditional routing).

**Inputs from state:** `destination`, `venue`, optional `interests` and `trip_style`.

**Outputs to state:**
- `search_results` (dict) — Raw Tavily response (the full LLM response dict)
- `search_notes` (str) — Structured markdown with highlights, restaurants, transport, tips
- `search_status` (str) — `"completed"` or `"failed"`

**Process:**
1. Creates a LangChain agent with `search_web` as a registered tool (one of only two agents that uses tools).
2. System prompt enforces that the agent must NOT output flights, hotels, itinerary planning, or booking advice.
3. Output must follow a strict markdown structure: Venue Highlights, Top Attractions, Recommended Restaurants, Transportation Options, Local Tips.
4. The LLM is instructed to call `search_web` to gather data.

**LLM usage:** Yes — one call that includes tool invocation.
**Tools used:** `search_web()` (Tavily), registered as a tool in the LangChain agent.
**Failure handling:** Catches exceptions, appends error, sets status to `"failed"`.

---

### 10.8 Local Agent (`agents/local_agent.py`)

**Purpose:** Discover local places near the destination using the Agentorist MCP `search_local_places` tool.

**Graph node:** Position 2-6 (conditional routing, last in execution order).

**Inputs from state:** `destination`, `venue`.

**Outputs to state:**
- `local_results` (dict) — Raw Agentorist response
- `local_notes` (str) — LLM summary
- `local_status` (str) — `"completed"` or `"failed"`

**Process:**
1. Creates a LangChain agent with `search_local_places` registered as a tool.
2. The agent decides whether to call the tool and summarizes recommendations.

**LLM usage:** Yes — one call with tool invocation capability.
**Tools used:** `search_local_places()` (Agentorist MCP).
**Failure handling:** Catches exceptions, appends error, sets status to `"failed"`.

---

### 10.9 Itinerary Agent (`agents/itinerary_agent.py`)

**Purpose:** Synthesize all agent outputs into a coherent day-by-day travel itinerary, then trigger report formatting.

**Graph node:** Position 7 (itinerary_agent → END).

**Inputs from state:** All agent notes (`flight_notes`, `hotel_notes`, `weather_notes`, `search_notes`, `supervisor_notes`) plus `destination`, `venue`, `event_date`.

**Outputs to state:**
- `itinerary` (str) — LLM-generated day-by-day itinerary
- `itinerary_notes` (str) — Copy of the itinerary
- `itinerary_status` (str) — `"completed"` or `"failed"`
- `final_report` (str) — Markdown travel report (from `report_formatter_agent`)
- `status` (str) — `"completed"` or `"failed"`

**Process:**
1. Creates a LangChain agent with no tools.
2. System prompt: "You are an itinerary planning agent. Create a complete travel itinerary... Include arrival recommendations, hotel check-in suggestions, event-day guidance, local highlights, dining recommendations, and return-trip planning."
3. User prompt includes all agent notes concatenated.
4. After LLM response, calls `report_formatter_agent(updated_state)` to produce the final Markdown report.
5. Sets `status = "completed"` on success.

**Fallback:** If the LLM call fails, `_build_fallback_itinerary()` assembles a non-empty itinerary from whatever state fields are available.

**LLM usage:** Yes — one call for itinerary generation.
**Tools used:** None (but calls `report_formatter_agent` directly as a Python function).
**Failure handling:** On exception, uses fallback itinerary builder, still calls `report_formatter_agent`, sets `status = "failed"`.

---

### 10.10 Report Formatter Agent (`agents/report_formatter_agent.py`)

**Purpose:** Deterministically assemble a professional Markdown travel report from state fields. **No LLM is used.**

**Not a graph node** — called internally by `itinerary_agent` as a Python function.

**Inputs:** Full `TripPlannerState` dict.

**Outputs:** `{"final_report": str}` — the complete Markdown document.

**Process:**

The formatter parses structured sections from the text-based agent notes and assembles them in a fixed order:

```
_SECTION_ORDER = [
    "exec_summary",       # Executive Summary
    "trip_overview",      # Trip Overview (table)
    "rec_flight",         # ⭐ Recommended Flight
    "other_flights",      # Other Available Flights
    "rec_hotels",         # ⭐ Recommended Hotels
    "add_hotels",         # Additional Hotel Options
    "weather_summary",    # Weather Summary
    "weather_details",    # Weather Details (Historical, Air Quality, Travel Advice)
    "highlights",         # Local Highlights
    "restaurants",        # Restaurants
    "transportation",     # Transportation
    "itinerary",          # Day-wise Itinerary
    "quick_links",        # Quick Links (booking links)
    "next_steps",         # Next Steps (checklist)
]
```

**Key implementation details:**
- `_parse_flight_notes()`: Splits flight_notes text by "Flight N" headings, separates "Agent Recommendation Notes:" trailer.
- `_parse_hotel_notes()`: Splits hotel_notes text by "Hotel N" headings, separates "Additional Recommendation Notes:" trailer.
- `_format_weather()`: Extracts subsections from weather_notes using heading-based text extraction (Forecast Summary, Historical Expectations, Air Quality, Travel Advice).
- `_format_local()`: Extracts Top Attractions, Recommended Restaurants, Transportation Options, and Local Tips from search_notes.
- `_collect_booking_links()`: Aggregates flight and hotel booking URLs from state fields and also scrapes from flight_notes text.
- `_clean_text()`: Removes duplicate non-empty lines while preserving order.
- Each section is only included if non-empty.

---

## 11. Tool Architecture

Every tool follows the same design pattern:

1. **Async core** — MCP clients use `asyncio` with `mcp.ClientSession`.
2. **Sync bridge** — `_run_coroutine()` bridges async→sync by either calling `asyncio.run()` or spawning a daemon thread with a new event loop.
3. **Standardized return format** — All tools return a dict with keys: `status` ("success" | "error"), `provider` (name string), `tool_used` (string), `data` (result payload), `error` (error message if failed).
4. **Error handling** — Timeouts, connection errors, tool execution errors, and empty results are all caught and returned as error dicts. Exceptions are never propagated to the agent.

### 11.1 Flight Tools (`tools/flight_tools.py`)

**Purpose:** Kiwi MCP flight search.

**Tool name on MCP server:** `search-flight`

**Function:** `search_flights(origin, destination, event_date, travelers) → dict`

**Input:**
- `origin` (str) — IATA code or city name
- `destination` (str) — IATA code or city name
- `event_date` (str) — YYYY-MM-DD, converted to DD/MM/YYYY for Kiwi
- `travelers` (int) — number of passengers

**MCP Payload:**
```python
{
    "flyFrom": origin,
    "flyTo": destination,
    "departureDate": departure_date,  # DD/MM/YYYY
}
```

**Connection flow:**
1. Normalize URL (strip trailing slash).
2. If URL ends with `/sse`, use SSE transport (`sse_client` → `ClientSession`).
3. Otherwise, use Streamable HTTP transport (`streamable_http_client` → `ClientSession`).
4. Initialize session with 20-second timeout.
5. List tools, verify `search-flight` exists.
6. Match payload against tool's `inputSchema` properties — strip keys not in schema.
7. Validate required fields in schema against payload.
8. Call tool, await result.

**Response parsing:**
1. Check `result.isError` — return error dict if true.
2. `_serialize_tool_result()` converts `CallToolResult` content array to serializable dict entries (TextContent, ImageContent, EmbeddedResource).
3. Limit content entries to first 5.

**Error handling:**
- `_flatten_exceptions()`: Recursively unwraps `ExceptionGroup`-style nested exceptions.
- `_format_exception_details()`: Produces detailed diagnostics including nested exception tree.
- Catches `asyncio.TimeoutError` and all other `Exception`.
- Returns error dict with `status: "error"`, detailed error string, and empty data.

**Used by:** `flight_agent`

---

### 11.2 Hotel Tools (`tools/hotel_tools.py`)

**Purpose:** Agentorist MCP hotel and local place search.

**Tool name on MCP server:** `search`

**Functions:**
- `search_hotels(destination) → dict`
- `search_local_places(destination, venue) → dict`

**MCP Payload (hotels):**
```python
{
    "vertical": "local",
    "query": "best hotels",
    "location": destination,
    "agent_client": "TripPlanner",
}
```

**MCP Payload (local):**
```python
{
    "vertical": "local",
    "query": f"best places near {query_target}",
    "location": destination,
    "agent_client": "TripPlanner",
}
```

**Connection flow:** Identical pattern to flight_tools but with a 20-second timeout and tool name "search".

**Response parsing:**
1. Check `result.isError`.
2. `_extract_structured_results()`: Prefers `structuredContent` if present, otherwise serializes content array.
3. `_is_empty_results()`: Checks `result_count` (int) or `results` (list) emptiness.
4. If empty results, returns error with `"No hotel results returned."`.
5. Limits results to first 5.

**Used by:** `hotel_agent`, `local_agent`

---

### 11.3 Weather MCP Client (`tools/weather_mcp_client.py`)

**Purpose:** Low-level LiveDataLink MCP client for weather data.

**Tool names on MCP server:** `weather_current`, `weather_forecast`, `air_quality`

**Functions:**
- `get_current_weather(location) → dict`
- `get_weather_forecast(location, days) → dict`
- `get_air_quality(location) → dict`

**MCP Payload (forecast):**
```python
{"location": location, "days": days}
```

**Connection flow:**
1. Uses Streamable HTTP transport only (`streamable_http_client`).
2. Session initialization + tool listing + tool call.

**Response parsing:**
- `_extract_text()`: Collects all `TextContent` entries from the result's content array, concatenates with newlines.
- `_handle_response()`: Checks `result.isError`, extracts text, returns standardized dict.
- Returns text data as a string in the `data` field (not structured JSON).

**Used by:** `weather_tools.py` (wrapper)

---

### 11.4 Weather Tools (`tools/weather_tools.py`)

**Purpose:** High-level weather logic wrapper combining forecast, air quality, and date calculations.

**Function:** `get_weather(destination, event_date) → dict`

**Logic:**
1. If `event_date` is None: fetches current weather only.
2. Parses `event_date` as YYYY-MM-DD, calculates days until event.
3. Clamps forecast days to range [1, 16].
4. Fetches weather forecast (required) — failure fails the whole request.
5. Fetches air quality (optional) — failure does not fail the overall request; error is preserved in the response.

**Used by:** `weather_agent`

---

### 11.5 Tavily Search (`tools/tavily_search.py`)

**Purpose:** Web search for destination research.

**Function:** `search_web(query, max_results=5) → dict`

**Process:**
1. Checks `TAVILY_API_KEY` is configured.
2. Creates `TavilyClient(api_key)`.
3. Retries up to 3 times with exponential backoff (`time.sleep(attempt)`).
4. Returns structured dict with `query`, `results` (list), and optional `error`.

**Used by:** `search_agent` (registered as a LangChain tool)

---

## 12. MCP Integration

### Protocol

The system uses the **Model Context Protocol (MCP)** for three external integrations. MCP provides a standardized way for LLM applications to discover and call external tools.

### MCP Connection Lifecycle

```
1. Connect to server URL
       │
       ▼
2. Create ClientSession(read_stream, write_stream)
       │
       ▼
3. session.initialize()  ─── negotiate protocol version
       │
       ▼
4. session.list_tools()  ─── discover available tools
       │
       ▼
5. Find target tool by name
       │
       ▼
6. Prepare payload against tool.inputSchema
       │
       ▼
7. session.call_tool(tool_name, payload)
       │
       ▼
8. Parse CallToolResult content[]
       │
       ▼
9. Return standardized dict
```

### Transport Protocols

| Protocol | Used By | Detection |
|---|---|---|
| SSE (`sse_client`) | Kiwi, Agentorist | URL ends with `/sse` |
| Streamable HTTP (`streamable_http_client`) | Kiwi, Agentorist, LiveDataLink | Default if not SSE |

### Async-to-Sync Bridging

Since LangGraph nodes are synchronous Python functions but MCP clients use `asyncio`, the `_run_coroutine()` helper handles the bridge:

```python
def _run_coroutine(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)  # No running loop → run directly
    
    # Running loop exists → spawn daemon thread with new loop
    def _runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_container["result"] = loop.run_until_complete(coro)
    
    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    return result_container["result"]
```

### Timeouts

All MCP operations use a **20-second default timeout** applied via `asyncio.wait_for()` on `session.initialize()`, `session.list_tools()`, and `session.call_tool()`.

### Retry Logic

No explicit retry logic at the MCP client layer. If a tool call fails (timeout, connection error, tool error), the error is returned to the agent, which records it in `errors[]` and marks that domain as `"failed"`.

### MCP Server Inventory

| Server | Tools | Data Format |
|---|---|---|
| **Kiwi** (mcp.kiwi.com) | `search-flight` | Structured JSON in TextContent |
| **Agentorist** (mcp.agentorist.com/mcp) | `search` | Structured JSON in TextContent or structuredContent |
| **LiveDataLink** (livedatalink.ai/mcp) | `weather_current`, `weather_forecast`, `air_quality` | Plain text tables |

---

## 13. External Services

### Groq

- **Purpose:** LLM provider for all agent reasoning, request parsing, and itinerary generation.
- **Usage location:** `config/models.py` — `get_text_llm()` returns `ChatGroq` used by every agent. `get_groq_client()` returns native client for audio transcription.
- **Model:** `openai/gpt-oss-20b` (configurable via `GROQ_TEXT_MODEL` env var)
- **Temperature:** 0.2 (consistent across all agents)
- **Returned data:** Chat completions with message content, used for JSON extraction (request parser) or markdown text (all other agents).

### Tavily

- **Purpose:** Web search for destination research (attractions, restaurants, transit, local tips).
- **Usage location:** `tools/tavily_search.py` — called by `search_agent`.
- **API:** REST API via `TavilyClient.search()`.
- **Returned data:** `{"results": [{"title": ..., "url": ..., "content": ...}, ...]}`
- **Retry:** 3 attempts with linear backoff.

### Kiwi MCP Server

- **Purpose:** Flight search — routes, prices, times, layovers, booking links.
- **Usage location:** `tools/flight_tools.search_flights()` — called by `flight_agent`.
- **Protocol:** MCP (SSE or Streamable HTTP).
- **Tools used:** `search-flight`.
- **Input:** `flyFrom`, `flyTo`, `departureDate`.
- **Output:** Structured JSON with flight arrays containing price, departure/arrival times, layovers, deep links, currency.

### Agentorist MCP Server

- **Purpose:** Hotel and local place search.
- **Usage location:** `tools/hotel_tools.search_hotels()` and `search_local_places()` — called by `hotel_agent` and `local_agent`.
- **Protocol:** MCP (SSE or Streamable HTTP).
- **Tools used:** `search`.
- **Input:** `vertical`, `query`, `location`, `agent_client`.
- **Output:** Structured results with `results[]` array containing `name`, `rating`, `price` (category), `address`, `booking_url`, `yelp_url`, `phone`, `categories`, `review_count`, `distance`.

### LiveDataLink MCP Server

- **Purpose:** Weather forecast and air quality data.
- **Usage location:** `tools/weather_mcp_client.py` (low-level), `tools/weather_tools.py` (high-level) — called by `weather_agent`.
- **Protocol:** MCP (Streamable HTTP only).
- **Tools used:** `weather_current`, `weather_forecast`, `air_quality`.
- **Input:** `location` (and `days` for forecast).
- **Output:** Plain text tables with forecast date range, high/low temps, conditions, rain probability, wind; air quality with AQI, PM2.5, PM10, Ozone, NO2, SO2, CO.

### LangSmith

- **Purpose:** Optional tracing and monitoring of LLM calls and agent executions.
- **Usage location:** `config/settings.get_settings()` sets environment variables `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT`, `LANGCHAIN_API_KEY`.
- **Status:** Optional — enabled only when `LANGCHAIN_API_KEY` is configured.

---

## 14. API Documentation

### Endpoint: Health Check

| Property | Value |
|---|---|
| **Method** | `GET` |
| **Route** | `/api/trips/health` |
| **Summary** | Health check |
| **Description** | Returns a simple health indicator to confirm the API is running and reachable. |

**Request:** None

**Response (200):** `HealthResponse`
```json
{"status": "healthy"}
```

---

### Endpoint: Plan a Trip

| Property | Value |
|---|---|
| **Method** | `POST` |
| **Route** | `/api/trips/plan` |
| **Summary** | Plan a new trip |
| **Description** | Accepts structured trip details or natural language. Parses sentence via LLM, invokes multi-agent graph, returns markdown report. |

**Request Model:** `TripPlanRequest`

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `origin` | `str \| None` | Conditional | min_length=3 | Departure airport/city IATA code |
| `destination` | `str \| None` | Conditional | min_length=3 | Arrival airport/city IATA code |
| `event_date` | `str \| None` | Conditional | pattern=YYYY-MM-DD | Travel date |
| `venue` | `str \| None` | Conditional | min_length=1 | Venue/event name |
| `sentence` | `str \| None` | Conditional | min_length=10 | Natural language request |

**Validation:** Either `sentence` must be provided, OR all four structured fields (`origin`, `destination`, `event_date`, `venue`) must be provided. Implemented via Pydantic `model_validator`.

**Response Model:** `TripPlanResponse`

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether graph completed without top-level error |
| `report` | `str` | Markdown travel report |
| `itinerary` | `str` | Day-by-day itinerary in markdown |
| `destination` | `str` | Destination from request |
| `event_date` | `str` | Event date from request |

**Errors:**
- **422:** Validation error (missing fields, invalid format)
- **500:** Graph execution failure

---

### Endpoint: Get Trip State

| Property | Value |
|---|---|
| **Method** | `GET` |
| **Route** | `/api/trips/{thread_id}` |
| **Summary** | Get trip state by thread ID |
| **Description** | Retrieves persisted internal state of a previously executed trip-planning run. |

**Path Parameters:**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `thread_id` | `str` | min_length=1 | Unique thread identifier |

**Response Model:** `TripStateResponse`

| Field | Type | Description |
|---|---|---|
| `thread_id` | `str` | Trip session identifier |
| `status` | `str` | Workflow status (pending, running, completed, failed, not_found) |
| `state` | `dict` | Full internal state dictionary |

---

### Endpoint: Resume Trip

| Property | Value |
|---|---|
| **Method** | `POST` |
| **Route** | `/api/trips/{thread_id}/resume` |
| **Summary** | Resume a trip-planning run |
| **Description** | Resumes execution from last persisted checkpoint. If already completed or failed, returns current state as-is. |

**Path Parameters:**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `thread_id` | `str` | min_length=1 | Thread to resume |

**Response Model:** `TripStateResponse`

**Logic:**
1. Load persisted state via `resume_trip(thread_id)`.
2. If state status is `completed`, `failed`, or `not_found`, return as-is (no re-execution).
3. Otherwise, invoke the graph again with the loaded state to continue execution.
4. Return updated state on success, or `status: "failed"` on error.

---

## 15. Data Models

### TripPlanRequest (`backend/api/schemas/request.py`)

```python
class TripPlanRequest(BaseModel):
    origin: str | None       # IATA code, min_length=3
    destination: str | None  # IATA code, min_length=3
    event_date: str | None   # YYYY-MM-DD, regex pattern
    venue: str | None        # Venue name, min_length=1
    sentence: str | None     # Natural language, min_length=10
    
    @model_validator(mode="after")
    def check_payload(self):
        # sentence XOR (origin AND destination AND event_date AND venue)
```

### HealthResponse (`backend/api/schemas/response.py`)

```python
class HealthResponse(BaseModel):
    status: str  # e.g., "healthy"
```

### TripPlanResponse (`backend/api/schemas/response.py`)

```python
class TripPlanResponse(BaseModel):
    success: bool       # Graph completed without top-level error
    report: str         # Markdown travel report
    itinerary: str      # Day-by-day itinerary
    destination: str    # From the original request
    event_date: str     # From the original request
```

### TripStateResponse (`backend/api/schemas/response.py`)

```python
class TripStateResponse(BaseModel):
    thread_id: str   # Session identifier
    status: str      # pending, running, completed, failed, not_found
    state: dict      # Full internal state
```

### TripPlannerState (`state/trip_state.py`)

TypedDict with ~30 fields (documented in Section 8 above).

---

## 16. Workflow Diagrams (Text)

### Overall Backend Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Entry Points                             │
│  ┌──────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ CLI      │  │ FastAPI REST API │  │ Python Import    │  │
│  │ main.py  │  │ backend/api/     │  │ services/        │  │
│  └────┬─────┘  └────────┬─────────┘  └────────┬─────────┘  │
│       │                 │                      │            │
└───────┼─────────────────┼──────────────────────┼────────────┘
        │                 │                      │
        ▼                 ▼                      ▼
┌────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  │
│  │ trip_planner_service    │  │ conversation_service     │  │
│  │ - plan_trip()           │  │ - start_conversation()   │  │
│  │ - resume_trip()         │  │ - continue_conversation()│  │
│  └───────────┬─────────────┘  └──────────┬───────────────┘  │
└──────────────┼────────────────────────────┼─────────────────┘
               │                            │
               ▼                            ▼
┌────────────────────────────────────────────────────────────┐
│              LangGraph Orchestration                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │  StateGraph[TripPlannerState]                      │    │
│  │                                                    │    │
│  │  START → coordinator → supervisor                  │    │
│  │             │              │                        │    │
│  │             ▼              ▼                        │    │
│  │          flight → hotel → weather → search         │    │
│  │  (conditional routing based on execution_plan)      │    │
│  │                                                    │    │
│  │  search → local → itinerary → END                  │    │
│  │                       │                             │    │
│  │                       ▼                             │    │
│  │              report_formatter_agent (internal call) │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────┐  ┌──────────────────────────────┐
│    Agent Layer          │  │    Tool Layer                │
│  8 graph nodes          │  │   5 tool modules             │
│  + 3 supporting agents  │  │                              │
│                         │  │  ┌────────────────────────┐  │
│  Each agent:            │  │  │ flight_tools.py        │  │
│  - Receives state dict  │  │  │  → Kiwi MCP            │  │
│  - Writes domain fields │  │  ├────────────────────────┤  │
│  - Returns updated dict │  │  │ hotel_tools.py         │  │
│                         │  │  │  → Agentorist MCP      │  │
│                         │  │  ├────────────────────────┤  │
│                         │  │  │ weather_mcp_client.py  │  │
│                         │  │  │ weather_tools.py       │  │
│                         │  │  │  → LiveDataLink MCP    │  │
│                         │  │  ├────────────────────────┤  │
│                         │  │  │ tavily_search.py       │  │
│                         │  │  │  → Tavily API          │  │
│                         │  │  └────────────────────────┘  │
│                         │  │                              │
│                         │  │  ┌────────────────────────┐  │
│                         │  │  │ config/models.py       │  │
│                         │  │  │  → Groq LLM API        │  │
│                         │  │  └────────────────────────┘  │
│                         │  │                              │
└─────────────────────────┘  └──────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────┐
│                    Persistence Layer                        │
│  ┌──────────────────────────────┐                          │
│  │ memory/sqlite_checkpoint.py  │                          │
│  │   → SqliteSaver              │                          │
│  │   → memory/trip_planner.db   │                          │
│  └──────────────────────────────┘                          │
└────────────────────────────────────────────────────────────┘
```

### FastAPI Request Flow

```
HTTP Request
    │
    ▼
┌──────────────────────────────────┐
│  Logging Middleware              │
│  - Generate request_id (uuid4)   │
│  - Set ContextVar for logs       │
│  - Start timer                   │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  CORS Middleware                 │
│  - Check allowed origins         │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  Router (/api/trips/*)           │
│  - Match endpoint                │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  Request Body Parsing            │
│  - Pydantic TripPlanRequest      │
│  - Validate sentence XOR fields  │
│  - On failure → 422 with details │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  plan_trip() handler             │
│  - Parse NL if sentence provided │
│  - Build TripPlannerState        │
│  - Invoke LangGraph with thread  │
│  - On failure → 500 response     │
│  - On success → TripPlanResponse │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│  Logging Middleware (response)   │
│  - Calculate elapsed_ms          │
│  - Log method/path/status/time   │
│  - Set X-Request-ID header       │
└──────────────────────────────────┘
           ▼
HTTP Response (200/422/500)
```

### LangGraph Execution Flow

```
 START
   │
   ▼
 coordinator_agent
   │ validate required fields
   │ init defaults: flight_details={}, hotel_details={}, etc.
   │ status = "processing"
   │
   ▼ (fixed edge)
 supervisor_agent
   │ validate destination, venue, event_date
   │ init domain defaults (empty dicts/strings)
   │ build execution_plan {run_flight, run_hotel, ...}
   │ LLM → supervisor_notes
   │ status = "blocked" if validation fails
   │
    ▼ (conditional edge — Send() fan-out)
  _route_from_supervisor(state)
    │
    ├── execution_plan["run_flight_agent"] == True  ──→ Send("flight_agent", state)
    ├── execution_plan["run_hotel_agent"]  == True  ──→ Send("hotel_agent",  state)
    ├── execution_plan["run_weather_agent"] == True ──→ Send("weather_agent", state)
    │
    │  All enabled Send() objects returned as a list.
    │  LangGraph executes them in parallel.
    │  Each agent returns only its own keys + errors.
    │
    ├── (none enabled) ──→ "search_agent" (string, direct skip)
    │
    ▼ (parallel execution, then fan-in)
  flight_agent      hotel_agent        weather_agent
    │ (Kiwi MCP)      │ (Agentorist)     │ (LiveDataLink)
    │ LLM summary     │ LLM summary      │ LLM summary
    │ return only     │ return only      │ return only
    │ flight_* keys   │ hotel_* keys     │ weather_* keys
    │ + errors        │ + errors         │ + errors
    │                 │                  │
    └─────────────────┼──────────────────┘
                      │ (fan-in: all three converge via add_edge)
                      ▼
                search_agent
                      │ Tavily search + LLM summary
                      │
                      ▼ (conditional, _make_route_after)
                local_agent (if enabled)
                      │
                      ▼ (conditional, _make_route_after)
                itinerary_agent
                      │ LLM → day-by-day itinerary
                      │ call report_formatter_agent (deterministic)
                      │ final_report = Markdown
                      │ status = "completed"
                      │
                      ▼
                     END
```

### Agent Interaction

```
                    TripPlannerState
                    ┌──────────────┐
                    │ origin       │
                    │ destination  │
                    │ event_date   │
                    │ travelers    │
                    │ venue        │
          ┌─────────┤ errors       │◄──────────────────────────┐
          │         │ status       │                           │
          │         │ ...          │                           │
          │         └──────┬───────┘                           │
          │                │                                   │
          ▼                ▼                                   │
┌─────────────────┐ ┌─────────────────┐                       │
│ supervisor_agent│ │ flight_agent    │                       │
│ reads: origin,  │ │ reads: origin,  │                       │
│   destination,  │ │   destination,  │                       │
│   event_date,   │ │   event_date,   │                       │
│   venue         │ │   travelers     │                       │
│ writes:         │ │ writes:         │                       │
│   execution_plan│ │   flight_details│                       │
│   supervisor_   │ │   flight_notes  │                       │
│   notes         │ │   flight_status │                       │
│   status        │ │   flight_booking│                       │
└────────┬────────┘ │   _link         │                       │
         │          └────────┬────────┘                       │
         │                   │                                │
         ▼                   ▼                                │
┌─────────────────┐ ┌─────────────────┐                       │
│ hotel_agent     │ │ weather_agent   │  Each agent reads     │
│ reads: dest,    │ │ reads: dest,    │  from shared state,   │
│   venue, date,  │ │   event_date    │  writes domain fields │
│   travelers     │ │ writes:         │  back, LangGraph      │
│ writes:         │ │   weather_      │  merges updates       │
│   hotel_details │ │   details,      │                       │
│   hotel_notes   │ │   weather_notes,│                       │
│   hotel_status  │ │   weather_status│                       │
│   hotel_booking │ └────────┬────────┘                       │
│   _links,       │          │                                │
│   hotel_price   │          ▼                                │
│   _details      │  ┌─────────────────┐                       │
└────────┬────────┘  │ search_agent    │                       │
         │           │ reads: dest,    │                       │
         ▼           │   venue, opts   │                       │
┌─────────────────┐  │ writes:         │                       │
│ local_agent     │  │   search_results│                       │
│ reads: dest,    │  │   search_notes  │                       │
│   venue         │  │   search_status │                       │
│ writes:         │  └────────┬────────┘                       │
│   local_results │           │                                │
│   local_notes   │           ▼                                │
│   local_status  │  ┌─────────────────┐                       │
└────────┬────────┘  │ itinerary_agent │                       │
         │           │ reads: ALL notes│                       │
         │           │ writes:         │                       │
         │           │   itinerary     │                       │
         │           │   final_report  │                       │
         │           │   status        │                       │
         │           └────────┬────────┘                       │
         │                    │                                │
         ▼                    ▼                                │
┌─────────────────────────────────────────────────────────────┐
│                    report_formatter_agent                     │
│  deterministic markdown assembly from state fields (no LLM)  │
└─────────────────────────────────────────────────────────────┘
```

### MCP Communication

```
Agent/Function (sync)
    │
    ▼
Tool Function (e.g., search_flights)
    │
    ▼
_run_coroutine(async_coro)
    │
    ├── if no running loop: asyncio.run(coro)
    └── if running loop: new thread → new event loop → run
                │
                ▼
async coroutine
    │
    ├── Connect to MCP server URL
    │   ├── if /sse: sse_client(url)
    │   └── else: streamable_http_client(url)
    │
    ├── ClientSession(read_stream, write_stream)
    │
    ├── session.initialize()      [timeout: 20s]
    │
    ├── session.list_tools()      [timeout: 20s]
    │   └── verify tool exists by name
    │
    ├── Match payload against tool.inputSchema
    │   ├── Strip keys not in schema properties
    │   └── Validate required fields
    │
    ├── session.call_tool(name, payload)  [timeout: 20s]
    │
    ├── Parse CallToolResult
    │   ├── Check isError flag
    │   ├── Extract content[] entries
    │   ├── Serialize TextContent/ImageContent/EmbeddedResource
    │   └── Normalize to {"status", "provider", "tool_used", "data", "error"}
    │
    └── Return dict to agent
```

### Report Generation

```
itinerary_agent (graph node)
    │
    ├── Collect all agent notes from state:
    │     flight_notes, hotel_notes, weather_notes,
    │     search_notes, supervisor_notes
    │
    ├── LLM: Synthesize day-by-day itinerary
    │   ↓
    │   state["itinerary"] = itinerary text
    │
    └── Call report_formatter_agent(state)
                │
                ▼
    report_formatter_agent (deterministic, no LLM)
                │
                ├── _format_executive_summary(state)
                │     → Origin, Destination, Event Date, Venue
                │
                ├── _format_trip_overview(state)
                │     → Markdown table
                │
                ├── _format_flights(state)
                │     ├── _parse_flight_notes() → parse "Flight N" blocks
                │     ├── _format_flight_block() → structured sub-section
                │     ├── "⭐ Recommended Flight" (first flight)
                │     └── "Other Available Flights" (remaining)
                │
                ├── _format_hotels(state)
                │     ├── _parse_hotel_notes() → parse "Hotel N" blocks
                │     ├── "⭐ Recommended Hotels" (first hotel)
                │     └── "Additional Hotel Options" (remaining)
                │
                ├── _format_weather(state)
                │     ├── Extract Forecast Summary, Historical, AQI, Advice
                │     ├── "Weather Summary"
                │     └── "Weather Details"
                │
                ├── _format_local(state)
                │     ├── Extract Attractions, Restaurants, Transit, Tips
                │     ├── "Local Highlights"
                │     ├── "Restaurants"
                │     └── "Transportation"
                │
                ├── _format_itinerary(state)
                │     → "Day-wise Itinerary"
                │
                ├── _format_booking_links(state)
                │     → "Quick Links" (all booking URLs)
                │
                └── _format_action_items(state)
                      → "Next Steps" (checklist)
                │
                ▼
         "# Executive Travel Report\n\n"
         + sections assembled in _SECTION_ORDER
                │
                ▼
         state["final_report"] = markdown string
```

### Checkpointing

```
Graph Invoke(config={"configurable": {"thread_id": "..."}})
    │
    ▼
StateGraph execution begins
    │
    ├── Node 1 executes
    │   │
    │   └── LangGraph framework saves state to checkpointer
    │       │
    │       └── SqliteSaver → INSERT/UPDATE memory/trip_planner.db
    │
    ├── Node 2 executes
    │   │
    │   └── LangGraph saves checkpoint (with thread_id)
    │
    ├── Node 3 executes
    │   │
    │   └── LangGraph saves checkpoint
    │
    ├── ... (every node)
    │
    └── Node N executes
        │
        └── LangGraph saves final checkpoint
                │
                ▼
        Result returned to caller

Resume later:
    get_state(config={"thread_id": "..."}) → load from SQLite
        │
        ▼
    graph.invoke(state, config={"thread_id": "..."})
        → continues from where it stopped
```

---

## 17. Execution Lifecycle

### Server Startup → Response Generation

1. **Process start:**
   - `uvicorn backend.api.app:app` reads the module-level `app = create_app()`.
   - FastAPI application is initialized with metadata, middleware, exception handlers, and router.
   - No database connections or MCP sessions are opened at startup — everything is lazy.

2. **First request:**
   - HTTP request arrives.
   - Logging middleware assigns `request_id`, starts timer.
   - CORS middleware validates origin.
   - Router matches endpoint.

3. **Trip plan request (`POST /api/trips/plan`):**
   - `TripPlanRequest` parsed and validated by Pydantic.
   - If `sentence` provided, `request_parser_agent` is called (Groq LLM → JSON extraction).
   - `build_trip_state()` normalizes values into `TripPlannerState`.
   - `_get_graph()` lazily builds and compiles the `StateGraph` (once per process).
   - `thread_id = "api_trip_" + uuid4.hex` generated.
   - `graph.invoke(state, config={"thread_id": thread_id})` begins.

4. **Graph execution (synchronous within LangGraph):**
   - `coordinator_agent`: Validates fields, sets defaults.
   - `supervisor_agent`: Validates, builds execution plan, LLM summary.
   - Conditional routing determines next agent.
   - Each specialist agent: calls external tool (MCP/Tavily), generates LLM summary.
   - After each node, `SqliteSaver` persists state to SQLite.
   - `itinerary_agent`: LLM itinerary + `report_formatter_agent` (deterministic markdown).
   - Graph returns final state dict.

5. **Response assembly:**
   - `TripPlanResponse` constructed from `final_report`, `itinerary`, `success` flag.
   - Errors logged, failure response returned on exception.
   - Logging middleware records elapsed time, sets `X-Request-ID` header.

6. **Response sent:**
   - JSON response with markdown report body returned to client.

---

## 18. Checkpointing

### SQLite Checkpointer (`memory/sqlite_checkpoint.py`)

**Provider:** `langgraph.checkpoint.sqlite.SqliteSaver`

**Default database path:** `PROJECT_ROOT / "memory" / "trip_planner.db"`

**Configuration:**
```python
def get_checkpointer(db_path=None):
    # Supports both direct Path and SQLAlchemy-style connection strings
    # Creates parent directories if needed
    # Uses SqliteSaver.from_conn_string() for best compatibility
    # Registers atexit handler for context manager cleanup
```

**How it works:**
1. After every node execution, LangGraph framework automatically calls the checkpointer to save the state.
2. Each save is associated with a `thread_id` from the invocation config.
3. Saved state includes: node name, state values, next node to execute, and timestamps.

### Resume Flow

The `resume_trip(thread_id)` function:
```python
def resume_trip(thread_id):
    snapshot = _get_graph().get_state(
        {"configurable": {"thread_id": thread_id}}
    )
    return snapshot.values  # Full state dict
```

**API endpoint `POST /{thread_id}/resume`:**
1. Loads persisted state.
2. If status is `completed`, `failed`, or `not_found`: returns state as-is.
3. Otherwise, invokes graph again with loaded state to continue from where it stopped.

### Use Cases

- **Fault recovery:** If an MCP timeout fails an agent mid-graph, the workflow can be resumed.
- **Multi-turn conversations:** The conversation service saves state after each user interaction.
- **Debugging:** State inspection via `GET /{thread_id}` shows all agent outputs.

### Persistence Details

- **Database type:** Local SQLite file (not suitable for multi-instance deployment).
- **Concurrency:** SQLite handles concurrent reads; writes are serialized.
- **Cleanup:** No automatic cleanup of old checkpoints. The `.db` file grows with use.

---

## 19. Error Handling

### API Errors

| Layer | Error Type | Handling |
|---|---|---|
| Request validation | `RequestValidationError` | Caught by `_validation_error_handler` → 422 JSON response with field errors |
| HTTP exceptions | `HTTPException` | Caught by `_http_error_handler` → appropriate status code |
| Unhandled exceptions | `Exception` | Caught by `_global_error_handler` → 500 JSON response with generic message |
| Middleware failures | Any | Caught by `_logging_middleware` → logged, re-raised |

### Tool Errors

| Scenario | Behavior |
|---|---|
| MCP server unreachable | `asyncio.TimeoutError` or connection error → error dict returned to agent |
| Tool not found on MCP server | `RuntimeError("Tool 'X' not available")` → error dict |
| Tool execution error | Check `result.isError` flag → serialized error dict |
| Empty results (hotels) | `_is_empty_results()` → error with "No hotel results" |
| Tavily API failure | 3 retries with linear backoff → error dict on final failure |
| Invalid date format | `ValueError` in `_calculate_forecast_days()` → error dict |

### Graph Errors

| Scenario | Behavior |
|---|---|
| Agent function exception | Caught in `try/except`, error message appended to `state["errors"]`, domain status set to `"failed"` |
| Supervisor LLM failure | `supervisor_notes` set to fallback string, `status = "degraded"` |
| Itinerary agent LLM failure | `_build_fallback_itinerary()` used, report still generated |
| Missing required fields | Supervisor sets `status = "blocked"` (workflow continues but may produce incomplete output) |

### LLM Failures

- If `GROQ_API_KEY` is missing or invalid: `get_text_llm()` raises `ValueError("GROQ_API_KEY is required")`.
- If Groq API returns errors: `ChatGroq` propagates the API error, caught by the calling agent's `try/except`.
- All LLM calls wrap in agent-level `try/except` — no LLM failure crashes the graph.

### Timeouts

- **MCP operations:** 20-second timeout on `session.initialize()`, `session.list_tools()`, and `session.call_tool()`.
- **Tavily:** No explicit timeout in the code (relies on default HTTP timeout).
- **LLM:** No explicit timeout (relies on Groq API defaults).

### Logging

All errors are logged with:
- Request correlation ID (from `request_id_var` ContextVar).
- Method, path, and status code.
- Exception traceback for unhandled errors.
- Agent-level errors include agent name prefix (e.g., `"flight_agent failed: ..."`).

---

## 20. Logging Architecture

### Configuration (`backend/api/log_config.py`)

```python
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

class _RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get() or "-"
        return True

# Format: "2024-01-01 12:00:00 | INFO     | trip_planner.api | request=abc123 | message"
```

### Where Logs Are Generated

| Module | Logger Name | What Is Logged |
|---|---|---|
| `backend/api/app.py` | `trip_planner.api` | Request start/end, elapsed_ms, status_code, exceptions |
| `backend/api/routes/trips.py` | `trip_planner.api` | NL parsing, graph invocation, results, errors |
| `tools/tavily_search.py` | `__name__` (root-level) | Search attempts, retries, failures |
| `backend/api/log_config.py` | `trip_planner.api` | Logger configuration |

### Execution Tracing

- The logging middleware captures a unique `request_id` per HTTP request.
- Every log line within that request includes the request_id via `_RequestIDFilter`.
- LangSmith tracing is also available (optional) for deeper LLM call tracing.

### Debug Information

- Each graph node has a debug wrapper (`_run_with_debug`) that prints `"RUNNING NODE: {name}"` to stdout.
- Individual agents have `DEBUG` flags (set to `False` by default) that, when enabled, print full state, inputs, and outputs.

---

## 21. Dependency Graph

```
main.py
  └── services.trip_planner_service
        ├── agents.request_parser_agent
        │     ├── langchain.agents.create_agent
        │     └── config.models
        │           └── config.settings
        ├── utils.state_builder
        │     └── state.trip_state
        └── graph.trip_graph
              ├── state.trip_state
              ├── memory.sqlite_checkpoint
              │     └── langgraph.checkpoint.sqlite
              ├── agents.coordinator
              │     └── config.models
              ├── agents.supervisor_agent
              │     └── config.models
              ├── agents.flight_agent
              │     ├── config.models
              │     └── tools.flight_tools
              │           └── config.settings
              ├── agents.hotel_agent
              │     ├── config.models
              │     └── tools.hotel_tools
              │           └── config.settings
              ├── agents.weather_agent
              │     ├── config.models
              │     └── tools.weather_tools
              │           └── tools.weather_mcp_client
              │                 └── config.settings
              ├── agents.search_agent
              │     ├── config.models
              │     └── tools.tavily_search
              │           └── config.settings
              ├── agents.local_agent
              │     ├── config.models
              │     └── tools.hotel_tools
              └── agents.itinerary_agent
                    ├── config.models
                    └── agents.report_formatter_agent

backend.api.app
  ├── backend.api.log_config
  └── backend.api.routes.trips
        ├── backend.api.log_config
        ├── agents.request_parser_agent
        ├── backend.api.schemas.request
        ├── backend.api.schemas.response
        ├── services.trip_planner_service
        └── utils.state_builder

services.conversation_service
  ├── agents.conversation_agent
  ├── agents.request_parser_agent
  ├── services.trip_planner_service
  └── utils.state_builder

tests/
  ├── test_state_builder → utils.state_builder
  ├── test_trip_planner_service → services.trip_planner_service
  └── test_conversation_service → services.conversation_service
```

**Key observation:** There are no circular dependencies. The dependency chain is:
`config.settings → config.models → agents/* → graph.trip_graph → services/* → main.py / backend/api/`

---

## 22. Complete Backend Sequence

```
User / HTTP Client
    │
    │ POST /api/trips/plan {"sentence": "Plan a trip from MIA to EWR..."}
    ▼
[FastAPI App] backend/api/app.py
    │ LoggingMiddleware: assign request_id=abc123, start timer
    │ CORSMiddleware: check origin
    │ Router: POST /api/trips/plan → plan_trip()
    ▼
[routes/trips.py] plan_trip()
    │ Parse body → TripPlanRequest(sentence="Plan a trip from MIA...")
    │ model_validator: sentence is provided ✓
    │
    │ if sentence: request_parser_agent("Plan a trip from MIA...")
    │   [request_parser_agent.py]
    │   Create LangChain agent (Groq LLM, no tools)
    │   System prompt: "Extract structured details... Return JSON..."
    │   Invoke: "Extract trip details... request: Plan a trip from MIA to EWR on 2026-07-15 for a concert at Prudential Center."
    │   Groq returns: {"origin": "MIA", "destination": "EWR", "travelers": 1, "venue": "Prudential Center", "event_date": "2026-07-15"}
    │   _extract_json_payload() → parsed dict
    │   Normalize fields → {"origin": "MIA", "destination": "EWR", ...}
    │
    │ parsed = {"origin": "MIA", "destination": "EWR", ...}
    │
    ▼
    │ state = build_trip_state(parsed)
    │   [state_builder.py]
    │   _normalize_text("MIA") → "MIA"
    │   _normalize_travelers(1) → 1
    │   Returns TripPlannerState with origin, destination, travelers, venue, event_date
    │   Empty errors[], flight_booking_link="", hotel_booking_links=[], etc.
    │
    ▼
    │ thread_id = "api_trip_a1b2c3d4e5f6"
    │ result = _get_graph().invoke(state, config={"configurable": {"thread_id": thread_id}})
    │
    ▼
[Graph] graph/trip_graph.py
    │ StateGraph[TripPlannerState] begins
    │
    ├── Node: coordinator_agent
    │   Validate destination="EWR" ✓, venue="Prudential Center" ✓, event_date="2026-07-15" ✓
    │   Init defaults → status="processing"
    │   SQLite: checkpoint saved (thread=api_trip_..., node=coordinator)
    │
    ├── Node: supervisor_agent
    │   Validate fields (all present ✓)
    │   execution_plan = {"run_flight_agent": True, "run_hotel_agent": True, ...}
    │   LLM → supervisor_notes: "Planning trip from MIA to EWR on 2026-07-15 for Prudential Center. Will search flights, hotels, weather, and local attractions."
    │   SQLite: checkpoint saved
    │
    ├── Conditional: _route_from_supervisor()  [Send() fan-out]
    │   execution_plan["run_flight_agent"] == True  → Send("flight_agent", state)
    │   execution_plan["run_hotel_agent"]  == True  → Send("hotel_agent",  state)
    │   execution_plan["run_weather_agent"] == True → Send("weather_agent", state)
    │   (Returns list of Send() for all enabled agents — executed in parallel)
    │   (If none enabled → returns "search_agent" string)
    │
    ├── Node: flight_agent (parallel)
    │   │ (runs concurrently with hotel_agent and weather_agent)
    │   │ Wrapper in trip_graph.py strips return to only flight_* keys + errors
    │   search_flights(origin="MIA", destination="EWR", event_date="2026-07-15", travelers=1)
    │     [flight_tools.py] Kiwi MCP:
    │       Connect to mcp.kiwi.com (Streamable HTTP)
    │       Initialize session, list tools → find "search-flight"
    │       Prepare payload: {"flyFrom": "MIA", "flyTo": "EWR", "departureDate": "15/07/2026"}
    │       Call tool → CallToolResult with text content (JSON array of flights)
    │     Parse flight data → flights_list (limit 5)
    │     LLM: "Select the best flight..." → recommendation text
    │     Format flight_notes → structured markdown
    │     flight_booking_link = "https://on.kiwi.com/..."
    │     recommended_flight_price = 150.0
    │     flight_status = "completed"
    │   Returns: {"flight_details": ..., "flight_notes": ..., "flight_status": "completed", "flight_booking_link": ..., "recommended_flight_price": 150.0, "errors": []}
    │
    ├── Node: hotel_agent (parallel, concurrent with flight_agent and weather_agent)
    │   │ Wrapper strips return to only hotel_* keys + errors
    │   search_hotels(destination="EWR")
    │     [hotel_tools.py] Agentorist MCP:
    │       Connect to mcp.agentorist.com/mcp (Streamable HTTP)
    │       Initialize, list tools → find "search"
    │       Payload: {"vertical": "local", "query": "best hotels", "location": "EWR", "agent_client": "TripPlanner"}
    │       Call tool → structured results
    │     Extract results[] → hotel names, ratings, price categories, booking URLs
    │     LLM: "Summarize hotel options..." → recommendation text
    |     Format hotel_notes → structured markdown
    │     hotel_booking_links = [...]
    │     hotel_price_details = [{hotel, price_category, rating}, ...]
    │     hotel_status = "completed"
    │   Returns: {"hotel_details": ..., "hotel_notes": ..., "hotel_status": "completed", "hotel_booking_links": [...], "hotel_price_details": [...], "errors": []}
    │
    ├── Node: weather_agent (parallel, concurrent with flight_agent and hotel_agent)
    │   │ Wrapper strips return to only weather_* keys + errors
    │   get_weather(destination="EWR", event_date="2026-07-15")
    │     [weather_tools.py]
    │     _calculate_forecast_days("2026-07-15") → days (clamped 1-16)
    │     [weather_mcp_client.py] LiveDataLink MCP:
    │       Connect to livedatalink.ai/mcp (Streamable HTTP)
    │       Call weather_forecast(location="EWR", days=N)
    │       Call air_quality(location="EWR")  (optional, failure non-fatal)
    │     Returns combined dict with forecast + air quality
    │   LLM: "Summarize weather forecast..." → structured markdown (Forecast Summary, Historical, AQI, Advice)
    │   weather_notes = formatted markdown
    │   weather_status = "completed"
    │   Returns: {"weather_details": ..., "weather_notes": ..., "weather_status": "completed", "errors": []}
    │
    │   [Fan-in: flight_agent, hotel_agent, weather_agent all converge via add_edge to search_agent.
    │    LangGraph waits for ALL scheduled parallel branches to complete before running search_agent.
    │    State updates from all branches are merged (errors accumulate via Annotated[list[str], operator.add]).]
    │
    ├── Node: search_agent (runs after all parallel branches complete)
    │
    ├── Node: search_agent
    │   LangChain agent with Tavily search_web tool
    │   LLM: "Use search_web to research destination..." → calls search_web("EWR attractions...")
    │     [tavily_search.py] TavilyClient.search(query="...", max_results=5)
    │     Returns {"results": [{"title": "...", "content": "..."}, ...]}
    │   LLM generates structured markdown: Venue Highlights, Top Attractions, Restaurants, Transit, Local Tips
    │   search_status = "completed"
    │   SQLite: checkpoint saved
    │
    ├── Conditional: _make_route_after("search_agent")
    │   execution_plan["run_local_agent"] == False → "itinerary_agent"
    │
    ├── Node: itinerary_agent
    │   LLM: "Create a complete travel itinerary..."
    │   Input: supervisor_notes, flight_notes, hotel_notes, weather_notes, search_notes
    │   → itinerary text (day-by-day plan)
    │   itinerary_status = "completed"
    │
    │   Call report_formatter_agent(state)
    │     [report_formatter_agent.py] (deterministic, no LLM)
    │     _format_executive_summary(state) → "## Executive Summary\n..."
    │     _format_trip_overview(state) → "## Trip Overview\n| Detail | Value |\n..."
    │     _format_flights(state) → "## ⭐ Recommended Flight\n### ⭐ Flight 1\n..."
    │     _format_hotels(state) → "## ⭐ Recommended Hotels\n### ⭐ Hotel 1\n..."
    │     _format_weather(state) → "## Weather Summary\n...\n## Weather Details\n..."
    │     _format_local(state) → "## Local Highlights\n...\n## Restaurants\n...\n## Transportation\n..."
    │     _format_itinerary(state) → "## Day-wise Itinerary\n..."
    │     _format_booking_links(state) → "## Quick Links\n* **Flight Booking:** ..."
    │     _format_action_items() → "## Next Steps\n- [ ] Book flight\n..."
    │     → "## Executive Travel Report" + all sections
    │   final_report = full Markdown string
    │   status = "completed"
    │   SQLite: final checkpoint saved
    │
    └── Node: END (graph returns final state)
    │
    ▼
[routes/trips.py] plan_trip() continues
    │ result = state dict with final_report, itinerary, status="completed"
    │ log: thread_id=... status=completed has_report=True has_itinerary=True
    │ Return TripPlanResponse(success=True, report=markdown, itinerary=..., destination="EWR", event_date="2026-07-15")
    │
    ▼
[FastAPI] Logging middleware
    │ elapsed_ms = 45231.87
    │ log: method=POST path=/api/trips/plan status_code=200 elapsed_ms=45231.87 | Request completed
    │ Set X-Request-ID: abc123
    ▼
HTTP 200 OK
Content-Type: application/json
{
  "success": true,
  "report": "# Executive Travel Report\n\n## Executive Summary\n\n...",
  "itinerary": "**Day 1** – Arrive at EWR...\n**Day 2** – Event at Prudential Center...",
  "destination": "EWR",
  "event_date": "2026-07-15"
}
```

---

## 23. Design Decisions

### Why FastAPI?

FastAPI was chosen over alternatives (Flask, Django REST Framework) because:
- **Native async support** — aligns with the asyncio-based MCP clients (though bridging is still needed for synchronous graph nodes).
- **Automatic OpenAPI documentation** — Swagger UI at `/docs` for easy API exploration.
- **Pydantic integration** — Request/response validation with minimal code, matching the project's use of Pydantic for settings.
- **Performance** — Uvicorn ASGI server provides competitive throughput.

### Why LangGraph?

- **StateGraph abstraction** — Allows each agent to be a pure function (state in → state out), eliminating the need for custom state management.
- **Built-in checkpointing** — SQLite persistence after every node enables resumability and state inspection without additional infrastructure.
- **Conditional routing** — The `execution_plan`-based routing allows flexible agent skipping (important for resume workflows).
- **Reducer pattern** — Automatic merging of partial state updates from each node.
- **LangChain ecosystem** — Compatible with LangChain agents, Groq provider, and LangSmith tracing.

### Why Supervisor Pattern?

The hierarchical (supervisor → specialists) pattern was chosen over:
- **Flat sequential pipeline** — Would couple all agents together; the supervisor provides a single point for validation, planning, and context-building.
- **Fully autonomous multi-agent** — Each agent deciding its own next action. The supervisor provides deterministic execution ordering while allowing conditional skipping.
- **Single LLM call** — Would lose domain specialization and graceful degradation.

### Why MCP?

MCP (Model Context Protocol) provides:
- **Standardized tool discovery** — `list_tools()` returns schemas, allowing dynamic payload preparation.
- **Multiple transport options** — SSE for persistent connections, Streamable HTTP for simpler firewalls.
- **Rich content types** — TextContent, ImageContent, EmbeddedResource for complex responses.
- **Growing ecosystem** — Kiwi, Agentorist, LiveDataLink all provide MCP servers for travel data.

### Why Tool Calling (LangChain Tools)?

Two agents (`search_agent`, `local_agent`) use LangChain's `create_agent` with registered tools. This pattern allows the LLM to decide when to call the tool (rather than calling it unconditionally), enabling more flexible behavior.

### Why SQLite Checkpointing?

- **Zero infrastructure** — No database server to configure, manages itself via `SqliteSaver`.
- **LangGraph native** — `SqliteSaver.from_conn_string()` is a first-class checkpointer.
- **Sufficient for development** — Single-process, single-user workloads common in development.
- **Replaceable** — LangGraph supports `PostgresSaver` for production deployments.

### Why StateGraph (vs. ControlFlow or Custom)?

StateGraph provides:
- Node registration with typed state.
- Fixed and conditional edges for flexible routing.
- Automatic checkpointing after every node.
- State merging (updates from each node are overlaid on global state).

### Why LLMs (Groq)?

- **Fast inference** — Groq provides low-latency LLM inference via custom hardware.
- **Cost-effective** — Competitive pricing for the `openai/gpt-oss-20b` model.
- **LangChain integration** — Native `langchain-groq` package.
- **Versatile model** — 70B parameter model handles JSON extraction, summarization, and creative itinerary generation.

### Why Multi-Agent Workflow?

1. **Specialization** — Each agent has a focused prompt optimized for its domain (e.g., weather agent's prompt is structurally different from the hotel agent's).
2. **Graceful degradation** — If weather MCP is down, only weather results are missing; flights and hotels still work.
3. **Debuggability** — Each domain's outputs and errors are independently tracked in state fields.
4. **Extensibility** — New data sources (car rental, activities, visa info) can be added as new agents without changing existing code.

---

## 24. Scalability

### Current Limitations

- **Synchronous graph execution** — All specialist agents ran sequentially (pre-v2). Now parallel for flight, hotel, weather agents.
- **Local SQLite** — Not suitable for multi-instance deployments. State would be lost on container restart or instance scale-out.
- **Single process** — The CLI and FastAPI server are single-process. No horizontal scaling.
- **Thread-based async bridging** — Each MCP call spawns a daemon thread. Under high concurrency, this could exhaust thread pools.

### Scalability Strategies

| Dimension | Current | Scalable Approach |
|---|---|---|
| **Parallel agent execution** | **Parallel** (flight, hotel, weather) via Send(); search, local remain sequential | Scalable to more parallel groups with additional fan-out nodes. |
| **State persistence** | Local SQLite | Replace with PostgreSQL via LangGraph's `PostgresSaver` for shared state across instances. |
| **API server** | Single uvicorn | Uvicorn supports workers: `uvicorn --workers 4`. Behind a load balancer for horizontal scale. |
| **MCP connections** | Per-request thread | Connection pooling or persistent MCP sessions across requests. |
| **LLM calls** | Sequential per agent | Could batch or parallelize independent LLM calls. |
| **Caching** | None | Cache MCP responses by query parameters to reduce external API calls for repeated requests. |

---

## 25. Future Extension Points

### New Agents

To add a new specialist agent (e.g., Car Rental Agent, Activity Booker):

1. Create `agents/car_rental_agent.py` following the existing agent pattern (try/except, write domain fields, return only own keys).
2. Add domain fields to `TripPlannerState` TypedDict in `state/trip_state.py`.
3. If the agent is independent and can run in parallel with others, add it to `_PARALLEL_AGENTS` in `graph/trip_graph.py`. If it depends on other agents' outputs, add it to `_AGENT_EXECUTION_ORDER` (sequential).
4. Register the node with `graph.add_node()`. If parallel, wrap it with a key-filtering wrapper (see `_flight_agent_wrapper` pattern).
5. Update `supervisor_agent._build_execution_plan()` to include the new flag.
6. Add fan-in/fan-out edges in `build_trip_graph()` as appropriate.
7. No existing agent code needs modification — the new agent integrates through shared state.

### New MCP Servers

To add a new MCP-based data source:

1. Create a new tool module in `tools/` (e.g., `tools/activity_tools.py`).
2. Follow the existing pattern: `_list_tools_and_call()`, `_run_coroutine()`, standard return format.
3. Add the server URL to `config/settings.py`.
4. Call the tool function from the appropriate agent.

### New API Providers

To swap a provider (e.g., replace Kiwi with a different flight API):

1. Create a new tool module with the same interface (`search_flights(origin, destination, date, travelers)`).
2. Update `flight_agent.py` to import from the new module.
3. No other files need changes — the agent only depends on the function's return format.

### New API Endpoints

To add new endpoints:

1. Add new route functions in `backend/api/routes/trips.py` or create new route modules.
2. Add new Pydantic schemas in `backend/api/schemas/`.
3. Register additional routers in `backend/api/app.py`.

### New Workflow Patterns

- **Parallel execution** — Use LangGraph's fan-out/fan-in pattern to run independent agents concurrently.
- **Human-in-the-loop** — Use LangGraph's `interrupt` feature to pause graph execution and wait for user confirmation.
- **Dynamic agent discovery** — Have the supervisor dynamically discover and invoke agents based on the trip context.

---

## 26. Backend Summary

### Architecture

The Trip Planner backend is a **multi-agent AI travel planning system** built on a layered architecture:

- **Entry layer:** CLI (`main.py`), FastAPI REST API (`backend/api/`), or direct Python imports (`services/`).
- **Service layer:** Orchestrates request parsing, state building, graph invocation, and conversation management.
- **LangGraph layer:** A `StateGraph` with 8 registered nodes executing in a configurable sequence with conditional routing based on a supervisor-generated execution plan.
- **Agent layer:** 11 agent modules (8 graph nodes + 3 supporting) implementing domain-specific logic using LangChain's `create_agent` with Groq LLM.
- **Tool layer:** 5 tool modules wrapping MCP clients (Kiwi, Agentorist, LiveDataLink) and REST APIs (Tavily).
- **State layer:** A single `TripPlannerState` TypedDict (~30 fields) flowing through all nodes.
- **Persistence layer:** SQLite checkpointing via `SqliteSaver` for state persistence and workflow resumption.

### Strengths

1. **Separation of concerns** — Each domain (flights, hotels, weather, search) is isolated in its own agent with a specialized prompt and data source.
2. **Graceful degradation** — Individual agent failures are recorded in `errors[]` without blocking the pipeline.
3. **Conditional execution** — The supervisor's execution plan enables skipping agents whose data is already available (useful for resume).
4. **Deterministic report formatting** — The `report_formatter_agent` produces consistent output without LLM variability.
5. **Checkpointing** — Full state persistence after every node enables resumability and debugging.
6. **Structured logging** — Per-request correlation IDs across the API layer.
7. **Lazy initialization** — Graph and settings are built once and cached, minimizing startup overhead.

### Workflow

Natural language request → `request_parser_agent` (LLM extracts JSON fields) → `state_builder` (normalizes values) → LangGraph `StateGraph` with conditional routing (Send() parallel fan-out) → supervisor validates & plans → specialist agents execute (flight/hotel/weather **in parallel**, search/local sequentially; all via MCP/Tavily calls + LLM summaries) → itinerary agent synthesizes → report formatter produces Markdown → response returned.

### Modularity

The project is organized into 9 top-level packages (`agents/`, `backend/`, `config/`, `graph/`, `memory/`, `services/`, `state/`, `tools/`, `utils/`) each with a single, well-defined responsibility. Dependencies flow downward: `config ← tools ← agents ← graph ← services ← entry points`.

### Extensibility

New agents can be added by: creating a new agent file, adding TypedDict fields, adding a node to the graph, updating the execution plan, and updating the report formatter. No existing agent code needs modification.

### Maintainability

- **Consistent agent pattern** — Every agent follows the same structure: copy state → try/except → execute → write fields → return.
- **Centralized configuration** — All environment variables in `config/settings.py`.
- **Standardized tool return format** — Every tool returns `{status, provider, tool_used, data, error}`.
- **Self-documenting API** — FastAPI generates OpenAPI spec automatically.
- **Comprehensive tests** — 3 test files covering state building, service behavior, and multi-turn conversations.
