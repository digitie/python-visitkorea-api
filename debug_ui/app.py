from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from pydantic import BaseModel

from visitkorea import (
    SERVICE_BY_KEY,
    SERVICE_DEFINITIONS,
    MobileOS,
    OperationParameter,
    TourApiError,
    TourApiHubClient,
    get_api_catalog,
    get_operation_schema,
    normalize_service_key,
    resolve_service_key,
    service_key_env_names,
    service_key_sources,
)
from visitkorea._service_views import SERVICE_ITEM_PARSERS


def service_supports_typed(service_id: str) -> bool:
    """Return whether a service has a registered typed model for the .typed view."""

    return service_id in SERVICE_ITEM_PARSERS


def jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def catalog_rows_for_service(service_id: str) -> list[dict[str, Any]]:
    return [row for row in get_api_catalog() if row["service_id"] == service_id]


def dataframe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        prepared = dict(row)
        env_names = prepared.get("service_key_env_names")
        if isinstance(env_names, (list, tuple)):
            prepared["service_key_env_names"] = ", ".join(str(name) for name in env_names)
        normalized.append(prepared)
    return normalized


def service_option_label(service_key: str) -> str:
    service = SERVICE_BY_KEY[service_key]
    return f"{service.dataset_name} | {service.key}"


def operation_option_label(row: dict[str, Any]) -> str:
    operation = str(row["operation"])
    alias = row.get("operation_alias")
    if alias:
        return f"{alias} | {operation}"
    return operation


def result_items_dataframe(result: Any) -> pd.DataFrame:
    rows = [jsonable(item) for item in result.items]
    if not rows:
        return pd.DataFrame()
    return pd.json_normalize(rows, sep=".")


def operation_parameters_dataframe(parameters: tuple[OperationParameter, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "label": parameter.label,
                "pythonic": parameter.name,
                "api": parameter.api_name,
                "type": parameter.kind,
                "required": parameter.required,
                "description": parameter.description,
            }
            for parameter in parameters
            if parameter.name != "service_specific"
        ]
    )


def operation_schema_payload() -> dict[str, Any]:
    return {
        "service_id": selected_schema.service_id,
        "service_name": selected_schema.service_name,
        "operation": selected_schema.operation,
        "pythonic_name": selected_schema.pythonic_name,
        "summary": selected_schema.summary,
        "details": selected_schema.details,
        "parameters": [
            {
                "name": parameter.name,
                "api_name": parameter.api_name,
                "kind": parameter.kind,
                "required": parameter.required,
                "default": parameter.default,
            }
            for parameter in selected_schema.parameters
            if parameter.name != "service_specific"
        ],
    }


def render_parameter_form(
    parameters: tuple[OperationParameter, ...],
    *,
    key_prefix: str,
) -> tuple[dict[str, Any], list[str]]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    visible_parameters = [param for param in parameters if param.name != "service_specific"]

    for parameter in visible_parameters:
        label = parameter.label + (" *" if parameter.required else "")
        help_text = f"{parameter.description} Pythonic: {parameter.name}; API: {parameter.api_name}"
        key = f"{key_prefix}:{parameter.name}"
        value = _render_parameter(parameter, label=label, key=key, help_text=help_text)
        has_value = value not in (None, "", {})
        if parameter.required and not has_value:
            missing.append(parameter.label)
        if has_value:
            values[parameter.name] = value

    extra_params = _render_extra_parameters(key_prefix=key_prefix)
    values.update(extra_params)
    return values, missing


