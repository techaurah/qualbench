"""QualBench command line.

Examples:

    qualbench run --pack packs/real-estate --agent reference
    qualbench run --all --agent webhook --agent-url http://localhost:8080/chat
    qualbench run --all --agent openai --agent-url http://localhost:11434/v1 \
        --model my-agent --baseline baseline.json
    qualbench validate --pack packs/real-estate

Exit codes: 0 = all scenarios passed (or, with --baseline, no regressions),
1 = scenario failures, 2 = regressions against the baseline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .agents.http_agent import OpenAICompatAgent
from .agents.webhook_agent import WebhookAgent, load_agent_file
from .assertions import run_assertions
from .report import (
    evaluate,
    find_regressions,
    load_baseline,
    render_markdown,
    results_to_dict,
    save_baseline,
)
from .runner import run_scenario
from .scenario import ScenarioError, discover_packs, load_pack

REFERENCE_AGENT_REL = Path("examples") / "reference-agent" / "agent.py"


def _find_reference_agent() -> Path:
    candidates = [Path.cwd() / REFERENCE_AGENT_REL]
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / REFERENCE_AGENT_REL)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "Could not find the reference agent (examples/reference-agent/agent.py). "
        "Run from the repository root or pass --agent-file."
    )


def _session_factory(args):
    if args.agent == "reference":
        path = _find_reference_agent()
        return lambda: load_agent_file(path)
    if args.agent == "file":
        if not args.agent_file:
            raise SystemExit("--agent file requires --agent-file PATH")
        return lambda: load_agent_file(args.agent_file)
    if args.agent == "webhook":
        if not args.agent_url:
            raise SystemExit("--agent webhook requires --agent-url URL")
        return lambda: WebhookAgent(args.agent_url)
    if args.agent == "openai":
        if not args.agent_url:
            raise SystemExit("--agent openai requires --agent-url BASE_URL")
        api_key = args.api_key or os.environ.get("QUALBENCH_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
        return lambda: OpenAICompatAgent(args.agent_url, model=args.model, api_key=api_key)
    raise SystemExit(f"Unknown agent kind: {args.agent}")


def _collect_packs(args):
    packs = []
    if args.all:
        packs.extend(discover_packs(args.packs_dir))
    for pack_dir in args.pack or []:
        packs.append(load_pack(pack_dir))
    if not packs:
        raise SystemExit("Nothing to run: pass --pack DIR or --all")
    return packs


def cmd_validate(args) -> int:
    packs = _collect_packs(args)
    total = 0
    for pack in packs:
        total += len(pack.scenarios)
        print(f"pack {pack.name}: {len(pack.scenarios)} scenarios OK")
    print(f"{total} scenarios valid")
    return 0


def cmd_run(args) -> int:
    packs = _collect_packs(args)
    factory = _session_factory(args)
    results = []
    assertion_map = {}
    for pack in packs:
        for scenario in pack.scenarios:
            result = run_scenario(factory, scenario)
            checks = run_assertions(scenario, result)
            assertion_map[scenario.scenario_id] = checks
            results.append(result)
            ok = all(c.passed for c in checks)
            print(f"{'PASS' if ok else 'FAIL'}  {scenario.scenario_id}")
            for check in checks:
                if not check.passed:
                    print(f"      [{check.kind}] {check.message}")
    rows, passed, total = evaluate(results, assertion_map)
    print(f"\n{passed}/{total} scenarios passed")
    data = results_to_dict(rows)
    if args.report:
        Path(args.report).write_text(render_markdown(rows, passed, total), encoding="utf-8")
        print(f"Report written to {args.report}")
    if args.out:
        Path(args.out).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Results written to {args.out}")
    if args.save_baseline:
        save_baseline(args.save_baseline, data)
        print(f"Baseline saved to {args.save_baseline}")
    if args.baseline:
        baseline = load_baseline(args.baseline)
        regressions = find_regressions(baseline, data)
        if regressions:
            print("\nRegressions against baseline:")
            for item in regressions:
                print(f"  - {item}")
            return 2
        print("\nNo regressions against baseline")
        return 0
    return 0 if passed == total else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qualbench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_pack_args(p):
        p.add_argument("--pack", action="append", help="Pack directory (repeatable)")
        p.add_argument("--all", action="store_true", help="Run every pack in --packs-dir")
        p.add_argument("--packs-dir", default="packs", help="Directory holding all packs")

    run = sub.add_parser("run", help="Run scenarios against an agent")
    add_pack_args(run)
    run.add_argument(
        "--agent",
        choices=["reference", "file", "webhook", "openai"],
        default="reference",
        help="Agent kind: bundled reference, a Python file, a webhook URL, "
        "or an OpenAI-compatible endpoint",
    )
    run.add_argument("--agent-file", help="Path to a Python agent file (create_session)")
    run.add_argument("--agent-url", help="Webhook URL or OpenAI-compatible base URL")
    run.add_argument("--model", default="default", help="Model name for --agent openai")
    run.add_argument("--api-key", help="API key for --agent openai (or env var)")
    run.add_argument("--report", help="Write a Markdown report to this path")
    run.add_argument("--out", help="Write machine-readable results JSON to this path")
    run.add_argument("--baseline", help="Compare against this baseline JSON file")
    run.add_argument("--save-baseline", help="Save this run as a baseline JSON file")
    run.set_defaults(func=cmd_run)

    validate = sub.add_parser("validate", help="Check pack and scenario files parse")
    add_pack_args(validate)
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ScenarioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
