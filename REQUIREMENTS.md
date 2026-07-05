# Requirements

## Core AI / LLM Framework

| Package | Version | Purpose |
|---|---|---|
| langchain | 1.3.1 | LLM application framework |
| langchain-core | 1.4.0 | Core LangChain abstractions |
| langchain-community | 0.4.2 | Community integrations |
| langchain-groq | 1.1.2 | Groq LLM provider |
| langgraph | 1.2.1 | Agent workflow orchestration |
| langgraph-checkpoint | 4.1.1 | Graph state persistence |
| langgraph-prebuilt | 1.1.0 | Pre-built graph components |
| langgraph-sdk | 0.3.12 | LangGraph cloud SDK |
| langsmith | 0.8.5 | Tracing and monitoring |
| groq | 0.37.1 | Groq API client |

## LLM Providers

| Package | Version | Purpose |
|---|---|---|
| openai | 2.30.0 | OpenAI API client |
| ollama | 0.6.1 | Ollama local LLM client |
| langchain-openai | 1.1.12 | OpenAI LangChain integration |
| langchain-nvidia-ai-endpoints | 1.4.1 | NVIDIA NIM integration |

## MCP (Model Context Protocol)

| Package | Version | Purpose |
|---|---|---|
| mcp | 1.27.1 | MCP client/server for tool integration |
| httpx-sse | 0.4.3 | SSE transport for MCP |

## Search & Data Retrieval

| Package | Version | Purpose |
|---|---|---|
| tavily-python | 0.7.24 | Web search API for AI agents |
| wikipedia | (bundled) | Wikipedia data (via langchain) |

## Data Processing & Validation

| Package | Version | Purpose |
|---|---|---|
| pydantic | 2.13.4 | Data validation & settings |
| pydantic-core | 2.46.4 | Pydantic core engine |
| pydantic-settings | 2.14.1 | Environment-based settings |
| numpy | 2.4.6 | Numerical computing |
| pandas | 3.0.3 | Data manipulation & analysis |

## HTTP & Networking

| Package | Version | Purpose |
|---|---|---|
| httpx | 0.28.1 | Async HTTP client |
| requests | 2.32.5 | HTTP client |
| urllib3 | 1.26.20 | HTTP library (requests dep) |
| aiohttp | 3.13.5 | Async HTTP server/client |
| yarl | 1.23.0 | URL manipulation |
| anyio | 4.12.0 | Async networking |
| httpcore | 1.0.9 | HTTP transport (httpx dep) |
| h11 | 0.16.0 | HTTP/1.1 protocol |
| sniffio | 1.3.1 | Async library detection |
| certifi | 2025.11.12 | SSL certificates |
| charset-normalizer | 3.4.4 | Character encoding |
| idna | 3.11 | Internationalized domain names |

## Web Framework

| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.115.0 | Web API framework |
| uvicorn | 0.32.1 | ASGI server |
| starlette | 0.38.6 | ASGI framework (FastAPI dep) |
| sse-starlette | 3.4.4 | Server-Sent Events for FastAPI |
| python-multipart | 0.0.22 | Multipart form parsing |
| websockets | 10.4 | WebSocket support |
| httptools | 0.7.1 | HTTP request parser |
| watchfiles | 1.1.1 | File watcher (hot reload) |

## Database & Persistence

| Package | Version | Purpose |
|---|---|---|
| SQLAlchemy | 2.0.36 | SQL ORM |
| alembic | 1.13.1 | Database migrations |
| pymongo | 4.16.0 | MongoDB driver |
| psycopg2-binary | 2.9.11 | PostgreSQL driver |
| sqlite-utils | 3.39 | SQLite utilities |

## Vector Database

| Package | Version | Purpose |
|---|---|---|
| chromadb | 1.5.9 | Vector database |
| onnxruntime | 1.27.0 | ONNX model runtime (chroma dep) |
| flatbuffers | 25.12.19 | Serialization (chroma dep) |
| mmh3 | 5.2.1 | Hashing (chroma dep) |
| PyPika | 0.51.1 | SQL builder (chroma dep) |

## Embeddings & Tokenization

| Package | Version | Purpose |
|---|---|---|
| tiktoken | 0.12.0 | OpenAI tokenizer |
| tokenizers | 0.23.1 | Fast tokenization |
| huggingface-hub | 1.19.0 | HuggingFace model hub |

## Audio / Transcription

| Package | Version | Purpose |
|---|---|---|
| sounddevice | 0.5.5 | Audio recording |
| numpy | 2.4.6 | Audio data handling |

## Documents & File Parsing

| Package | Version | Purpose |
|---|---|---|
| unstructured | 0.23.1 | Document parsing |
| pypdf | 6.13.2 | PDF parsing |
| pypdfium2 | 5.10.1 | PDF rendering |
| python-magic | 0.4.27 | File type detection |
| python-oxmsg | 0.0.2 | Outlook .msg parsing |
| olefile | 0.47 | OLE file parsing |
| pillow | 12.0.0 | Image processing |
| lxml | 6.1.1 | XML/HTML parsing |
| beautifulsoup4 | 4.14.3 | HTML parsing |
| markdown-it-py | 4.0.0 | Markdown parsing |
| langdetect | 1.0.9 | Language detection |
| html5lib | 1.1 | HTML parsing |
| tabulate | 0.10.0 | Table formatting |
| emoji | 2.15.0 | Emoji handling |

## Jupyter / Notebooks

| Package | Version | Purpose |
|---|---|---|
| jupyter | 1.1.1 | Jupyter notebook |
| jupyterlab | 4.5.7 | JupyterLab IDE |
| notebook | 7.5.6 | Classic notebook |
| ipykernel | 7.2.0 | Python kernel |
| ipython | 9.13.0 | Interactive Python |
| ipywidgets | 8.1.8 | Interactive widgets |
| nbconvert | 7.17.1 | Notebook conversion |
| nbformat | 5.10.4 | Notebook file format |

