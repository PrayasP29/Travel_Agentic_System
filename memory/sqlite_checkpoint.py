"""SQLite checkpointer configuration for LangGraph."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "memory" / "trip_planner.db"


def _path_from_sqlite_uri(conn_string: str) -> Path | None:
    parsed = urlparse(conn_string)
    if parsed.scheme != "sqlite":
        return None

    raw_path = unquote(parsed.path or "")
    if not raw_path or raw_path in (":memory:", "/:memory:"):
        return None

    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path[1:]

    return Path(raw_path)


async def get_checkpointer(db_path: Path | str | None = None) -> AsyncSqliteSaver:
    """Return an async SQLite-backed LangGraph checkpointer."""
    conn_str: str
    path: Path | None
    if isinstance(db_path, str) and db_path.startswith("sqlite:"):
        path = _path_from_sqlite_uri(db_path)
        conn_str = str(path) if path else ":memory:"
    else:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        conn_str = str(path.resolve())

    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(conn_str)
    return AsyncSqliteSaver(conn)
