import json
from pathlib import Path

import pytest
from doubles import mock_registry
from real_llm_helpers import HonestLlm
from test_streamlit_app import MISSING_SPEED

from ontoproduct import cli
from ontoproduct.graph.workflow import build_workflow

FIXTURES = Path(__file__).parent / "fixtures" / "documents"


@pytest.fixture
def run_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ONTOPRODUCT_DATA_DIR", str(tmp_path / "data"))
    llm = HonestLlm()
    monkeypatch.setattr(
        cli, "create_llm_services", lambda settings: {"extraction": llm, "ontology": llm}
    )

    def run(*argv, stdin=None):
        if stdin is not None:
            answers = iter(stdin)
            monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
        cli.main([str(a) for a in argv])
        return capsys.readouterr().out

    return run


def test_cli_registers_complete_document(run_cli):
    out = run_cli(FIXTURES / "motor_spec.txt")
    assert out.count("INTERRUPT ") == 1
    assert 'RESUME {"action": "APPROVE"}' in out
    assert '"case_status": "REGISTERED"' in out
    assert '"product_name": "DM-600"' in out
    assert "agent_started: parser running" in out


def test_cli_leaves_case_suspended_when_human_repair_is_needed(run_cli, tmp_path):
    source = tmp_path / "dm500_spec.txt"
    source.write_bytes(MISSING_SPEED)
    out = run_cli(source)
    assert "Human repair is required" in out
    assert "REGISTERED" not in out


def test_cli_invalid_json_keeps_checkpoint_then_edits_and_approves(run_cli, tmp_path):
    source = tmp_path / "dm500_spec.txt"
    source.write_bytes(MISSING_SPEED)
    commands = [
        "invalid json",
        json.dumps(
            {
                "action": "EDIT",
                "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}},
            }
        ),
        json.dumps({"action": "APPROVE"}),
    ]
    out = run_cli("--interactive", source, stdin=commands)
    assert "Invalid JSON" in out
    assert '"case_status": "REGISTERED"' in out
    assert out.count("agent_started: parser") == 1


def test_cli_requires_documents_or_diagram(run_cli):
    with pytest.raises(SystemExit):
        run_cli()


def test_mermaid_document_matches_actual_compiled_graph():
    actual = build_workflow(mock_registry()).get_graph().draw_mermaid()
    assert Path("docs/workflow.mmd").read_text(encoding="utf-8") == actual


def test_cli_generates_diagram(run_cli, tmp_path):
    target = tmp_path / "workflow.mmd"
    run_cli("--diagram", target)
    assert (
        target.read_text(encoding="utf-8")
        == build_workflow(mock_registry()).get_graph().draw_mermaid()
    )
