from __future__ import annotations

import os

import pytest

from visitkorea import KrTourApiClient, TourApiHubClient
from visitkorea.exceptions import TourApiAuthError

pytestmark = pytest.mark.live


def _service_key() -> str:
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
    return key


def test_live_korean_area_codes_returns_tourapi_shape():
    key = _service_key()
    client = KrTourApiClient(
        key,
        mobile_app="visitkorea-live-test",
        timeout=20,
    )

    page = client.area_codes(num_of_rows=5)

    assert page.page_no >= 1
    assert page.num_of_rows >= 1
    assert page.total_count >= len(page.items)
    assert isinstance(page.raw, dict)
    assert page.context.service_name == "KorService2"
    assert page.context.endpoint == "areaCode2"
    assert page.context.request_params["MobileApp"] == "visitkorea-live-test"
    assert page.context.request_params["numOfRows"] == 5
    assert page.context.collected_at is not None
    assert "serviceKey" not in page.context.request_params
    assert key not in repr(page.context.request_params)
    for item in page.items:
        assert item.raw


def test_live_unsubscribed_foreign_service_maps_to_auth_error():
    key = _service_key()
    hub = TourApiHubClient(
        key,
        mobile_app="visitkorea-live-test",
        timeout=20,
    )

    with pytest.raises(TourApiAuthError, match="403|SERVICE|AUTH|KEY|SERVICE_KEY") as exc_info:
        hub.eng.area_code(num_of_rows=1)

    exc = exc_info.value
    assert exc.failure_kind == "auth"
    assert exc.endpoint == "areaCode2"
    assert exc.service_name == "EngService2"
    assert key not in str(exc)
    assert key not in repr(exc)
    assert key not in repr(exc.metadata)
