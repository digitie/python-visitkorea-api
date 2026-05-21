from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_local_markdown_links_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)", readme)

    missing: list[str] = []
    for link in links:
        if "://" in link:
            continue
        target = link.split("#", 1)[0]
        if not (ROOT / target).exists():
            missing.append(link)

    assert missing == []


def test_user_docs_cover_public_model_usage() -> None:
    user_guide = (ROOT / "docs" / "user-guide.md").read_text(encoding="utf-8")
    pydantic_guide = (ROOT / "docs" / "pydantic-models.md").read_text(encoding="utf-8")

    for term in (
        "KrTourApiClient",
        "TourApiHubClient",
        "PlaceCoordinate",
        "model_dump",
        "DATA_GO_KR_SERVICE_KEY",
    ):
        assert term in user_guide

    for term in (
        "TourApiModel",
        "model_dump_json",
        "model_json_schema",
        "model_copy",
        "raw",
    ):
        assert term in pydantic_guide