def _render_parameter(
    parameter: OperationParameter,
    *,
    label: str,
    key: str,
    help_text: str,
) -> Any:
    if parameter.kind == "enum":
        return _render_enum_parameter(parameter, label=label, key=key, help_text=help_text)
    if parameter.kind == "boolean":
        return _render_boolean_parameter(parameter, label=label, key=key, help_text=help_text)
    if parameter.kind == "coordinate":
        return _render_coordinate_parameter(label=label, key=key, help_text=help_text)
    if parameter.kind == "number":
        raw_value = st.text_input(
            label,
            value=str(parameter.default or ""),
            placeholder=_placeholder(parameter),
            key=key,
            help=help_text,
        )
        return _parse_number(raw_value)
    raw_text = st.text_input(
        label,
        value=str(parameter.default or ""),
        placeholder=_placeholder(parameter),
        key=key,
        help=help_text,
    )
    return raw_text.strip() or None


def _render_enum_parameter(
    parameter: OperationParameter,
    *,
    label: str,
    key: str,
    help_text: str,
) -> str | None:
    option_values = {option.label: option.value for option in parameter.options}
    labels = [""] + list(option_values)
    if parameter.default is None:
        index = 0
    else:
        default_label = next(
            (
                option.label
                for option in parameter.options
                if option.value == str(parameter.default)
            ),
            "",
        )
        index = labels.index(default_label) if default_label in labels else 0
    selected_label = st.selectbox(label, labels, index=index, key=key, help=help_text)
    if not selected_label:
        return None
    return option_values[selected_label]


def _render_boolean_parameter(
    parameter: OperationParameter,
    *,
    label: str,
    key: str,
    help_text: str,
) -> bool | None:
    labels = ["", "Yes", "No"]
    index = 0
    if parameter.default is True:
        index = 1
    elif parameter.default is False:
        index = 2
    selected = st.selectbox(label, labels, index=index, key=key, help=help_text)
    if selected == "Yes":
        return True
    if selected == "No":
        return False
    return None


def _render_coordinate_parameter(
    *,
    label: str,
    key: str,
    help_text: str,
) -> dict[str, float] | None:
    st.caption(label)
    lon_col, lat_col = st.columns(2)
    lon_text = lon_col.text_input(
        "Longitude",
        placeholder="mapX / lon",
        key=f"{key}:lon",
        help=help_text,
    )
    lat_text = lat_col.text_input(
        "Latitude",
        placeholder="mapY / lat",
        key=f"{key}:lat",
        help=help_text,
    )
    if not lon_text.strip() and not lat_text.strip():
        return None
    if not lon_text.strip() or not lat_text.strip():
        return None
    return {"lon": float(lon_text), "lat": float(lat_text)}


def _render_extra_parameters(*, key_prefix: str) -> dict[str, str]:
    params: dict[str, str] = {}
    with st.expander("Additional pythonic parameters"):
        for index in range(4):
            key_col, value_col = st.columns([1, 2])
            extra_key = key_col.text_input(
                f"Extra key {index + 1}",
                key=f"{key_prefix}:extra-key:{index}",
                label_visibility="collapsed",
                placeholder="pythonic_name",
            )
            extra_value = value_col.text_input(
                f"Extra value {index + 1}",
                key=f"{key_prefix}:extra-value:{index}",
                label_visibility="collapsed",
                placeholder="value",
            )
            if extra_key.strip() and extra_value.strip():
                params[extra_key.strip()] = extra_value.strip()
    return params


def _placeholder(parameter: OperationParameter) -> str | None:
    if parameter.placeholder:
        return parameter.placeholder
    if parameter.kind == "date":
        return "YYYYMMDD"
    if parameter.kind == "month":
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


def build_trace(
    *,
    selected_catalog_row: dict[str, Any],
    selected_key_source: str,
    default_key: str,
    normalized_key: str | None,
    key_was_normalized: bool,
) -> list[str]:
    return [
        f"dataset={selected_catalog_row['dataset_name']}",
        f"service_id={selected_catalog_row['service_id']}",
        f"service_name={selected_catalog_row['service_name']}",
        f"operation={selected_catalog_row['operation']}",
        f"data_source={selected_catalog_row['data_source']}",
        f"catalog_source={selected_catalog_row['catalog_source']}",
        f"service_key_source={selected_key_source}",
        f"service_key_env_names={service_key_env_names(selected_key_source)}",
        f"service_key_loaded_from_env_or_dotenv={bool(default_key)}",
        f"service_key_present={bool(normalized_key)}",
        f"service_key_whitespace_normalized={key_was_normalized}",
        f"service_key_apply_url={selected_catalog_row['service_key_apply_url']}",
        f"manual_url={selected_catalog_row['manual_url']}",
    ]


