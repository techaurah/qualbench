# Reference qualification agent

A tiny deterministic agent that passes every QualBench scenario pack out of
the box. It uses no LLM and no dependencies beyond the Python standard
library. It exists for three reasons:

1. **Smoke test.** If the packs fail against this agent, the bench broke,
   not your agent.
2. **Protocol example.** It implements the QualBench webhook protocol
   (payloads, tool calls, outcome reporting) in one readable file.
3. **Starting point.** Copy it and replace the rule-based brain with your
   own agent behind the same interface.

## How it works

The agent extracts contact details with patterns, tracks conversation
signals (problem, fit, value, size, payment readiness, access, urgency,
activity) and scores the lead with the TechAurah qualification model:

| Component | Points |
|---|---|
| Problem | 20 |
| Fit | 20 |
| Value | 15 |
| Size | 10 |
| Pay | 10 |
| Access | 10 |
| Urgency | 10 |
| Activity | 5 |

Bands: HOT 80+, WARM 65-79, NURTURE 50-64, below 50 not qualified.

Two gates override the score: a safety or medical trigger hands off to a
human (`HANDOFF`), and an out-of-area lead is `UNQUALIFIED` even when the
raw score is high. When a user proposes a concrete date and time, the agent
checks availability through the runner's mock calendar before booking, and
it never promises discounts or specific prices under price pressure.

## Run it

In-process, through the CLI (from the repository root):

```bash
qualbench run --all --agent reference
```

As a standalone webhook server:

```bash
python agent.py --port 8080
qualbench run --all --agent webhook --agent-url http://localhost:8080/chat
```

## Protocol quick reference

Request: `{session_id, message, history, context, tool_results?}` where
`message` is null when delivering tool results.

Response: `{reply, tool_calls, outcome}` where `outcome` is
`{stage, score, fields, handoff}`.

Tools the runner executes for the agent: `calendar.check_availability`,
`calendar.book`, `crm.upsert_lead`, `crm.get_lead`.
