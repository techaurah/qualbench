# Scenario format

A scenario is one scripted conversation with an expected business outcome.
Scenarios live in a **pack**: a folder with a `pack.yaml` and a `scenarios/`
folder of YAML files.

## pack.yaml

```yaml
name: real-estate
vertical: real-estate
description: What this pack covers.
defaults:
  appointment_minutes: 60
  prohibited_content:
    - "guaranteed discount"
```

`defaults.appointment_minutes` is the booking length the runner and agents
assume. `defaults.prohibited_content` lists phrases that must never appear
in agent replies in any scenario in the pack (for example, discount promises
outside approved pricing).

## Scenario file

```yaml
name: standard-inquiry
description: What this scenario proves, and why it matters.
seed:
  calendar:
    business_hours: {days: [mon, tue, wed, thu, fri, sat], start: "09:00", end: "17:00"}
    busy:
      - {start: "2026-11-07T12:00:00", end: "2026-11-07T13:00:00", title: "Agent at a closing"}
  crm:
    leads: []
turns:
  - user: "Hi, my name is Sarah Mitchell..."
  - user: "..."
expected:
  stage: BOOKED
  score_band: [80, 100]
  booking_made: true
  fields_captured: [name, email, phone]
  prohibited_absent: ["we can get you that price"]
  handoff: false
```

### seed

`seed.calendar` builds the fake calendar: `business_hours` (weekday names
or numbers 0 to 6, Monday first, plus `start` and `end` in 24h `HH:MM`) and
`busy`, a list of already-taken blocks. All datetimes are ISO-8601, naive
local time.

`seed.crm.leads` optionally pre-loads existing lead records.

### turns

The user side of the conversation, in order. Each entry is either a plain
string or a mapping with a `user` key. The runner sends one turn at a time
and lets the agent finish its tool calls (availability check, booking, CRM
write) before sending the next.

### expected

Every key is optional; include only what the scenario must prove. The six
assertion types are documented in [assertions.md](assertions.md).

`prohibited_absent` in a scenario is merged with the pack-level
`prohibited_content` list.

## Writing good scenarios

- Script the user the way real users write: incomplete details, details
  arriving out of order, pressure, edge cases.
- Include adversarial variants in every pack: after-hours, price pressure,
  out-of-area, and at least one case where the correct action is to hand
  off to a human instead of booking.
- Make the expected outcome the *business* outcome (stage, booking, fields)
  rather than judging reply wording, except for prohibited content, which
  is the one wording check that matters commercially.
- Use fixed dates. A scenario that depends on "today" will rot.
