# Changelog

## Unreleased

- Expanded documentation around installation, authentication, typed client usage, Hub usage, Pydantic models, coordinate normalization, exceptions, CLI usage, and testing.
- Added `docs/user-guide.md` as the primary library usage guide.
- Added `docs/pydantic-models.md` for Pydantic v2 serialization, JSON schema, frozen models, and `raw` preservation.
- Added documentation guardrails for local markdown links and public model usage.
- Replaced the legacy coordinate dependency with local `python-kraddr-base` and `kraddr.base.PlaceCoordinate`.
- Renamed the distribution to `python-visitkorea-api`, moved code to `src/visitkorea`, and switched public imports/CLI defaults to `visitkorea`.

## 0.1.0

- Initial `visitkorea` package scaffold.
- Added `KrTourApiClient` for Korea Tourism Organization TourAPI `KorService2`.
- Added list/search/detail/image/sync/code lookup methods.
- Added typed response models and exception hierarchy.
- Added offline tests for request shape, response parsing, error mapping, validation, and CLI output.
- Added README, API notes, testing guide, troubleshooting guide, and repeated mistake guardrails.
- Added `TourApiHubClient` and `SERVICE_DEFINITIONS` for all 27 OpenAPI services listed on `api.visitkorea.or.kr/#/useUtilExercises`.
- Added `docs/openapi-catalog.md` and a manual download script for reproducing the official ZIP/DOCX review.
- Added offline tests for Hub service routing, operation aliases, environment fallback, and Pythonic parameter aliases.
- Added live server tests loaded from local `.env.local`, with Korean service success and unsubscribed foreign service auth-error coverage.
- Added a browser-compatible User-Agent and `resultCode=0000` success handling based on real TourAPI responses.
- Added public `Language` and `AreaCode` enums, integration-facing type aliases, and `PlaceCoordinate`/`Wgs84Coordinate` coordinate exports.
- Added coordinate normalization for `location_based_list()` while preserving `map_x`/`map_y` compatibility.
- Migrated public response models to frozen Pydantic v2 models with `model_dump()` and JSON schema support.
