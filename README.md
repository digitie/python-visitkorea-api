# python-visitkorea-api

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![GPL-3.0-or-later 라이선스](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)
![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

`visitkorea`는 한국관광공사(KTO) TourAPI를 Python 애플리케이션에서 다루기 쉽게 감싼 비공식 클라이언트입니다. 기본 typed 클라이언트는 공공데이터포털의 **한국관광공사_국문 관광정보서비스_GW**(`KorService2`)를 대상으로 하며, 한국관광콘텐츠랩 OpenAPI 활용신청 목록에 있는 전체 27개 서비스·211개 operation은 `TourApiHubClient`로 카탈로그 기반 generic 호출할 수 있습니다.

## 현재 상태

최근 변경 사항은 [CHANGELOG.md](CHANGELOG.md)의 `Unreleased` 항목을 참고하세요.

## 제공 표면

| 표면 | 진입점 | 설명 |
|------|--------|------|
| Python 라이브러리 (typed) | `from visitkorea import KrTourApiClient` | `KorService2` 자주 쓰는 endpoint를 typed method와 Pydantic 모델로 제공 |
| Python 라이브러리 (generic hub) | `from visitkorea import TourApiHubClient` | 활용신청 목록 27개 서비스 전체를 카탈로그 기반으로 호출 |
| CLI | `visitkorea --help` | 터미널에서 키워드/좌표/상세/코드 조회 |
| 디버그 UI (선택) | `streamlit run examples/streamlit_debug_ui.py` | 전체 서비스 카탈로그를 브라우저에서 탐색하는 내부 도구 (`pip install -e ".[debug-ui]"`) |

## 먼저 읽을 문서

README는 입구 역할만 합니다. 세부 사용법과 결정은 아래 문서를 정본으로 봅니다.

| 필요 정보 | 문서 |
|-----------|------|
| 설치부터 typed client, Hub, Pydantic, 좌표, 테스트까지 흐름 중심 가이드 | [docs/user-guide.md](docs/user-guide.md) |
| Pydantic v2 응답 모델, 직렬화, JSON schema, `raw` 보존 규칙 | [docs/pydantic-models.md](docs/pydantic-models.md) |
| 구현 원칙과 응답/예외 매핑 메모 | [krtourapi-api.md](krtourapi-api.md) |
| 27개 서비스·211개 operation 카탈로그 | [docs/openapi-catalog.md](docs/openapi-catalog.md) |
| 테스트 정책 | [docs/testing.md](docs/testing.md) |
| 문제 해결 | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 반복 실수 방지 규칙 | [docs/repeated-mistakes.md](docs/repeated-mistakes.md) |
| 구조적 의사결정 기록 | [docs/decisions.md](docs/decisions.md) |

## 설치

```bash
pip install -e ".[dev]"
```

런타임 의존성은 `httpx`, `pydantic>=2.7`, `python-kraddr-base`(GitHub 저장소에서 커밋 고정 설치, 로컬 경로 아님), Windows용 `tzdata`입니다. 정확한 버전 고정 값은 [pyproject.toml](pyproject.toml)을 확인하세요.

## 인증키

공공데이터포털에서 API 활용신청 후 **Decoding 인증키**를 환경변수에 넣는 방식을 권장합니다.

```bash
export DATA_GO_KR_SERVICE_KEY="발급받은_decoding_인증키"
```

PowerShell:

```powershell
$env:DATA_GO_KR_SERVICE_KEY="발급받은_decoding_인증키"
```

`.env`/`.env.local`을 통한 로드, `api.visitkorea.or.kr` 쪽 대체 인증키 이름, 인증키 취급 시 주의사항은 [docs/user-guide.md](docs/user-guide.md#인증키)에 정리되어 있습니다.

## 빠른 시작

```python
from visitkorea import ContentType, KrTourApiClient

client = KrTourApiClient.from_env(mobile_app="my-travel-app")

page = client.search_keyword(
    "경복궁",
    content_type_id=ContentType.TOURIST_ATTRACTION,
    l_dong_regn_cd="11",
)

for item in page.items:
    print(item.content_id, item.title, item.addr1, item.coordinate)

detail = client.detail_common(page.items[0].content_id)
print(detail.overview)
```

`AsyncKrTourApiClient`는 같은 public method 이름을 `await` 가능한 형태로 제공합니다. `TourApiHubClient`, Pydantic 모델 직렬화, 좌표 규칙, 페이지 반복, 예외 처리, 전체 CLI 명령은 [docs/user-guide.md](docs/user-guide.md)에서 다룹니다.

## 개발과 테스트

```bash
python -m compileall src/visitkorea tests
python -m pytest
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

기본 테스트는 실제 TourAPI를 호출하지 않습니다. live test는 `@pytest.mark.live`로 분리하고, `DATA_GO_KR_SERVICE_KEY`가 없으면 skip합니다. 자세한 정책은 [docs/testing.md](docs/testing.md)를 참고하세요.

## 데이터와 외부 API

| 항목 | 기준 |
|------|------|
| 원천 서비스 | 공공데이터포털 [한국관광공사_국문 관광정보서비스_GW](https://www.data.go.kr/en/data/15101578/openapi.do) (`KorService2`) |
| 전체 서비스 카탈로그 | [한국관광콘텐츠랩 OpenAPI 활용신청 목록](https://api.visitkorea.or.kr/#/useUtilExercises) |
| 변경 공지 | [2026-01-09 TourAPI URL/입출력 변경 공지](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004471) |

> 확인 기준일: 2026-04-30

## 디렉터리 개요

| 경로 | 역할 |
|------|------|
| `src/visitkorea/` | 패키지 소스 — typed client, hub client, 모델, CLI 등 (세부는 [AGENTS.md](AGENTS.md) 모듈 소유권 참고) |
| `tests/` | offline 단위 테스트 + `@pytest.mark.live` 라이브 테스트 |
| `examples/` | Streamlit 기반 선택 디버그 UI (`streamlit_debug_ui.py`) |
| `docs/` | 사용자 가이드, Pydantic 모델, 카탈로그, 테스트/문제해결/의사결정 문서 |
| `scripts/` | 매뉴얼 다운로드, live test 실행 스크립트 |

## 문서와 기여 규칙

- Markdown 문서는 한글로 작성합니다. 코드 식별자, 명령어, URL, 공식 API 용어만 예외입니다(자세한 규칙은 [AGENTS.md](AGENTS.md#문서-언어-정책)).
- 작업 전 [AGENTS.md](AGENTS.md)를 확인합니다.
- API 동작이나 public type을 바꾸면 README뿐 아니라 관련 `docs/`도 함께 갱신합니다.
- 사용자 가시 변경은 [CHANGELOG.md](CHANGELOG.md)에 기록합니다.

## 법적 고지

이 저장소의 GPL-3.0-or-later 라이선스는 저장소에 포함된 소스 코드와 문서에 적용됩니다. 자세한 조건은 [LICENSE](LICENSE)를 확인하십시오. 이 패키지가 감싸는 한국관광공사 TourAPI, 공공데이터포털, 한국관광콘텐츠랩의 데이터·API 이용은 각 제공 기관의 이용약관과 저작권 정책을 따르며, 이 패키지는 해당 데이터의 정확성이나 법적 효력을 보장하지 않습니다.
