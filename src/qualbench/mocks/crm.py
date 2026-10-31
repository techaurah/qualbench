"""A fake CRM that records every write an agent makes.

Agents never touch this object directly. The runner executes their
``crm.upsert_lead`` tool calls here and keeps the full write log, so tests
can assert exactly which fields the agent captured.
"""

from __future__ import annotations

import copy


class FakeCRM:
    def __init__(self, seed: dict | None = None):
        seed = seed or {}
        self.leads: dict[str, dict] = {}
        self.writes: list[dict] = []
        self._counter = 0
        for lead in seed.get("leads", []) or []:
            self._counter += 1
            record = dict(lead)
            record.setdefault("lead_id", f"lead-{self._counter:03d}")
            self.leads[record["lead_id"]] = record

    def upsert_lead(self, fields: dict) -> dict:
        """Create or merge a lead. Matching is by email, then phone, then the
        single open lead, which mirrors how a simple pipeline behaves."""
        if not isinstance(fields, dict) or not fields:
            raise ValueError("crm.upsert_lead requires a non-empty fields object")
        record = self._find_match(fields)
        if record is None:
            self._counter += 1
            record = {"lead_id": f"lead-{self._counter:03d}"}
            self.leads[record["lead_id"]] = record
        record.update({k: v for k, v in fields.items() if v is not None})
        self.writes.append(copy.deepcopy(record))
        return copy.deepcopy(record)

    def _find_match(self, fields: dict) -> dict | None:
        for key in ("email", "phone"):
            value = fields.get(key)
            if value:
                for record in self.leads.values():
                    if record.get(key) == value:
                        return record
        if len(self.leads) == 1:
            return next(iter(self.leads.values()))
        return None

    def get_lead(self) -> dict | None:
        """Return the most recently written lead, or the only lead."""
        if self.writes:
            return self.writes[-1]
        if len(self.leads) == 1:
            return next(iter(self.leads.values()))
        return None

    def captured_fields(self) -> dict:
        """Merged view of everything the agent has written to the CRM."""
        merged: dict = {}
        for write in self.writes:
            merged.update(write)
        if not merged and len(self.leads) == 1:
            merged = dict(next(iter(self.leads.values())))
        return merged
