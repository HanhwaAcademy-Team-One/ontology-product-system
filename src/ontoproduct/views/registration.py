import streamlit as st

from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.services.evidence_service import evidence_candidates, is_conflict
from ontoproduct.services.settings import Settings
from ontoproduct.views.presentation import (
    CLASS_LABELS,
    LABELS,
    STATUS_LABELS,
    attribute_rows,
    parse_value,
)
from ontoproduct.views.resources import current_runtime
from ontoproduct.views.streaming import consume


def _resume(runtime, thread_id, payload):
    try:
        consume(runtime.resume(thread_id, payload))
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    st.rerun()


def _start(runtime, uploads, *, demo=False):
    try:
        session_id = st.session_state.session_id
        if demo:
            references = [
                runtime.documents.save(
                    session_id,
                    "demo_motor_spec.txt",
                    b"MOCK DM-500 BLDC Motor specification",
                )
            ]
        else:
            references = [
                runtime.documents.save(session_id, upload.name, upload.getvalue())
                for upload in uploads
            ]
        thread_id = runtime.create_case(session_id)
        st.session_state.thread_id = thread_id
        st.query_params["case"] = thread_id
        consume(
            runtime.start(
                thread_id,
                references,
                max_extraction_retries=int(
                    st.session_state.get("max_extraction_retries", 1)
                ),
                max_ontology_retries=int(
                    st.session_state.get("max_ontology_retries", 1)
                ),
            )
        )
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    st.rerun()


def _mode_caption(settings):
    if settings.mode == "mock":
        return "Mock 추출 모드 · 업로드 파일은 보관되며, 현재 추출 결과는 DM-500 예제 데이터를 사용합니다."
    models = settings.models
    if len(set(models.values())) == 1:
        model = next(iter(models.values()))
    else:
        model = f"추출 {models['extraction']} · 분류 {models['ontology']}"
    return (
        "실제 문서 분석 (Parser·Extraction·Ontology·Validation·Reviewer 실제)"
        f" · 모델: {settings.provider}/{model}"
    )


def _upload_form(runtime, *, demo):
    st.subheader("등록할 제품의 문서를 추가하세요")
    st.write("한 작업에 여러 문서를 올릴 수 있습니다. 등록 대상 제품은 하나입니다.")
    uploads = st.file_uploader(
        "제품 사양서 · 데이터시트 · BOM · 시험 결과",
        type=["pdf", "xlsx", "txt"],
        accept_multiple_files=True,
        key=f"source_uploads_{st.session_state.upload_generation}",
        help="파일당 최대 20 MB. 업로드한 원본은 작업 폴더에 보관됩니다.",
    )
    with st.expander("자동 재시도 설정"):
        left, right = st.columns(2)
        left.number_input(
            "정보 추출 추가 시도",
            min_value=0,
            max_value=3,
            value=1,
            step=1,
            key="max_extraction_retries",
        )
        right.number_input(
            "분류 매핑 추가 시도",
            min_value=0,
            max_value=3,
            value=1,
            step=1,
            key="max_ontology_retries",
        )
    left, right = st.columns(2)
    if left.button(
        "업로드 문서로 시작",
        disabled=not uploads,
        type="primary",
        key="start_upload",
        width="stretch",
    ):
        _start(runtime, uploads)
    if demo and right.button("Mock 예제로 시작", key="start_demo", width="stretch"):
        _start(runtime, [], demo=True)


