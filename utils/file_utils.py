"""File utilities for project directories, text outputs, and recordings."""

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from config.settings import PROJECT_ROOT, settings

PathLike = Union[str, Path]


def _project_path(path: PathLike) -> Path:
    """Resolve relative paths from the project root."""
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return PROJECT_ROOT / resolved


def ensure_project_dirs() -> dict[str, Path]:
    """Create configured project directories if they do not already exist."""
    directories = {
        "recordings": _project_path(settings.recordings_dir),
        "outputs": _project_path(settings.outputs_dir),
        "logs": _project_path(settings.logs_dir),
    }

    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    return directories


def save_text_output(
    text: str,
    filename: Optional[str] = None,
    output_dir: Optional[PathLike] = None,
    encoding: str = "utf-8",
) -> Path:
    """Save text output to the configured outputs directory."""
    directories = ensure_project_dirs()
    target_dir = _project_path(output_dir) if output_dir else directories["outputs"]
    target_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trip_plan_{timestamp}.txt"

    file_path = target_dir / filename
    file_path.write_text(text, encoding=encoding)
    return file_path


def read_text_file(file_path: PathLike, encoding: str = "utf-8") -> str:
    """Read and return text from a file."""
    path = _project_path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path must point to a text file: {path}")

    return path.read_text(encoding=encoding)


def audio_to_base64(audio_path: PathLike) -> str:
    """Read an audio file and return its Base64-encoded contents."""
    path = _project_path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path must point to an audio file: {path}")

    # Base64 is useful when an API expects audio as text-safe payload data.
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def get_latest_file(directory: PathLike, pattern: str = "*") -> Optional[Path]:
    """Return the most recently modified file in a directory."""
    path = _project_path(directory)

    if not path.exists():
        return None

    if not path.is_dir():
        raise ValueError(f"Path must point to a directory: {path}")

    files = [candidate for candidate in path.glob(pattern) if candidate.is_file()]
    if not files:
        return None

    return max(files, key=lambda candidate: candidate.stat().st_mtime)


def get_latest_recording(pattern: str = "*") -> Optional[Path]:
    """Return the most recent file from the configured recordings directory."""
    ensure_project_dirs()
    return get_latest_file(settings.recordings_dir, pattern=pattern)
