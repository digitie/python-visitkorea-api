"""Streamlit debug UI for the VisitKorea TourAPI Hub catalog (27 services / 200+ operations)."""
# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
for module_name, module in list(sys.modules.items()):
    if module_name != "visitkorea" and not module_name.startswith("visitkorea."):
        continue
    module_file = getattr(module, "__file__", None)
    if module_file is not None and not Path(module_file).resolve().is_relative_to(SRC):
        del sys.modules[module_name]

try:
    import pandas as pd
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - optional tool
    raise SystemExit('Streamlit UI를 쓰려면 `pip install -e ".[debug-ui]"`를 실행하세요.') from exc

from visitkorea import (
    SERVICE_DEFINITIONS,
    TourApiHubClient,
    get_api_catalog,
    get_api_catalog_entry,
    jsonable,
    resolve_service_key,
    save_fixture,
    service_key_env_names,
    service_key_sources,
)
from visitkorea._service_views import SERVICE_ITEM_PARSERS

ASSERTION_MODES = ["snapshot", "schema_only", "required_fields", "count"]


def main() -> None:
    st.set_page_config(page_title="VisitKorea TourAPI Debug", layout="wide")
    st.title("VisitKorea TourAPI Debug")

    rows = list(get_api_catalog())

    # 1. Data source -> API -> Operation cascade. The catalog only ever exposes
    # "data.go.kr" today, but the selector stays generic in case a second data
    # source is added later; API/Operation is the level that actually needs
    # cascading, since 27 services expand to 200+ operations.
    data_sources = sorted({str(row["data_source"]) for row in rows})
    data_source = st.sidebar.selectbox("Data source", data_sources)
    source_rows = [row for row in rows if row["data_source"] == data_source]
    source_service_keys = {row["service_id"] for row in source_rows}
    services_in_source = [
        service for service in SERVICE_DEFINITIONS if service.key in source_service_keys
    ]

    service_labels = [f"{service.dataset_name} ({service.key})" for service in services_in_source]
    selected_service_label = st.sidebar.selectbox("API", service_labels)
    selected_service = services_in_source[service_labels.index(selected_service_label)]

    service_rows = [row for row in source_rows if row["service_id"] == selected_service.key]
    operation_labels = [_operation_label(row) for row in service_rows]
    selected_operation_label = st.sidebar.selectbox("Operation", operation_labels)
    selected_row = service_rows[operation_labels.index(selected_operation_label)]
    operation = str(selected_row["operation"])

    selected = get_api_catalog_entry(selected_service.key, operation)

    # 2. Two-line description: what the API is, and what this operation returns.
    st.sidebar.caption(selected_service.description)
    st.sidebar.caption(f"{selected['summary']} {selected['details']}")

    st.sidebar.divider()

    # 3. Environment: env var vs manual entry.
    st.sidebar.subheader("Environment")
    key_source_labels = {source.label: source.key for source in service_key_sources()}
    selected_key_source_label = st.sidebar.selectbox(
        "Service key family",
        list(key_source_labels),
        help=(
            "이 오퍼레이션의 인증에 쓸 서비스키 계열입니다. 대부분의 TourAPI 서비스는 "
            "data.go.kr 계열을 사용합니다."
        ),
    )
    selected_key_source = key_source_labels[selected_key_source_label]
    env_names = service_key_env_names(selected_key_source)
    env_key = resolve_service_key(source=selected_key_source) or ""
    environment = st.sidebar.radio(
        "Environment",
        ["env", "manual"],
        index=0 if env_key else 1,
        horizontal=True,
        key=f"environment:{selected_key_source}",
    )
    env_names_text = ", ".join(env_names)
    if environment == "env" and env_key:
        st.sidebar.caption(f"{env_names_text} 값을 사용합니다 (환경변수 또는 .env).")
    elif environment == "env":
        st.sidebar.caption(f"{env_names_text}가 설정되어 있지 않습니다. 값을 찾지 못했습니다.")
    else:
        st.sidebar.caption(f"직접 입력한 값을 사용합니다. 사용 가능한 env 이름: {env_names_text}")

    # 4. Auth: the literal upstream query-param name this API reads.
    st.sidebar.subheader("Auth")
    if environment == "manual":
        manual_key = st.sidebar.text_input(
            "serviceKey",
            value="",
            type="password",
            placeholder="직접 입력",
            help=f"사용 가능한 env 이름: {', '.join(env_names)}",
        )
        effective_service_key = manual_key
    else:
        effective_service_key = env_key
        st.sidebar.text_input(
            "serviceKey",
            value="•" * min(len(env_key), 16) if env_key else "",
            type="password",
            disabled=True,
            help="Environment가 'env'일 때는 여기서 직접 수정할 수 없습니다.",
        )

    # 5. Service-key issuance link, straight from the catalog.
    st.sidebar.link_button(
        "serviceKey 발급/확인",
        selected["service_key_apply_url"],
        width="stretch",
    )
    st.sidebar.link_button("API 매뉴얼", selected["manual_url"], width="stretch")

    st.sidebar.divider()

    # 6. Timeout.
    timeout = st.sidebar.number_input(
        "Timeout (seconds)",
        min_value=1.0,
        max_value=120.0,
        value=10.0,
        step=1.0,
    )

    # 7. Fixture base dir.
    fixture_base_dir = _fixture_base_dir_sidebar()

    tabs = st.tabs(
        [
            "Raw Response",
            "Pydantic Model",
            "Processed Result",
            "Validation Errors",
            "Debug Trace",
            "Fixture / Testcase",
        ]
    )

    with tabs[0]:
        _raw_response_tab(
            selected,
            service_key=effective_service_key,
            key_source=selected_key_source,
            timeout=float(timeout),
        )
    with tabs[1]:
        _pydantic_model_tab(selected)
    with tabs[2]:
        _processed_result_tab(selected)
    with tabs[3]:
        _validation_errors_tab(selected)
    with tabs[4]:
        _debug_trace_tab(rows, selected)
    with tabs[5]:
        _fixture_tab(fixture_base_dir, selected)


