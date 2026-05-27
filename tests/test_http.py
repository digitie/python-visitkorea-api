from __future__ import annotations

import pytest

from visitkorea._http import DEFAULT_USER_AGENT, TourApiHttp, build_session, tourapi_request_params
from visitkorea.client import KrTourApiClient
from visitkorea.enums import MobileOS
from visitkorea.exceptions import (
    TourApiAuthError,
    TourApiError,
    TourApiNoDataError,
    TourApiParseError,
    TourApiRateLimitError,
    TourApiRequestError,
    TourApiServerError,
)

from .conftest import FakeResponse, FakeSession, tour_payload


def assert_error_metadata(
    exc: TourApiError,
    *,
    failure_kind: str,
    endpoint: str = "areaCode2",
    service_name: str = "KorService2",
    status_code: int | None = None,
    result_code: str | None = None,
) -> None:
    assert exc.failure_kind == failure_kind
    assert exc.endpoint == endpoint
    assert exc.service_name == service_name
    assert exc.status_code == status_code
    assert exc.result_code == result_code
    metadata = exc.metadata
    assert metadata["failure_kind"] == failure_kind
    assert "TEST_KEY" not in str(exc)
    assert "TEST_KEY" not in repr(exc)
    assert "TEST_KEY" not in repr(metadata)


def test_common_request_params_and_endpoint_url(fake_client_factory):
    client, session = fake_client_factory(
        FakeResponse(tour_payload([])),
        mobile_app="UnitTest",
        mobile_os=MobileOS.WEB,
    )

    page = client.area_codes()

    assert page.items == ()
    call = session.calls[0]
    assert call["url"] == "http://apis.data.go.kr/B551011/KorService2/areaCode2"
    assert call["params"]["serviceKey"] == "TEST_KEY"
    assert call["params"]["MobileOS"] == "WEB"
    assert call["params"]["MobileApp"] == "UnitTest"
    assert call["params"]["_type"] == "json"
    assert call["params"]["pageNo"] == 1
    assert "areaCode" not in call["params"]


def test_service_key_whitespace_is_removed_before_request():
    session = FakeSession([FakeResponse(tour_payload([]))])
    client = KrTourApiClient(" \n TEST\t_KEY \r\n", session=session)

    client.area_codes()

    assert client.service_key == "TEST_KEY"
    assert session.calls[0]["params"]["serviceKey"] == "TEST_KEY"

    params = tourapi_request_params(
        service_key=" A B\nC ",
        mobile_os="WEB",
        mobile_app="UnitTest",
        params={"serviceKey": " X\tY "},
    )
    assert params["serviceKey"] == "XY"


def test_non_json_xml_service_key_error_maps_to_auth(fake_client_factory):
    xml = """
    <OpenAPI_ServiceResponse>
      <cmmMsgHeader>
        <errMsg>SERVICE ERROR</errMsg>
        <returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>
        <returnReasonCode>30</returnReasonCode>
      </cmmMsgHeader>
    </OpenAPI_ServiceResponse>
    """
    client, _session = fake_client_factory(
        FakeResponse(text=xml, json_error=ValueError("not json")),
    )

    with pytest.raises(TourApiAuthError, match="SERVICE_KEY_IS_NOT_REGISTERED_ERROR") as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="auth", result_code="30")


def test_result_code_03_returns_empty_page(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(tour_payload(None, result_code="03", result_msg="NO_DATA")),
    )

    page = client.area_codes()

    assert page.is_empty
    assert page.total_count == 0


def test_result_code_0000_is_treated_as_success(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(tour_payload([], result_code="0000", result_msg="OK")),
    )

    page = client.area_codes()

    assert page.items == ()


def test_http_and_header_error_mapping(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse({}, status_code=429, text="too many"))
    with pytest.raises(TourApiRateLimitError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="rate_limit", status_code=429)

    client, _session = fake_client_factory(
        FakeResponse(
            {
                "response": {
                    "header": {"resultCode": "99", "resultMsg": "SERVER_ERROR"},
                    "body": {},
                }
            }
        )
    )
    with pytest.raises(TourApiServerError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="server", result_code="99")