def store_run_state(
    *,
    result: Any | None,
    error: dict[str, Any] | None,
    trace: list[str],
    request_params: dict[str, Any],
    page_no: int,
    num_of_rows: int,
    selected_catalog_row: dict[str, Any],
    selected_key_source: str,
    default_key: str,
    normalized_key: str | None,
    key_was_normalized: bool,
) -> None:
    st.session_state["last_run"] = {
        "result": result,
        "error": error,
        "trace": trace,
        "request_params": request_params,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
        "selected_catalog_row": selected_catalog_row,
        "key_info": {
            "selected_source": selected_key_source,
            "env_names": service_key_env_names(selected_key_source),
            "loaded_from_env_or_dotenv": bool(default_key),
            "normalized": bool(normalized_key),
            "whitespace_removed": key_was_normalized,
        },
    }


st.set_page_config(page_title="VisitKorea API Workbench", layout="wide")

if "last_run" not in st.session_state:
    st.session_state["last_run"] = None

catalog = tuple(get_api_catalog())
service_options = {
    service_option_label(service.key): service.key for service in SERVICE_DEFINITIONS
}

st.title("VisitKorea API Workbench")
st.caption("Catalog-first debug UI for official TourAPI services.")

with st.sidebar:
    st.header("Request")
    selected_service_label = st.selectbox("Dataset", list(service_options))
    selected_service_id = service_options[selected_service_label]
    selected_service = SERVICE_BY_KEY[selected_service_id]
    selected_rows = catalog_rows_for_service(selected_service_id)

    operation_options = {
        operation_option_label(row): str(row["operation"])
        for row in selected_rows
        if row["operation"]
    }
    selected_operation_label = st.selectbox("Operation", list(operation_options))
    selected_operation = operation_options[selected_operation_label]
    selected_catalog_row = next(
        row for row in selected_rows if row["operation"] == selected_operation
    )
    selected_schema = get_operation_schema(selected_service_id, selected_operation)

    st.divider()
    st.subheader("Client")
    mobile_os_options = {
        f"{item.name.replace('_', ' ').title()} ({item.value})": item.value
        for item in MobileOS
    }
    mobile_os_labels = list(mobile_os_options)
    default_mobile_os_index = mobile_os_labels.index("Etc (ETC)")
    selected_mobile_os_label = st.selectbox(
        "MobileOS",
        mobile_os_labels,
        index=default_mobile_os_index,
    )
    selected_mobile_os = mobile_os_options[selected_mobile_os_label]
    mobile_app = st.text_input("MobileApp", value="visitkorea")

    st.divider()
    st.subheader("Service key")
    key_sources = {source.label: source.key for source in service_key_sources()}
    selected_key_source_label = st.selectbox("Key source", list(key_sources))
    selected_key_source = key_sources[selected_key_source_label]
    default_key = resolve_service_key(source=selected_key_source) or ""
    service_key_input = st.text_input(
        "Service key",
        value=default_key,
        type="password",
        placeholder="Loaded from .env when available",
        help="Whitespace from copy-paste is removed before requests.",
    )
    normalized_key = normalize_service_key(service_key_input)
    key_was_normalized = bool(service_key_input and normalized_key != service_key_input)
    if key_was_normalized:
        st.caption("Copy-paste whitespace will be removed before the request.")
    st.caption("Env: " + ", ".join(service_key_env_names(selected_key_source)))

    st.divider()
    st.link_button(
        "Open service-key page",
        selected_service.apply_url,
        use_container_width=True,
    )
    st.link_button("Open API manual", selected_service.manual_url, use_container_width=True)

