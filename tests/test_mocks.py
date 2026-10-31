from datetime import datetime

import pytest

from qualbench.mocks.calendar import FakeCalendar
from qualbench.mocks.crm import FakeCRM

MON_10AM = datetime(2026, 11, 2, 10, 0)
MON_11AM = datetime(2026, 11, 2, 11, 0)
SAT_10AM = datetime(2026, 11, 7, 10, 0)
SAT_11AM = datetime(2026, 11, 7, 11, 0)


def seed_calendar():
    return FakeCalendar.from_seed(
        {
            "business_hours": {"days": ["mon", "tue", "wed", "thu", "fri"],
                               "start": "09:00", "end": "17:00"},
            "busy": [
                {"start": "2026-11-02T12:00:00", "end": "2026-11-02T13:00:00",
                 "title": "Lunch"}
            ],
        }
    )


def test_weekday_names_map_to_real_weekdays():
    cal = seed_calendar()
    # 2026-11-04 is a Wednesday and must be a business day.
    assert cal.is_available(datetime(2026, 11, 4, 10, 0), datetime(2026, 11, 4, 11, 0))


def test_weekend_is_not_available_by_default():
    cal = seed_calendar()
    assert not cal.is_available(SAT_10AM, SAT_11AM)


def test_busy_block_is_not_available():
    cal = seed_calendar()
    assert not cal.is_available(
        datetime(2026, 11, 2, 12, 30), datetime(2026, 11, 2, 13, 30)
    )


def test_outside_business_hours_is_not_available():
    cal = seed_calendar()
    assert not cal.is_available(
        datetime(2026, 11, 2, 7, 0), datetime(2026, 11, 2, 8, 0)
    )


def test_booking_blocks_the_slot_and_validates():
    cal = seed_calendar()
    booking = cal.book(MON_10AM, MON_11AM, "Viewing")
    assert booking.booking_id == "bk-001"
    assert not cal.is_available(MON_10AM, MON_11AM)
    valid, _reason = cal.validate_booking(booking)
    assert valid


def test_booking_an_unavailable_slot_raises():
    cal = seed_calendar()
    with pytest.raises(ValueError):
        cal.book(datetime(2026, 11, 2, 12, 0), datetime(2026, 11, 2, 13, 0))


def test_validate_booking_rejects_overlap_with_busy():
    cal = seed_calendar()
    from qualbench.mocks.calendar import Booking

    fake = Booking("bk-x", datetime(2026, 11, 2, 12, 30),
                   datetime(2026, 11, 2, 13, 30))
    valid, reason = cal.validate_booking(fake)
    assert not valid
    assert "busy" in reason


def test_crm_upsert_creates_and_merges_by_email():
    crm = FakeCRM()
    crm.upsert_lead({"name": "Sam", "email": "sam@example.com"})
    crm.upsert_lead({"email": "sam@example.com", "phone": "555-0100"})
    assert len(crm.leads) == 1
    captured = crm.captured_fields()
    assert captured["name"] == "Sam"
    assert captured["phone"] == "555-0100"
    assert len(crm.writes) == 2


def test_crm_seed_leads_are_loaded():
    crm = FakeCRM({"leads": [{"name": "Existing", "email": "old@example.com"}]})
    assert crm.get_lead()["name"] == "Existing"


def test_crm_rejects_empty_upsert():
    crm = FakeCRM()
    with pytest.raises(ValueError):
        crm.upsert_lead({})
