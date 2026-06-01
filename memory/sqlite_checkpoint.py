"""SQLite checkpointer configuration for LangGraph."""

from __future__ import annotations

import atexit
from pathlib import Path
from urllib.parse import unquote, urlparse

from langgraph.checkpoint.sqlite import SqliteSaver

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


def get_checkpointer(db_path: Path | str | None = None) -> SqliteSaver:
    """Return a SQLite-backed LangGraph checkpointer."""
    conn_string: str
    path: Path | None
    if isinstance(db_path, str) and db_path.startswith("sqlite:"):
        conn_string = db_path
        path = _path_from_sqlite_uri(db_path)
    else:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        conn_string = str(path.resolve())

    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(SqliteSaver, "from_conn_string"):
        saver_or_context = SqliteSaver.from_conn_string(conn_string)
        if isinstance(saver_or_context, SqliteSaver):
            return saver_or_context
        if hasattr(saver_or_context, "__enter__") and hasattr(saver_or_context, "__exit__"):
            saver = saver_or_context.__enter__()
            atexit.register(saver_or_context.__exit__, None, None, None)
            return saver
        raise TypeError(
            "Unsupported checkpointer type returned by SqliteSaver.from_conn_string."
        )

    if path is None:
        raise ValueError("SqliteSaver.from_conn_string is required for SQLite URIs.")

    return SqliteSaver(path)
