# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-04 (QualBench Benchmark v1.0)

The v0.2.0 release carries QualBench Benchmark v1.0.

### Added

- QualBench Benchmark v1.0: the 50-scenario suite frozen as a public
  benchmark, with BENCHMARK.md (method, scoring, tiers, safety gate,
  submission guide, governance) and LEADERBOARD.md generated from
  per-run results files in results/ by scripts/build_leaderboard.py.
- Difficulty tiers on every scenario (core, edge, safety) and a
  safety gate in reporting: an agent failing any safety scenario
  cannot rank on the leaderboard.
- Headline metrics in the results JSON: outcome pass rate, per-tier
  totals, safety gate result, booking accuracy, handoff correctness,
  and field capture completeness, all computed deterministically
  from the run's assertions and captured fields.
- Two new scenario packs, dental and agencies, and five new
  scenarios in each of the original three packs: 50 scenarios in
  total across five packs. The reference agent passes 50/50.
- examples/naive-agent: a deliberately careless agent, honestly
  labelled, that books without checking, captures almost nothing,
  never hands off, and agrees to discounts. It scores 0/50 on
  Benchmark v1.0 and is gate-blocked on safety; it is the
  benchmark's published risk baseline.
- scripts/build_results.py, which converts a CLI run into the
  benchmark results format, and an anatomy visual
  (assets/benchmark-anatomy.svg) embedded in the README and
  BENCHMARK.md.

## [0.1.0] - 2026-10-31

### Added

- YAML scenario format: scripted multi-turn user messages, seeded mock
  state, and an expected-outcome block (`docs/scenario-format.md`).
- Runner that drives any agent through two adapters: an OpenAI-compatible
  chat endpoint (function calling) and a plain HTTP webhook protocol.
  In-process Python agents are also supported for tests and examples.
- Built-in mocks: a fake calendar with seeded business hours and busy
  blocks, and a fake CRM that records every write.
- Six deterministic assertion types: final stage equals, score within
  band, booking made or not made with a valid slot, required fields
  captured, prohibited content absent, and handoff triggered or not
  triggered. No LLM-judge metrics.
- Three vertical scenario packs with five scenarios each: real-estate,
  med-spa, home-services. Every pack includes adversarial variants
  (after-hours, price pressure, out-of-area, handoff cases).
- Reference qualification agent (`examples/reference-agent/`) implementing
  a documented scoring model; all 15 shipped scenarios pass against it.
- Markdown report, machine-readable results JSON, and a CI baseline mode
  with a dedicated regression exit code (`docs/ci.md`).