info_cols = st.columns([1.8, 1, 1, 1, 1])
info_cols[0].caption("Dataset")
info_cols[0].write(selected_catalog_row["dataset_name"])
info_cols[1].caption("Service")
info_cols[1].write(selected_catalog_row["service_name"])
info_cols[2].caption("Operation")
info_cols[2].write(selected_operation)
info_cols[3].caption("Data source")
info_cols[3].write(selected_catalog_row["data_source"])
info_cols[4].caption("Key")
info_cols[4].write("loaded" if default_key else "manual")

link_cols = st.columns(2)
link_cols[0].link_button(
    "Service-key page",
    selected_catalog_row["service_key_apply_url"],
    use_container_width=True,
)
link_cols[1].link_button(
    "Manual",
    selected_catalog_row["manual_url"],
    use_container_width=True,
)

st.subheader(selected_schema.summary)
st.write(selected_schema.details)
parameter_df = operation_parameters_dataframe(selected_schema.parameters)
if not parameter_df.empty:
    st.dataframe(parameter_df, use_container_width=True, hide_index=True)

with st.form("request_form"):
    param_col, option_col = st.columns([3, 1])
    with param_col:
        form_params, missing_params = render_parameter_form(
            selected_schema.parameters,
            key_prefix=f"{selected_service_id}:{selected_operation}",
        )
    page_no = option_col.number_input("pageNo", min_value=1, value=1)
    num_of_rows = option_col.number_input("numOfRows", min_value=1, max_value=1000, value=10)
    timeout = option_col.number_input(
        "Timeout seconds",
        min_value=1.0,
        max_value=120.0,
        value=10.0,
    )
    if service_supports_typed(selected_service_id):
        use_typed = option_col.checkbox(
            "typed 모델로 파싱",
            value=False,
            help="이 서비스의 .typed 뷰로 응답을 서비스별 모델로 파싱합니다.",
        )
    else:
        use_typed = False
    run_clicked = st.form_submit_button(
        "Run request",
        type="primary",
        use_container_width=True,
    )

if run_clicked:
    trace = build_trace(
        selected_catalog_row=selected_catalog_row,
        selected_key_source=selected_key_source,
        default_key=default_key,
        normalized_key=normalized_key,
        key_was_normalized=key_was_normalized,
    )
    request_params: dict[str, Any] = {}
    result: Any | None = None
    error: dict[str, Any] | None = None
    try:
        if not normalized_key:
            raise ValueError("Service key is required.")
        if missing_params:
            missing_text = ", ".join(missing_params)
            raise ValueError(f"Required parameters are missing: {missing_text}")
        request_params = form_params
        trace.append(f"request_params_pythonic={request_params}")
        trace.append(f"operation_summary={selected_schema.summary}")
        hub = TourApiHubClient(
            normalized_key,
            mobile_os=selected_mobile_os,
            mobile_app=mobile_app,
            timeout=float(timeout),
            service_key_source=selected_key_source,
        )
        service_client = hub.service(selected_service_id)
        caller = service_client.typed if use_typed else service_client
        result = caller.call(
            selected_operation,
            page_no=int(page_no),
            num_of_rows=int(num_of_rows),
            **request_params,
        )
        trace.append(f"typed={use_typed}")
        trace.append(f"items={len(result.items)}")
        trace.append(f"total_count={result.total_count}")
    except TourApiError as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "metadata": exc.metadata}
        trace.append(f"error={type(exc).__name__}")
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        trace.append(f"error={type(exc).__name__}")
    store_run_state(
        result=result,
        error=error,
        trace=trace,
        request_params=request_params,
        page_no=int(page_no),
        num_of_rows=int(num_of_rows),
        selected_catalog_row=selected_catalog_row,
        selected_key_source=selected_key_source,
        default_key=default_key,
        normalized_key=normalized_key,
        key_was_normalized=key_was_normalized,
    )

