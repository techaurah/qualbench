# Assertions

QualBench has exactly six assertion types. All six are deterministic: string
equality, numeric bands, set membership, substring absence. There is no
LLM judge anywhere in the tool, by design. The failures that cost money in
a qualification and booking agent are outcome failures, and outcome checks
should be exact, not scored by another model.

## 1. Final stage equals (`stage`)

```yaml
expected:
  stage: BOOKED
```

The agent's reported final stage, upper-cased, must equal the expected
stage. Stage values are yours to define per vertical; the shipped packs use
`BOOKED`, `QUALIFIED`, `NURTURE`, `UNQUALIFIED` and `HANDOFF`.

The runner reads the stage from, in order: the agent's outcome report
(webhook `outcome.stage` or the `report_outcome` tool), fields written to
the CRM, and finally the CRM lead record.

## 2. Score within band (`score_band`)

```yaml
expected:
  score_band: [65, 79]
```

Inclusive on both ends. Fails if the agent reports no score. Bands are more
honest than exact scores: two reasonable scoring implementations should
land a warm lead in the warm band even if they differ by a few points.

## 3. Booking made / not made, with a valid slot (`booking_made`, `booking_valid_slot`)

```yaml
expected:
  booking_made: true
  booking_valid_slot: true   # default true when booking_made is true
```

Bookings are read from the mock calendar, so an agent cannot claim a
booking it did not make. A slot is valid when it sits inside the seeded
business hours and does not overlap any seeded busy block.

## 4. Required fields captured (`fields_captured`)

```yaml
expected:
  fields_captured: [name, email, phone]
```

Every listed field must be present and non-empty in the merged view of what
the agent wrote to the mock CRM plus the fields in its outcome report.

## 5. Prohibited content absent (`prohibited_absent`)

```yaml
expected:
  prohibited_absent:
    - "guaranteed discount"
```

Case-insensitive substring check over **agent replies only** (users asking
for a discount is normal; the agent promising one is the failure). Scenario
entries merge with the pack-level `defaults.prohibited_content` list. This
is the assertion that catches invented discounts and prices outside the
approved tiers you configure.

## 6. Handoff triggered / not triggered (`handoff`)

```yaml
expected:
  handoff: true
```

Reads the agent's outcome report. Use it both ways: safety and medical
cases must hand off; ordinary sales conversations must not.