def _edit_form(runtime, thread_id, state):
    product = state["normalized_product"]
    revision = len(state.get("agent_logs", []))
    flagged = {
        field.removeprefix("attributes.")
        for field in state["review_result"].get("retry_fields", [])
    }
    with st.expander(
        "제품 정보 수정", expanded=not state["review_result"]["can_register"]
    ):
        if flagged:
            st.warning(
                "AI 신뢰도가 낮거나 없는 항목: "
                + ", ".join(LABELS.get(key, key) for key in sorted(flagged))
                + " — 원문과 비교해 값이 맞으면 'AI 값 확인'을 체크하세요."
            )
        selected_class = st.selectbox(
            "제품 분류",
            options=list(runtime.ontology.definition.classes),
            index=list(runtime.ontology.definition.classes).index(
                product["product_class"]
            ),
            format_func=lambda name: CLASS_LABELS.get(name, name),
            key=f"edit_class_{thread_id}_{revision}",
        )
        properties = runtime.ontology.resolve_properties(selected_class)
        required = runtime.ontology.resolve_required_properties(selected_class)
        with st.form(f"edit_product_{thread_id}"):
            confirm_class = (
                "product_class" not in state.get("locked_fields", [])
                and st.checkbox(
                    "AI 분류 확정 (현재 분류가 맞습니다)",
                    key=f"confirm_class_{thread_id}_{revision}",
                )
            )
            name = st.text_input(
                "제품명",
                value=product.get("product_name") or "",
                key=f"edit_name_{thread_id}_{revision}",
            )
            inputs = {}
            for key, prop in properties.items():
                attr = product["attributes"].get(key, {})
                value = attr.get("value")
                label = LABELS.get(key, key) + (" *" if key in required else "")
                left, right = st.columns([3, 1])
                if prop.type == "boolean":
                    choices = ["", "예", "아니오"]
                    initial = "" if value is None else ("예" if value else "아니오")
                    text = left.selectbox(
                        label,
                        choices,
                        index=choices.index(initial),
                        key=f"edit_value_{thread_id}_{revision}_{selected_class}_{key}",
                    )
                else:
                    text = left.text_input(
                        label,
                        value="" if value is None else str(value),
                        key=f"edit_value_{thread_id}_{revision}_{selected_class}_{key}",
                    )
                unit = None
                if prop.units:
                    current_unit = (
                        attr.get("unit")
                        if attr.get("unit") in prop.units
                        else prop.canonical_unit
                    )
                    unit = right.selectbox(
                        "단위",
                        prop.units,
                        index=prop.units.index(current_unit),
                        key=f"edit_unit_{thread_id}_{revision}_{selected_class}_{key}",
                    )
                confirm = (
                    left.checkbox(
                        "AI 값 확인",
                        key=f"confirm_{thread_id}_{revision}_{selected_class}_{key}",
                    )
                    if key in flagged and value is not None
                    else False
                )
                inputs[key] = (text, unit, prop.type, confirm)
            submitted = st.form_submit_button(
                "수정 후 재검증", type="primary", key="submit_edit"
            )
        if submitted:
            try:
                edits = {}
                if name != (product.get("product_name") or ""):
                    if not name.strip():
                        raise ValueError("제품명은 비워둘 수 없습니다.")
                    edits["product_name"] = name.strip()
                for key, (text, unit, property_type, confirm) in inputs.items():
                    value = parse_value(text, property_type)
                    old = product["attributes"].get(key, {})
                    if confirm or value != old.get("value") or (
                        value is not None and unit != old.get("unit")
                    ):
                        edits[f"attributes.{key}"] = ProductAttribute(
                            value=value, unit=unit
                        ).model_dump(mode="json")
                changed_class = (
                    selected_class
                    if selected_class != product["product_class"] or confirm_class
                    else None
                )
                if not edits and not changed_class:
                    st.info("변경된 값이 없습니다.")
                else:
                    _resume(
                        runtime,
                        thread_id,
                        {
                            "action": "EDIT",
                            "edits": edits or None,
                            "changed_class": changed_class,
                        },
                    )
            except (ValueError, KeyError) as exc:
                st.error(f"입력값을 확인하세요: {exc}")


def _review(runtime, thread_id, state, payload):
    review = state["review_result"]
    if review["can_register"]:
        st.success("필수 항목 검증을 통과했습니다. 내용을 확인하고 등록을 승인하세요.")
    else:
        st.warning("수정이 필요한 항목이 있습니다. 필수 값을 보완한 뒤 재검증하세요.")
    if payload.get("feedback"):
        st.error(payload["feedback"])
    conflicts = []
    for key, raw in state["normalized_product"]["attributes"].items():
        attr = ProductAttribute.model_validate(raw)
        if is_conflict(attr):
            conflicts.extend(
                {
                    "항목": LABELS.get(key, key),
                    "값": candidate.value,
                    "단위": candidate.unit,
                    "출처": candidate.source_file,
                    "페이지": candidate.page,
                    "근거": candidate.evidence,
                }
                for candidate in evidence_candidates(attr)
            )
    if conflicts:
        st.error("문서마다 값이 다른 항목이 있습니다. 원문을 확인해 올바른 값을 입력하세요.")
        st.dataframe(conflicts, hide_index=True, width="stretch")
    issues = state.get("validation_result", {}).get("issues", [])
    if issues:
        with st.expander("검증 결과", expanded=not review["can_register"]):
            st.dataframe(
                [
                    {
                        "항목": LABELS.get(
                            i["field"].removeprefix("attributes."), i["field"]
                        ),
                        "수준": i["severity"],
                        "내용": i["message"],
                    }
                    for i in issues
                ],
                hide_index=True,
                width="stretch",
            )
    candidates = state.get("duplicate_candidates", [])
    if candidates:
        st.info("유사한 기존 제품이 있습니다. 후보를 확인한 뒤 등록 여부를 결정하세요.")
        verdicts = {"LIKELY_DUPLICATE": "중복 가능성 높음", "POSSIBLE_DUPLICATE": "중복 의심"}
        st.dataframe([{"제품명": c["product_name"], "판정": verdicts.get(c.get("verdict"), "-"),
                       "규칙 기반 유사도": f"{c['score']:.0%}", "근거": c["reason"]}
                      for c in candidates], hide_index=True, width="stretch")
    orphaned = state.get("orphaned_overrides", {})
    if orphaned:
        st.warning(
            "현재 제품 분류에서 사용할 수 없는 수동 수정값을 보관했습니다. 분류를 되돌리면 복원됩니다."
        )
        st.json(orphaned, expanded=False)
    _edit_form(runtime, thread_id, state)
    left, right = st.columns(2)
    if left.button(
        "등록 승인",
        type="primary",
        disabled=not review["can_register"],
        key="approve_case",
        width="stretch",
    ):
        _resume(runtime, thread_id, {"action": "APPROVE"})
    if right.button("등록 거절", key="reject_case", width="stretch"):
        _resume(runtime, thread_id, {"action": "REJECT"})


