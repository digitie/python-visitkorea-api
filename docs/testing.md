# 테스트 가이드

## 기본 원칙

- 기본 테스트는 실제 TourAPI를 호출하지 않는다.
- HTTP는 비동기 fake session, 또는 `httpx.MockTransport`로 고정한다.
- 응답 fixture 값은 실제 TourAPI처럼 문자열 중심으로 둔다.
- live test는 별도 marker로 격리한다.

## 실행

```bash
python -m compileall src/visitkorea tests
python -m pytest
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

## 반드시 유지할 테스트 범위

- 공통 요청 파라미터: `serviceKey`, `MobileOS`, `MobileApp`, `_type=json`
- endpoint URL 조합
- HTTP status 및 `resultCode` 예외 매핑
- XML 오류 응답 매핑
- `items.item` 단일 dict/list/empty 정규화
- 날짜 `YYYYMMDD` 변환
- 법정동/분류체계/카테고리 의존성 검증
- 주요 Pydantic 모델 변환과 `model_dump()` 직렬화
- CLI JSON 직렬화
- 전체 OpenAPI 카탈로그 개수와 서비스 alias
- `TourApiHubClient`의 service/operation 동적 라우팅과 snake_case operation alias
- `KrTourApiClient`와 `TourApiHubClient`의 awaitable method와 async iterator
- Hub 요청의 Pythonic parameter alias(`content_id` -> `contentId` 등)
- public enum/type export
- `PlaceCoordinate` 좌표 검증과 `lon`/`lat` -> `mapX`/`mapY` 변환
- README와 문서 링크가 실제 파일을 가리키는지
- 사용자 가이드가 Pydantic, Hub, 좌표, 인증키 보안 흐름을 계속 설명하는지

## 문서 테스트

문서가 public API의 일부처럼 쓰이므로 기본 테스트에 가벼운 문서 guardrail을 둔다.

- README의 로컬 `.md` 링크는 깨지면 안 된다.
- `docs/user-guide.md`는 `KrTourApiClient`, `TourApiHubClient`, `PlaceCoordinate`, `model_dump`, `DATA_GO_KR_SERVICE_KEY`를 언급해야 한다.
- `docs/pydantic-models.md`는 `TourApiModel`, `model_dump_json`, `model_json_schema`, `raw`, `model_copy`를 언급해야 한다.

문서 테스트는 문장 품질을 검증하는 용도가 아니라, 기능 추가 후 문서 파일을 빠뜨리는 실수를 막는 최소 안전장치다.

## 라이브 테스트 규칙

실제 API를 호출하는 테스트를 추가할 때:

```python
import os
import pytest

@pytest.mark.live
def test_live_area_codes():
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if os.getenv("VISITKOREA_RUN_LIVE") != "1" or not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
```

live test에서는 관광지 이름, 총 건수, 정렬 순서처럼 변하기 쉬운 값을 단정하지 않는다. 응답 shape, 타입, 필수 공통 필드만 확인한다.

로컬에서 실 서버 테스트를 실행할 때는 `.env.local`에 `DATA_GO_KR_SERVICE_KEY=...`를 넣고 아래 스크립트를 사용한다. `.env.local`은 커밋하지 않는다.

```powershell
.\scripts\run_live_tests.ps1
```

라이브 검증은 국문 코드/검색·상세 연결/반려동물, 캐시·TPS, Hub 타입 응답과 디버그 응답을 확인한다. 영문과 GoCamping의 인증 거부는 HTTP 상태를 포함한 skip으로 명시하고 데이터 성공으로 집계하지 않는다. 인증 이외의 전송·응답 오류는 실패로 보고한다. 모든 클라이언트는 테스트 안의 async context에서 종료한다.

실제 실행에는 `VISITKOREA_RUN_LIVE=1`과 `DATA_GO_KR_SERVICE_KEY`가 모두 필요하다. 키만 설정된 기본 pytest가 외부 API를 호출하지 않도록 한다. `scripts/run_live_tests.ps1`가 명시적 실행 플래그를 설정한다.
