# Using QualBench in CI

The point of a regression bench is that it runs on every change. Two modes
matter.

## Gate mode (no baseline)

```bash
qualbench run --all --agent webhook --agent-url "$AGENT_URL" --report report.md
```

Exit code `1` if any scenario fails, `0` when all pass. The Markdown report
is written either way, with the failing assertions and the full transcript
for each failure, ready to attach to a pull request.

## Baseline mode (regression exit code)

Save a known-good run once:

```bash
qualbench run --all --agent reference --save-baseline baseline.json
```

Then compare future runs against it:

```bash
qualbench run --all --agent webhook --agent-url "$AGENT_URL" --baseline baseline.json
```

Exit code `2` when anything **regressed**: a scenario that passed in the
baseline and fails now, or a single assertion that flipped from pass to
fail. Scenarios that failed in the baseline and still fail are reported but
do not change the exit code, so a team can adopt QualBench against an
imperfect agent and still catch new breakage from day one. New scenarios
are never regressions.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All scenarios passed, or (baseline mode) no regressions |
| 1 | One or more scenarios failed (gate mode) |
| 2 | Regressions detected against the baseline |

## Tips

- Run the bundled reference agent in CI as a smoke test of the bench
  itself: `qualbench run --all --agent reference` must always be green.
  If it is not, the bench broke, not your agent.
- Keep `baseline.json` in version control and update it in the same pull
  request that intentionally changes agent behaviour.
- Machine-readable results for dashboards: add `--out results.json`.