last_run = st.session_state["last_run"]
last_result = last_run["result"] if last_run else None
last_error = last_run["error"] if last_run else None

if last_error:
    st.error(f"{last_error['type']}: {last_error['message']}")
elif last_result is not None:
    st.success(f"{len(last_result.items)} items, total_count={last_result.total_count}")
else:
    st.info("Select a dataset and run a request.")

response_tab, table_tab, trace_tab, catalog_tab, fixture_tab = st.tabs(
    ["Response", "Table", "Debug Trace", "Catalog", "Fixture / Testcase"]
)

with response_tab:
    if last_result is not None:
        raw_col, model_col = st.columns(2)
        raw_col.subheader("Raw response")
        raw_col.json(jsonable(last_result.raw))
        model_col.subheader("Pydantic model")
        model_col.json(jsonable(last_result))
    elif last_error is not None:
        st.json(last_error)
    else:
        st.info("Run an API call to see the response.")

with table_tab:
    if last_result is not None:
        result_df = result_items_dataframe(last_result)
        if result_df.empty:
            st.info("No items returned.")
        else:
            st.dataframe(result_df, use_container_width=True, hide_index=True)
    else:
        st.info("Run an API call to see rows.")

with trace_tab:
    st.subheader("Selected catalog item")
    st.json(selected_catalog_row)
    st.subheader("Operation schema")
    st.json(operation_schema_payload())
    st.subheader("Service-key lookup")
    key_info = (
        last_run["key_info"]
        if last_run is not None
        else {
            "selected_source": selected_key_source,
            "env_names": service_key_env_names(selected_key_source),
            "loaded_from_env_or_dotenv": bool(default_key),
            "normalized": bool(normalized_key),
            "whitespace_removed": key_was_normalized,
        }
    )
    st.json(key_info)
    st.subheader("Trace")
    trace = (
        last_run["trace"]
        if last_run is not None
        else build_trace(
            selected_catalog_row=selected_catalog_row,
            selected_key_source=selected_key_source,
            default_key=default_key,
            normalized_key=normalized_key,
            key_was_normalized=key_was_normalized,
        )
    )
    st.code("\n".join(trace), language="text")
    st.subheader("Dataset catalog rows")
    st.dataframe(
        pd.DataFrame(dataframe_rows(selected_rows)),
        use_container_width=True,
        hide_index=True,
    )

with catalog_tab:
    query = st.text_input("Filter catalog", placeholder="dataset, service, operation")
    catalog_df = pd.DataFrame(dataframe_rows(list(catalog)))
    if query:
        lowered = query.lower()
        mask = catalog_df.apply(
            lambda row: row.astype(str).str.lower().str.contains(lowered).any(),
            axis=1,
        )
        catalog_df = catalog_df[mask]
    st.dataframe(catalog_df, use_container_width=True, hide_index=True)

with fixture_tab:
    if last_result is None and last_error is None:
        st.info("Run an API call to create a fixture summary.")
    else:
        fixture = {
            "service_id": last_run["selected_catalog_row"]["service_id"],
            "service_name": last_run["selected_catalog_row"]["service_name"],
            "operation": last_run["selected_catalog_row"]["operation"],
            "params": last_run["request_params"],
            "page_no": last_run["page_no"],
            "num_of_rows": last_run["num_of_rows"],
            "error": last_error,
        }
        if last_result is not None:
            first_item = jsonable(last_result.items[0]) if last_result.items else {}
            fixture["result"] = {
                "item_count": len(last_result.items),
                "total_count": last_result.total_count,
                "first_item_keys": sorted(first_item) if isinstance(first_item, dict) else [],
            }
        st.json(fixture)
