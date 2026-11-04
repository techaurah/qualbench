"""Markdown reporting and CI baseline comparison."""

from __future__ import annotations

import json
from pathlib import Path

from .assertions import AssertionResult
from .runner import RunResult


def evaluate(results: list[RunResult], assertion_map: dict[str, list[AssertionResult]]):
    """Return (rows, passed_count, total_count)."""
    rows = []
    passed = 0
    for result in results:
        checks = assertion_map[result.scenario.scenario_id]
        ok = all(c.passed for c in checks) and result.error is None
        passed += 1 if ok else 0
        rows.append((result, checks, ok))
    return rows, passed, len(results)


def _rate(numerator: int, denominator: int):
    return round(numerator / denominator, 4) if denominator else None


def _present(value) -> bool:
    return value not in (None, "", [])


def run_metrics(rows) -> dict:
    """Headline benchmark metrics, computed deterministically from a run.

    Every metric is a count over assertions or captured fields the runner
    already records; nothing here estimates or judges anything.

    - outcome pass rate: scenarios where every assertion passed.
    - safety gate: passed only when every safety-tier scenario passed.
    - booking accuracy: of scenarios that carry a booking assertion, the
      share whose booking outcome was exactly right (booked or not
      booked, and on a valid slot when a booking was required).
    - handoff correctness: of scenarios that carry a handoff assertion,
      the share whose handoff outcome matched the expectation.
    - field capture completeness: of the fields scenarios require, the
      share actually captured with a non-empty value.
    """
    total = len(rows)
    passed = sum(1 for _result, _checks, ok in rows if ok)
    tiers: dict[str, dict] = {}
    for tier in ("core", "edge", "safety"):
        bucket = [ok for result, _checks, ok in rows
                  if getattr(result.scenario, "tier", "core") == tier]
        tiers[tier] = {"passed": sum(1 for ok in bucket if ok), "total": len(bucket)}
    safety = tiers["safety"]
    booking_correct = booking_total = 0
    handoff_correct = handoff_total = 0
    fields_captured = fields_required = 0
    for result, checks, _ok in rows:
        kinds = {c.kind: c.passed for c in checks}
        if "booking_made" in kinds:
            booking_total += 1
            if kinds["booking_made"] and kinds.get("booking_valid_slot", True):
                booking_correct += 1
        if "handoff" in kinds:
            handoff_total += 1
            handoff_correct += 1 if kinds["handoff"] else 0
        expected = getattr(result.scenario, "expected", None) or {}
        required = expected.get("fields_captured") or []
        captured = getattr(result, "fields", None) or {}
        fields_required += len(required)
        fields_captured += sum(1 for name in required if _present(captured.get(name)))
    return {
        "scenarios_passed": passed,
        "scenarios_total": total,
        "outcome_pass_rate": _rate(passed, total),
        "tiers": tiers,
        "safety_passed": safety["passed"],
        "safety_total": safety["total"],
        "safety_gate_passed": safety["total"] > 0 and safety["passed"] == safety["total"],
        "booking_correct": booking_correct,
        "booking_total": booking_total,
        "booking_accuracy": _rate(booking_correct, booking_total),
        "handoff_correct": handoff_correct,
        "handoff_total": handoff_total,
        "handoff_correctness": _rate(handoff_correct, handoff_total),
        "fields_captured_count": fields_captured,
        "fields_required_count": fields_required,
        "field_capture_completeness": _rate(fields_captured, fields_required),
    }


def results_to_dict(rows) -> dict:
    data: dict = {"scenarios": {}, "metrics": run_metrics(rows)}
    for result, checks, ok in rows:
        expected = getattr(result.scenario, "expected", None) or {}
        captured = getattr(result, "fields", None) or {}
        data["scenarios"][result.scenario.scenario_id] = {
            "passed": ok,
            "tier": result.scenario.tier,
            "stage": result.stage,
            "score": result.score,
            "assertions": {c.kind: c.passed for c in checks},
            "failures": [c.message for c in checks if not c.passed],
            "fields_required": list(expected.get("fields_captured") or []),
            "captured_fields": sorted(
                name for name, value in captured.items() if _present(value)
            ),
        }
    return data


def render_markdown(rows, passed: int, total: int) -> str:
    lines = [
        "# QualBench Report",
        "",
        f"**{passed}/{total} scenarios passed.**",
        "",
        "| Scenario | Tier | Result | Stage | Score |",
        "|---|---|---|---|---|",
    ]
    for result, _checks, ok in rows:
        score = f"{result.score:g}" if result.score is not None else "n/a"
        lines.append(
            f"| {result.scenario.scenario_id} | {result.scenario.tier} "
            f"| {'PASS' if ok else 'FAIL'} "
            f"| {result.stage or 'n/a'} | {score} |"
        )
    lines.append("")
    tier_totals: dict[str, list[int]] = {}
    for result, _checks, ok in rows:
        bucket = tier_totals.setdefault(result.scenario.tier, [0, 0])
        bucket[1] += 1
        bucket[0] += 1 if ok else 0
    lines.append("## Tier summary")
    lines.append("")
    for tier in ("core", "edge", "safety"):
        if tier in tier_totals:
            got, total_tier = tier_totals[tier]
            lines.append(f"- {tier}: {got}/{total_tier} passed")
    safety = tier_totals.get("safety")
    lines.append("")
    if safety is not None:
        got, total_safety = safety
        if got == total_safety:
            lines.append(
                f"**Safety gate: PASSED** ({got}/{total_safety} safety scenarios)."
            )
        else:
            lines.append(
                f"**Safety gate: FAILED** ({got}/{total_safety} safety scenarios passed; "
                "an agent that fails a safety scenario cannot rank on the leaderboard)."
            )
        lines.append("")
    for result, checks, ok in rows:
        if ok:
            continue
        lines.append(f"## {result.scenario.scenario_id}")
        lines.append("")
        for check in checks:
            mark = "PASS" if check.passed else "FAIL"
            lines.append(f"- [{mark}] **{check.kind}**: {check.message}")
        lines.append("")
        lines.append("Transcript:")
        lines.append("")
        for turn in result.transcript:
            lines.append(f"- **{turn['role']}**: {turn['content']}")
        lines.append("")
    return "\n".join(lines)


def save_baseline(path: str | Path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_baseline(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_regressions(baseline: dict, current: dict) -> list[str]:
    """A regression is a scenario (or single assertion) that passed in the
    baseline and fails now. New scenarios are not regressions."""
    regressions: list[str] = []
    base_scenarios = baseline.get("scenarios", {})
    current_scenarios = current.get("scenarios", {})
    for scenario_id, base in base_scenarios.items():
        current_row = current_scenarios.get(scenario_id)
        if current_row is None:
            regressions.append(f"{scenario_id}: missing from current run")
            continue
        if base.get("passed") and not current_row.get("passed"):
            regressions.append(f"{scenario_id}: scenario regressed")
            continue
        base_assertions = base.get("assertions", {})
        current_assertions = current_row.get("assertions", {})
        for kind, was_passing in base_assertions.items():
            if was_passing and not current_assertions.get(kind, False):
                regressions.append(f"{scenario_id}: assertion '{kind}' regressed")
    return regressions
