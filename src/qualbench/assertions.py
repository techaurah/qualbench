"""The six deterministic assertion types.

Every check here is exact: string equality, numeric bands, set membership,
substring absence. There is deliberately no LLM judge anywhere in QualBench.
A check that should be exact must not be delegated to a model score.
"""

from __future__ import annotations

from dataclasses import dataclass

from .runner import RunResult


@dataclass
class AssertionResult:
    kind: str
    passed: bool
    message: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "passed": self.passed, "message": self.message}


def check_stage(expected: dict, result: RunResult) -> AssertionResult | None:
    want = expected.get("stage")
    if want is None:
        return None
    got = (result.stage or "").upper()
    ok = got == str(want).upper()
    return AssertionResult(
        "stage_equals", ok, f"final stage is {got or 'MISSING'}, expected {want}"
    )


def check_score_band(expected: dict, result: RunResult) -> AssertionResult | None:
    band = expected.get("score_band")
    if band is None:
        return None
    low, high = float(band[0]), float(band[1])
    if result.score is None:
        return AssertionResult("score_band", False, "agent reported no score")
    ok = low <= result.score <= high
    return AssertionResult(
        "score_band", ok, f"score {result.score:g} is within [{low:g}, {high:g}]"
        if ok
        else f"score {result.score:g} is outside [{low:g}, {high:g}]",
    )


def check_booking(expected: dict, result: RunResult) -> list[AssertionResult]:
    out: list[AssertionResult] = []
    if "booking_made" not in expected:
        return out
    want_made = bool(expected["booking_made"])
    bookings = result.bookings
    made = len(bookings) > 0
    out.append(
        AssertionResult(
            "booking_made",
            made == want_made,
            f"booking made: {made}, expected: {want_made}",
        )
    )
    if want_made and made and expected.get("booking_valid_slot", True):
        valid, reason = result.calendar.validate_booking(bookings[0])
        out.append(
            AssertionResult(
                "booking_valid_slot",
                valid,
                f"booked slot {bookings[0].start.isoformat()} is valid ({reason})"
                if valid
                else f"booked slot is invalid: {reason}",
            )
        )
    return out


def check_fields(expected: dict, result: RunResult) -> AssertionResult | None:
    want = expected.get("fields_captured")
    if not want:
        return None
    captured = result.fields
    missing = [
        name
        for name in want
        if captured.get(name) in (None, "", [])
    ]
    ok = not missing
    return AssertionResult(
        "fields_captured",
        ok,
        "all required fields captured"
        if ok
        else f"missing captured fields: {', '.join(missing)}",
    )


def check_prohibited(scenario, result: RunResult) -> AssertionResult | None:
    prohibited = scenario.prohibited_content
    if not prohibited:
        return None
    replies = result.replies_text.lower()
    found = [item for item in prohibited if item.lower() in replies]
    ok = not found
    return AssertionResult(
        "prohibited_absent",
        ok,
        "no prohibited content in agent replies"
        if ok
        else f"prohibited content found in replies: {', '.join(found)}",
    )


def check_handoff(expected: dict, result: RunResult) -> AssertionResult | None:
    if "handoff" not in expected:
        return None
    want = bool(expected["handoff"])
    ok = result.handoff == want
    return AssertionResult(
        "handoff", ok, f"handoff triggered: {result.handoff}, expected: {want}"
    )


def run_assertions(scenario, result: RunResult) -> list[AssertionResult]:
    if result.error:
        return [
            AssertionResult("run_error", False, f"agent run failed: {result.error}")
        ]
    expected = scenario.expected
    results: list[AssertionResult] = []
    for single in (
        check_stage(expected, result),
        check_score_band(expected, result),
        check_fields(expected, result),
        check_handoff(expected, result),
        check_prohibited(scenario, result),
    ):
        if single is not None:
            results.append(single)
    results.extend(check_booking(expected, result))
    return results
