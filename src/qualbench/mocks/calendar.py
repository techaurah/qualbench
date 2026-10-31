"""A deterministic fake calendar with seeded availability.

The calendar is seeded from a scenario file: business hours plus a list of
busy blocks. Agents interact with it only through the runner, which executes
their ``calendar.check_availability`` and ``calendar.book`` tool calls here,
so a booking agent can be tested end to end offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time

WEEKDAYS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 datetime (a trailing ``Z`` is accepted)."""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _parse_hhmm(value: str) -> time:
    parts = str(value).split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def _normalise_days(days) -> set[int]:
    out: set[int] = set()
    for day in days or []:
        if isinstance(day, int):
            out.add(day)
        else:
            out.add(WEEKDAYS[str(day).strip().lower()[:3]])
    return out


@dataclass
class Booking:
    booking_id: str
    start: datetime
    end: datetime
    title: str = ""

    def to_dict(self) -> dict:
        return {
            "booking_id": self.booking_id,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "title": self.title,
        }


@dataclass
class FakeCalendar:
    """Seeded calendar. All datetimes are naive local times."""

    business_days: set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})
    day_start: time = time(9, 0)
    day_end: time = time(17, 0)
    busy: list[tuple[datetime, datetime, str]] = field(default_factory=list)
    bookings: list[Booking] = field(default_factory=list)
    _counter: int = 0

    @classmethod
    def from_seed(cls, seed: dict | None) -> FakeCalendar:
        seed = seed or {}
        hours = seed.get("business_hours") or {}
        cal = cls(
            business_days=_normalise_days(hours.get("days", [0, 1, 2, 3, 4])),
            day_start=_parse_hhmm(hours.get("start", "09:00")),
            day_end=_parse_hhmm(hours.get("end", "17:00")),
        )
        for block in seed.get("busy", []) or []:
            cal.busy.append(
                (
                    parse_dt(block["start"]),
                    parse_dt(block["end"]),
                    str(block.get("title", "Busy")),
                )
            )
        return cal

    # -- queries ---------------------------------------------------------
    def within_business_hours(self, start: datetime, end: datetime) -> bool:
        if end <= start:
            return False
        if start.weekday() not in self.business_days:
            return False
        if start.date() != end.date():
            return False
        return start.time() >= self.day_start and end.time() <= self.day_end

    def _overlaps(self, start: datetime, end: datetime) -> bool:
        for b_start, b_end, _title in self.busy:
            if start < b_end and b_start < end:
                return True
        for booking in self.bookings:
            if start < booking.end and booking.start < end:
                return True
        return False

    def is_available(self, start: datetime, end: datetime) -> bool:
        return self.within_business_hours(start, end) and not self._overlaps(start, end)

    # -- mutations -------------------------------------------------------
    def book(self, start: datetime, end: datetime, title: str = "") -> Booking:
        if not self.is_available(start, end):
            raise ValueError(
                f"Slot {start.isoformat()} to {end.isoformat()} is not available"
            )
        self._counter += 1
        booking = Booking(
            booking_id=f"bk-{self._counter:03d}", start=start, end=end, title=title
        )
        self.bookings.append(booking)
        return booking

    # -- validation used by assertions ----------------------------------
    def validate_booking(self, booking: Booking) -> tuple[bool, str]:
        """A booking is valid when it sits inside business hours and does not
        overlap any seeded busy block."""
        if not self.within_business_hours(booking.start, booking.end):
            return False, "booking is outside business hours"
        for b_start, b_end, title in self.busy:
            if booking.start < b_end and b_start < booking.end:
                return False, f"booking overlaps seeded busy block '{title}'"
        return True, "ok"
