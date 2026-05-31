"""Typed response models for individual TourAPI Hub services.

These models map documented field names for each service to typed attributes. Every
model preserves the full upstream record in `raw`, so fields that are not yet stably
modeled remain accessible. Field names follow the service manuals; until they are
confirmed against live fixtures, `raw` stays the single source of truth.
"""

from __future__ import annotations

from kraddr.base import PlaceCoordinate
from pydantic import Field

from .models import RawRecord, TourApiModel


class _CoordinateModel(TourApiModel):
    """Base for service models that expose WGS84 coordinates via map_x/map_y."""

    map_x: float | None
    map_y: float | None

    @property
    def coordinate(self) -> PlaceCoordinate | None:
        """Return standardized WGS84 coordinates when both axes are present."""

        if self.map_x is None or self.map_y is None:
            return None
        return PlaceCoordinate(lat=self.map_y, lon=self.map_x)


class GoCampingItem(_CoordinateModel):
    """Camping site record from the GoCamping service."""

    content_id: str | None
    facility_name: str | None
    line_intro: str | None
    induty: str | None
    do_name: str | None
    sigungu_name: str | None
    addr1: str | None
    addr2: str | None
    tel: str | None
    homepage: str | None
    first_image_url: str | None
    raw: RawRecord = Field(repr=False)


class DurunubiCourseItem(TourApiModel):
    """Walking/cycling course record from the Durunubi service."""

    route_idx: str | None
    course_idx: str | None
    name: str | None
    distance: str | None
    required_time: str | None
    level: str | None
    summary: str | None
    contents: str | None
    sigun: str | None
    gpx_path: str | None
    raw: RawRecord = Field(repr=False)


class DataLabVisitorItem(TourApiModel):
    """Regional visitor-statistics record from the DataLab service."""

    base_ymd: str | None
    daywk_name: str | None
    area_code: str | None
    area_name: str | None
    signgu_code: str | None
    signgu_name: str | None
    tour_division_name: str | None
    visitor_count: str | None
    raw: RawRecord = Field(repr=False)


class OdiiItem(_CoordinateModel):
    """Audio-guide theme/story record from the Odii service."""

    story_id: str | None
    title: str | None
    theme_id: str | None
    theme_name: str | None
    mp3_path: str | None
    script: str | None
    image_path: str | None
    raw: RawRecord = Field(repr=False)


class MedicalTourItem(_CoordinateModel):
    """Medical-tourism record from the MdclTursmService service."""

    content_id: str | None
    content_type_id: str | None
    title: str | None
    addr1: str | None
    addr2: str | None
    tel: str | None
    first_image: str | None
    raw: RawRecord = Field(repr=False)


class WellnessTourItem(_CoordinateModel):
    """Wellness-tourism record from the WellnessTursmService service."""

    content_id: str | None
    content_type_id: str | None
    title: str | None
    addr1: str | None
    addr2: str | None
    tel: str | None
    first_image: str | None
    raw: RawRecord = Field(repr=False)
