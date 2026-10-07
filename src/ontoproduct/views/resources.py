import dataclasses
import json
from pathlib import Path

import streamlit as st

from ontoproduct.agents.real_registry import build_document_registry
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.llm_service import create_llm_services
from ontoproduct.services.parser_service import ParserService
from ontoproduct.services.settings import Settings, SettingsError
from ontoproduct.services.workflow_runtime import WorkflowRuntime


@st.cache_resource(on_release=lambda runtime: runtime.close())
def get_runtime(storage_root: str, settings_json: str | None = None):
    """Cached runtime. Real-mode settings are part of the cache key; API keys are not."""
    paths = ApplicationPaths(Path(storage_root))
    if settings_json is None:
        return WorkflowRuntime(paths)
    llm_services = create_llm_services(Settings(**json.loads(settings_json)))
    parser_service = ParserService(paths.uploads)

    def registry_factory(ontology):
        return build_document_registry(
            ontology, parser_service=parser_service, llm_services=llm_services
        )

    return WorkflowRuntime(paths, registry_factory=registry_factory)


def settings_json(settings):
    return json.dumps(dataclasses.asdict(settings), sort_keys=True)


def current_runtime():
    """Runtime for the configured mode; a settings error stops the page, never falls back to mock."""
    root = str(ApplicationPaths.from_environment().root)
    try:
        settings = Settings.from_environment()
        if settings.mode == "mock":
            return get_runtime(root)
        return get_runtime(root, settings_json(settings))
    except SettingsError as exc:
        st.error(f"실행 설정 오류: {exc}")
        st.caption(
            "AGENT_MODE, OPENAI_API_KEY 환경변수와 src/ontoproduct/config/llm.yaml을 확인한 뒤 앱을 다시 시작하세요."
        )
        st.stop()
