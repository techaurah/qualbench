from datetime import datetime

from qualbench.assertions import run_assertions
from qualbench.mocks.calendar import Booking, FakeCalendar
from qualbench.mocks.crm import FakeCRM
from qualbench.runner import RunResult
from qualbench.scenario import Scenario


def make_scenario(expected, prohibited=None):
    return Scenario(
        name="demo",
        description="",
        turns=["hi"],
        seed_calendar={},
        seed_crm={},
        expected=expected,
        pack_name="demo-pack",
        prohibited_content=prohibited or [],
    )


def make_result(**kwargs):
    result = RunResult(
        scenario=make_scenario({}),
        calendar=FakeCalendar.from_seed({}),
        crm=FakeCRM(),
    )
    for key, value in kwargs.items():
        setattr(result, key, value)
    return result


def verdicts(scenario, result):
    return {a.kind: a.passed for a in run_assertions(scenario, result)}


def test_stage_equals_is_case_insensitive():
    scenario = make_scenario({"stage": "booked"})
    assert verdicts(scenario, make_result(stage="BOOKED"))["stage_equals"]


def test_score_band_boundaries_are_inclusive():
    scenario = make_scenario({"score_band": [65, 79]})
    assert verdicts(scenario, make_result(score=65))["score_band"]
    assert verdicts(scenario, make_result(score=79))["score_band"]
    assert not verdicts(scenario, make_result(score=80))["score_band"]


def test_missing_score_fails_the_band():
    scenario = make_scenario({"score_band": [0, 100]})
    assert not verdicts(scenario, make_result(score=None))["score_band"]


def test_booking_made_and_valid_slot():
    result = make_result()
    booking = result.calendar.book(
        datetime(2026, 11, 2, 10, 0), datetime(2026, 11, 2, 11, 0)
    )
    assert booking
    scenario = make_scenario({"booking_made": True})
    checks = verdicts(scenario, result)
    assert checks["booking_made"] and checks["booking_valid_slot"]


def test_booking_not_made_when_one_was_expected():
    scenario = make_scenario({"booking_made": True})
    assert not verdicts(scenario, make_result())["booking_made"]


def test_invalid_slot_fails_validity_even_when_booked():
    result = make_result()
    # 2026-11-07 is a Saturday: outside the default Mon-Fri business days.
    result.calendar.bookings.append(
        Booking("bk-bad", datetime(2026, 11, 7, 10, 0), datetime(2026, 11, 7, 11, 0))
    )
    scenario = make_scenario({"booking_made": True})
    checks = verdicts(scenario, result)
    assert checks["booking_made"]
    assert not checks["booking_valid_slot"]


def test_fields_captured_reports_missing():
    scenario = make_scenario({"fields_captured": ["name", "email", "phone"]})
    result = make_result(fields={"name": "Sam", "email": "sam@example.com"})
    assert not verdicts(scenario, result)["fields_captured"]
    result.fields["phone"] = "555-0100"
    assert verdicts(scenario, result)["fields_captured"]


def test_prohibited_content_found_in_agent_replies():
    scenario = make_scenario({}, prohibited=["guaranteed discount"])
    result = make_result()
    result.transcript.append(
        {"role": "agent", "content": "We can offer a Guaranteed Discount today."}
    )
    result.transcript.append({"role": "user", "content": "guaranteed discount please"})
    # Only agent replies are scanned; the user asking is not a failure.
    assert not verdicts(scenario, result)["prohibited_absent"]
    result.transcript[0] = {"role": "agent", "content": "Pricing is confirmed after assessment."}
    assert verdicts(scenario, result)["prohibited_absent"]


def test_handoff_expectation():
    scenario = make_scenario({"handoff": True})
    assert verdicts(scenario, make_result(handoff=True))["handoff"]
    assert not verdicts(scenario, make_result(handoff=False))["handoff"]


def test_run_error_becomes_a_failed_assertion():
    scenario = make_scenario({"stage": "BOOKED"})
    result = make_result(error="AgentError: boom")
    checks = run_assertions(scenario, result)
    assert len(checks) == 1 and not checks[0].passed
