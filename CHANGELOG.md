# 변경 기록

## Unreleased

- 내부 HTTP layer를 `httpx`로 교체하고 asyncio application용 `AsyncKrTourApiClient`/`AsyncTourApiHubClient`를 추가했다.
- 설치, 인증, typed client 사용, Hub 사용, Pydantic model, coordinate normalization, exception, CLI, test 문서를 확장했다.
- 기본 사용 guide로 `docs/user-guide.md`를 추가했다.
- Pydantic v2 serialization, JSON schema, frozen model, `raw` 보존 설명을 담은 `docs/pydantic-models.md`를 추가했다.
- Local Markdown link와 public model 사용에 대한 문서 guardrail을 추가했다.
- Legacy coordinate dependency를 local `python-kraddr-base`와 `kraddr.base.PlaceCoordinate`로 교체했다.
- Distribution 이름을 `python-visitkorea-api`로 바꾸고 code를 `src/visitkorea`로 이동했으며 public import/CLI default를 `visitkorea`로 전환했다.

## 0.1.0

- 초기 `visitkorea` package scaffold.
- Korea Tourism Organization TourAPI `KorService2`용 `KrTourApiClient` 추가.
- List/search/detail/image/sync/code lookup method 추가.
- Typed response model과 exception hierarchy 추가.
- Request shape, response parsing, error mapping, validation, CLI output에 대한 offline test 추가.
- README, API note, testing guide, troubleshooting guide, repeated mistake guardrail 추가.
- `api.visitkorea.or.kr/#/useUtilExercises`의 27개 OpenAPI service를 위한 `TourApiHubClient`와 `SERVICE_DEFINITIONS` 추가.
- Official ZIP/DOCX review 재현을 위한 `docs/openapi-catalog.md`와 manual download script 추가.
- Hub service routing, operation alias, environment fallback, Pythonic parameter alias에 대한 offline test 추가.
- Local `.env.local`에서 읽는 live server test 추가.
- Real TourAPI response 기반 browser-compatible User-Agent와 `resultCode=0000` success handling 추가.
- 공개 `Language`, `AreaCode` enum, integration-facing type alias, `PlaceCoordinate`/`Wgs84Coordinate` coordinate export 추가.
- `location_based_list()`의 coordinate normalization 추가와 `map_x`/`map_y` compatibility 보존.
- 공개 response model을 frozen Pydantic v2 model로 migration하고 `model_dump()`와 JSON schema를 지원.
