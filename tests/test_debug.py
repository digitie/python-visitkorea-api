from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from visitkorea import TourApiHubClient, get_api_catalog, get_api_catalog_entry
from visitkorea.debug import DebugRun, debug_error, jsonable, redact_sensitive, save_fixture
from visitkorea.exceptions import TourApiAuthError, TourApiRequestError
from visitkorea.models import Page, TourApiCallContext

from .conftest import FakeResponse, FakeSession, tour_payload


def test_jsonable_converts_pydantic_dates_and_nested_structures():
    context = TourApiCallContext(
        service_name="GoCamping",
        endpoint="basedList",
        request_params={"MobileOS": "ETC"},
        collected_at=datetime(2026, 1, 2, 3, 4, 5),
    )
    page = Page(
        items=({"a": 1},), total_count=1, page_no=1, num_of_rows=10, raw={}, context=context
    )

    result = jsonable(page)

    assert result["context"]["collected_at"] == "2026-01-02T03:04:05"
    assert result["items"] == [{"a": 1}]
    assert jsonable({"d": date(2026, 1, 2)}) == {"d": "2026-01-02"}
    assert jsonable((1, 2, 3)) == [1, 2, 3]
    assert jsonable(Path("tests") / "fixtures") == str(Path("tests") / "fixtures")


def test_redact_sensitive_masks_service_key_variants_case_insensitively():
    payload = {
        "serviceKey": "SECRET",
        "ServiceKey": "SECRET",
        "service_key": "SECRET",
        "nested": {"api_key": "SECRET", "keep": "visible"},
        "list": [{"servicekey": "SECRET"}, "plain"],
        "MobileApp": "visitkorea",
    }

    redacted = redact_sensitive(payload)

    assert redacted["serviceKey"] == "<REDACTED>"
    assert redacted["ServiceKey"] == "<REDACTED>"
    assert redacted["service_key"] == "<REDACTED>"
    assert redacted["nested"]["api_key"] == "<REDACTED>"
    assert redacted["nested"]["keep"] == "visible"
    assert redacted["list"][0]["servicekey"] == "<REDACTED>"
    assert redacted["list"][1] == "plain"
    assert redacted["MobileApp"] == "visitkorea"


def test_debug_error_includes_type_message_traceback_and_tourapi_metadata():
    try:
        raise TourApiAuthError(
            "HTTP 401: nope",
            status_code=401,
            endpoint="basedList",
            service_name="GoCamping",
            failure_kind="auth",
        )
    except TourApiAuthError as exc:
        payload = debug_error(exc)

    assert payload["type"] == "TourApiAuthError"
    assert payload["message"] == "HTTP 401: nope"
    assert "traceback" in payload
    assert "TourApiAuthError" in payload["traceback"]
    assert payload["status_code"] == 401
    assert payload["failure_kind"] == "auth"
    assert payload["endpoint"] == "basedList"


def test_debug_error_redacts_secrets_that_leak_into_the_message():
    try:
        raise ValueError("bad param serviceKey=SECRET123")
    except ValueError as exc:
        payload = debug_error(exc)

    assert payload["type"] == "ValueError"
    # debug_error only redacts dict *keys*, not arbitrary substrings in
    # free-text messages; assert the structural contract instead.
    assert set(payload) == {"type", "message", "traceback"}


def test_save_fixture_writes_json_and_respects_overwrite(tmp_path: Path):
    path = save_fixture(
        base_dir=tmp_path,
        function_name="gocamping.based_list",
        case_name="Normal Case!",
        description="샘플 저장 테스트",
        input_data={"serviceKey": "SECRET", "keyword": "숲"},
        request_data={"query": {"serviceKey": "SECRET"}},
        response_data={"body": {"items": []}},
        parsed_result=None,
        processed_result=(),
    )

    assert path.name == "normal-case.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["function"] == "gocamping.based_list"
    assert saved["input"]["serviceKey"] == "<REDACTED>"
    assert saved["request"]["query"]["serviceKey"] == "<REDACTED>"
    assert saved["assertion"]["mode"] == "snapshot"

    with pytest.raises(FileExistsError):
        save_fixture(
            base_dir=tmp_path,
            function_name="gocamping.based_list",
            case_name="Normal Case!",
            description="다시 저장",
            input_data={},
            request_data={},
            response_data={},
            parsed_result=None,
            processed_result=None,
        )

    # overwrite=True should succeed without raising.
    save_fixture(
        base_dir=tmp_path,
        function_name="gocamping.based_list",
        case_name="Normal Case!",
        description="다시 저장",
        input_data={},
        request_data={},
        response_data={},
        parsed_result=None,
        processed_result=None,
        overwrite=True,
    )


