# Naive agent (deliberately careless, do not copy)

A dependency-free agent that does almost everything wrong, on purpose.
It is the second entry on the QualBench Benchmark v1 leaderboard, and it
exists to price the risk of a careless build: the gap between this agent
and the reference agent is the headline number of the benchmark.

What it does wrong, by design:

- Books the first date and time it can spot, without checking
  availability, then claims the booking succeeded even when the
  calendar rejected the slot.
- Captures almost nothing: a name only in the simplest form. It never
  asks for or records an email or phone number.
- Never hands off to a human, including medical disclosures,
  emergencies, minors, and legal questions.
- Agrees to discounts and price pressure immediately.
- Scores every lead 95 (HOT) and reports QUALIFIED or BOOKED
  regardless of qualification.

It speaks exactly the same webhook protocol as the reference agent, so
its leaderboard score reflects behaviour, not plumbing. Run it:

```bash
qualbench run --all --agent file --agent-file examples/naive-agent/agent.py
```

Or as a standalone webhook server on port 8081 (see the module
docstring in `agent.py`). Its careless behaviours are pinned by tests
in `tests/test_naive_agent.py`.
