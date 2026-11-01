# Roadmap: QualBench

Where QualBench is going after v0.1.0. This is a plan, not a
promise: items land when they are built, tested, and reviewed, in
roughly this order.

## What v0.2 adds

- **More vertical packs:** dental, legal intake, and roofing
  scenario packs, each with adversarial cases, on the same format
  as the three shipped packs.
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
