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


def results_to_dict(rows) -> dict:
    data: dict = {"scenarios": {}}
    for result, checks, ok in rows:
        data["scenarios"][result.scenario.scenario_id] = {
            "passed": ok,
            "stage": result.stage,
            "score": result.score,
            "assertions": {c.kind: c.passed for c in checks},
            "failures": [c.message for c in checks if not c.passed],
        }
    return data


def render_markdown(rows, passed: int, total: int) -> str:
    lines = [
        "# QualBench Report",
        "",
        f"**{passed}/{total} scenarios passed.**",
        "",
        "| Scenario | Result | Stage | Score |",
        "|---|---|---|---|",
    ]
    for result, _checks, ok in rows:
        score = f"{result.score:g}" if result.score is not None else "n/a"
        lines.append(
            f"| {result.scenario.scenario_id} | {'PASS' if ok else 'FAIL'} "
            f"| {result.stage or 'n/a'} | {score} |"
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
