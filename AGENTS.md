# AGENTS.md

## 목표

`visitkorea`는 한국관광공사(KTO) TourAPI(data.go.kr 공개 API)를 감싸는 **비공식 Python
클라이언트 라이브러리**다. 자주 쓰는 국문 관광정보서비스(`KorService2`)는 typed client
(`KrTourApiClient`/`AsyncKrTourApiClient`)로 제공하고, `api.visitkorea.or.kr` 활용신청
목록의 27개 서비스 전체는 카탈로그 기반 generic client(`TourApiHubClient`/
`AsyncTourApiHubClient`)로 제공한다.

## Think Before Coding

- TourAPI 필드가 매뉴얼과 실제 응답에서 다르면 추측으로 모델링하지 말고 `raw` 보존으로
  갈지 먼저 확인할 것
- 상위 코드 없이 하위 코드(`sigunguCode`, `cat2`/`cat3`, `lDongSignguCd`,
  `lclsSystm2`/`lclsSystm3`)만 요청하는 변경은 계층적 의존성을 먼저 확인할 것
- 동기 클라이언트만 고치는 변경은 비동기 쪽 반영 여부를 먼저 표면화할 것(그 반대도 동일)
- 요청이 모호할 때는 조용히 해석을 정하지 말고 드러낼 것

## Simplicity First

- 요청을 해결하는 최소한의 typed method/model만 추가할 것
- 안정적으로 확인되지 않은 TourAPI 필드를 서둘러 모델화하지 말고 `raw` 보존을 우선할 것
- 단순 전달용 래퍼/어댑터/게이트웨이를 새로 만들지 말 것(`docs/decisions.md` D-002)
- 구체적 필요 없이 설정 가능성이나 옵션을 늘리지 말 것

## Surgical Changes

- 요청을 처리하는 데 필요한 `client.py`/`hub.py`/`models.py` 등 해당 모듈만 변경할 것
- 관련 없는 서비스 정의, 코드 스타일, 포맷을 함께 건드리지 말 것
- 기존 typed method 이름과 패턴을 따르고, 더 넓은 리팩터링이 필요하면 별도로 언급할 것
- 관련 없는 문제를 발견하면 패치에 섞지 말고 따로 보고할 것

## Goal-Driven Execution

- 버그 수정은 실제 TourAPI 응답이나 재현 fixture 없이 바로 신뢰하지 말 것
- offline 테스트만으로 부족하면 무엇이 미검증인지 밝힐 것(live test는
  `DATA_GO_KR_SERVICE_KEY`가 있어야 실행된다)
- 리팩터링은 typed client와 Hub client 양쪽의 동작 보존을 전후로 확인할 것
- 완전한 검증이 불가능하면 무엇이 아직 미검증인지 밝힐 것

## Practical Bias

- 새 endpoint/서비스 추가처럼 비단순 작업은 성급함보다 신중함을 우선할 것
- 변경 범위는 요청 범위와 리뷰 가능한 크기로 유지할 것
- 아주 단순한 필드 수정이나 오탈자 수정은 과하게 무겁게 다루지 말 것

## 문서 언어 정책

이 저장소의 **모든 Markdown/RST 문서는 한글로 작성한다**. 예외 없음. `README.md`, `AGENTS.md`, `krtourapi-api.md`, `docs/*`도 본문은 한글이다.

다음 항목만 영어를 유지한다 — 한글로 옮기면 의미가 변하거나 정확성이 깨지기 때문:
- **코드 식별자**: 함수/클래스/메서드/변수/타입/모듈 이름 (`KrTourApiClient`, `TourApiHubClient`, `PlaceCoordinate`, `ContentId`).
- **명령어와 경로**: `python -m pytest`, `ruff check .`, `src/visitkorea`.
- **외부 공식 용어**: TourAPI, KorService2, Pydantic, httpx, data.go.kr, XML/JSON, DTO.
- **표준 keyword**: ADR, CHANGELOG, ISO 8601 날짜, semver 라벨.
- **shell 출력 / 로그 예시**: 그대로 캡처한 문자열은 보존.

설명 문장, 절제목, 표 column 헤더, ADR 본문, 빠른 시작 가이드, 일지 항목은 한글로 적는다. 새 문서를 만들 때 영문 초안을 두지 않는다 — 처음부터 한글로 쓴다.

