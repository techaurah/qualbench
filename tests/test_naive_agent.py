"""Tests pinning the naive agent's deliberately careless behaviours.

The naive agent is a benchmark fixture, not a bug: these tests make sure
its carelessness stays exactly as documented in its docstring (books
without qualifying, never hands off, captures almost nothing, agrees to
discounts, scores everyone HOT). If a future change makes it careful,
these tests should fail loudly.
"""

import importlib.util
from pathlib import Path

from qualbench.agents.webhook_agent import load_agent_file
from qualbench.assertions import run_assertions
from qualbench.runner import run_scenario
from qualbench.scenario import load_pack

ROOT = Path(__file__).resolve().parents[1]
NAIVE = ROOT / "examples" / "naive-agent" / "agent.py"
PACKS = ROOT / "packs"


def _module():
    spec = importlib.util.spec_from_file_location("naive_agent", NAIVE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(pack_name, scenario_name):
    pack = load_pack(PACKS / pack_name)
    scenario = next(s for s in pack.scenarios if s.name == scenario_name)
    result = run_scenario(lambda: load_agent_file(NAIVE), scenario)
    return scenario, result


def test_naive_books_the_happy_path_but_captures_almost_nothing():
    _scenario, result = _run("real-estate", "standard-inquiry")
    assert len(result.bookings) == 1
    assert result.fields.get("name") == "Sarah Mitchell"
    assert "email" not in result.fields
    assert "phone" not in result.fields


def test_naive_never_hands_off_on_a_safety_scenario():
    scenario, result = _run("med-spa", "contraindication-handoff")
    assert result.handoff is False
    checks = {c.kind: c.passed for c in run_assertions(scenario, result)}
    assert checks["handoff"] is False


def test_naive_never_hands_off_on_an_emergency():
    _scenario, result = _run("home-services", "emergency-repair")
    assert result.handoff is False
    assert result.error is None


def test_naive_agrees_to_discount_pressure():
    _scenario, result = _run("real-estate", "price-pressure")
    assert "discount is no problem" in result.replies_text.lower()


def test_naive_scores_everyone_hot_regardless_of_qualification():
    module = _module()
    session = module.NaiveAgentSession()
    session.start({"vertical": "real-estate", "appointment_minutes": 60})
    response = session.handle(
        {"message": "Just browsing really, maybe someday, no rush at all."}
    )
    assert response["outcome"]["score"] == 95
    assert response["outcome"]["stage"] == "QUALIFIED"
    assert response["outcome"]["handoff"] is False


def test_naive_claims_a_booking_the_calendar_rejected():
    # The requested 12:00 slot overlaps a seeded busy block, so the mock
    # calendar refuses it. The naive agent reports BOOKED anyway.
    _scenario, result = _run("real-estate", "double-booking-conflict")
    assert result.bookings == []
    assert result.stage == "BOOKED"
    assert result.error is None
