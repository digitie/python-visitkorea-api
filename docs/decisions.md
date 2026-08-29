# decisions.md — 의사결정 기록

이 문서는 이 프로젝트의 구조적 결정을 결정 시점 순서로 누적한다.
결정이 뒤집힐 때는 새 항목을 추가하고, 옛 항목은 지우지 않은 채
(supersedes: 위 항목)으로 표시한다.

## D-001: `TourApiHubClient`는 27개 서비스를 카탈로그 기반 제네릭 디스패치로 다룬다

- 상태: accepted
- 날짜: 2026-04-30

### 컨텍스트

`api.visitkorea.or.kr/#/useUtilExercises`의 공식 활용신청 목록은 27개 서비스, 211개
operation으로 구성된다. 서비스마다 응답 item의 모양이 달라 전부를 typed model로
유지보수하는 것은 비용이 크다.

### 결정

`SERVICE_DEFINITIONS` 카탈로그(서비스 key, base URL, operation 목록, alias)를 데이터로
유지하고, `TourApiHubClient`/`AsyncTourApiHubClient`는 이 카탈로그를 기준으로 모든
서비스를 제네릭하게 호출해 `Page[Mapping]`으로 반환한다. `KrTourApiClient`만 자주 쓰는
`KorService2`를 typed wrapper로 감싼다.

### 근거

- `krtourapi-api.md`: "`KrTourApiClient`는 자주 쓰는 `KorService2`용 typed wrapper이고,
  나머지 서비스와 모든 operation은 `TourApiHubClient`가 카탈로그 기반 generic wrapper로
  제공한다."
- `AGENTS.md` 모듈 소유권: `services.py`가 "SERVICE_DEFINITIONS 카탈로그(api.visitkorea.or.kr
  매뉴얼 기반)"로 명시되어 있다.

### 결과

새 서비스 추가는 코드 대신 카탈로그 항목 추가로 처리한다(`AGENTS.md` "자주 묻는 작업" 표).
안정성이 확인된 일부 서비스(`gocamping`, `durunubi` 등)는 이후 `.typed` 뷰로 typed model을
추가 제공하되, 등록되지 않은 서비스는 계속 `Page[Mapping]`을 반환한다.

## D-002: 외부 API는 단순 전달용 래퍼/어댑터/게이트웨이를 두지 않고 직접 감싼 안정된
공개 클라이언트만 제공한다

- 상태: accepted
- 날짜: 2026-05-09

### 컨텍스트

여러 하위 프로젝트가 TourAPI를 소비하는 상황에서, 프로젝트마다 자체 wrapper나 facade를
두면 유지보수 지점이 늘고 안정성 계약이 흐려질 위험이 있었다.

### 결정

`visitkorea`는 TourAPI 앞에 별도의 전달용 wrapper/adapter/gateway 계층을 두지 않는다.
대신 하위 사용자에게 안정적인 public client(`KrTourApiClient`, `TourApiHubClient`),
typed model, enum, helper를 직접 제공해 그것을 그대로 쓰게 한다.

### 근거

- 커밋 `1c64a6f` "docs: prefer direct adoption over thin wrappers".
- `AGENTS.md` 개발 환경 정책: "**안정적 public API**: 외부 API 작업을 시작하기 전에
  'Direct public API rule'을 최우선으로 적용한다. 공급자 전용 wrapper, adapter, 또는
  gateway 레이어를 별도로 만들지 않고, 직접 호출할 수 있는 안정적인 public client, typed
  model, enum, helper를 제공한다."
- `AGENTS.md` DO-NOT #9: "단순 전달용 래퍼/어댑터/게이트웨이 작성 금지".

### 결과

임시 facade나 장기 호환 별칭을 새로 만들지 않는다. 이전 이름(`Wgs84Coordinate` 등)을
유지해야 할 때도 별도 계층이 아니라 같은 클래스의 alias로만 남긴다.

## D-003: 공개 좌표 DTO는 `(lat, lon)` 순서를 쓰고, TourAPI `mapX`/`mapY` 변환은 요청
경계에서만 한다

- 상태: accepted
- 날짜: 2026-05-18

### 컨텍스트

TourAPI 원문은 `mapX=경도`, `mapY=위도`를 사용하며, GeoJSON 등 일부 생태계는
`(lon, lat)` 순서를 쓴다. 좌표 축 순서 혼동은 반복되는 실수 유형이다.

### 결정

