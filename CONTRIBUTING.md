# 기여 가이드

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API field, code identifier, 명령어, URL, provider 원문은 필요한 경우 원문을 유지한다.

## 개발 환경

```bash
pip install -e ".[dev]"
python -m pytest
```

## Pull request checklist

- Public behavior에는 test가 있다.
- 기본 test는 실제 API를 호출하지 않는다.
- 새 endpoint는 `krtourapi-api.md`에 문서화한다.
- 사용자-facing 변경은 `README.md`에 문서화한다.
- 반복 실수는 `docs/repeated-mistakes.md`에 추가한다.
- `CHANGELOG.md`를 갱신한다.

## Style

- Python 3.11+
- Typed public surface
- 반환 model은 frozen Pydantic model 사용
- Provider-specific raw field는 `raw`에 보존
