from __future__ import annotations

import os
from typing import Any

import pytest

from visitkorea import (
    ContentType,
    GoCampingItem,
    KrTourApiClient,
    TokenBucketRateLimiter,
    TourApiHubClient,
)
from visitkorea.exceptions import TourApiAuthError, TourApiError, TourApiNoDataError

pytestmark = pytest.mark.live


def _service_key() -> str:
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
    return key


def _kor_client(**kwargs: Any) -> KrTourApiClient:
    return KrTourApiClient(_service_key(), mobile_app="visitkorea-live-test", timeout=20, **kwargs)


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


def test_live_search_keyword_and_detail_chain():
    client = _kor_client()

    page = client.search_keyword(
        "경복궁",
        content_type_id=ContentType.TOURIST_ATTRACTION,
        num_of_rows=3,
    )

    assert page.context.endpoint == "searchKeyword2"
    assert page.total_count >= len(page.items)
    if page.is_empty or not page.items[0].content_id:
        pytest.skip("no live keyword result to chain a detail lookup")

    item = page.items[0]
    assert item.raw

    detail = client.detail_common(item.content_id)
    assert detail.content_id == item.content_id
    assert detail.context.endpoint == "detailCommon2"
    assert "serviceKey" not in detail.context.request_params


def test_live_detail_pet_tour_returns_page_shape():
    client = _kor_client()

    page = client.search_keyword("반려견", num_of_rows=3)
    if page.is_empty or not page.items[0].content_id:
        pytest.skip("no live content id to query detailPetTour2")

    try:
        pet_page = client.detail_pet_tour(page.items[0].content_id)
    except TourApiNoDataError:
        return

    assert pet_page.context.endpoint == "detailPetTour2"
    for info in pet_page.items:
        assert info.content_id is not None
        assert info.raw


def test_live_retry_and_rate_limiter_plumbing_succeeds():
    client = _kor_client(
        max_retries=2,
        backoff_factor=0.2,
        rate_limiter=TokenBucketRateLimiter(rate=5, per=1.0),
    )

    page = client.area_codes(num_of_rows=3)

    assert page.context.endpoint == "areaCode2"
    assert page.total_count >= len(page.items)


def test_live_code_cache_returns_same_page_instance():
    cache: dict = {}
    client = _kor_client(code_cache=cache)

    first = client.area_codes(num_of_rows=3)
    second = client.area_codes(num_of_rows=3)

    assert second is first
    assert len(cache) == 1


def test_live_typed_hub_view_or_auth_error():
    hub = TourApiHubClient(_service_key(), mobile_app="visitkorea-live-test", timeout=20)

    try:
        page = hub.gocamping.typed.based_list(num_of_rows=3)
    except TourApiAuthError:
        pytest.skip("GoCamping service is not subscribed for this key")
    except TourApiError as exc:  # pragma: no cover - depends on live service state
        pytest.skip(f"GoCamping live call unavailable: {exc.failure_kind}")

    assert page.context.service_name == "GoCamping"
    for item in page.items:
        assert isinstance(item, GoCampingItem)
        assert item.raw
