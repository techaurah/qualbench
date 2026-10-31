from pathlib import Path

import pytest

from qualbench.scenario import ScenarioError, discover_packs, load_pack

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"


def test_all_three_packs_load_with_five_scenarios_each():
    packs = discover_packs(PACKS)
    assert [p.name for p in packs] == ["home-services", "med-spa", "real-estate"]
    for pack in packs:
        assert len(pack.scenarios) == 5, pack.name


def test_real_estate_scenario_names_match_the_pack_design():
    pack = load_pack(PACKS / "real-estate")
    names = {s.name for s in pack.scenarios}
    assert names == {
        "standard-inquiry",
        "after-hours-inquiry",
        "price-pressure",
        "out-of-area",
        "urgent-viewing",
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
