# 변경 기록

## Unreleased

- asyncio 전환 재검증을 위한 2인 적대적 리뷰어 서브에이전트(동시성/자원관리 관점, 보안/데이터
  무결성 관점) 감사에서 발견·검증된 버그 수정: `AsyncKrTourApiClient._cached_code_page()`의
  코드 조회 stampede 방지용 `asyncio.Lock`이 캐시가 채워진 뒤에도 `_code_cache_locks` 딕셔너리에
  계속 남아, 서로 다른 파라미터 조합으로 코드 조회 API(`area_codes`/`category_codes`/
  `legal_dong_codes`/`classification_system_codes`)를 호출할 때마다 프로세스 수명 동안 무한정
  누적되던 메모리 누수 수정 — 캐시에 값을 채운 직후 해당 키의 lock을 제거하도록 변경. 두 리뷰어
  모두 다른 관점(레이트리미터 async-safety, pagination 절단 신호 대칭성, 자격증명 마스킹,
  result-code 처리)에서는 실제 버그를 찾지 못함(레이트리미터의 `threading.Lock`은 임계 구역에
  `await`가 없어 단일 이벤트 루프에서 실질적으로 원자적임을 확인; 이 저장소에는
  `PaginationLimitWarning` 개념 자체가 없어 sibling 저장소(kma)에서 발견된 절단-경고 누락 버그
  유형이 재현되지 않음을 확인).
- 4인 전문 리뷰어 서브에이전트의 적대적 코드 리뷰로 발견·검증된 버그 수정: 페이지네이션이 서버가
  echo하는 `pageNo`를 신뢰해 다음 페이지를 계산하다가(`client.py`/`hub.py` 6개 호출부) 값이
  틀리게 오면 같은 페이지를 반복 재요청하거나 조기 종료해 조용히 데이터가 유실되던 문제(로컬에서
  추적한 요청 페이지 번호를 우선하도록 수정), TourAPI 결과 코드 `21`(서비스키 일시 비활성화)이
  `TourApiAuthError`로 분류되지 않던 문제, 기본 base URL이 `http://`(평문)였던 문제를 `https://`로
  전환, CLI가 클라이언트 HTTP 세션을 닫지 않던 문제(`with` 컨텍스트 매니저로 전환) 등. GitHub
  Actions CI(`lint`/`typecheck`/`test`) 추가.
- `GoCampingItem.line_intro`가 실제 응답 필드 `intro`를 읽도록 수정했다(기존 `lineIntro`는 응답에 없어 항상 None이었다). 실 API 응답으로 검증.
- 디버그 UI에 typed 모델 등록 서비스용 'typed 모델로 파싱' 옵션을 추가했다(`.typed` 뷰 호출).

## 0.2.0 - 2026-05-31

- HTTP 재시도/지수 백오프(jitter)와 `Retry-After` 지원을 추가했다(동기·비동기). `max_retries`로 opt-in이며 기본값 0이라 기존 오류 동작은 유지된다.
- 클라이언트 측 요청 제한 `TokenBucketRateLimiter`/`RateLimiter`(`rate_limiter=`), 코드 조회 캐시(`code_cache=`), `httpx.Timeout` 세분화 타임아웃, `visitkorea.http` DEBUG 로깅을 추가했다.
- `detail_pet_tour()` typed method와 `PetTourInfo` model(`detailPetTour2`), `IntroInfo`의 콘텐츠타입 공통 intro 접근자를 추가했다.
- CLI에 `pet-detail`/`festival`/`stay`/`area-based`/`catalog` 명령을 추가했다.
- Hub 서비스 클라이언트의 `.typed` 뷰와 서비스별 typed model(`GoCampingItem`, `DurunubiCourseItem`, `DataLabVisitorItem`, `OdiiItem`, `MedicalTourItem`, `WellnessTourItem`)을 추가했다.
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
