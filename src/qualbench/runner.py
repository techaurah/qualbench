"""The scenario runner: drives the agent, executes its tool calls against
the mocks, and collects the business outcomes assertions check.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .agents.base import AgentSession
from .mocks.calendar import FakeCalendar, parse_dt
from .mocks.crm import FakeCRM
from .scenario import Scenario

MAX_TOOL_ROUNDS = 8


@dataclass
class RunResult:
    scenario: Scenario
    transcript: list[dict] = field(default_factory=list)
    stage: str | None = None
    score: float | None = None
    fields: dict = field(default_factory=dict)
    handoff: bool = False
    outcome_reported: bool = False
    calendar: FakeCalendar | None = None
    crm: FakeCRM | None = None
    error: str | None = None

    @property
    def replies_text(self) -> str:
        return "\n".join(
            turn["content"] for turn in self.transcript if turn["role"] == "agent"
        )

    @property
    def bookings(self) -> list:
        return list(self.calendar.bookings) if self.calendar else []


class ToolExecutor:
    """Executes agent tool calls against the mocks and records outcomes."""

    def __init__(self, calendar: FakeCalendar, crm: FakeCRM, result: RunResult):
        self.calendar = calendar
        self.crm = crm
        self.result = result

    def execute(self, tool: str, args: dict) -> Any:
        args = args or {}
        if tool == "calendar.check_availability":
            start, end = parse_dt(args["start"]), parse_dt(args["end"])
            return {"available": self.calendar.is_available(start, end)}
        if tool == "calendar.book":
            start, end = parse_dt(args["start"]), parse_dt(args["end"])
            booking = self.calendar.book(start, end, str(args.get("title", "")))
            return booking.to_dict()
        if tool == "crm.upsert_lead":
            fields = args.get("fields", args)
            record = self.crm.upsert_lead(fields)
            self._absorb_outcome(fields)
            return record
        if tool == "crm.get_lead":
            return self.crm.get_lead() or {}
        if tool == "report_outcome":
            self._absorb_outcome(args)
            return {"recorded": True}
        raise ValueError(f"Unknown tool: {tool}")

    def _absorb_outcome(self, data: dict) -> None:
        """Outcome data can arrive via report_outcome or inside CRM fields."""
        if not isinstance(data, dict):
            return
        if data.get("stage"):
            self.result.stage = str(data["stage"]).upper()
            self.result.outcome_reported = True
        if data.get("score") is not None:
            try:
                self.result.score = float(data["score"])
                self.result.outcome_reported = True
            except (TypeError, ValueError):
                pass
        if data.get("handoff") is not None:
            self.result.handoff = bool(data["handoff"])
            self.result.outcome_reported = True


def run_scenario(session_factory, scenario: Scenario) -> RunResult:
    """Run one scenario. ``session_factory`` is a zero-arg callable returning
    a fresh agent session, so state never leaks between scenarios."""
    calendar = FakeCalendar.from_seed(scenario.seed_calendar)
    crm = FakeCRM(scenario.seed_crm)
    result = RunResult(scenario=scenario, calendar=calendar, crm=crm)
    executor = ToolExecutor(calendar, crm, result)
    context = {
        "pack": scenario.pack_name,
        "vertical": scenario.vertical,
        "appointment_minutes": scenario.appointment_minutes,
        "scenario": scenario.name,
    }
    session: AgentSession = session_factory()
    try:
        session.start(context)
        for user_text in scenario.turns:
            _drive_turn(session, scenario, result, executor, user_text, context)
    except Exception as exc:  # noqa: BLE001 - agent errors are scenario failures, not crashes
        result.error = f"{type(exc).__name__}: {exc}"
    _finalise(result, crm)
    return result


def _drive_turn(session, scenario, result, executor, user_text, context) -> None:
    result.transcript.append({"role": "user", "content": user_text})
    payload: dict[str, Any] = {
        "session_id": scenario.scenario_id,
        "message": user_text,
        "history": copy.deepcopy(result.transcript),
        "context": context,
    }
    for _round in range(MAX_TOOL_ROUNDS):
        response = session.send(payload)
        if not isinstance(response, dict):
            raise TypeError("Agent returned a non-dict response")
        _absorb_response(result, executor, response)
        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            return
        tool_results = []
        for call in tool_calls:
            call_id = call.get("id") or f"call-{len(tool_results) + 1}"
            tool = call.get("tool", "")
            try:
                outcome = executor.execute(tool, call.get("args") or {})
                tool_results.append(
                    {"id": call_id, "tool": tool, "ok": True, "result": outcome}
                )
            except Exception as exc:  # noqa: BLE001 - tool failures go back to the agent
                tool_results.append(
                    {"id": call_id, "tool": tool, "ok": False, "error": str(exc)}
                )
        payload = {
            "session_id": scenario.scenario_id,
            "message": None,
            "history": copy.deepcopy(result.transcript),
            "context": context,
            "tool_results": tool_results,
        }
    raise ValueError(f"Agent exceeded {MAX_TOOL_ROUNDS} tool rounds in one turn")


def _absorb_response(result: RunResult, executor: ToolExecutor, response: dict) -> None:
    reply = response.get("reply") or ""
    if reply:
        result.transcript.append({"role": "agent", "content": str(reply)})
    outcome = response.get("outcome") or {}
    if isinstance(outcome, dict):
        executor._absorb_outcome(outcome)
        fields = outcome.get("fields")
        if isinstance(fields, dict):
            result.fields.update(fields)


def _finalise(result: RunResult, crm: FakeCRM) -> None:
    captured = crm.captured_fields()
    merged = dict(captured)
    merged.update(result.fields)
    result.fields = merged
    lead = crm.get_lead() or {}
    if result.stage is None and lead.get("stage"):
        result.stage = str(lead["stage"]).upper()
    if result.score is None and lead.get("score") is not None:
        try:
            result.score = float(lead["score"])
        except (TypeError, ValueError):
            pass


def default_duration(minutes: int) -> timedelta:
    return timedelta(minutes=minutes)