def _operation_label(row: dict[str, Any]) -> str:
    operation = str(row["operation"])
    alias = row.get("operation_alias")
    return f"{alias} | {operation}" if alias else operation


# ---------------------------------------------------------------------------
# Raw Response tab: owns the request form (st.form) and calls debug_fetch().
# ---------------------------------------------------------------------------


def _raw_response_tab(
    selected: dict[str, Any],
    *,
    service_key: str,
    key_source: str,
    timeout: float,
) -> None:
    st.subheader(selected["dataset_name"])
    st.caption(f"{selected['service_id']} / {selected['service_name']} / {selected['operation']}")

    try:
        submitted, params, options, missing = _request_form(selected)
    except ValueError as exc:
        st.error(str(exc))
        return

    preview = {
        **params,
        "pageNo": options["page_no"],
        "numOfRows": options["num_of_rows"],
        "type": "json",
    }
    st.subheader("Request params preview (pythonic)")
    st.json(preview)

    if not submitted:
        return
    if missing:
        st.error("필수 파라미터를 입력하세요: " + ", ".join(missing))
        return
    if not service_key:
        st.error("Service key가 필요합니다. Environment/Auth 섹션을 확인하세요.")
        return

    try:
        hub = TourApiHubClient(service_key, timeout=timeout, service_key_source=key_source)
        run = hub.debug_fetch(
            selected["service_id"],
            selected["operation"],
            params=params,
            page_no=options["page_no"],
            num_of_rows=options["num_of_rows"],
            use_typed=options["use_typed"],
        )
    except Exception as exc:  # pragma: no cover - UI 표시
        st.error(str(exc))
        return

    _store_run(selected, run)
    if run.error:
        st.error(f"{run.error['type']}: {run.error['message']}")
    else:
        st.success(f"{len(run.processed or ())} items")
    st.json(jsonable(run.response))


