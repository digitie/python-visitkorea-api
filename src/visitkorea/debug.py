"""Shared helpers for the Streamlit debug UI and fixture generation.

These functions are intentionally decoupled from Streamlit so they stay
importable (and unit-testable) from plain Python: `examples/streamlit_debug_ui.py`
imports them instead of re-implementing jsonable/redaction/fixture logic inline.
"""

from __future__ import annotations

import json
import re
import traceback as _traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from os import PathLike
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .exceptions import TourApiError

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "x-api-key",
        "api_key",
        "apikey",
        "service_key",
        "servicekey",
        "service-key",
        "access_token",
        "refresh_token",
    }
)
_NORMALIZED_SENSITIVE_KEYS: frozenset[str] = frozenset(
    name.replace("_", "").replace("-", "") for name in SENSITIVE_KEYS
)
DEFAULT_ASSERTION: dict[str, Any] = {
    "mode": "snapshot",
    "exclude_fields": ["fetched_at", "request_id", "updated_at", "collected_at"],
    "required_fields": [],
}


@dataclass(frozen=True)
class DebugRun:
    """One debug-UI/fixture run's input, request, response, parsed, and processed data."""

    function: str
    input: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    parsed: Any
    processed: Any
    trace: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    catalog: dict[str, Any] | None = None


def jsonable(obj: Any) -> Any:
    """Convert pydantic models, dataclasses, dates, and Paths into JSON-safe values."""

    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Mapping):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in obj]
    if isinstance(obj, datetime | date):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def redact_sensitive(obj: Any) -> Any:
    """Mask API-key/token-shaped values anywhere in a dict/list structure."""

    if isinstance(obj, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in obj.items():
            text_key = str(key).replace("_", "").replace("-", "").lower()
            if text_key in _NORMALIZED_SENSITIVE_KEYS:
                redacted[str(key)] = "<REDACTED>"
            else:
                redacted[str(key)] = redact_sensitive(value)
        return redacted
    if isinstance(obj, (list, tuple)):
        return [redact_sensitive(item) for item in obj]
    return obj


def debug_error(exc: Exception) -> dict[str, Any]:
    """Turn an exception into a structured, redacted dict for UI/fixture display."""

    payload: dict[str, Any] = {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "traceback": "".join(
            _traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    }
    if isinstance(exc, TourApiError):
        payload.update(exc.metadata)
    return cast("dict[str, Any]", redact_sensitive(payload))


def save_fixture(
    *,
    base_dir: str | PathLike[str],
    function_name: str,
    case_name: str,
    description: str,
    input_data: Any,
    request_data: Any,
    response_data: Any,
    parsed_result: Any,
    processed_result: Any,
    assertion: Mapping[str, Any] | None = None,
    library_version: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Save one debug run as a pytest-replayable fixture JSON file."""

    safe_case_name = slugify_case_name(case_name)
    fixture_dir = Path(base_dir) / function_name
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / f"{safe_case_name}.json"
    if fixture_path.exists() and not overwrite:
        raise FileExistsError(f"Fixture already exists: {fixture_path}")

    fixture = {
        "name": safe_case_name,
        "function": function_name,
        "description": description,
        "input": redact_sensitive(jsonable(input_data)),
        "request": redact_sensitive(jsonable(request_data)),
        "response": redact_sensitive(jsonable(response_data)),
        "parsed": jsonable(parsed_result),
        "processed": jsonable(processed_result),
        "assertion": dict(assertion or DEFAULT_ASSERTION),
        "meta": {
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "library_version": library_version,
            "source": "debug_ui",
        },
    }
    with fixture_path.open("w", encoding="utf-8") as handle:
        json.dump(fixture, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return fixture_path


def slugify_case_name(value: str) -> str:
    """Loosely normalize a case name so it is safe to use as a filename."""

    cleaned = value.strip().lower()
    slug = re.sub(r"[^\w.-]+", "-", cleaned, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-._")
    return slug or "case"