def _error_review(runtime, thread_id, payload):
    st.error(
        "Agent 실행 중 오류가 발생했습니다. 원인을 확인하고 재시도하거나 작업을 중단하세요."
    )
    for error in payload["errors"]:
        st.write(f"**{error['stage']}** · {error['message']}")
    if payload.get("feedback"):
        st.warning(payload["feedback"])
    left, right = st.columns(2)
    recoverable = "RETRY" in payload.get("actions", []) and all(
        e["recoverable"] and e.get("exception_type") != "DocumentConflictError"
        for e in payload["errors"]
    )
    if not recoverable:
        st.info(
            "같은 문서 재시도로 해결되지 않습니다. 후보를 확인해 문서를 수정한 뒤 작업을 중단하고 사이드바의 '새 등록 작업'으로 올리세요."
        )
    if recoverable and left.button(
        "오류 재시도", type="primary", key="retry_error", width="stretch"
    ):
        _resume(runtime, thread_id, {"action": "RETRY"})
    if right.button("작업 중단", key="stop_error", width="stretch"):
        _resume(runtime, thread_id, {"action": "STOP"})


def render():
    runtime = current_runtime()
    # current_runtime() already validated the settings or stopped the page.
    settings = Settings.from_environment()
    st.title("제품 등록")
    st.caption(_mode_caption(settings))
    thread_id = st.session_state.get("thread_id")
    if not thread_id:
        _upload_form(runtime, demo=settings.mode == "mock")
        return
    snapshot = runtime.snapshot(thread_id)
    state = snapshot.values
    if not state:
        st.info("아직 실행되지 않은 작업입니다. 새 등록 작업을 시작하세요.")
        return
    pending = [i.value for task in snapshot.tasks for i in task.interrupts]
    status = (
        "ERROR" if pending and pending[0]["kind"] == "error" else state["case_status"]
    )
    left, middle, right = st.columns(3)
    left.metric("작업 상태", STATUS_LABELS.get(status, status))
    middle.metric(
        "추출 재시도",
        f"{state['extraction_retry_count']} / {state['max_extraction_retries']}",
    )
    right.metric(
        "분류 재시도",
        f"{state['ontology_retry_count']} / {state['max_ontology_retries']}",
    )
    st.caption(f"작업 ID: {thread_id}")
    if "normalized_product" in state:
        product = state["normalized_product"]
        st.subheader(
            f"{product.get('product_name') or '이름 없는 제품'} · {CLASS_LABELS.get(product['product_class'], product['product_class'])}"
        )
        st.dataframe(attribute_rows(state), hide_index=True, width="stretch")
    if pending:
        if pending[0]["kind"] == "error":
            _error_review(runtime, thread_id, pending[0])
        else:
            _review(runtime, thread_id, state, pending[0])
    elif status == "REGISTERED":
        record = runtime.products.get_by_case(thread_id)
        st.success("제품이 SQLite에 등록되었습니다.")
        if record:
            st.download_button(
                "제품 JSON 다운로드",
                runtime.registration.json_bytes(record),
                file_name=f"{record['product_id']}.json",
                mime="application/json",
                on_click="ignore",
                key="download_registered",
            )
        else:
            st.error("등록된 제품 레코드를 찾을 수 없습니다.")
    elif status in {"REJECTED", "STOPPED"}:
        st.info(
            "작업이 종료되었습니다. 새 등록 작업으로 다른 제품을 등록할 수 있습니다."
        )
    elif snapshot.next or snapshot.tasks:
        st.warning("이전 실행이 완료되지 않았습니다. 저장된 실행을 이어갈 수 있습니다.")
        if st.button("실행 이어가기", key="continue_workflow"):
            try:
                consume(runtime.continue_run(thread_id))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
    with st.expander("원본 문서와 실행 이력"):
        st.dataframe(
            [
                {"파일": d["name"], "크기 (bytes)": d["size"], "형식": d["mime_type"]}
                for d in state.get("source_documents", [])
            ],
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            [
                {
                    "Agent": log["agent"],
                    "상태": log["status"],
                    "시도": log["attempt"],
                    "실행 시간 (초)": log["execution_time"],
                }
                for log in state.get("agent_logs", [])
                if log["status"] != "running"
            ],
            hide_index=True,
            width="stretch",
        )
        if state.get("error_events"):
            st.dataframe(state["error_events"], hide_index=True, width="stretch")


if __name__ == "__main__":
    render()
