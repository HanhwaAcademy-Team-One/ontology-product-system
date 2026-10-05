import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from ontoproduct.agents.base import AgentContractError
from ontoproduct.agents.registry import CONTRACTS
from ontoproduct.graph.execution import execute_agent
from ontoproduct.schemas.product import ProductAttribute
from ontoproduct.schemas.review import ReviewResult


@pytest.mark.parametrize("name", list(CONTRACTS))
def test_metadata_and_required_only_reads(name, registry, paused_state):
    agent = registry.get(name)
    assert agent.name == name and agent.provider and agent.version and agent.is_mock
    assert agent.health_check() is True
    state = {key: deepcopy(paused_state.get(key)) for key in agent.required_reads}
    if name == "registration":
        state["human_review"] = {"action": "APPROVE"}
    result = execute_agent(registry, name, state)
    assert result["agent_logs"][-1]["status"] == "success"
    assert set(agent.writes) <= result.keys()
    assert not result["error_events"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("name", list(CONTRACTS))
def test_missing_required_read_is_error(name, registry):
    result = execute_agent(registry, name, {})
    assert result["agent_logs"][-1]["status"] == "error"
    assert result["error_events"][0]["exception_type"] == "AgentContractError"
    assert not set(registry.get(name).writes) & result.keys()


@pytest.mark.parametrize("output", [
    {}, {"parsed_documents": [], "normalized_product": {}},
    {"parsed_documents": [{"source_file": "x", "text": 42}]},
    {"parsed_documents": [object()]},
])
def test_invalid_output_is_atomic(output, registry):
    registry.get("parser").run = lambda state: output
    result = execute_agent(registry, "parser", {"source_documents": []})
    assert result["agent_logs"][-1]["status"] == "error"
    assert "parsed_documents" not in result


def test_mutation_is_detected_and_isolated(registry):
    state = {"source_documents": [{"name": "x"}]}
    before = deepcopy(state)

    def mutate(inputs):
        inputs["source_documents"].clear()
        return {"parsed_documents": []}
    registry.get("parser").run = mutate
    assert execute_agent(registry, "parser", state)["agent_logs"][-1]["status"] == "error"
    assert state == before


def test_undeclared_inputs_are_not_exposed(registry):
    def run(state):
        assert set(state) == {"source_documents"}
        return {"parsed_documents": []}
    registry.get("parser").run = run
    result = execute_agent(registry, "parser", {"source_documents": [], "human_review": {"action": "APPROVE"}})
    assert result["agent_logs"][-1]["status"] == "success"


@pytest.mark.parametrize("field,value", [("writes", {"normalized_product": dict}),
                                       ("required_reads", {"human_review"}), ("provider", "")])
def test_registry_rejects_contract_changes(registry, field, value):
    agent = deepcopy(registry.get("parser"))
    setattr(agent, field, value)
    with pytest.raises(AgentContractError):
        registry.register(agent, replace=True)


def test_duplicate_registration_and_replacement(registry):
    agent = registry.get("parser")
    with pytest.raises(AgentContractError):
        registry.register(agent)
    registry.register(agent, replace=True)
    registry.validate_complete()
    assert len(registry.metadata()) == 7


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {"nested": 1}])
def test_non_finite_or_structured_attribute_is_rejected(value):
    with pytest.raises(ValidationError):
        ProductAttribute(value=value)


def test_review_cannot_claim_ready_while_blocking_or_allow_needs_fix():
    for decision, can_register in [("NEEDS_FIX", True), ("REJECT", True), ("READY_FOR_HUMAN", False)]:
        with pytest.raises(ValidationError):
            ReviewResult(decision=decision, reason="x", can_register=can_register)


def test_required_null_is_error(registry):
    result = execute_agent(registry, "parser", {"source_documents": None})
    assert result["agent_logs"][-1]["status"] == "error"
