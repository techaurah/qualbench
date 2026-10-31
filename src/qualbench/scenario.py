"""Loading and validation for QualBench packs and YAML scenarios.

A pack is a folder with a ``pack.yaml`` and a ``scenarios/`` folder of YAML
files. A scenario scripts the user side of a conversation, seeds the mock
calendar and CRM, and states the expected business outcomes. See
``docs/scenario-format.md`` for the full format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ScenarioError(ValueError):
    """Raised when a pack or scenario file is malformed."""


@dataclass
class Scenario:
    name: str
    description: str
    turns: list[str]
    seed_calendar: dict
    seed_crm: dict
    expected: dict
    pack_name: str = ""
    vertical: str = ""
    appointment_minutes: int = 60
    prohibited_content: list[str] = field(default_factory=list)
    path: str = ""

    @property
    def scenario_id(self) -> str:
        return f"{self.pack_name}/{self.name}" if self.pack_name else self.name


@dataclass
class Pack:
    name: str
    vertical: str
    description: str
    path: Path
    scenarios: list[Scenario]
    defaults: dict = field(default_factory=dict)


def _load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioError(f"{path}: expected a YAML mapping at the top level")
    return data


def load_scenario(path: Path, pack_meta: dict, defaults: dict) -> Scenario:
    data = _load_yaml(path)
    name = data.get("name") or path.stem
    turns_raw = data.get("turns")
    if not turns_raw or not isinstance(turns_raw, list):
        raise ScenarioError(f"{path}: 'turns' must be a non-empty list")
    turns: list[str] = []
    for i, turn in enumerate(turns_raw):
        if isinstance(turn, dict):
            text = turn.get("user")
            if text is None:
                raise ScenarioError(f"{path}: turn {i} mapping must have a 'user' key")
            turns.append(str(text))
        else:
            turns.append(str(turn))
    expected = data.get("expected") or {}
    if not isinstance(expected, dict):
        raise ScenarioError(f"{path}: 'expected' must be a mapping")
    seed = data.get("seed") or {}
    prohibited = list(defaults.get("prohibited_content") or [])
    for item in expected.get("prohibited_absent") or []:
        if item not in prohibited:
            prohibited.append(item)
    return Scenario(
        name=str(name),
        description=str(data.get("description", "")),
        turns=turns,
        seed_calendar=dict(seed.get("calendar") or {}),
        seed_crm=dict(seed.get("crm") or {}),
        expected=expected,
        pack_name=str(pack_meta.get("name", "")),
        vertical=str(pack_meta.get("vertical", data.get("vertical", ""))),
        appointment_minutes=int(
            data.get("appointment_minutes", defaults.get("appointment_minutes", 60))
        ),
        prohibited_content=prohibited,
        path=str(path),
    )


def load_pack(pack_dir: str | Path) -> Pack:
    pack_dir = Path(pack_dir)
    meta_path = pack_dir / "pack.yaml"
    if not meta_path.exists():
        raise ScenarioError(f"{pack_dir}: missing pack.yaml")
    meta = _load_yaml(meta_path)
    defaults = meta.get("defaults") or {}
    scenarios_dir = pack_dir / "scenarios"
    if not scenarios_dir.is_dir():
        raise ScenarioError(f"{pack_dir}: missing scenarios/ folder")
    files = sorted(scenarios_dir.glob("*.yaml")) + sorted(scenarios_dir.glob("*.yml"))
    if not files:
        raise ScenarioError(f"{pack_dir}: no scenario YAML files found")
    scenarios = [load_scenario(f, meta, defaults) for f in files]
    return Pack(
        name=str(meta.get("name", pack_dir.name)),
        vertical=str(meta.get("vertical", "")),
        description=str(meta.get("description", "")),
        path=pack_dir,
        scenarios=scenarios,
        defaults=defaults,
    )


def discover_packs(packs_dir: str | Path) -> list[Pack]:
    packs_dir = Path(packs_dir)
    found = []
    for child in sorted(packs_dir.iterdir()):
        if child.is_dir() and (child / "pack.yaml").exists():
            found.append(load_pack(child))
    if not found:
        raise ScenarioError(f"{packs_dir}: no packs found")
    return found
