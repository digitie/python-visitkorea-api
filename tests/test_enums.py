from __future__ import annotations

from visitkorea import (
    AREA_CODE_TO_LDONG,
    CLASSIFICATION_SYSTEM_L1,
    LDONG_TO_AREA_CODE,
    AreaCode,
    Arrange,
    ContentType,
    CoordinateInput,
    Language,
    LDongRegnCode,
    MobileOS,
)
from visitkorea.client import KrTourApiClient
from visitkorea.enums import area_code_label, content_type_label, ldong_regn_label

from .conftest import FakeResponse, tour_payload


def test_content_type_labels():
    assert content_type_label(ContentType.TOURIST_ATTRACTION) == "관광지"
    assert content_type_label("39") == "음식점"
    assert content_type_label("999") is None
    assert area_code_label(AreaCode.SEOUL) == "서울"
    assert area_code_label("39") == "제주"
    assert area_code_label("999") is None


def test_language_maps_to_service_name():
    session_response = FakeResponse(tour_payload([]))
    from .conftest import FakeSession

    session = FakeSession([session_response])
    client = KrTourApiClient(
        "KEY",
        language=Language.ENGLISH,
        session=session,
        mobile_os=MobileOS.ETC,
    )
    client.area_codes()

    assert session.calls[0]["url"].endswith("/EngService2/areaCode2")
    assert str(Arrange.TITLE) == "A"
    assert CoordinateInput is not None


def test_ldong_regn_codes():
    assert LDongRegnCode.SEOUL == "11"
    assert LDongRegnCode.BUSAN == "26"
    assert ldong_regn_label(LDongRegnCode.SEOUL) == "서울특별시"
    assert ldong_regn_label("50") == "제주특별자치도"
    assert ldong_regn_label("999") is None


def test_area_code_to_ldong_mapping():
    assert AREA_CODE_TO_LDONG["1"] == "11"
    assert AREA_CODE_TO_LDONG["6"] == "26"
    assert LDONG_TO_AREA_CODE["11"] == "1"
    assert LDONG_TO_AREA_CODE["26"] == "6"
    assert len(AREA_CODE_TO_LDONG) == 17
    assert len(LDONG_TO_AREA_CODE) == 17


def test_classification_system_l1():
    assert CLASSIFICATION_SYSTEM_L1["HS"] == "역사관광"
    assert CLASSIFICATION_SYSTEM_L1["NA"] == "자연관광"
    assert len(CLASSIFICATION_SYSTEM_L1) == 10
