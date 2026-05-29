# Multi-Agent Trip Planner

A minimal, hackathon-friendly Python project for a LangGraph-based trip planner that runs first from Jupyter Notebook.

## Stack

- LangGraph for orchestration
- LangChain for agent/model interfaces
- Groq for text generation and audio transcription
- Tavily for web search
- MCP server wrappers for:
  - Kiwi Flight Search MCP
  - Gribstream Weather MCP
  - Agentorist Hotel MCP

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add your API keys and MCP server values to `.env`.
4. Start Jupyter and open `notebooks/trip_planner.ipynb`.

```bash
jupyter notebook
```

## Environment Variables

The `.env` file stores all API and server configuration:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_TEXT_MODEL=llama-3.3-70b-versatile
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
TAVILY_API_KEY=your_tavily_api_key_here
KIWI_MCP_SERVER_URL=your_kiwi_flight_search_mcp_server_url_here
GRIBSTREAM_MCP_SERVER_URL=your_gribstream_weather_mcp_server_url_here
AGENTORIST_MCP_SERVER_URL=your_agentorist_hotel_mcp_server_url_here
```

## Notes

The MCP tool files are intentionally placeholders. Wire each wrapper to your MCP client once the corresponding servers are available in your environment.