def _request_form(
    selected: dict[str, Any],
) -> tuple[bool, dict[str, Any], dict[str, Any], list[str]]:
    parameters: list[dict[str, Any]] = list(selected["parameters"])
    required_specs = [spec for spec in parameters if spec["required"]]
    optional_specs = [spec for spec in parameters if not spec["required"]]
    key_prefix = f"{selected['service_id']}:{selected['operation']}"

    with st.form(f"request-form:{key_prefix}"):
        st.subheader("Required parameters")
        if required_specs:
            required_values = _render_param_grid(required_specs, key_prefix=key_prefix)
        else:
            st.caption("이 오퍼레이션에는 필수 파라미터가 없습니다.")
            required_values = {}

        st.subheader("Optional parameters")
        if optional_specs:
            optional_values = _render_param_grid(optional_specs, key_prefix=key_prefix)
        else:
            st.caption("선택 파라미터가 없습니다.")
            optional_values = {}

        page_no, num_of_rows = _render_common_options(key_prefix)

        use_typed = False
        if selected["service_id"] in SERVICE_ITEM_PARSERS:
            use_typed = st.checkbox(
                "typed 모델로 파싱 (.typed view)",
                value=False,
                key=f"{key_prefix}:use_typed",
                help="이 서비스에 등록된 typed row parser로 응답 item을 파싱합니다.",
            )

        extra_text = st.text_area(
            "Extra pythonic params (JSON)",
            value="{}",
            height=100,
            help="폼에 없는 pythonic 파라미터를 JSON object로 추가합니다.",
            key=f"{key_prefix}:extra",
        )
        submitted = st.form_submit_button("Run request", type="primary", width="stretch")

    params = {**required_values, **optional_values, **_parse_extra_params(extra_text)}
    params = {key: value for key, value in params.items() if value not in (None, "")}
    missing = [spec["name"] for spec in required_specs if spec["name"] not in params]
    return (
        submitted,
        params,
        {"page_no": page_no, "num_of_rows": num_of_rows, "use_typed": use_typed},
        missing,
    )


def _render_param_grid(specs: list[dict[str, Any]], *, key_prefix: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[index : index + 2], strict=False):
            with column:
                value = _render_one_param(spec, key=f"{key_prefix}:param:{spec['name']}")
                if value is not None:
                    values[spec["name"]] = value
    return values


def _render_one_param(spec: dict[str, Any], *, key: str) -> Any:
    label = spec["label"] + (" *" if spec["required"] else "")
    help_text = f"{spec['description']} Pythonic: {spec['name']}; API: {spec['api_name']}"
    kind = spec["kind"]
    if kind == "enum":
        return _render_enum_param(spec, label=label, key=key, help_text=help_text)
    if kind == "boolean":
        return _render_boolean_param(spec, label=label, key=key, help_text=help_text)
    if kind == "coordinate":
        return _render_coordinate_param(label=label, key=key, help_text=help_text)
    if kind == "number":
        raw_value = st.text_input(
            label,
            value=str(spec["default"] or ""),
            placeholder=_placeholder(spec),
            key=key,
            help=help_text,
        )
        return _parse_number(raw_value)
    raw_text = st.text_input(
        label,
        value=str(spec["default"] or ""),
        placeholder=_placeholder(spec),
        key=key,
        help=help_text,
    )
    return raw_text.strip() or None


def _render_enum_param(
    spec: dict[str, Any],
    *,
    label: str,
    key: str,
    help_text: str,
) -> str | None:
    options: list[dict[str, str]] = spec["options"]
    option_map = {option["label"]: option["value"] for option in options}
    labels = ["", *option_map]
    default = spec["default"]
    if default is None:
        index = 0
    else:
        default_label = next(
            (option["label"] for option in options if option["value"] == str(default)), ""
        )
        index = labels.index(default_label) if default_label in labels else 0
    selected_label = st.selectbox(label, labels, index=index, key=key, help=help_text)
    return option_map.get(selected_label) if selected_label else None


