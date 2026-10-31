# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
