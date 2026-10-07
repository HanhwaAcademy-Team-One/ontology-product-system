import json
from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4
from langgraph.config import get_stream_writer
from pydantic import TypeAdapter
from ontoproduct.agents.base import AgentContractError
from ontoproduct.agents.registry import validate_contract
from ontoproduct.schemas.agent import AgentExecution, CustomStreamEvent
from ontoproduct.schemas.error import WorkflowErrorEvent, unresolved_errors


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def execute_agent(registry, name, state, *, writer=None):
    agent = registry.get(name)
    if writer is None:
        try:
            writer = get_stream_writer()
        except RuntimeError:
            writer = lambda event: None
    attempt = 1 + sum(
        log["agent"] == name and log["status"] != "running"
        for log in state.get("agent_logs", [])
    )
    execution_id = str(uuid4())
    running = AgentExecution(
        execution_id=execution_id,
        agent=name,
        status="running",
        message="Agent started",
        attempt=attempt,
        execution_time=None,
        timestamp=timestamp(),
    ).model_dump(mode="json")
    writer(CustomStreamEvent(**running, event="agent_started").model_dump(mode="json"))
    started = perf_counter()
    errors, result = [], {}
    try:
        validate_contract(agent)
        missing = agent.required_reads - state.keys()
        if missing:
            raise AgentContractError(f"Missing required reads: {sorted(missing)}")
        inputs = {
            key: deepcopy(state[key])
            for key in agent.required_reads | agent.optional_reads
            if key in state
        }
        json.dumps(inputs, allow_nan=False)
        before = deepcopy(inputs)
        output = agent.run(inputs)
        if inputs != before:
            raise AgentContractError("Agent mutated its input state")
        if not isinstance(output, dict) or output.keys() != agent.writes.keys():
            raise AgentContractError(f"Expected output keys {sorted(agent.writes)}")
        json.dumps(output, allow_nan=False)
        for key, schema in agent.writes.items():
            adapter = TypeAdapter(schema)
            validated = adapter.validate_python(output[key])
            result[key] = adapter.dump_python(validated, mode="json")
        json.dumps(result, allow_nan=False)
        for error in unresolved_errors(state.get("error_events", [])):
            if error["stage"] == name:
                errors.append(
                    WorkflowErrorEvent(
                        **{
                            **error,
                            "status": "RESOLVED",
                            "message": "Agent retry succeeded.",
                            "timestamp": timestamp(),
                        }
                    ).model_dump(mode="json")
                )
        status, message = "success", "Agent completed"
    except Exception as exc:
        result = {}
        status, message = "error", str(exc)
        errors.append(
            WorkflowErrorEvent(
                error_id=f"ERR-{uuid4()}",
                stage=name,
                attempt=attempt,
                status="OPEN",
                message=message,
                recoverable=True,
                exception_type=type(exc).__name__,
                timestamp=timestamp(),
            ).model_dump(mode="json")
        )
    finished = AgentExecution(
        execution_id=execution_id,
        agent=name,
        status=status,
        message=message,
        attempt=attempt,
        execution_time=perf_counter() - started,
        timestamp=timestamp(),
    ).model_dump(mode="json")
    writer(
        CustomStreamEvent(**finished, event="agent_finished").model_dump(mode="json")
    )
    return {**result, "agent_logs": [running, finished], "error_events": errors}
