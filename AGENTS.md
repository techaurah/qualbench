# AGENTS.md

Guidance for AI coding agents (and humans skimming) working in this repo.

## What this project is

QualBench is a deterministic regression bench for qualification and booking
agents. YAML scenarios drive an agent through mock tools; six exact
assertion types check business outcomes. There is deliberately **no LLM
judge** anywhere in this codebase. Do not add one.

## Layout

- `src/qualbench/` package code: `cli.py` (entry point), `scenario.py`
  (pack loading), `runner.py` (drives the agent, executes tool calls),
  `assertions.py` (the six checks), `report.py` (Markdown + baselines),
  `mocks/` (fake calendar and CRM), `agents/` (endpoint adapters).
- `packs/` scenario packs (data only: `pack.yaml` + `scenarios/*.yaml`).
- `examples/reference-agent/` the dependency-free reference agent.
- `tests/` pytest suite. `docs/` format, assertions, and CI docs.

## Commands

- Test: `pytest`
- Lint: `ruff check src tests`
- Dogfood run: `qualbench run --all --agent reference` (must print 50/50)

## Conventions

- PyYAML is the only hard runtime dependency. HTTP uses the standard
  library on purpose. Do not add runtime dependencies casually.
- Runner and assertion code must stay deterministic: no randomness, no
  wall clock, no network.
- Scenario dates are fixed on purpose. Do not convert them to relative
  dates.
- Every behaviour change needs a test. Pack changes need a
  `qualbench run` result quoted in the PR.
- No em dashes in prose or docs.
