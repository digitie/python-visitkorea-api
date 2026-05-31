from __future__ import annotations

from typing import Any

from visitkorea.cli import main
from visitkorea.models import Page


class DummyClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def search_keyword(self, keyword: str, **kwargs: Any) -> Page[dict[str, str]]:
        return Page(
            items=({"keyword": keyword, "content_type_id": str(kwargs.get("content_type_id"))},),
            total_count=1,
            page_no=1,
            num_of_rows=10,
            raw={},
        )

    def location_based_list(self, **kwargs: Any) -> Page[dict[str, str]]:
        return Page(
            items=({"radius": str(kwargs["radius"])},),
            total_count=1,
            page_no=1,
            num_of_rows=10,
            raw={},
        )

    def detail_common(self, content_id: str) -> dict[str, str]:
        return {"content_id": content_id}

    def area_codes(self, **kwargs: Any) -> Page[dict[str, str]]:
        return Page(
            items=({"area_code": str(kwargs.get("area_code"))},),
            total_count=1,
            page_no=1,
            num_of_rows=10,
            raw={},
        )


def test_cli_keyword(monkeypatch, capsys):
    monkeypatch.setattr("visitkorea.cli.KrTourApiClient", DummyClient)

    assert main(["--service-key", "KEY", "keyword", "궁", "--content-type-id", "12"]) == 0

    out = capsys.readouterr().out
    assert '"keyword": "궁"' in out
    assert '"content_type_id": "12"' in out


def test_cli_other_commands(monkeypatch, capsys):
    monkeypatch.setattr("visitkorea.cli.KrTourApiClient", DummyClient)

    assert main(["--service-key", "KEY", "location", "--map-x", "1", "--map-y", "2"]) == 0
    assert '"radius": "1000"' in capsys.readouterr().out

    assert main(["--service-key", "KEY", "detail", "126508"]) == 0
    assert '"content_id": "126508"' in capsys.readouterr().out

    assert main(["--service-key", "KEY", "area-codes", "--area-code", "1"]) == 0
    assert '"area_code": "1"' in capsys.readouterr().out


class _FakeCliClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def _page(self, **item: str) -> Page[dict[str, str]]:
        return Page(items=(item,), total_count=1, page_no=1, num_of_rows=10, raw={})

    def search_festival(self, start: str, **kw: Any) -> Page[dict[str, str]]:
        return self._page(kind="festival", start=start)

    def search_stay(self, **kw: Any) -> Page[dict[str, str]]:
        return self._page(kind="stay")

    def area_based_list(self, **kw: Any) -> Page[dict[str, str]]:
        return self._page(kind="area", ctid=str(kw.get("content_type_id")))

    def detail_pet_tour(self, content_id: str, **kw: Any) -> Page[dict[str, str]]:
        return self._page(pet=content_id)


def test_cli_new_commands(monkeypatch, capsys):
    monkeypatch.setattr("visitkorea.cli.KrTourApiClient", _FakeCliClient)

    assert main(["--service-key", "K", "festival", "20260501"]) == 0
    assert '"festival"' in capsys.readouterr().out
    assert main(["--service-key", "K", "stay"]) == 0
    assert '"stay"' in capsys.readouterr().out
    assert main(["--service-key", "K", "area-based", "--content-type-id", "12"]) == 0
    assert '"area"' in capsys.readouterr().out
    assert main(["--service-key", "K", "pet-detail", "8"]) == 0
    assert '"pet": "8"' in capsys.readouterr().out


def test_cli_catalog_needs_no_service_key(monkeypatch, capsys):
    import json as _json

    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    assert main(["catalog"]) == 0
    rows = _json.loads(capsys.readouterr().out)
    assert any(r["service_id"] == "kor" for r in rows)
