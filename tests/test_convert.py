from __future__ import annotations

from datetime import date

import pytest
from kraddr.base import PlaceCoordinate
from pydantic import ValidationError

from visitkorea import Wgs84Coordinate
from visitkorea._convert import (
    strip_or_none,
    to_float_or_none,
    to_int_or_none,
    to_yyyymmdd,
    yn,
)
from visitkorea._time import parse_tour_datetime


def test_strip_and_numeric_conversions():
    assert strip_or_none("  서울  ") == "서울"
    assert strip_or_none(" ") is None
    assert to_int_or_none("12.0") == 12
    assert to_float_or_none("37.5") == 37.5
    assert to_float_or_none("not-number") is None


def test_date_and_yn_conversions():
    assert to_yyyymmdd(date(2026, 4, 30), field="event_start_date") == "20260430"
    assert to_yyyymmdd("20260430", field="event_start_date") == "20260430"
    with pytest.raises(ValueError):
        to_yyyymmdd("2026-04-30", field="event_start_date")
    assert yn(True) == "Y"
    assert yn(False) == "N"
    assert yn("y") == "Y"
    with pytest.raises(ValueError):
        yn("yes")


def test_place_coordinate_is_public_coordinate_type():
    coordinate = PlaceCoordinate(lat=37.5796, lon=126.9769)

    assert Wgs84Coordinate is PlaceCoordinate
    assert coordinate.map_x == 126.9769
    assert coordinate.map_y == 37.5796
    assert coordinate.lonlat == (126.9769, 37.5796)
    assert coordinate.latlon == (37.5796, 126.9769)
    assert PlaceCoordinate.from_tuple((37.5, 126.9)).longitude == 126.9
    assert PlaceCoordinate.from_mapping({"lon": 126.9, "lat": 37.5}).latitude == 37.5
    assert PlaceCoordinate.from_mapping({"mapX": "126.9", "mapY": "37.5"}).lonlat == (
        126.9,
        37.5,
    )

    dumped = coordinate.model_dump()
    assert dumped["lon"] == 126.9769
    assert PlaceCoordinate.model_json_schema()["properties"]["lon"]

    with pytest.raises(ValidationError, match="lon"):
        PlaceCoordinate(lat=37.5, lon=181)
    with pytest.raises(ValidationError, match="lat"):
        PlaceCoordinate(lat=91, lon=126.9)
    assert PlaceCoordinate.from_mapping({"not_x": 126.9, "not_y": 37.5}) is None


def test_parse_tour_datetime():
    parsed = parse_tour_datetime("20260430123456")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 4
    assert parsed.tzinfo is not None
    assert parse_tour_datetime("20260430").hour == 0  # type: ignore[union-attr]
    assert parse_tour_datetime("bad") is None