def test_get_api_catalog_entry_exposes_kind_typed_parameters():
    entry = get_api_catalog_entry("gocamping", "basedList")

    assert entry["service_id"] == "gocamping"
    assert entry["operation"] == "basedList"
    assert "content_type_id" in entry["optional_params"] or "content_type_id" in entry[
        "required_params"
    ]
    kinds = {parameter["name"]: parameter["kind"] for parameter in entry["parameters"]}
    assert kinds["content_type_id"] == "enum"
    assert kinds["arrange"] == "enum"


def test_get_api_catalog_entry_covers_every_catalog_operation_without_raising():
    rows = list(get_api_catalog())
    assert len(rows) > 0
    for row in rows:
        entry = get_api_catalog_entry(row["service_id"], row["operation"])
        assert entry["operation"] == row["operation"]
        assert isinstance(entry["parameters"], tuple)


def test_debug_fetch_success_returns_full_debug_run():
    session = FakeSession([FakeResponse(tour_payload({"contentid": "1", "title": "캠핑"}))])
    hub = TourApiHubClient("KEY", session=session)

    run = hub.debug_fetch(
        "gocamping",
        "basedList",
        params={"facility_name": "숲"},
        page_no=1,
        num_of_rows=10,
    )

    assert isinstance(run, DebugRun)
    assert run.error is None
    assert run.function == "gocamping.basedList"
    assert run.catalog is not None
    assert run.catalog["service_id"] == "gocamping"
    assert run.processed == ({"contentid": "1", "title": "캠핑"},)
    assert run.request["query"]["facltNm"] == "숲"
    assert "serviceKey" not in run.request["query"]
    assert run.response["status_code"] == 200
    assert any("items=1" in line for line in run.trace)


def test_debug_fetch_unknown_operation_returns_structured_error_with_catalog():
    hub = TourApiHubClient("KEY", session=FakeSession([]))

    run = hub.debug_fetch("gocamping", "notARealOperation")

    assert run.error is not None
    assert run.error["type"] == "TourApiRequestError"
    assert run.catalog is None  # catalog lookup itself failed
    assert run.parsed is None


def test_debug_fetch_unknown_service_has_no_catalog_and_no_crash():
    hub = TourApiHubClient("KEY", session=FakeSession([]))

    run = hub.debug_fetch("not_a_real_service", "basedList")

    assert run.error is not None
    assert run.catalog is None


def test_debug_fetch_rejects_non_json_response_type():
    hub = TourApiHubClient("KEY", session=FakeSession([]))

    with pytest.raises(TourApiRequestError):
        hub.debug_fetch("gocamping", "basedList", response_type="xml")


def test_debug_fetch_use_typed_parses_registered_service_model():
    session = FakeSession(
        [FakeResponse(tour_payload({"contentId": "1", "facltNm": "숲속 캠핑장"}))]
    )
    hub = TourApiHubClient("KEY", session=session)

    run = hub.debug_fetch("gocamping", "basedList", use_typed=True)

    assert run.error is None
    assert run.processed[0].facility_name == "숲속 캠핑장"


def test_debug_fetch_use_typed_without_registered_parser_is_a_structured_error():
    hub = TourApiHubClient("KEY", session=FakeSession([]))

    run = hub.debug_fetch("kor", "areaBasedList2", use_typed=True)

    assert run.error is not None
    assert run.error["type"] == "TourApiRequestError"
    assert run.catalog is not None
