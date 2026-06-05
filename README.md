# Agentic Trip Planner

> An agentic AI travel planning system that coordinates specialized agents for flight discovery, hotel recommendations, weather analysis, destination research, and itinerary generation through a LangGraph-powered workflow.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-workflow-1C3C3C?style=flat-square)
![LangChain](https://img.shields.io/badge/LangChain-agents-1C3C3C?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square)
![MCP Integration](https://img.shields.io/badge/MCP-integration-4B5563?style=flat-square)
![SQLite Checkpointing](https://img.shields.io/badge/SQLite-checkpointing-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active%20Development-2563EB?style=flat-square)

Multi-agent travel planning using LangGraph, MCP integrations, and LLM-powered itinerary generation.

---

# Overview

The project demonstrates a multi-agent travel workflow built around LangGraph shared state. A user request is parsed into structured trip fields, then passed through specialist agents for flight search, hotel search, weather lookup, destination research, itinerary generation, and final report formatting.

The main workflow is exposed through service functions rather than a web server or CLI. The primary entry point is `services.trip_planner_service.plan_trip(user_request)`, with additional conversation helpers in `services.conversation_service` for collecting missing required fields across multiple turns.

Main workflow:

1. Parse the user request into `origin`, `destination`, `travelers`, `venue`, and `event_date`.
2. Build a LangGraph-compatible `TripPlannerState`.
3. Run the compiled LangGraph workflow with SQLite checkpointing.
4. Call external MCP/API-backed tools for flights, hotels, weather, and search.
5. Generate an itinerary from collected agent notes.
6. Assemble a final Markdown report.

# Architecture

The LangGraph workflow is defined in `graph/trip_graph.py`. It is a sequential graph with a SQLite checkpointer from `memory/sqlite_checkpoint.py`.

```mermaid
flowchart TD
    A[User request] --> B[request_parser_agent]
    B --> C[build_trip_state]
    C --> D[LangGraph invoke]
    D --> E[supervisor_agent]
    E --> F[flight_agent]
    F --> G[hotel_agent]
    G --> H[weather_agent]
    H --> I[search_agent]
    I --> J[itinerary_agent]
    J --> K[report_formatter_agent]
    K --> L[Final Markdown report]

    F --> F1[Kiwi MCP search-flight]
    G --> G1[Agentorist MCP search]
    H --> H1[LiveDataLink MCP weather tools]
    I --> I1[Tavily Search API]
```

Execution flow:

| Step | Module | Purpose |
| --- | --- | --- |
| Request parsing | `agents/request_parser_agent.py` | Uses the Groq-backed LangChain agent to extract structured trip fields from natural language. |
| State creation | `utils/state_builder.py` | Normalizes parsed fields and initializes booking, pricing, and error fields. |
| Graph orchestration | `graph/trip_graph.py` | Runs the fixed LangGraph node order and stores checkpoints in SQLite. |
| Agent execution | `agents/*.py` | Runs each specialist agent and appends results to shared state. |
| Report generation | `agents/report_formatter_agent.py` | Deterministically formats the final Markdown report from state. |

# Features

- Natural-language request parsing into structured trip fields.
- Sequential LangGraph workflow for multi-agent trip planning.
- SQLite-backed LangGraph checkpointing with generated thread IDs.
- Flight search through the Kiwi MCP `search-flight` tool.
- Hotel search through the Agentorist MCP `search` tool.
- Weather forecast and air quality lookup through LiveDataLink MCP tools.
- Destination research through Tavily web search.
- LLM-generated summaries for supervisor, flight, hotel, weather, search, and itinerary outputs.
- Deterministic final report formatting.
- Conversation service for collecting missing `origin`, `destination`, and `event_date` fields.
- Unit tests for state building, trip planning service behavior, and conversation state handling.
- Groq Whisper transcription helper in `config/models.py`.

# Project Structure

```text
trip_planner/
├── agents/
│   ├── conversation_agent.py
│   ├── coordinator.py
│   ├── flight_agent.py
│   ├── hotel_agent.py
│   ├── itinerary_agent.py
│   ├── local_agent.py
│   ├── report_formatter_agent.py
│   ├── request_parser_agent.py
│   ├── search_agent.py
│   ├── supervisor_agent.py
│   └── weather_agent.py
├── config/
│   ├── models.py
│   └── settings.py
├── graph/
│   └── trip_graph.py
├── memory/
│   └── sqlite_checkpoint.py
├── notebooks/
│   ├── mcp_connection_test.ipynb
│   └── trip_planner.ipynb
├── services/
│   ├── conversation_service.py
│   └── trip_planner_service.py
├── state/
│   └── trip_state.py
├── tests/
│   ├── test_conversation_service.py
│   ├── test_state_builder.py
│   └── test_trip_planner_service.py
├── tools/
│   ├── flight_tools.py
│   ├── hotel_tools.py
│   ├── tavily_search.py
│   ├── weather_mcp_client.py
│   └── weather_tools.py
├── utils/
│   ├── file_utils.py
│   └── state_builder.py
├── requirements.txt
└── README.md
```

Important files:

| Path | Purpose |
| --- | --- |
| `graph/trip_graph.py` | Builds and compiles the LangGraph workflow. |
| `state/trip_state.py` | Defines the shared `TripPlannerState` fields. |
| `services/trip_planner_service.py` | Provides `plan_trip()` and `resume_trip()` entry points. |
| `services/conversation_service.py` | Provides multi-turn collection and resume helpers. |
| `config/settings.py` | Loads API keys, model names, MCP URLs, and directory settings from `.env`. |
| `config/models.py` | Creates Groq text and transcription clients. |
| `memory/sqlite_checkpoint.py` | Configures SQLite checkpoint persistence. |
| `tools/` | Contains wrappers for Kiwi MCP, Agentorist MCP, LiveDataLink MCP, and Tavily. |
| `tests/` | Contains `unittest` coverage for service and state behavior. |

# Agent Responsibilities

| Agent | Inputs | Outputs |
| --- | --- | --- |
| `supervisor_agent` | Current trip state, required fields, prior agent outputs if present. | `supervisor_notes`, `execution_plan`, initialized state defaults, validation errors, `status` updates. |
| `flight_agent` | `origin`, `destination`, `event_date`, `travelers`. | `flight_details`, `flight_notes`, `flight_status`, `flight_booking_link`, `recommended_flight_price`. |
| `hotel_agent` | `destination`, `venue`, `event_date`, `travelers`, optional `budget` and `hotel_preferences`. | `hotel_details`, `hotel_notes`, `hotel_status`, `hotel_booking_links`, `hotel_price_details`. |
| `weather_agent` | `destination`, `event_date`. | `weather_details`, `weather_notes`, `weather_status`. |
| `search_agent` | `destination`, `venue`, optional `interests` and `trip_style`. | `search_results`, `search_notes`, `search_status`. |
| `itinerary_agent` | Destination details plus supervisor, flight, hotel, weather, and search notes. | `itinerary`, `itinerary_notes`, `itinerary_status`, `final_report`, final `status`. |
| `report_formatter_agent` | Full state with agent notes and optional booking links. | Deterministic `final_report` Markdown string. |

Supporting agents:

| Agent | Current use |
| --- | --- |
| `request_parser_agent` | Called before graph execution to extract structured fields from user input. |
| `conversation_agent` | Used by `conversation_service` to detect missing required fields and select the next question. |
| `local_agent` | Implemented for Agentorist local discovery, but not wired into the main LangGraph workflow. |
| `coordinator_agent` | Implemented state validation helper, but not wired into the main LangGraph workflow. |

# Technologies Used

| Category | Technology |
| --- | --- |
| Language | Python |
| Agent workflow | LangGraph |
| Agent framework | LangChain |
| LLM provider | Groq via `langchain-groq` |
| Text model default | `llama-3.3-70b-versatile` |
| Transcription model default | `whisper-large-v3` |
| Search API | Tavily |
| Flight provider | Kiwi MCP server |
| Hotel/local provider | Agentorist MCP server |
| Weather provider | LiveDataLink MCP server |
| Checkpointing | LangGraph `SqliteSaver` |
| Configuration | `pydantic-settings`, `.env`, `python-dotenv` |
| Testing | Python `unittest` |
| Notebook usage | Jupyter, IPython kernel |
| Data utilities | pandas, numpy |
| HTTP/MCP support | `requests`, `httpx`, `mcp` |

# Installation

The local virtual environment in this repository was observed running Python 3.13.7. The project does not currently pin a Python version in packaging metadata.

1. Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd trip_planner
```

2. Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:

```env
GROQ_API_KEY=
TAVILY_API_KEY=
LANGCHAIN_TRACING=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=TripPlanner
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
KIWI_MCP_SERVER_URL=https://mcp.kiwi.com
WEATHER_PROVIDER=livedatalink
WEATHER_MCP_SERVER_URL=https://livedatalink.ai/mcp
AGENTORIST_MCP_SERVER_URL=https://mcp.agentorist.com/mcp
```

5. Run the test suite:

```bash
python -m unittest discover tests
```

# Configuration

Configuration is loaded from `.env` by `config/settings.py`.

| Variable | Required | Default | Used by |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | Yes | Empty | Text LLM and audio transcription clients. |
| `TAVILY_API_KEY` | Required for destination search | Empty | `tools/tavily_search.py`. |
| `LANGCHAIN_API_KEY` | Optional | Empty | LangSmith tracing, when configured. |
| `LANGCHAIN_TRACING` | Optional | `true` | Sets `LANGCHAIN_TRACING_V2`. |
| `LANGCHAIN_PROJECT` | Optional | `TripPlanner` | LangSmith project name. |
| `LANGCHAIN_ENDPOINT` | Optional | `https://api.smith.langchain.com` | LangSmith endpoint. |
| `GROQ_TEXT_MODEL` | Optional | `llama-3.3-70b-versatile` | Chat model name. |
| `GROQ_TRANSCRIPTION_MODEL` | Optional | `whisper-large-v3` | Groq transcription model. |
| `KIWI_MCP_SERVER_URL` | Required for flights | `https://mcp.kiwi.com` | Kiwi MCP flight search. |
| `WEATHER_PROVIDER` | Optional | `livedatalink` | Weather provider label. |
| `WEATHER_MCP_SERVER_URL` | Required for weather | `https://livedatalink.ai/mcp` | LiveDataLink MCP weather tools. |
| `AGENTORIST_MCP_SERVER_URL` | Required for hotels | `https://mcp.agentorist.com/mcp` | Agentorist MCP hotel/local search. |
| `RECORDINGS_DIR` | Optional | `recordings` | File utility helpers. |
| `OUTPUTS_DIR` | Optional | `outputs` | Text report output helpers. |
| `LOGS_DIR` | Optional | `logs` | File utility helpers. |

Do not commit real API keys or service credentials.

# Example Usage

Run a complete planning request from Python:

```python
from services.trip_planner_service import plan_trip

result = plan_trip(
    "Plan a trip from Miami to New York for 2 travelers on 2026-08-15 "
    "visiting Madison Square Garden"
)

print(result["thread_id"])
print(result.get("final_report"))
```

Resume a graph checkpoint:

```python
from services.trip_planner_service import resume_trip

snapshot = resume_trip("trip_00000000000000000000000000000001")
print(snapshot["status"])
```

Use the multi-turn conversation service:

```python
from services.conversation_service import start_conversation, continue_conversation

start = start_conversation("Plan a trip to New York on 2026-08-15")
print(start["next_question"])

continued = continue_conversation(start["thread_id"], "Miami")
print(continued["status"])
```

Save a generated report to the configured outputs directory:

```python
from services.trip_planner_service import plan_trip
from utils.file_utils import save_text_output

result = plan_trip(
    "Plan a trip from Miami to New York on 2026-08-15 visiting Madison Square Garden"
)

path = save_text_output(result.get("final_report", ""))
print(path)
```

# Current Limitations

- The main graph is sequential and does not dynamically skip nodes based on the supervisor execution plan.
- The project provides Python service functions and notebooks, but no CLI, API server, or web UI.
- Flight results depend on the availability and response format of the Kiwi MCP server.
- Hotel results depend on Agentorist MCP data; hotel pricing is limited to returned price categories unless the provider returns more detail.
- Weather forecast range is clamped to 1-16 days by `tools/weather_tools.py`.
- Air quality lookup failures do not fail the full weather request, but they are preserved in the weather result.
- Destination research requires `TAVILY_API_KEY`; missing or failing Tavily calls return empty results with an error.
- Agent summaries depend on Groq LLM responses and may fail if `GROQ_API_KEY` is missing or the provider is unavailable.
- `local_agent` and `coordinator_agent` are implemented but not part of the compiled LangGraph workflow.
- Tests mock graph and parser behavior; they do not perform live MCP, Tavily, or Groq integration tests.

# Development Notes

LangGraph state is defined as a `TypedDict` in `state/trip_state.py`. Each agent receives the current state dictionary, copies it, adds or updates its own fields, appends errors when needed, and returns the updated state.

Checkpointing is configured by `memory/sqlite_checkpoint.py`. By default, checkpoints are stored at `memory/trip_planner.db`, and service functions pass a generated `thread_id` through LangGraph's `configurable` configuration.

Agent orchestration is implemented in `graph/trip_graph.py` with the following fixed edge order:

```text
START -> supervisor_agent -> flight_agent -> hotel_agent -> weather_agent
      -> search_agent -> itinerary_agent -> END
```

Error handling is local to each agent. Tool or LLM failures are caught, a status such as `failed` or `degraded` is written into state, and a message is appended to the `errors` list. The workflow generally continues unless required validation fails in the supervisor.

The final report formatter does not call an LLM. It assembles sections directly from the state and preserves specialist agent notes verbatim.

# Future Improvements

- Add a CLI or API server entry point for running trip planning outside notebooks or direct Python imports.
- Use supervisor output for conditional graph routing instead of always running every specialist node.
- Add live integration tests for MCP services and Tavily behind optional environment flags.
- Add structured schemas for external provider responses before LLM summarization.
- Add a license file.
- Add pinned dependency versions for repeatable installs.

# License

No license file is currently included in this repository. Add a license before distributing or accepting external contributions.