## Testing

| Package | Version | Purpose |
|---|---|---|
| pytest | 8.2.1 | Test framework |
| pytest-asyncio | 0.23.7 | Async test support |
| mypy | 1.19.1 | Static type checking |
| black | 25.12.0 | Code formatting |

## Developer Tools

| Package | Version | Purpose |
|---|---|---|
| python-dotenv | 1.0.1 | Environment file loading |
| typer | 0.25.1 | CLI argument parser |
| rich | 14.3.3 | Terminal formatting |
| textual | 8.2.1 | TUI framework |
| click | 8.4.1 | CLI framework |
| PyYAML | 6.0.3 | YAML config files |
| psutil | 7.2.2 | System/process utilities |
| tqdm | 4.68.2 | Progress bars |
| tenacity | 8.3.0 | Retry logic |
| orjson | 3.11.8 | Fast JSON parsing |
| wrapt | 2.2.1 | Decorator utilities |
| colorama | 0.4.6 | Terminal colors |
| bcrypt | 5.0.0 | Password hashing |
| cryptography | 48.0.0 | Encryption |

## NLP / spaCy

| Package | Version | Purpose |
|---|---|---|
| spacy | 3.8.14 | NLP pipeline |
| thinc | 8.3.13 | ML library (spacy dep) |
| preshed | 3.0.13 | Cython hash tables |
| blis | 1.3.3 | BLAS linear algebra |
| murmurhash | 1.0.15 | Hashing |
| cymem | 2.0.13 | C memory management |
| srsly | 2.5.3 | Serialization |
| wasabi | 1.1.3 | Terminal output formatting |
| confection | 1.3.3 | Configuration system |
| catalogue | 2.0.10 | Function registry |
| weasel | 1.0.0 | Project system |
| ngram | (bundled) | N-gram utils |

## Monitoring & Observability

| Package | Version | Purpose |
|---|---|---|
| opentelemetry-api | 1.42.1 | OpenTelemetry API |
| opentelemetry-sdk | 1.42.1 | OpenTelemetry SDK |
| opentelemetry-exporter-otlp-proto-grpc | 1.42.1 | OTLP gRPC exporter |
| opentelemetry-exporter-otlp-proto-common | 1.42.1 | OTLP common protos |
| opentelemetry-proto | 1.42.1 | OTLP protobuf definitions |

## Cloud & Services

| Package | Version | Purpose |
|---|---|---|
| kagglehub | 0.3.13 | Kaggle dataset download |
| kubernetes | 36.0.2 | k8s API client |
| googleapis-common-protos | 1.75.0 | Google API protos |
| protobuf | 6.33.2 | Protocol Buffers |
| jsonpatch | 1.33 | JSON patch operations |
| deprecation | 2.1.0 | Deprecation notices |

## Transitive Dependencies (notable)

| Package | Version | Purpose |
|---|---|---|
| fsspec | 2026.6.0 | Filesystem abstraction |
| frozenlist | 1.8.0 | Immutable lists |
| multidict | 6.7.1 | Multi-value dicts |
| propcache | 0.4.1 | Property caching |
| aiosignal | 1.4.0 | Async signal handling |
| greenlet | 3.3.2 | Coroutine support |
| packaging | 26.2 | Package version utils |
| platformdirs | 4.5.1 | Platform directories |
| pluggy | 1.6.0 | Plugin hook engine |
| referencing | 0.37.0 | JSON Schema references |
| regex | 2026.2.28 | Regular expressions |
| rpds-py | 0.30.0 | Rust persistent data structures |
| six | 1.17.0 | Python 2/3 compat |
| typing-extensions | 4.15.0 | Type hints backport |
| tzdata | 2025.3 | Timezone database |
| zstandard | 0.25.0 | Zstandard compression |

## Key Indirect Dependencies (automatically installed)

- `aiofiles`, `attrs`, `babel`, `bleach`, `decorator`, `defusedxml`, `distro`, `executing`, `fastjsonschema`, `filelock`, `fqdn`, `future`, `importlib-resources`, `iniconfig`, `isoduration`, `jedi`, `Jinja2`, `json5`, `jsonschema`, `jupyter-client`, `jupyter-core`, `jupyter-events`, `jupyter-server`, `jupyter-server-terminals`, `lark`, `linkify-it-py`, `Mako`, `MarkupSafe`, `marshmallow`, `matplotlib-inline`, `mdit-py-plugins`, `mdurl`, `mistune`, `msgpack`, `nbclient`, `nest-asyncio`, `oauthlib`, `overrides`, `parso`, `pathspec`, `prometheus-client`, `prompt-toolkit`, `pure-eval`, `pycparser`, `Pygments`, `PyJWT`, `pyproject-hooks`, `pyte`, `python-dateutil`, `python-json-logger`, `python-slugify`, `pytz`, `pywin32`, `pywinpty`, `pyzmq`, `qrcode`, `RapidFuzz`, `ratelim`, `requests-oauthlib`, `requests-toolbelt`, `rfc3339-validator`, `rfc3986-validator`, `rfc3987-syntax`, `scipy`, `semantic-version`, `Send2Trash`, `setuptools-rust`, `shellingham`, `smart-open`, `soupsieve`, `stack-data`, `terminado`, `text-unidecode`, `tinycss2`, `tornado`, `traitlets`, `types-requests`, `types-tqdm`, `typing-inspect`, `typing-inspection`, `uc-micro-py`, `uri-template`, `wcwidth`, `webcolors`, `webencodings`, `websocket-client`, `wheel`, `widgetsnbextension`, `xxhash`