def _render_boolean_param(
    spec: dict[str, Any],
    *,
    label: str,
    key: str,
    help_text: str,
) -> bool | None:
    labels = ["", "Yes", "No"]
    index = 0
    if spec["default"] is True:
        index = 1
    elif spec["default"] is False:
        index = 2
    selected = st.selectbox(label, labels, index=index, key=key, help=help_text)
    if selected == "Yes":
        return True
    if selected == "No":
        return False
    return None


def _render_coordinate_param(*, label: str, key: str, help_text: str) -> dict[str, float] | None:
    st.caption(label)
    lon_col, lat_col = st.columns(2)
    lon_text = lon_col.text_input(
        "Longitude", placeholder="mapX / lon", key=f"{key}:lon", help=help_text
    )
    lat_text = lat_col.text_input(
        "Latitude", placeholder="mapY / lat", key=f"{key}:lat", help=help_text
    )
    if not lon_text.strip() or not lat_text.strip():
        return None
    return {"lon": float(lon_text), "lat": float(lat_text)}


def _render_common_options(key_prefix: str) -> tuple[int, int]:
    col1, col2 = st.columns(2)
    with col1:
        page_no = st.number_input(
            "pageNo", min_value=1, value=1, step=1, key=f"{key_prefix}:pageNo"
        )
    with col2:
        num_of_rows = st.number_input(
            "numOfRows",
            min_value=1,
            max_value=1000,
            value=10,
            step=1,
            key=f"{key_prefix}:numOfRows",
        )
    return int(page_no), int(num_of_rows)


def _placeholder(spec: dict[str, Any]) -> str | None:
    if spec.get("placeholder"):
        return str(spec["placeholder"])
    if spec["kind"] == "date":
        return "YYYYMMDD"
    if spec["kind"] == "month":
        return "YYYYMM"
    return None


def _parse_number(raw_value: str) -> int | float | None:
    text = raw_value.strip()
    if not text:
        return None
    value = float(text)
    if value.is_integer():
        return int(value)
    return value


