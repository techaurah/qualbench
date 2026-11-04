"""Tests for scripts/build_leaderboard.py: the safety gate, ordering,
and the worked-example labelling of the reference agent.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_leaderboard.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_leaderboard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(agent, passed, total, safety_passed, safety_total, gate):
    rate = passed / total if total else 0.0
    return {
        "agent": agent,
        "agent_version": "1.0.0",
        "date": "2026-11-04",
        "suite_version": "QualBench Benchmark v1.0",
        "scenarios": [],
        "totals": {
            "passed": passed,
            "total": total,
            "outcome_pass_rate": rate,
            "safety_passed": safety_passed,
            "safety_total": safety_total,
            "safety_gate_passed": gate,
            "booking_accuracy": 1.0,
            "handoff_correctness": 1.0,
            "field_capture_completeness": 1.0,
        },
    }


def test_gate_blocked_agent_cannot_outrank_a_gate_passing_agent():
    board = _module()
    strong_but_unsafe = _entry("risky-agent", 49, 50, 8, 9, False)
    weaker_but_safe = _entry("careful-agent", 20, 50, 9, 9, True)
    ordered = board.order_entries([strong_but_unsafe, weaker_but_safe])
    assert [e["agent"] for e in ordered] == ["careful-agent", "risky-agent"]


def test_ordering_within_gate_passers_uses_pass_rate():
    board = _module()
    low = _entry("low-agent", 10, 50, 9, 9, True)
    high = _entry("high-agent", 40, 50, 9, 9, True)
    ordered = board.order_entries([low, high])
    assert [e["agent"] for e in ordered] == ["high-agent", "low-agent"]


def test_render_marks_blocked_agents_and_labels_reference_as_worked_example():
    board = _module()
    entries = [
        _entry("reference-agent", 50, 50, 9, 9, True),
        _entry("naive-agent", 0, 50, 0, 9, False),
    ]
    md = board.render_leaderboard(entries)
    assert "reference-agent (worked example)" in md
    assert "| 1 | reference-agent (worked example)" in md
    assert "| Gate blocked | naive-agent" in md
    assert "BLOCKED" in md
    assert "BENCHMARK.md" in md


def test_load_results_reads_every_json_in_the_directory(tmp_path):
    board = _module()
    for name in ("a-agent", "b-agent"):
        (tmp_path / f"{name}.json").write_text(
            json.dumps(_entry(name, 1, 50, 9, 9, True)), encoding="utf-8"
        )
    entries = board.load_results(tmp_path)
    assert {e["agent"] for e in entries} == {"a-agent", "b-agent"}
