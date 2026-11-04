from types import SimpleNamespace

from qualbench.assertions import AssertionResult
from qualbench.report import render_markdown, results_to_dict


def _row(scenario_id, tier, ok):
    scenario = SimpleNamespace(scenario_id=scenario_id, tier=tier)
    result = SimpleNamespace(
        scenario=scenario, stage="BOOKED", score=90.0, error=None, transcript=[]
    )
    checks = [AssertionResult(kind="stage", passed=ok, message="")]
    return result, checks, ok


def _rows(*specs):
    rows = [_row(*s) for s in specs]
    return rows


def test_report_shows_tier_summary_and_safety_gate_pass():
    rows = _rows(
        ("p/core-1", "core", True),
        ("p/edge-1", "edge", False),
        ("p/safe-1", "safety", True),
    )
    md = render_markdown(rows, 2, 3)
    assert "- core: 1/1 passed" in md
    assert "- edge: 0/1 passed" in md
    assert "**Safety gate: PASSED**" in md


def test_report_safety_gate_fails_when_a_safety_scenario_fails():
    rows = _rows(
        ("p/core-1", "core", True),
        ("p/safe-1", "safety", False),
    )
    md = render_markdown(rows, 1, 2)
    assert "**Safety gate: FAILED**" in md


def test_results_dict_carries_tier():
    result, checks, ok = _row("p/safe-1", "safety", True)
    data = results_to_dict([(result, checks, ok)])
    assert data["scenarios"]["p/safe-1"]["tier"] == "safety"


def _metric_row(scenario_id, tier, ok, checks, fields=None, required=None):
    scenario = SimpleNamespace(
        scenario_id=scenario_id,
        tier=tier,
        expected={"fields_captured": required or []},
    )
    result = SimpleNamespace(
        scenario=scenario,
        stage="BOOKED",
        score=90.0,
        error=None,
        transcript=[],
        fields=fields or {},
    )
    return result, checks, ok


def test_run_metrics_computes_headline_numbers():
    from qualbench.report import run_metrics

    rows = [
        _metric_row(
            "p/booked", "core", True,
            [
                AssertionResult("booking_made", True, ""),
                AssertionResult("booking_valid_slot", True, ""),
                AssertionResult("handoff", True, ""),
                AssertionResult("fields_captured", True, ""),
            ],
            fields={"name": "A", "email": "a@example.com"},
            required=["name", "email"],
        ),
        _metric_row(
            "p/unsafe", "safety", False,
            [
                AssertionResult("booking_made", True, ""),
                AssertionResult("handoff", False, ""),
                AssertionResult("fields_captured", False, ""),
            ],
            fields={"name": "B"},
            required=["name", "phone"],
        ),
    ]
    metrics = run_metrics(rows)
    assert metrics["scenarios_passed"] == 1
    assert metrics["outcome_pass_rate"] == 0.5
    assert metrics["tiers"]["core"] == {"passed": 1, "total": 1}
    assert metrics["tiers"]["safety"] == {"passed": 0, "total": 1}
    assert metrics["safety_gate_passed"] is False
    assert metrics["booking_accuracy"] == 1.0
    assert metrics["handoff_correctness"] == 0.5
    assert metrics["fields_required_count"] == 4
    assert metrics["fields_captured_count"] == 3
    assert metrics["field_capture_completeness"] == 0.75


def test_results_dict_carries_metrics_and_field_detail():
    result, checks, ok = _metric_row(
        "p/core-1", "core", True,
        [AssertionResult("fields_captured", True, "")],
        fields={"name": "A"},
        required=["name"],
    )
    data = results_to_dict([(result, checks, ok)])
    row = data["scenarios"]["p/core-1"]
    assert row["fields_required"] == ["name"]
    assert row["captured_fields"] == ["name"]
    assert data["metrics"]["scenarios_total"] == 1
    assert data["metrics"]["field_capture_completeness"] == 1.0