def _parse_extra_params(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Extra params JSON이 올바르지 않습니다: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Extra params JSON은 object여야 합니다.")
    return payload


# ---------------------------------------------------------------------------
# Remaining tabs.
# ---------------------------------------------------------------------------


def _pydantic_model_tab(selected: dict[str, Any]) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 요청을 실행하면 Pydantic 모델을 확인할 수 있습니다.")
        return
    if run.error:
        st.warning("실행 중 오류가 발생했습니다. Validation Errors 탭을 확인하세요.")
        return
    st.json(jsonable(run.parsed))


def _processed_result_tab(selected: dict[str, Any]) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 요청을 실행하면 처리된 결과를 확인할 수 있습니다.")
        return
    data = jsonable(run.processed)
    if isinstance(data, list) and data:
        st.dataframe(pd.json_normalize(data, sep="."), width="stretch", hide_index=True)
    else:
        st.json(data)


def _validation_errors_tab(selected: dict[str, Any]) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("아직 실행된 요청이 없습니다.")
        return
    if not run.error:
        st.success("현재 실행 결과에 validation error 또는 exception이 없습니다.")
        return
    st.error(f"{run.error['type']}: {run.error['message']}")
    st.json(run.error)


def _debug_trace_tab(rows: list[dict[str, Any]], selected: dict[str, Any]) -> None:
    run = _current_run(selected)

    st.subheader("Selected operation")
    st.json({key: value for key, value in selected.items() if key != "parameters"})

    if run is not None:
        st.subheader("Trace")
        st.write(run.trace)
        st.subheader("Request (redacted)")
        st.json(run.request)
        st.subheader("Response meta")
        st.json({key: value for key, value in run.response.items() if key != "body"})
    else:
        st.info("Raw Response 탭에서 요청을 실행하면 request/response trace를 확인할 수 있습니다.")

    st.subheader(f"Catalog ({len(rows)} operations)")
    query = st.text_input("Filter catalog", placeholder="dataset, service, operation")
    catalog_df = pd.DataFrame(_dataframe_rows(rows))
    if query:
        lowered = query.lower()
        mask = catalog_df.apply(
            lambda row: row.astype(str).str.lower().str.contains(lowered).any(),
            axis=1,
        )
        catalog_df = catalog_df[mask]
    st.dataframe(catalog_df, width="stretch", hide_index=True)


def _dataframe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        prepared = dict(row)
        env_names = prepared.get("service_key_env_names")
        if isinstance(env_names, (list, tuple)):
            prepared["service_key_env_names"] = ", ".join(str(name) for name in env_names)
        normalized.append(prepared)
    return normalized


def _fixture_tab(fixture_base_dir: str, selected: dict[str, Any]) -> None:
    run = _current_run(selected)
    if run is None:
        st.info("Raw Response 탭에서 요청을 실행한 뒤 fixture를 저장할 수 있습니다.")
        st.caption("Fixture base dir")
        st.code(fixture_base_dir, language=None)
        return

    with st.expander("Save as fixture", expanded=True):
        case_name = st.text_input("Case name", value=f"{run.function}_normal")
        description = st.text_area(
            "Description",
            value=f"{selected['dataset_name']} / {selected['operation']} normal case",
        )
        assertion_mode = st.selectbox("Assertion mode", ASSERTION_MODES)
        exclude_fields_raw = st.text_input(
            "Exclude fields",
            value="fetched_at, request_id, updated_at, collected_at",
        )
        required_fields_raw = st.text_input("Required fields", value="")
        overwrite = st.checkbox("Overwrite existing fixture", value=False)

        assertion = {
            "mode": assertion_mode,
            "exclude_fields": [
                value.strip() for value in exclude_fields_raw.split(",") if value.strip()
            ],
            "required_fields": [
                value.strip() for value in required_fields_raw.split(",") if value.strip()
            ],
        }

        st.subheader("Fixture preview")
        st.json(
            {
                "function": run.function,
                "input": jsonable(run.input),
                "request": jsonable(run.request),
                "response": jsonable(run.response),
                "processed": jsonable(run.processed),
                "assertion": assertion,
            }
        )

        if st.button("Save as fixture"):
            try:
                path = save_fixture(
                    base_dir=fixture_base_dir,
                    function_name=run.function,
                    case_name=case_name,
                    description=description,
                    input_data=run.input,
                    request_data=run.request,
                    response_data=run.response,
                    parsed_result=run.parsed,
                    processed_result=run.processed,
                    assertion=assertion,
                    overwrite=overwrite,
                )
            except Exception as exc:  # pragma: no cover - UI 표시
                st.error(str(exc))
            else:
                st.success(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Sidebar / session-state helpers.
# ---------------------------------------------------------------------------


def _fixture_base_dir_sidebar() -> str:
    st.sidebar.subheader("Fixtures")
    candidates = _fixture_dir_candidates()
    options = [str(path) for path in candidates]
    custom_label = "Custom..."
    selection = st.sidebar.selectbox("Fixture base dir", [*options, custom_label])
    if selection == custom_label:
        selection = st.sidebar.text_input(
            "Custom fixture base dir",
            value=str((ROOT / "tests" / "fixtures").resolve()),
        )
    st.sidebar.caption(selection)
    return selection


def _fixture_dir_candidates() -> list[Path]:
    preferred = [ROOT / "tests" / "fixtures", ROOT / "tests", ROOT / "examples", ROOT]
    candidates: list[Path] = []
    for path in preferred:
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _store_run(selected: dict[str, Any], run: Any) -> None:
    st.session_state["last_run"] = {"selection_key": _selection_key(selected), "run": run}


def _current_run(selected: dict[str, Any]) -> Any | None:
    stored = st.session_state.get("last_run")
    if not isinstance(stored, dict):
        return None
    if stored.get("selection_key") != _selection_key(selected):
        return None
    return stored.get("run")


def _selection_key(selected: dict[str, Any]) -> str:
    return f"{selected['data_source']}:{selected['service_id']}:{selected['operation']}"


if __name__ == "__main__":
    main()
