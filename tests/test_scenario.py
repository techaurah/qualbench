from pathlib import Path

import pytest

from qualbench.scenario import ScenarioError, discover_packs, load_pack

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"


def test_all_five_packs_load_with_ten_scenarios_each():
    packs = discover_packs(PACKS)
    assert [p.name for p in packs] == [
        "agencies",
        "dental",
        "home-services",
        "med-spa",
        "real-estate",
    ]
    for pack in packs:
        assert len(pack.scenarios) == 10, pack.name


def test_real_estate_scenario_names_match_the_pack_design():
    pack = load_pack(PACKS / "real-estate")
    names = {s.name for s in pack.scenarios}
    assert names == {
        "standard-inquiry",
        "after-hours-inquiry",
        "price-pressure",
        "out-of-area",
        "urgent-viewing",
        "double-booking-conflict",
        "reschedule-viewing",
        "spanish-language-inquiry",
        "tenant-inquiry-routing",
        "referral-from-past-client",
    }


def test_dental_scenario_names_match_the_pack_design():
    pack = load_pack(PACKS / "dental")
    names = {s.name for s in pack.scenarios}
    assert names == {
        "hygiene-booking",
        "toothache-triage",
        "insurance-coverage-question",
        "new-patient-forms",
        "orthodontic-consult-minor",
        "implant-price-shopping",
        "after-hours-emergency",
        "reschedule-flow",
        "recall-reminder-acceptance",
        "referral-from-patient",
    }


def test_agencies_scenario_names_match_the_pack_design():
    pack = load_pack(PACKS / "agencies")
    names = {s.name for s in pack.scenarios}
    assert names == {
        "discovery-call-booking",
        "budget-below-minimum",
        "multi-stakeholder-thread",
        "nda-legal-handoff",
        "rush-project-pressure",
        "portfolio-request",
        "existing-client-upsell",
        "competitor-badmouthing",
        "vague-brief-qualification",
        "after-hours-founder-inquiry",
    }


def test_scenario_fields_parse():
    pack = load_pack(PACKS / "real-estate")
    scenario = next(s for s in pack.scenarios if s.name == "standard-inquiry")
    assert scenario.turns and all(isinstance(t, str) for t in scenario.turns)
    assert scenario.expected["stage"] == "BOOKED"
    assert scenario.appointment_minutes == 60
    # Pack-level prohibited content is merged into every scenario.
    assert "guaranteed discount" in scenario.prohibited_content
    assert scenario.seed_calendar["business_hours"]["start"] == "09:00"


def test_pack_without_scenarios_fails(tmp_path):
    (tmp_path / "pack.yaml").write_text("name: empty\nvertical: x\n")
    (tmp_path / "scenarios").mkdir()
    with pytest.raises(ScenarioError):
        load_pack(tmp_path)


def test_scenario_without_turns_fails(tmp_path):
    (tmp_path / "pack.yaml").write_text("name: bad\nvertical: x\n")
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "broken.yaml").write_text("name: broken\nexpected: {}\n")
    with pytest.raises(ScenarioError):
        load_pack(tmp_path)


def test_missing_pack_yaml_fails(tmp_path):
    with pytest.raises(ScenarioError):
        load_pack(tmp_path)


def _write_pack(tmp_path, scenario_yaml: str):
    (tmp_path / "pack.yaml").write_text("name: t\nvertical: x\n")
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir(exist_ok=True)
    (scenarios / "s.yaml").write_text(scenario_yaml)


BASE_YAML = "name: s\nturns:\n  - user: hi\nexpected:\n  stage: NEW\n"


def test_tier_defaults_to_core(tmp_path):
    _write_pack(tmp_path, BASE_YAML)
    pack = load_pack(tmp_path)
    assert pack.scenarios[0].tier == "core"


def test_tier_parses_and_validates(tmp_path):
    _write_pack(tmp_path, "tier: safety\n" + BASE_YAML)
    pack = load_pack(tmp_path)
    assert pack.scenarios[0].tier == "safety"
    _write_pack(tmp_path, "tier: critical\n" + BASE_YAML)
    with pytest.raises(ScenarioError):
        load_pack(tmp_path)


def test_existing_packs_have_the_designed_tier_mix():
    packs = {p.name: p for p in discover_packs(PACKS)}
    tiers = {
        name: {s.name: s.tier for s in pack.scenarios}
        for name, pack in packs.items()
    }
    assert tiers["med-spa"]["contraindication-handoff"] == "safety"
    assert tiers["home-services"]["gas-safety-handoff"] == "safety"
    assert tiers["home-services"]["emergency-repair"] == "safety"
    assert tiers["real-estate"]["standard-inquiry"] == "core"
    assert tiers["dental"]["toothache-triage"] == "safety"
    assert tiers["dental"]["after-hours-emergency"] == "safety"
    assert tiers["dental"]["orthodontic-consult-minor"] == "safety"
    assert tiers["med-spa"]["underage-inquiry"] == "safety"
    assert tiers["med-spa"]["treatment-complaint"] == "safety"
    assert tiers["med-spa"]["botox-first-timer"] == "safety"
    safety_total = sum(
        1 for pack in tiers.values() for tier in pack.values() if tier == "safety"
    )
    assert safety_total == 9
