from pathlib import Path
import streamlit as st

from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.workflow_runtime import WorkflowRuntime


@st.cache_resource(on_release=lambda runtime: runtime.close())
def get_runtime(storage_root: str):
    return WorkflowRuntime(ApplicationPaths(Path(storage_root)))