## 역할

이 저장소(GitHub 이름 `python-visitkorea-api`, Python 패키지 `visitkorea`)는 한국관광공사 TourAPI(data.go.kr 공개 API) 전체를 커버하는 **Python 클라이언트 라이브러리**다. api.visitkorea.or.kr의 27개 서비스 카탈로그를 기반으로 typed client(`KrTourApiClient`)와 generic hub client(`TourApiHubClient`)를 제공한다.

## 식별자 (혼동 방지)

| 항목 | 값 |
|------|----|
| GitHub 저장소 이름 | `python-visitkorea-api` |
| Python import 경로 | `from visitkorea import ...` |
| CLI 명령 | `visitkorea` |
| 환경변수 prefix | `DATA_GO_KR_*`, `VISITKOREA_API_*` |
| 기본 base URL | `http://apis.data.go.kr/B551011` |
| 기본 서비스 | `KorService2` |
| 디버그 UI | `examples/streamlit_debug_ui.py` (Streamlit) |

## 개발 환경 정책

PC 개발은 Windows 호스트에서 직접 진행한다.
- **안정적 public API**: 외부 API 작업을 시작하기 전에 "Direct public API rule"을 최우선으로 적용한다. 공급자 전용 wrapper, adapter, 또는 gateway 레이어를 별도로 만들지 않고, 직접 호출할 수 있는 안정적인 public client, typed model, enum, helper를 제공한다(`docs/decisions.md` D-002).
- **로컬 검증 실행**: 본 저장소는 GitHub CI/CD에 과도하게 의존하지 않으며, 작업자가 머지 전에 로컬 품질 게이트를 실행해 모든 검증 명령이 통과하는지 직접 확인한다.

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `README.md` 및 `docs/`, 기존 코드와 테스트

## 모듈 소유권

```text
src/visitkorea/
├── client.py            # KrTourApiClient / AsyncKrTourApiClient — KorService2 typed wrapper
├── hub.py               # TourApiHubClient / AsyncTourApiHubClient — 27개 서비스 generic client
├── services.py          # SERVICE_DEFINITIONS 카탈로그 (api.visitkorea.or.kr 매뉴얼 기반)
├── operation_schema.py  # 오퍼레이션별 파라미터 스키마 + get_api_catalog_entry() (디버그 UI용)
├── debug.py             # jsonable/redact_sensitive/debug_error/save_fixture (디버그 UI·fixture 공용)
├── models.py            # Pydantic v2 공개 response model (frozen)
├── types.py             # downstream integration용 공개 type alias
├── enums.py             # 공개 constant와 enum (AreaCode, ContentType, Language 등)
├── exceptions.py        # TourApiError 예외 계층
├── display.py           # HTML 정리, 저작권 표시 helper
├── cli.py               # command-line entrypoint
├── _http.py             # httpx client, TourAPI envelope, error mapping
├── _auth.py             # 서비스키 탐색 (env, dotenv, 다중 소스)
├── _convert.py          # 작은 변환 helper
├── _time.py             # KST timestamp parsing
├── _pagination.py       # 페이지네이션 iterator
└── _provenance.py       # TourApiCallContext 생성
```

## 절대 하지 말 것 (DO NOT)

1. **동기/비동기 코드 불일치 금지** — `_list_params()`, `_page_params()` 등 공유 로직은 sync/async 클래스에서 동일하게 유지한다. 한쪽을 수정하면 반드시 다른 쪽도 갱신한다(`docs/decisions.md` D-005).
2. **서비스 키 평문 노출·커밋 금지** — 예외 메시지, 로그, response, git 커밋 어디에도 서비스 키를 포함하지 않는다. `_redact_secret()`을 거치고, `.env`는 gitignore 대상이다.
3. **상위 코드 없이 하위 코드 전달 금지** — `areaCode` 없는 `sigunguCode`, `cat1` 없는 `cat2`/`cat3`, `lDongRegnCd` 없는 `lDongSignguCd`, `lclsSystm1`/`lclsSystm2` 없는 `lclsSystm2`/`lclsSystm3` 전달을 금지한다(계층적 의존성).
4. **TourAPI timestamp를 UTC로 해석 금지** — 항상 KST(Asia/Seoul)이다.
5. **좌표 순서 혼동 금지** — 공개 API는 `PlaceCoordinate(lat, lon)`. TourAPI의 `mapX`(경도)/`mapY`(위도) 변환은 request boundary에서만 한다(`docs/decisions.md` D-003).
6. **단순 전달용 래퍼/어댑터/게이트웨이 작성 금지** — 하위 사용자에게는 안정된 공개 클라이언트(`KrTourApiClient`, `TourApiHubClient`), 타입 모델, 열거형, 보조 함수를 직접 제공한다. 장기 호환 별칭이나 임시 facade도 만들지 않는다(`docs/decisions.md` D-002).

