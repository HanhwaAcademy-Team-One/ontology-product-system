import json
import subprocess
import sys
from pathlib import Path

from ontoproduct.graph.workflow import build_workflow


def test_cli_demo_exercises_interrupts_and_registration():
    result = subprocess.run([sys.executable, "-m", "ontoproduct.cli"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("INTERRUPT ") == 2
    assert '"case_status": "REGISTERED"' in result.stdout
    assert "agent_started: validation running" in result.stdout


def test_cli_invalid_json_keeps_checkpoint_then_edits_and_approves():
    commands = [
        "invalid json",
        json.dumps({"action": "EDIT", "edits": {"attributes.rated_speed": {"value": 3000, "unit": "rpm"}}}),
        json.dumps({"action": "APPROVE"}),
    ]
    result = subprocess.run([sys.executable, "-m", "ontoproduct.cli", "--interactive"],
                            input="\n".join(commands)+"\n", capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "Invalid JSON" in result.stdout
    assert '"case_status": "REGISTERED"' in result.stdout
    assert result.stdout.count("agent_started: parser") == 1
    assert result.stdout.count("agent_started: extraction") == 2


def test_mermaid_document_matches_actual_compiled_graph():
    actual = build_workflow().get_graph().draw_mermaid()
    assert Path("docs/workflow.mmd").read_text(encoding="utf-8") == actual


def test_cli_generates_diagram(tmp_path):
    target = tmp_path / "workflow.mmd"
    result = subprocess.run([sys.executable, "-m", "ontoproduct.cli", "--diagram", str(target)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == build_workflow().get_graph().draw_mermaid()
