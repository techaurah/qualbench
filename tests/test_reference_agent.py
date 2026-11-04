"""Focused tests for the reference-agent model extensions that the
Benchmark v1 suite growth required: the dental and agencies vertical
configs, routing handoffs, minor protection, and Spanish name capture.
The pack scenarios themselves are covered end to end by test_runner.
"""

import importlib.util
from pathlib import Path

from qualbench.agents.webhook_agent import load_agent_file
from qualbench.runner import run_scenario
from qualbench.scenario import load_pack

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "reference-agent" / "agent.py"
PACKS = ROOT / "packs"


def _module():
    spec = importlib.util.spec_from_file_location("ref_agent", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(pack_name, scenario_name):
    pack = load_pack(PACKS / pack_name)
    scenario = next(s for s in pack.scenarios if s.name == scenario_name)
    return run_scenario(lambda: load_agent_file(REFERENCE), scenario)


def test_dental_vertical_config_scores_toronto_as_in_area():
    module = _module()
    session = module.ReferenceAgentSession()
    session.start({"vertical": "dental", "appointment_minutes": 45})
    session.handle({"message": "Hi, my name is Test Person. I need a cleaning in Toronto."})
    # Problem 20 + Fit 20 (Toronto is in the dental service area) + Size 5.
    assert session.score() == 45
    assert session.fields["name"] == "Test Person"


def test_dental_emergency_hands_off_with_urgent_guidance():
    result = _run("dental", "after-hours-emergency")
    assert result.handoff is True
    assert "emergency care" in result.replies_text


def test_agencies_nda_request_hands_off():
    result = _run("agencies", "nda-legal-handoff")
    assert result.handoff is True
    assert result.stage == "HANDOFF"


def test_med_spa_minor_self_booking_hands_off():
    result = _run("med-spa", "underage-inquiry")
    assert result.handoff is True
    assert result.bookings == []


def test_warranty_handoff_is_routing_not_the_emergency_script():
    result = _run("home-services", "warranty-callback")
    assert result.handoff is True
    assert "leave the property" not in result.replies_text.lower()


def test_gas_handoff_keeps_the_emergency_script():
    result = _run("home-services", "gas-safety-handoff")
    assert result.handoff is True
    assert "leave the property" in result.replies_text.lower()


def test_spanish_inquiry_captures_the_name():
    result = _run("real-estate", "spanish-language-inquiry")
    assert result.fields.get("name") == "Carlos Mendez"
    assert result.stage == "QUALIFIED"