## 자주 묻는 작업

| 작업 | 시작 파일 |
|------|-----------|
| 새 typed endpoint 추가 | `client.py` (sync + async 양쪽) → `models.py` → `test_client.py` + `test_async.py` |
| 새 서비스 정의 추가 | `services.py` SERVICE_DEFINITIONS → `test_hub.py` 개수 업데이트 |
| 새 enum/constant 추가 | `enums.py` → `__init__.py` export → `test_enums.py` |
| 새 예외 타입 추가 | `exceptions.py` → `_http.py` 매핑 → `test_http.py` |
| TourAPI 응답 파싱 오류 수정 | `docs/repeated-mistakes.md`에 기록 → 가드레일 테스트 추가 → 코드 수정 |
| 디버그 UI 수정 | `examples/streamlit_debug_ui.py`, `src/visitkorea/debug.py` |

## 도메인 어휘

| 약어/용어 | 의미 |
|-----------|------|
| `contentId` | TourAPI 콘텐츠 고유 ID |
| `contentTypeId` | 콘텐츠 유형 코드 (12=관광지, 14=문화시설, 15=축제, 25=코스, 28=레포츠, 32=숙박, 38=쇼핑, 39=음식점) |
| `areaCode` | 시도 코드 (1=서울, 6=부산 등) |
| `sigunguCode` | 시군구 코드 (areaCode 하위) |
| `lDongRegnCd` | 법정동 광역 코드 |
| `lDongSignguCd` | 법정동 시군구 코드 |
| `lclsSystm1/2/3` | 관광분류체계 코드 (대/중/소) |
| `mapX` / `mapY` | TourAPI 좌표 (X=경도/longitude, Y=위도/latitude) |
| `resultCode` | TourAPI 응답 코드 (0000=성공, 03=데이터 없음, 20/30/31=인증오류) |
| `KorService2` | 국문 관광정보 서비스 (기본 서비스) |

## 테스트 정책

- 기본 테스트는 **오프라인(offline)**이어야 한다 (실제 API 호출 금지).
- HTTP 동작에는 `FakeSession`/`FakeAsyncSession` 또는 `httpx.MockTransport`를 사용한다.
- 라이브 테스트(Live test)에는 `@pytest.mark.live`와 `DATA_GO_KR_SERVICE_KEY`가 필요하다.
- 불안정한 실제 관광 데이터 값을 assert하지 말고, 형태(shape)와 타입(type)만 assert한다.
- `TourApiHubClient` 테스트는 catalog-driven으로 유지하고 기본 테스트에서 실제 27개 서비스를 호출하지 않는다.
- 좌표(Coordinate) 테스트는 `PlaceCoordinate` WGS84 `lon`/`lat`와 TourAPI `mapX`/`mapY` 차이를 명시한다.

## 작업 후 체크리스트

- [ ] `python -m pytest -q` 통과 (오프라인 테스트 전부 성공)
- [ ] `ruff check .` / `mypy src/visitkorea` 통과
- [ ] 실수를 고쳤다면 `docs/repeated-mistakes.md`에 기록
- [ ] 사용자 가시 변경이면 `CHANGELOG.md` 갱신
- [ ] 새 endpoint/서비스 추가 시 `krtourapi-api.md` 갱신
- [ ] 재론쟁될 만한 구조적 결정을 내렸다면 `docs/decisions.md`에 항목 추가

## 검증

```bash
python -m compileall src/visitkorea tests
python -m pytest -q
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

## 문서화 정책

실수를 고쳤다면 반드시 `docs/repeated-mistakes.md`에 **증상(symptom)**, **원인(cause)**, **규칙(rule)**, **가드레일 테스트(guardrail test)**를 추가 또는 업데이트한다.
