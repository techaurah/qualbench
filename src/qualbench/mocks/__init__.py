"""Built-in mock business tools (fake calendar, fake CRM)."""

from .calendar import Booking, FakeCalendar
from .crm import FakeCRM

__all__ = ["Booking", "FakeCRM", "FakeCalendar"]
