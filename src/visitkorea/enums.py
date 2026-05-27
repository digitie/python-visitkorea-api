"""Public constants and enum helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class MobileOS(StrEnum):
    """TourAPI MobileOS parameter values."""

    IOS = "IOS"
    ANDROID = "AND"
    WEB = "WEB"
    WINDOWS_PHONE = "WIN"
    ETC = "ETC"


class Language(StrEnum):
    """TourAPI language service selectors."""

    KOREAN = "ko"
    ENGLISH = "en"
    JAPANESE = "ja"
    SIMPLIFIED_CHINESE = "zh-cn"
    TRADITIONAL_CHINESE = "zh-tw"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    RUSSIAN = "ru"


class Arrange(StrEnum):
    """TourAPI arrange parameter values."""

    TITLE = "A"
    MODIFIED = "C"
    CREATED = "D"
    DISTANCE = "E"
    TITLE_WITH_IMAGE = "O"
    MODIFIED_WITH_IMAGE = "Q"
    CREATED_WITH_IMAGE = "R"
    DISTANCE_WITH_IMAGE = "S"


class ContentType(StrEnum):
    """KorService2 content type IDs."""

    TOURIST_ATTRACTION = "12"
    CULTURAL_FACILITY = "14"
    FESTIVAL = "15"
    TRAVEL_COURSE = "25"
    LEISURE_SPORTS = "28"
    ACCOMMODATION = "32"
    SHOPPING = "38"
    RESTAURANT = "39"


class AreaCode(StrEnum):
    """KorService2 areaCode values."""

    SEOUL = "1"
    INCHEON = "2"
    DAEJEON = "3"
    DAEGU = "4"
    GWANGJU = "5"
    BUSAN = "6"
    ULSAN = "7"
    SEJONG = "8"
    GYEONGGI = "31"
    GANGWON = "32"
    CHUNGBUK = "33"
    CHUNGNAM = "34"
    GYEONGBUK = "35"
    GYEONGNAM = "36"
    JEONBUK = "37"
    JEONNAM = "38"
    JEJU = "39"


CONTENT_TYPE_LABELS: Final[dict[str, str]] = {
    "12": "관광지",
    "14": "문화시설",
    "15": "축제/공연/행사",
    "25": "여행코스",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
    "39": "음식점",
}

AREA_CODE_LABELS: Final[dict[str, str]] = {
    "1": "서울",
    "2": "인천",
    "3": "대전",
    "4": "대구",
    "5": "광주",
    "6": "부산",
    "7": "울산",
    "8": "세종",
    "31": "경기",
    "32": "강원",
    "33": "충북",
    "34": "충남",
    "35": "경북",
    "36": "경남",
    "37": "전북",
    "38": "전남",
    "39": "제주",
}

class LDongRegnCode(StrEnum):
    """법정동 시도코드 (lDongRegnCd). areaCode와 다른 코드 체계."""

    SEOUL = "11"
    BUSAN = "26"
    DAEGU = "27"
    INCHEON = "28"
    GWANGJU = "29"
    DAEJEON = "30"
    ULSAN = "31"
    SEJONG = "36"
    GYEONGGI = "41"
    GANGWON = "51"
    CHUNGBUK = "43"
    CHUNGNAM = "44"
    JEONBUK = "52"
    JEONNAM = "46"
    GYEONGBUK = "47"
    GYEONGNAM = "48"
    JEJU = "50"


LDONG_REGN_LABELS: Final[dict[str, str]] = {
    "11": "서울특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "29": "광주광역시",
    "30": "대전광역시",
    "31": "울산광역시",
    "36": "세종특별자치시",
    "41": "경기도",
    "51": "강원특별자치도",
    "43": "충청북도",
    "44": "충청남도",
    "52": "전북특별자치도",
    "46": "전라남도",
    "47": "경상북도",
    "48": "경상남도",
    "50": "제주특별자치도",
}

AREA_CODE_TO_LDONG: Final[dict[str, str]] = {
    "1": "11",
    "2": "28",
    "3": "30",
    "4": "27",
    "5": "29",
    "6": "26",
    "7": "31",
    "8": "36",
    "31": "41",
    "32": "51",
    "33": "43",
    "34": "44",
    "35": "47",
    "36": "48",
    "37": "52",
    "38": "46",
    "39": "50",
}

LDONG_TO_AREA_CODE: Final[dict[str, str]] = {v: k for k, v in AREA_CODE_TO_LDONG.items()}


CLASSIFICATION_SYSTEM_L1: Final[dict[str, str]] = {
    "AC": "숙박",
    "C01": "추천코스",
    "EV": "축제/공연/행사",
    "EX": "체험관광",
    "FD": "음식",
    "HS": "역사관광",
    "LS": "레저스포츠",
    "NA": "자연관광",
    "SH": "쇼핑",
    "VE": "문화관광",
}


def ldong_regn_label(value: str | LDongRegnCode | None) -> str | None:
    if value is None:
        return None
    return LDONG_REGN_LABELS.get(str(value))


SERVICE_NAME_BY_LANGUAGE: Final[dict[str, str]] = {
    "ko": "KorService2",
    "en": "EngService2",
    "ja": "JpnService2",
    "jp": "JpnService2",
    "zh-cn": "ChsService2",
    "zh": "ChsService2",
    "zh-tw": "ChtService2",
    "de": "GerService2",
    "fr": "FreService2",
    "es": "SpnService2",
    "ru": "RusService2",
}


def content_type_label(value: str | ContentType | None) -> str | None:
    """Return the Korean label for a KorService2 content type ID."""

    if value is None:
        return None
    return CONTENT_TYPE_LABELS.get(str(value))


def area_code_label(value: str | AreaCode | None) -> str | None:
    """Return the Korean label for a KorService2 area code."""

    if value is None:
        return None
    return AREA_CODE_LABELS.get(str(value))
