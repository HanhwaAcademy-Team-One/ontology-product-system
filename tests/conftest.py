import os
from pathlib import Path
from copy import deepcopy
from uuid import uuid4

import pytest

from ontoproduct.graph.state import initial_state
from ontoproduct.graph.workflow import build_workflow
from ontoproduct.mocks.agents import ExtractionMock, mock_registry
from ontoproduct.services.ontology_service import OntologyService


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # Separate every run from private directories created by another Windows account.
    # Keep an explicitly supplied --basetemp unchanged.
    if config.option.basetemp is None:
        temporary_root = config.rootpath / ".pytest_tmp"
        temporary_root.mkdir(exist_ok=True)
        config.option.basetemp = str(temporary_root / uuid4().hex)

    # Create the cache with inherited workspace permissions before cacheprovider
    # creates it by renaming a private temporary directory.
    cache_path = Path(os.path.expandvars(config.getini("cache_dir")))
    if not cache_path.is_absolute():
        cache_path = config.rootpath / cache_path
    cache_path.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def ontology():
    return OntologyService()


@pytest.fixture
def registry(ontology):
    return mock_registry(ontology)


@pytest.fixture
def config():
    return {"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 150}


@pytest.fixture
def complete_registry(registry):
    attrs = deepcopy(registry.get("extraction").attributes)
    attrs["rated_speed"] = {
        "value": 3000,
        "unit": "rpm",
        "confidence": 0.95,
        "provenance": "AI",
    }
    registry.register(ExtractionMock(attributes=attrs), replace=True)
    return registry


@pytest.fixture
def paused_state(complete_registry, ontology, config):
    graph = build_workflow(complete_registry, ontology=ontology)
    graph.invoke(initial_state(), config)
    return graph.get_state(config).values


def count_runs(state, agent):
    return sum(
        log["agent"] == agent and log["status"] != "running"
        for log in state["agent_logs"]
    )


def fail_once(agent):
    original = agent.run
    calls = []

    def run(state):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Injected one-time failure")
        return original(state)

    agent.run = run
    return calls
