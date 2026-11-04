#!/usr/bin/env python3
"""Convert a QualBench CLI results file into a benchmark results file.

Usage:

    qualbench run --all --agent file --agent-file examples/naive-agent/agent.py \
        --out /tmp/naive-cli.json
    python scripts/build_results.py --input /tmp/naive-cli.json \
        --agent naive-agent --version 1.0.0 --date 2026-11-04 \
        --output results/naive-agent.json

The benchmark format is specified in BENCHMARK.md: one JSON per run with
agent metadata, the frozen suite version, per-scenario outcomes, and the
headline totals computed by the runner. Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SUITE_VERSION = "QualBench Benchmark v1.0"


def build_benchmark_result(cli_data: dict, agent: str, version: str, date: str,
                           suite_version: str = SUITE_VERSION) -> dict:
    metrics = cli_data.get("metrics") or {}
    scenarios = []
    for scenario_id in sorted(cli_data.get("scenarios", {})):
        row = cli_data["scenarios"][scenario_id]
        pack, _, name = scenario_id.partition("/")
        scenarios.append({
            "id": scenario_id,
            "pack": pack,
            "scenario": name,
            "tier": row.get("tier", "core"),
            "passed": bool(row.get("passed")),
            "assertions": row.get("assertions", {}),
        })
    totals = {
        "passed": metrics.get("scenarios_passed"),
        "total": metrics.get("scenarios_total"),
        "outcome_pass_rate": metrics.get("outcome_pass_rate"),
        "tiers": metrics.get("tiers", {}),
        "safety_passed": metrics.get("safety_passed"),
        "safety_total": metrics.get("safety_total"),
        "safety_gate_passed": metrics.get("safety_gate_passed"),
        "booking_accuracy": metrics.get("booking_accuracy"),
        "handoff_correctness": metrics.get("handoff_correctness"),
        "field_capture_completeness": metrics.get("field_capture_completeness"),
    }
    return {
        "agent": agent,
        "agent_version": version,
        "date": date,
        "suite_version": suite_version,
        "scenarios": scenarios,
        "totals": totals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CLI --out JSON file")
    parser.add_argument("--agent", required=True, help="Agent name for the board")
    parser.add_argument("--version", required=True, help="Agent version (submitter declared)")
    parser.add_argument("--date", required=True, help="Run date, YYYY-MM-DD")
    parser.add_argument("--suite-version", default=SUITE_VERSION)
    parser.add_argument("--output", required=True, help="Benchmark results JSON to write")
    args = parser.parse_args()
    cli_data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = build_benchmark_result(
        cli_data, args.agent, args.version, args.date, args.suite_version
    )
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    totals = result["totals"]
    print(f"{args.agent}: {totals['passed']}/{totals['total']} scenarios passed, "
          f"safety {totals['safety_passed']}/{totals['safety_total']}")


if __name__ == "__main__":
    main()
