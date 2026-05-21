"""Service-key lookup helpers."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class ServiceKeySource:
    """Environment lookup policy for one upstream key source."""

    key: str
    label: str
    env_names: tuple[str, ...]
    description: str


DATA_GO_KR_ENV_NAMES: Final[tuple[str, ...]] = (
    "DATA_GO_KR_SERVICE_KEY",
)
API_VISITKOREA_ENV_NAMES: Final[tuple[str, ...]] = (
    "VISITKOREA_API_SERVICE_KEY",
    "API_VISITKOREA_SERVICE_KEY",
    "KTO_VISITKOREA_SERVICE_KEY",
)
DEFAULT_SERVICE_KEY_SOURCE: Final = "data.go.kr"
DEFAULT_ENV_FILE_NAMES: Final[tuple[str, ...]] = (".env",)

SERVICE_KEY_SOURCES: Final[dict[str, ServiceKeySource]] = {
    "data.go.kr": ServiceKeySource(
        key="data.go.kr",
        label="data.go.kr",
        env_names=DATA_GO_KR_ENV_NAMES,
        description="공공데이터포털 TourAPI 호출용 Decoding 서비스키",
    ),
    "api.visitkorea": ServiceKeySource(
        key="api.visitkorea",
        label="api.visitkorea.or.kr",
        env_names=API_VISITKOREA_ENV_NAMES,
        description="한국관광콘텐츠랩 API 호출용 서비스키가 별도로 필요할 때 사용",
    ),
}
_SERVICE_KEY_SOURCE_ALIASES: Final[dict[str, str]] = {
    "data": "data.go.kr",
    "datagokr": "data.go.kr",
    "data_go_kr": "data.go.kr",
    "data.go.kr": "data.go.kr",
    "api": "api.visitkorea",
    "api_visitkorea": "api.visitkorea",
    "api.visitkorea": "api.visitkorea",
    "api.visitkorea.or.kr": "api.visitkorea",
    "visitkorea": "api.visitkorea",
}


def normalize_service_key(value: object | None) -> str | None:
    """Remove whitespace commonly introduced while copying a service key."""

    if value is None:
        return None
    normalized = "".join(str(value).split())
    return normalized or None


def service_key_source(source: str = DEFAULT_SERVICE_KEY_SOURCE) -> ServiceKeySource:
    """Return the key-source policy for a source name or alias."""

    key = source.strip().lower().replace("-", "_")
    key = _SERVICE_KEY_SOURCE_ALIASES.get(key, key)
    try:
        return SERVICE_KEY_SOURCES[key]
    except KeyError as exc:
        known = ", ".join(sorted(SERVICE_KEY_SOURCES))
        raise ValueError(f"unknown service key source {source!r}; known: {known}") from exc


def service_key_env_names(
    source: str = DEFAULT_SERVICE_KEY_SOURCE,
    *,
    extra_names: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return environment variable names for a key source, preserving order."""

    names: list[str] = []
    for name in (*extra_names, *service_key_source(source).env_names):
        if name and name not in names:
            names.append(name)
    return tuple(names)


def resolve_service_key(
    service_key: object | None = None,
    *,
    source: str = DEFAULT_SERVICE_KEY_SOURCE,
    env_names: Iterable[str] = (),
    env_file_paths: Iterable[str | Path] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve an explicit, environment, or local `.env` service key."""

    explicit_key = normalize_service_key(service_key)
    if explicit_key:
        return explicit_key

    names = service_key_env_names(source, extra_names=env_names)
    env = os.environ if environ is None else environ
    for name in names:
        env_value = normalize_service_key(env.get(name))
        if env_value:
            return env_value

    dotenv_values = _read_dotenv_values(env_file_paths)
    for name in names:
        dotenv_value = normalize_service_key(dotenv_values.get(name))
        if dotenv_value:
            return dotenv_value
    return None


def service_key_sources() -> tuple[ServiceKeySource, ...]:
    """Return supported service-key sources."""

    return tuple(SERVICE_KEY_SOURCES.values())


def _read_dotenv_values(env_file_paths: Iterable[str | Path] | None) -> dict[str, str]:
    values: dict[str, str] = {}
    paths = _candidate_env_paths(env_file_paths)
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            values.setdefault(key, value)
    return values


def _candidate_env_paths(env_file_paths: Iterable[str | Path] | None) -> tuple[Path, ...]:
    if env_file_paths is not None:
        return tuple(Path(path) for path in env_file_paths)

    paths: list[Path] = []
    current = Path.cwd()
    for directory in (current, *current.parents):
        for name in DEFAULT_ENV_FILE_NAMES:
            path = directory / name
            if path not in paths:
                paths.append(path)
    return tuple(paths)


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    key, separator, value = stripped.partition("=")
    if not separator:
        return None
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value