공개 API는 `kraddr.base.PlaceCoordinate(lat=, lon=)`을 그대로 노출하고, 튜플 좌표도
`(latitude, longitude)` 순서로 고정한다. TourAPI 원문 파라미터 이름(`mapX`, `mapY`)으로의
변환은 요청을 만드는 경계에서만 수행하고, 그 밖의 공개 표면에는 노출하지 않는다.

### 근거

- 커밋 `b92698d` "Align VisitKorea coordinates to lat-lon DTO order".
- `AGENTS.md` DO-NOT #10: "좌표 순서 혼동 금지 — 공개 API는 `PlaceCoordinate(lat, lon)`.
  TourAPI의 `mapX`(경도)/`mapY`(위도) 변환은 request boundary에서만."
- README "좌표 규칙": "TourAPI 원문은 `mapX=경도`, `mapY=위도`를 사용합니다. ... 공개 DTO
  축 순서는 `(lat, lon)`입니다."

### 결과

기존 `map_x`/`map_y` 키워드 인자는 하위 호환을 위해 계속 받되, 내부에서 즉시
`PlaceCoordinate`로 정규화한다. 좌표 관련 테스트는 WGS84 `lon`/`lat`와 TourAPI
`mapX`/`mapY`의 차이를 명시적으로 검증한다(`AGENTS.md` 테스트 정책).

## D-004: 좌표 DTO는 자체 타입을 만들지 않고 `python-kraddr-base`의
`PlaceCoordinate`에 위임한다

- 상태: accepted
- 날짜: 2026-05-13

### 컨텍스트

`visitkorea`를 포함한 여러 형제 패키지(`pymcst`, `pykrforest`, `pymois`, `pyairkorea` 등)가
같은 모양의 좌표/주소 DTO가 필요했다. 초기에는 로컬 `pykrtour` 좌표 타입을 자체 유지했다.

### 결정

좌표 DTO를 자체 유지하지 않고 공용 패키지 `python-kraddr-base`(import 경로
`kraddr.base`)의 `PlaceCoordinate`를 `pyproject.toml` 의존성으로 채택해 그대로
re-export한다. 버전은 GitHub 커밋으로 고정한다
(`python-kraddr-base @ git+https://github.com/digitie/python-kraddr-base.git@<commit>`).

### 근거

- 커밋 `bf90de9` "Use git dependency for kraddr base".
- `CHANGELOG.md` 0.2.0: "Legacy coordinate dependency를 local `python-kraddr-base`와
  `kraddr.base.PlaceCoordinate`로 교체했다."
- `pyproject.toml` `dependencies`의 `python-kraddr-base @ git+...` 항목.

### 결과

README/문서에 의존성을 설명할 때는 로컬 경로(`file:`)가 아니라 `pyproject.toml`의 실제
git 의존성 형태를 기준으로 서술한다. 로컬 checkout이 없는 CI/신규 환경에서도 그대로
설치된다.

## D-005: 동기/비동기 클라이언트는 같은 public method 이름을 공유하고, 공유 로직은
분기 없이 양쪽에 동일하게 유지한다

- 상태: accepted
- 날짜: 2026-05-19

### 컨텍스트

`httpx` 도입 이전에는 동기 클라이언트만 있었다. asyncio 기반 애플리케이션 지원 요청에 맞춰
비동기 클라이언트를 추가하면서, 두 구현이 갈라지면 페이지네이션·에러 매핑 같은 공유 로직이
한쪽만 수정되는 회귀 위험이 생겼다.

### 결정

`httpx.Client`/`httpx.AsyncClient`를 함께 채택해 `AsyncKrTourApiClient`,
`AsyncTourApiHubClient`를 추가하고, 동기 클라이언트와 완전히 같은 public method 이름을
쓰게 한다. `_list_params()`, `_page_params()` 등 공유 로직은 두 클래스에서 동일하게
유지하는 것을 규칙으로 못박는다.

### 근거

- 커밋 `2e4568e` "Add httpx async TourAPI clients".
- `CHANGELOG.md` 0.2.0: "내부 HTTP layer를 `httpx`로 교체하고 asyncio application용
  `AsyncKrTourApiClient`/`AsyncTourApiHubClient`를 추가했다."
- `AGENTS.md` DO-NOT #1: "동기/비동기 코드 불일치 금지 — ... 공유 로직은 sync/async
  클래스에서 동일하게 유지한다. 한쪽을 수정하면 반드시 다른 쪽도 갱신한다."

### 결과

새 typed endpoint를 추가할 때는 `client.py`의 동기/비동기 양쪽을 함께 고친다
(`AGENTS.md` "자주 묻는 작업" 표). 테스트도 `test_client.py`/`test_async.py`로 짝을
맞춘다.
