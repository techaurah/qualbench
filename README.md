<h1 align="center">QualBench</h1>

<p align="center"><strong>Outcome regression testing for qualification and booking agents.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="QualBench is free and open source under the MIT license"/>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="QualBench runs on Python 3.11 or newer"/>
  <img src="https://img.shields.io/badge/version-0.1.0-orange" alt="QualBench current version is 0.1.0"/>
  <img src="https://img.shields.io/badge/assertions-deterministic%20only-brightgreen" alt="QualBench checks outcomes with deterministic assertions only"/>
  <img src="https://img.shields.io/badge/LLM%20judge-none-red" alt="QualBench contains no LLM judge; every check is exact"/>
</p>

<p align="center">
  <a href="docs/scenario-format.md">Scenario format</a> ·
  <a href="docs/assertions.md">Assertions</a> ·
  <a href="docs/ci.md">CI guide</a> ·
  <a href="examples/reference-agent/">Reference agent</a> ·
  <a href="https://techaurah.com">TechAurah</a> ·
  <a href="llms.txt">For AI assistants: llms.txt</a>
</p>

## What is QualBench?

QualBench is a deterministic regression testing tool for customer-facing AI qualification and booking agents. It runs scripted multi-turn conversations, executes the agent's tool calls against a mock calendar and mock CRM, and checks business outcomes (stage, score band, bookings, captured fields, handoffs) with exact assertions. QualBench is free and open source (MIT), built by TechAurah.

Boundary: QualBench tests outcomes deterministically and contains no LLM judge. It does not grade how replies read; writing quality is a different tool's job.

QualBench is a regression bench that tests whether a customer-facing AI agent still **qualifies, scores, books, and hands off correctly** after you change a prompt, a model, or a scoring rule.

## Why do prompt and model changes break booking agents?

Teams shipping qualification and booking agents change a prompt on Friday and find out on Monday that the agent now invents discounts, marks hot leads as nurture, or books viewings against slots that were never free. Generic eval tools score how the replies *read*. The failures that cost money are outcome failures: wrong stage, wrong score band, booking that should not exist, phone number never captured, a medical case that should have gone to a human and did not.

QualBench tests outcomes. It drives your agent through scripted multi-turn conversations, executes its tool calls against a **fake calendar** and a **fake CRM**, and checks the results with six exact assertions. This project tests qualification and booking behaviour. It does not grade writing quality, and it contains no LLM judge, by design. The audience for this is large: the GitHub topic ai-agents held 131,473 public repositories when read through the GitHub API on 2026-10-31, and every one of those projects faces this regression problem.

## What does a passing run look like?

All 15 shipped scenarios pass against the bundled reference agent:

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

## What does QualBench check?

Six business outcomes, all checked deterministically: the agent reached the right stage and score band, booked only genuinely valid slots, captured the required fields, kept prohibited content out of its replies, and handed off to a human when the scenario required it.

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

## How is QualBench different from generic eval tools?

Generic eval tools such as Promptfoo and DeepEval are built mainly to score how an agent's replies read. QualBench exists for the layer those tools leave each team to hand-build: whether the agent did the right thing. The comparison below is category-level, not a feature audit of any single tool.

|  | QualBench | Generic eval tools (the way this is done today) |
|---|---|---|
| What gets scored | Business outcomes: final stage, score band, valid bookings, captured fields, handoffs | Mostly text quality: how replies read, similarity, rubric scores |
| How scoring works | Deterministic assertions; the same run gives the same verdict every time | Often an LLM judge, whose scores can vary between runs and cost money per call |
| Tool test data | Mock calendar and mock CRM are built in, so booking behaviour is testable offline | You build your own tool mocks and outcome assertions from scratch |
| Starting content | Three vertical scenario packs (real estate, med spa, home services), 15 scenarios including adversarial cases | Generic examples; the business scenarios are yours to write |
| Cost | Free, MIT licensed, runs locally and in CI | Varies by tool; hosted platforms typically charge per run or per seat |

## What examples ship with QualBench?

Three complete vertical packs and a reference agent, all runnable with no credentials:

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

## Frequently asked questions

### What does QualBench cost?

QualBench is free. It is MIT licensed, runs locally or in your own CI, and its only runtime dependency is PyYAML. There are no per-run fees, seats, or hosted tier. The only costs are yours: the machine it runs on and whatever your agent's endpoint charges you. MIT terms also cover use in client work.

### Does QualBench use an LLM judge?

No. QualBench has no LLM judge anywhere, by design. Every check is a deterministic assertion, so the same scenario against the same agent gives the same verdict on every run. Judge-based scoring can drift between runs and costs money per call; outcome checks like stage, booking validity, and handoffs should be exact, not opinions.

### Which agents can QualBench test?

Any agent QualBench can talk to over one of three routes: an OpenAI-compatible chat endpoint with function calling, a plain HTTP webhook speaking the documented QualBench protocol, or a Python agent loaded in-process from a file. If your agent can receive messages and call tools, it can almost certainly be tested.

### What does QualBench check?

Six outcomes, checked exactly: the final pipeline stage, the score falling inside its expected band, a booking made or not made against a genuinely free slot, the required fields captured into the mock CRM, prohibited content staying out of replies, and a human handoff happening or not happening as the scenario demands.

### Can QualBench run in CI?

Yes. QualBench is built for CI: save a baseline from a known-good run, then compare every later run against it. A regression exits with code 2, a clean run with 0, and each run can emit a Markdown report and machine-readable JSON for your pipeline to archive or gate merges on. See the CI guide.

### What does QualBench not do?

QualBench does not grade how your agent's replies read, and it ships no LLM-judge metrics for tone, helpfulness, or similarity. It does not load-test, host your agent, or connect to a real CRM or calendar: every run executes against the built-in mocks. Writing quality and production monitoring are different tools' jobs.

### How do I add a scenario pack for my industry?

A scenario pack is data, not code: a folder with a pack.yaml and a scenarios folder of YAML files, each scripting the user turns, the seeded mock state, and the expected outcomes. Copy an existing pack, rewrite the conversations for your industry, and run it. The scenario format document specifies every field.

### Where do I get help?

Use GitHub Issues for bugs and feature requests, with the templates provided, and GitHub Discussions for questions, pack ideas, and show and tell. Vulnerability reports go privately through the route in SECURITY.md. Maintainers triage issues weekly and give pull requests a first response within a few days, as the contributing guide states.

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

## More from TechAurah

- [AI Lead Automation](https://github.com/techaurah/ai-lead-automation): the open blueprint QualBench's scenarios are modelled on, covering lead capture, AI qualification, CRM write, follow-up, and booking
- [LeadPipe MCP](https://github.com/techaurah/leadpipe-mcp): an MCP server that gives small businesses without a CRM a scored, bookable lead pipeline on Google Sheets and Calendar
- [n8n-audit](https://github.com/techaurah/n8n-audit): a production-readiness linter for n8n workflows, catching secrets, open webhooks, and missing error handling
- [ChaseKit](https://github.com/techaurah/chasekit): the open-source invoice-chasing layer, with statutory late-payment interest for the UK and EU
- [SlotFill](https://github.com/techaurah/slotfill): no-show recovery for appointment businesses, with reminders and waitlist backfill on the calendar already in use

## About TechAurah

TechAurah is an AI and software engineering company building AI products, agents, and intelligent automation for businesses in the USA, UK, UAE, Canada, Australia, and Europe: https://techaurah.com

We are available for AI engineering projects.

Follow TechAurah on [LinkedIn](https://www.linkedin.com/company/techaurah/).