def test_unregistered_ip_error_maps_to_auth_error(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(
            {
                "response": {
                    "header": {"resultCode": "32", "resultMsg": "UNREGISTERED_IP_ERROR"},
                    "body": {},
                }
            }
        )
    )
    with pytest.raises(TourApiAuthError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="auth", result_code="32")


def test_malformed_items_shape_raises_parse_error(fake_client_factory):
    payload = tour_payload("not-a-dict")
    client, _session = fake_client_factory(FakeResponse(payload))

    with pytest.raises(TourApiParseError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")


def test_build_session_and_empty_service_key():
    session = build_session(retries=0)
    try:
        assert session is not None
        assert session.headers["User-Agent"] == DEFAULT_USER_AGENT
    finally:
        session.close()
    retry_session = build_session(retries=1)
    try:
        assert retry_session is not None
    finally:
        retry_session.close()

    with pytest.raises(TourApiAuthError):
        TourApiHttp(
            "",
            base_url="http://example.com",
            service_name="KorService2",
            mobile_os="ETC",
            mobile_app="test",
        )


def test_more_http_error_branches(fake_client_factory):
    client, _session = fake_client_factory(FakeResponse("not-object"))
    with pytest.raises(TourApiParseError, match="root") as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")

    client, _session = fake_client_factory(FakeResponse({"response": {}}))
    with pytest.raises(TourApiParseError, match="response.header") as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")

    client, _session = fake_client_factory(
        FakeResponse({"response": {"header": {"resultCode": "00"}, "body": []}})
    )
    with pytest.raises(TourApiParseError, match="body") as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")

    client, _session = fake_client_factory(
        FakeResponse({}, status_code=401, text="denied TEST_KEY")
    )
    with pytest.raises(TourApiAuthError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="auth", status_code=401)

    client, _session = fake_client_factory(FakeResponse({}, status_code=403, text="forbidden"))
    with pytest.raises(TourApiAuthError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="auth", status_code=403)

    client, _session = fake_client_factory(FakeResponse({}, status_code=400, text="bad TEST_KEY"))
    with pytest.raises(TourApiRequestError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="request", status_code=400)

    client, _session = fake_client_factory(FakeResponse({}, status_code=500, text="down TEST_KEY"))
    with pytest.raises(TourApiServerError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="server", status_code=500)


def test_non_xml_json_parse_error_stays_parse_error(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(text="not xml", json_error=ValueError("bad json")),
    )

    with pytest.raises(TourApiParseError, match="not valid JSON") as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")


def test_json_openapi_service_response_errors(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(
            {
                "OpenAPI_ServiceResponse": {
                    "cmmMsgHeader": {
                        "returnReasonCode": "22",
                        "returnAuthMsg": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR",
                    }
                }
            }
        )
    )
    with pytest.raises(TourApiRateLimitError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="rate_limit", result_code="22")

    client, _session = fake_client_factory(FakeResponse({"OpenAPI_ServiceResponse": []}))
    with pytest.raises(TourApiParseError) as exc_info:
        client.area_codes()
    assert_error_metadata(exc_info.value, failure_kind="parse")


def test_json_result_code_request_error_metadata(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(
            {
                "response": {
                    "header": {
                        "resultCode": "10",
                        "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR",
                    },
                    "body": {},
                }
            }
        )
    )

    with pytest.raises(TourApiRequestError) as exc_info:
        client.area_codes()

    assert_error_metadata(exc_info.value, failure_kind="request", result_code="10")


def test_detail_no_data_error_metadata(fake_client_factory):
    client, _session = fake_client_factory(
        FakeResponse(tour_payload(None, result_code="03", result_msg="NO_DATA")),
    )

    with pytest.raises(TourApiNoDataError) as exc_info:
        client.detail_common("missing")

    assert_error_metadata(
        exc_info.value,
        failure_kind="no_data",
        endpoint="detailCommon2",
        result_code="03",
    )
