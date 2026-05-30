# AGENTS.md

## 문서 언어 정책

이 저장소의 **모든 Markdown/RST 문서는 한글로 작성한다**. 예외 없음. `README.md`, `AGENTS.md`, `krtourapi-api.md`, `docs/*`도 본문은 한글이다.

다음 항목만 영어를 유지한다 — 한글로 옮기면 의미가 변하거나 정확성이 깨지기 때문:
- **코드 식별자**: 함수/클래스/메서드/변수/타입/모듈 이름 (`KrTourApiClient`, `TourApiHubClient`, `PlaceCoordinate`, `ContentId`).
- **명령어와 경로**: `python -m pytest`, `ruff check .`, `f:\dev\python-visitkorea-api\src`.
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
| 디버그 UI | `debug_ui/app.py` (Streamlit) |

## 개발 환경 정책

PC 개발은 Windows 호스트에서 직접 진행한다.
- **안정적 public API**: 외부 API 작업을 시작하기 전에 "Direct public API rule"을 최우선으로 적용한다. 공급자 전용 wrapper, adapter, 또는 gateway 레이어를 별도로 만들지 않고, 직접 호출할 수 있는 안정적인 public client, typed model, enum, helper를 제공한다.
- **에이전트별 고정 worktree**: ChatGPT Codex는 `F:\dev\vw-codex`, Claude Code는 `F:\dev\vw-claude`, Google Antigravity 2.0은 `F:\dev\python-visitkorea-api`를 사용한다. 작업마다 브랜치만 새로 만들고, CodeGraph는 worktree마다 1회 `codegraph init -i` 후 `codegraph sync`로 유지한다.
- **로컬 검증 실행**: 본 저장소는 GitHub CI/CD에 과도하게 의존하지 않으며, 작업자가 머지 전에 로컬 품질 게이트를 실행해 모든 검증 명령이 통과하는지 직접 확인한다.

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `SKILL.md`
4. `krtourapi-api.md`
5. `docs/repeated-mistakes.md`, `docs/testing.md`, `docs/troubleshooting.md`
6. `README.md` 및 나머지 `docs/`
7. 기존 코드와 테스트
8. 최소한의, 되돌릴 수 있는 가정

## 모듈 소유권

```text
src/visitkorea/
├── client.py            # KrTourApiClient / AsyncKrTourApiClient — KorService2 typed wrapper
├── hub.py               # TourApiHubClient / AsyncTourApiHubClient — 27개 서비스 generic client
├── services.py          # SERVICE_DEFINITIONS 카탈로그 (api.visitkorea.or.kr 매뉴얼 기반)
├── operation_schema.py  # 오퍼레이션별 파라미터 스키마 (디버그 UI용)
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

1. **동기/비동기 코드 불일치 금지** — `_list_params()`, `_page_params()` 등 공유 로직은 sync/async 클래스에서 동일하게 유지한다. 한쪽을 수정하면 반드시 다른 쪽도 갱신한다.
2. **서비스 키 평문 노출 금지** — 예외 메시지, 로그, response에 서비스 키를 포함하지 않는다. `_redact_secret()`을 거친다.
3. **`areaCode` 없이 `sigunguCode` 전달 금지** — TourAPI가 무시하거나 오류를 반환한다.
4. **`cat1` 없이 `cat2`, `cat1`/`cat2` 없이 `cat3` 전달 금지** — 계층적 의존성.
5. **`lDongRegnCd` 없이 `lDongSignguCd` 전달 금지** — 계층적 의존성.
6. **`lclsSystm1` 없이 `lclsSystm2`, `lclsSystm1`/`lclsSystm2` 없이 `lclsSystm3` 전달 금지** — 계층적 의존성.
7. **TourAPI timestamp를 UTC로 해석 금지** — 항상 KST(Asia/Seoul)이다.
8. **불안정한 TourAPI 필드를 과도하게 model화 금지** — `raw`에 보존하고 content-type별 세부 필드는 `IntroInfo.raw`에 위임한다.
9. **단순 전달용 래퍼/어댑터/게이트웨이 작성 금지** — downstream 사용자에게 안정 public client, typed model, enum, helper를 직접 제공한다.
10. **좌표 순서 혼동 금지** — 공개 API는 `PlaceCoordinate(lat, lon)`. TourAPI의 `mapX`(경도)/`mapY`(위도) 변환은 request boundary에서만.
11. **외부 API 키 평문 커밋 금지** — `.env`는 gitignore. 테스트에 키를 하드코드하지 않는다.

## 제공자 API 사용 원칙

- 외부 API 관련 작업은 단순 전달용 래퍼/어댑터/게이트웨이 지양 원칙을 먼저 확인하고 문서/코드에 반영한 뒤 진행한다.
- 하위 사용자에게는 안정된 공개 클라이언트(`KrTourApiClient`, `TourApiHubClient`), 타입 모델, 열거형, 보조 함수를 제공한다.
- 단순 전달용 래퍼, 장기 호환 별칭, 임시 facade를 만들지 않는다.
- TourAPI 호출은 `httpx.Client`/`httpx.AsyncClient` + connection-level retry를 갖춘다.
- 응답의 알 수 없는 필드는 `raw`에 보존하여 downstream에서 접근 가능하도록 한다.

## 자주 묻는 작업

| 작업 | 시작 파일 |
|------|-----------|
| 새 typed endpoint 추가 | `client.py` (sync + async 양쪽) → `models.py` → `test_client.py` + `test_async.py` |
| 새 서비스 정의 추가 | `services.py` SERVICE_DEFINITIONS → `test_hub.py` 개수 업데이트 |
| 새 enum/constant 추가 | `enums.py` → `__init__.py` export → `test_enums.py` |
| 새 예외 타입 추가 | `exceptions.py` → `_http.py` 매핑 → `test_http.py` |
| TourAPI 응답 파싱 오류 수정 | `docs/repeated-mistakes.md`에 기록 → 가드레일 테스트 추가 → 코드 수정 |
| 디버그 UI 수정 | `debug_ui/app.py` |

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
