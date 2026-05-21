# Testing Guide

## 기본 원칙

- 기본 테스트는 실제 TourAPI를 호출하지 않는다.
- HTTP는 fake session, fake async session, 또는 `httpx.MockTransport`로 고정한다.
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
- `AsyncKrTourApiClient`와 `AsyncTourApiHubClient`의 awaitable method와 async iterator
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

## Live test 규칙

실제 API를 호출하는 테스트를 추가할 때:

```python
import os
import pytest

@pytest.mark.live
def test_live_area_codes():
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
```

live test에서는 관광지 이름, 총 건수, 정렬 순서처럼 변하기 쉬운 값을 단정하지 않는다. 응답 shape, 타입, 필수 공통 필드만 확인한다.

로컬에서 실 서버 테스트를 실행할 때는 `.env.local`에 `DATA_GO_KR_SERVICE_KEY=...`를 넣고 아래 스크립트를 사용한다. `.env.local`은 커밋하지 않는다.

```powershell
.\scripts\run_live_tests.ps1
```

현재 live 테스트는 두 가지를 확인한다.

- 신청된 국문 `KorService2`의 `areaCode2`가 실제 서버에서 정상 shape로 응답하는지
- 신청하지 않은 영문 `EngService2`가 HTTP 403 또는 인증/권한 오류로 매핑되는지
