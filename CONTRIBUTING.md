# Contributing to QualBench

Thank you for considering a contribution. The highest-leverage contribution
to QualBench is **data, not code**: a scenario pack is a folder of YAML
files, and a new vertical pack makes the bench useful to every team
building agents in that industry.

## Development setup (under 10 minutes)

```bash
git clone https://github.com/techaurah/qualbench
cd qualbench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
qualbench run --all --agent reference
```

You should see the full test suite pass and **15/15 scenarios passed**.
Python 3.11 or newer is required. The only hard runtime dependency is
PyYAML; please do not add new runtime dependencies without discussing it
in an issue first.

## Ways to contribute

- **A new scenario pack** for your vertical: copy an existing pack, change
  the conversations and expectations. Each pack needs 5 scenarios including
  at least one adversarial case (price pressure, out-of-area, or a handoff
  case). The reference agent does not need to pass your pack; your pack is
  a spec for agents in your industry. Use the "New scenario pack" issue
  template so we can agree the vertical and cases first.
- **A new scenario** in an existing pack: one YAML file.
- **A new agent adapter** (a new endpoint shape): implement the session
  protocol in `src/qualbench/agents/base.py` and add tests with a fake
  server, following `tests/test_runner.py`.
- **A new assertion type**: small and well-bounded, but discuss it first.
  The bar is high: assertions must be deterministic. No LLM judges.
- **Docs and examples**: error message improvements, edge-case tests, and
  doc fixes are excellent first contributions.

## Claiming an issue

Comment on the issue to claim it. Issues labelled `good first issue` are
scoped to one file or one example, have acceptance criteria written in the
issue, and need no credentials or paid services. If a claimed issue goes
quiet for two weeks, we may unassign it kindly so someone else can pick it
up.

## Pull request rules

- Link the issue in the PR description (`Closes #...`). PRs without a
  linked issue may be asked to open one first.
- Include test evidence: the command you ran and its result (for example
  the `pytest` summary or the `qualbench run` output), not just "tested
  locally".
- Keep PRs small and focused: one scenario pack, one adapter, one fix.
- CI must pass: install, ruff, and the test suite run on every PR.
- If your change alters scenario results, update `baseline.json` in the
  same PR and say so in the description.

## Code style

- Ruff is the linter and formatter of record (`ruff check`, line length
  100).
- Deterministic code paths in the runner and assertions: no randomness, no
  wall-clock dependence, no network in tests except localhost fake servers.

## Response rhythm

Issues are triaged weekly at minimum. Pull requests get a first human
response within a few days. If something is quiet for longer than that, a
polite ping on the thread is welcome.

## Code of conduct

Participation is covered by our [Code of Conduct](CODE_OF_CONDUCT.md).
