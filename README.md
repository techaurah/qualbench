<h1 align="center">QualBench</h1>

<p align="center"><strong>Outcome regression testing for qualification and booking agents.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license"/>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11 or newer"/>
  <img src="https://img.shields.io/badge/version-0.1.0-orange" alt="Version 0.1.0"/>
  <img src="https://img.shields.io/badge/assertions-deterministic%20only-brightgreen" alt="Deterministic assertions only"/>
  <img src="https://img.shields.io/badge/LLM%20judge-none-red" alt="No LLM judge"/>
</p>

<p align="center">
  <a href="docs/scenario-format.md">Scenario format</a> ·
  <a href="docs/assertions.md">Assertions</a> ·
  <a href="docs/ci.md">CI guide</a> ·
  <a href="examples/reference-agent/">Reference agent</a> ·
  <a href="https://techaurah.com">TechAurah</a>
</p>

QualBench is a regression bench that tests whether a customer-facing AI agent still **qualifies, scores, books, and hands off correctly** after you change a prompt, a model, or a scoring rule.

## The problem

Teams shipping qualification and booking agents change a prompt on Friday and find out on Monday that the agent now invents discounts, marks hot leads as nurture, or books viewings against slots that were never free. Generic eval tools score how the replies *read*. The failures that cost money are outcome failures: wrong stage, wrong score band, booking that should not exist, phone number never captured, a medical case that should have gone to a human and did not.

QualBench tests outcomes. It drives your agent through scripted multi-turn conversations, executes its tool calls against a **fake calendar** and a **fake CRM**, and checks the results with six exact assertions. This project tests qualification and booking behaviour. It does not grade writing quality, and it contains no LLM judge, by design.

## Demo

The three shipped packs against the bundled reference agent:

```text
$ qualbench run --all --agent reference

PASS  home-services/emergency-repair
PASS  home-services/gas-safety-handoff
PASS  home-services/out-of-area
PASS  home-services/price-pressure
PASS  home-services/standard-quote
PASS  med-spa/after-hours-booking
PASS  med-spa/contraindication-handoff
PASS  med-spa/package-buyer
PASS  med-spa/price-shopping
PASS  med-spa/standard-consultation
PASS  real-estate/after-hours-inquiry
PASS  real-estate/out-of-area
PASS  real-estate/price-pressure
PASS  real-estate/standard-inquiry
PASS  real-estate/urgent-viewing

15/15 scenarios passed
```

## Quickstart

Prerequisites: Python 3.11 or newer. No accounts, no API keys, no paid services.

```bash
git clone https://github.com/techaurah/qualbench
cd qualbench
pip install -e .
qualbench run --pack packs/real-estate --agent reference
```

Expected: `5/5 scenarios passed` for the real estate pack.

Now point it at your own agent:

```bash
# Any agent behind an OpenAI-compatible chat endpoint
qualbench run --all --agent openai --agent-url http://localhost:11434/v1 --model my-agent

# Any agent that accepts the QualBench webhook protocol (docs/scenario-format.md)
qualbench run --all --agent webhook --agent-url http://localhost:8080/chat
```

## What it does

- [x] YAML scenarios: scripted user turns, seeded mock state, expected outcomes ([format](docs/scenario-format.md))
- [x] Two agent adapters: OpenAI-compatible chat endpoints and a plain HTTP webhook protocol, plus in-process Python agents
- [x] A fake calendar with seeded business hours and busy blocks, so booking behaviour is testable offline
- [x] A fake CRM that records every write, so captured fields are verifiable
- [x] Six deterministic assertions: stage, score band, booking and slot validity, captured fields, prohibited content, handoff ([details](docs/assertions.md))
- [x] Three vertical packs, 15 scenarios: real estate, med spa, home services, each with adversarial cases
- [x] A reference agent that passes every pack, so you can tell a bench failure from an agent failure
- [x] Markdown reports with transcripts for failures, results JSON, and a CI baseline mode with a regression exit code ([CI guide](docs/ci.md))

## Key options

| Option | What it does |
|---|---|
| `--pack DIR` | Run one pack (repeatable) |
| `--all` | Run every pack under `--packs-dir` (default `packs/`) |
| `--agent reference` | Test against the bundled reference agent |
| `--agent webhook --agent-url URL` | Test an agent speaking the webhook protocol |
| `--agent openai --agent-url URL --model NAME` | Test an OpenAI-compatible endpoint |
| `--agent file --agent-file PATH` | Test a Python agent file exposing `create_session()` |
| `--report PATH` | Write a Markdown report |
| `--out PATH` | Write machine-readable results JSON |
| `--baseline PATH` / `--save-baseline PATH` | CI regression comparison (exit code 2 on regression) |
| `QUALBENCH_API_KEY` / `OPENAI_API_KEY` | API key for the OpenAI-compatible adapter |

## Examples

| Example | What it demonstrates | Time | Credentials |
|---|---|---|---|
| `packs/real-estate` | Viewing qualification and booking, incl. out-of-area and price pressure | 1 min | None |
| `packs/med-spa` | Consultation booking, gift-card warm lead, medical handoff | 1 min | None |
| `packs/home-services` | Emergency booking, quote visits, gas safety handoff | 1 min | None |
| `examples/reference-agent` | A complete agent implementing the protocol and scoring model | 5 min to read | None |

## Roadmap

**Now (v0.1):** deterministic outcome assertions, mock calendar and CRM, two endpoint adapters, three vertical packs, CI baseline mode.

**Next:** more vertical packs (dental, legal intake, roofing) as contributors add them; a JSON diff view for reports; a pack validation linter for scenario authors.

**Later:** additional agent transports if the ecosystem settles on them; scheduled-pack runs against staging agents. Anything involving model-graded scoring stays out: that is a different tool's job.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), find a `good first issue`, and open a PR that links its issue and passes CI. The best first contribution is a scenario pack for your own vertical: it is YAML, not code. Maintainers triage issues weekly and give PRs a first response within a few days.

## Community and support

| Channel | Best for |
|---|---|
| GitHub Issues | Bugs and feature requests (use the templates) |
| GitHub Discussions | Questions, pack ideas, show and tell |
| [SECURITY.md](SECURITY.md) | Vulnerability reports, privately |

## License

MIT. See [LICENSE](LICENSE).

## About TechAurah

TechAurah is an AI and software engineering company building AI products, agents, and intelligent automation for businesses in the USA, UK, UAE, Canada, Australia, and Europe: https://techaurah.com

We are available for AI engineering projects.
