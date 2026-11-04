# Roadmap: QualBench

Where QualBench is going after v0.2.0. This is a plan, not a
promise: items land when they are built, tested, and reviewed, in
roughly this order.

## What v0.2 adds (QualBench Benchmark v1.0)

- **The benchmark:** the scenario suite frozen as QualBench
  Benchmark v1.0, with a public leaderboard (LEADERBOARD.md),
  a published method (BENCHMARK.md), and a submission path where
  maintainers rerun every entry before a row merges.
- **50 scenarios, five packs:** dental and agencies packs join
  real estate, med spa, and home services, ten scenarios per pack.
- **Difficulty tiers and a safety gate:** every scenario is
  tiered core, edge, or safety; failing any safety scenario
  blocks ranking on the leaderboard.
- **Headline metrics:** outcome pass rate, safety pass count,
  booking accuracy, handoff correctness, and field capture
  completeness in every run's results JSON.
- **A risk baseline:** the deliberately careless naive agent
  (0/50 on v1.0) ships as an example, so the cost of a careless
  build is a published number, not an opinion.

## After v0.2

- **Community leaderboard entries:** the growth path for the
  board, run through the BENCHMARK.md submission and rerun
  process.
- **Benchmark v1.1 proposals:** new scenario packs (legal
  intake, roofing) and scenario additions ship as a new frozen
  version with a changelog, never as edits to v1.0.
- **Webhook protocol v2:** a versioned agent protocol with an
  explicit capability handshake, so agents declare which tool
  calls and session features they support before a run starts.
- A JSON diff view for reports, so a regression shows exactly
  which outcome changed between two runs.
- A pack validation linter for scenario authors.

## Deliberately out of scope

- **No LLM judge, ever.** Scoring stays deterministic; anything
  involving model-graded evaluation is a different tool's job.
- **It does not grade how replies read.** Writing quality,
  tone, and brand voice are not outcome assertions.
- **Not a load or performance testing tool.** QualBench runs
  scripted conversations one at a time and checks outcomes.

## How priorities are set

Priorities are set from GitHub issues and Discussions: open an
issue for concrete, actionable work (a new pack starts as an
issue naming the vertical), and start a discussion for ideas
and questions.
