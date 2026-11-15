# ai-generated: 70% - an AI assistant drafted the boundary cases from the docstrings; I checked each against the spec
"""Tests for the course module slaclock.py (Lab 5, Stretch 1).

Every test states the behaviour its docstring promises, at and around the boundary.
"""

from datetime import datetime, timedelta

import pytest

import slaclock
from slaclock import (
    add_business_minutes,
    business_minutes_between,
    escalation_tier,
    is_business_time,
    parse_duration,
    priority_of,
    sla_state,
    targets,
)


# --- priority_of ---------------------------------------------------------------

@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"),
        (1, 2, "P2"),
        (2, 1, "P2"),
        (1, 3, "P3"),
        (2, 2, "P3"),
        (3, 1, "P3"),
        (2, 3, "P4"),
        (3, 2, "P4"),
        (3, 3, "P4"),
    ],
)
def test_priority_matrix(impact, urgency, expected):
    assert priority_of(impact, urgency) == expected


@pytest.mark.parametrize(
    "impact, urgency, vip, expected",
    [
        (1, 1, True, "P1"),
        (1, 2, True, "P2"),
        (2, 1, True, "P2"),
        (1, 3, True, "P2"),
        (2, 2, True, "P2"),
        (3, 1, True, "P2"),
        (2, 3, True, "P2"),
        (3, 2, True, "P2"),
        (3, 3, True, "P2"),
    ],
)
def test_priority_vip_never_below_p2(impact, urgency, vip, expected):
    assert priority_of(impact, urgency, vip=vip) == expected


def test_priority_vip_false_is_unchanged():
    assert priority_of(3, 3, vip=False) == "P4"


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, True, False, "1", None])
def test_priority_rejects_bad_impact(bad):
    with pytest.raises(ValueError):
        priority_of(bad, 1)


@pytest.mark.parametrize("bad", [0, 4, 2.0, True, "3"])
def test_priority_rejects_bad_urgency(bad):
    with pytest.raises(ValueError):
        priority_of(1, bad)


# --- targets -------------------------------------------------------------------

@pytest.mark.parametrize(
    "priority, expected", [("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320))]
)
def test_targets_exact(priority, expected):
    assert targets(priority) == expected


@pytest.mark.parametrize("bad", ["", "p1", " P1", "P1 ", "P5", "P0"])
def test_targets_exact_lookup(bad):
    with pytest.raises(ValueError):
        targets(bad)


# --- sla_state -----------------------------------------------------------------

@pytest.mark.parametrize(
    "elapsed, target, expected",
    [
        (0, 15, "ok"),
        (11, 15, "ok"),
        (12, 15, "warning"),
        (14, 15, "warning"),
        (15, 15, "warning"),
        (16, 15, "breached"),
        (74, 100, "ok"),
        (75, 100, "warning"),
        (99, 100, "warning"),
        (100, 100, "warning"),
        (101, 100, "breached"),
        (0, 1, "ok"),
        (1, 1, "warning"),
        (2, 1, "breached"),
        (3, 4, "warning"),
        (2, 4, "ok"),
    ],
)
def test_sla_state_boundaries(elapsed, target, expected):
    assert sla_state(elapsed, target) == expected


@pytest.mark.parametrize("elapsed, target", [(-1, 10), (0, 0), (0, -5), (-1, 0)])
def test_sla_state_rejects_bad_values(elapsed, target):
    with pytest.raises(ValueError):
        sla_state(elapsed, target)


# --- is_business_time ----------------------------------------------------------

def test_is_business_time_weekday_boundaries():
    monday = datetime(2026, 1, 5)
    assert is_business_time(monday.replace(hour=8, minute=0)) is True
    assert is_business_time(monday.replace(hour=7, minute=59)) is False
    assert is_business_time(monday.replace(hour=15, minute=59)) is True
    assert is_business_time(monday.replace(hour=16, minute=0)) is False
    assert is_business_time(monday.replace(hour=12, minute=30)) is True


def test_is_business_time_weekend():
    saturday = datetime(2026, 1, 10, 10, 0)
    sunday = datetime(2026, 1, 11, 10, 0)
    friday = datetime(2026, 1, 9, 12, 0)
    assert saturday.weekday() == 5
    assert is_business_time(saturday) is False
    assert is_business_time(sunday) is False
    assert is_business_time(friday) is True


def test_is_business_time_ignores_seconds():
    assert is_business_time(datetime(2026, 1, 5, 15, 59, 59)) is True
    assert is_business_time(datetime(2026, 1, 5, 7, 59, 59)) is False


# --- add_business_minutes ------------------------------------------------------

def test_add_zero_minutes_inside_returns_start_at_minute_resolution():
    start = datetime(2026, 1, 5, 10, 0, 45, 123)
    assert add_business_minutes(start, 0) == datetime(2026, 1, 5, 10, 0)


def test_add_zero_minutes_before_opening_moves_to_opening():
    start = datetime(2026, 1, 5, 7, 59)
    assert add_business_minutes(start, 0) == datetime(2026, 1, 5, 8, 0)


def test_add_zero_minutes_after_closing_moves_to_next_day():
    start = datetime(2026, 1, 5, 17, 0)
    assert add_business_minutes(start, 0) == datetime(2026, 1, 6, 8, 0)


def test_add_zero_minutes_friday_evening_moves_to_monday():
    start = datetime(2026, 1, 9, 16, 0)
    assert start.weekday() == 4
    assert add_business_minutes(start, 0) == datetime(2026, 1, 12, 8, 0)


def test_add_from_weekend_moves_to_monday_opening():
    start = datetime(2026, 1, 10, 10, 0)
    assert add_business_minutes(start, 0) == datetime(2026, 1, 12, 8, 0)


def test_add_inside_a_day():
    start = datetime(2026, 1, 5, 9, 0)
    assert add_business_minutes(start, 90) == datetime(2026, 1, 5, 10, 30)


def test_add_ending_exactly_at_closing_stays_that_day():
    start = datetime(2026, 1, 5, 8, 0)
    assert add_business_minutes(start, 480) == datetime(2026, 1, 5, 16, 0)


def test_add_one_minute_past_closing_moves_to_next_opening():
    start = datetime(2026, 1, 5, 15, 59)
    assert add_business_minutes(start, 1) == datetime(2026, 1, 5, 16, 0)
    assert add_business_minutes(start, 2) == datetime(2026, 1, 6, 8, 1)


def test_add_crosses_day_boundary():
    start = datetime(2026, 1, 5, 15, 0)
    assert add_business_minutes(start, 120) == datetime(2026, 1, 6, 9, 0)


def test_add_crosses_weekend():
    friday = datetime(2026, 1, 9, 15, 0)
    assert friday.weekday() == 4
    assert add_business_minutes(friday, 120) == datetime(2026, 1, 12, 9, 0)


def test_add_exactly_one_week_ends_friday_at_closing():
    start = datetime(2026, 1, 5, 8, 0)
    assert add_business_minutes(start, 5 * 480) == datetime(2026, 1, 9, 16, 0)


def test_add_rejects_negative():
    with pytest.raises(ValueError):
        add_business_minutes(datetime(2026, 1, 5, 9, 0), -1)


def test_add_accepts_a_due_date_366_days_after_start():
    # Mon 2026-01-05 08:00 + 262 business days ends Tue 2027-01-05 16:00; one more minute is
    # Wed 2027-01-06 08:01, a due date 366 calendar days after the start's date (still allowed).
    start = datetime(2026, 1, 5, 8, 0)
    assert add_business_minutes(start, 125_761) == datetime(2027, 1, 6, 8, 1)


def test_add_rejects_more_than_max_days():
    with pytest.raises(ValueError):
        add_business_minutes(datetime(2026, 1, 5, 8, 0), 200_000)


# --- business_minutes_between --------------------------------------------------

def test_between_zero_interval():
    moment = datetime(2026, 1, 5, 12, 0)
    assert business_minutes_between(moment, moment) == 0


def test_between_full_business_day():
    day = datetime(2026, 1, 5)
    assert business_minutes_between(day.replace(hour=8), day.replace(hour=16)) == 480


def test_between_half_open_window():
    day = datetime(2026, 1, 5)
    assert business_minutes_between(day.replace(hour=7), day.replace(hour=8)) == 0
    assert business_minutes_between(day.replace(hour=16), day.replace(hour=17)) == 0
    assert business_minutes_between(day.replace(hour=7), day.replace(hour=9)) == 60
    assert business_minutes_between(day.replace(hour=15), day.replace(hour=17)) == 60


def test_between_across_weekend():
    friday = datetime(2026, 1, 9, 15, 0)
    monday = datetime(2026, 1, 12, 9, 0)
    assert business_minutes_between(friday, monday) == 120


def test_between_ignores_seconds():
    start = datetime(2026, 1, 5, 8, 0, 30)
    end = datetime(2026, 1, 5, 8, 1, 30)
    assert business_minutes_between(start, end) == 1


def test_between_rejects_reversed_interval():
    with pytest.raises(ValueError):
        business_minutes_between(datetime(2026, 1, 6, 9, 0), datetime(2026, 1, 5, 9, 0))


def test_between_accepts_a_span_of_366_days():
    start = datetime(2026, 1, 5, 8, 0)
    end = start + timedelta(days=366)
    assert business_minutes_between(start, end) == 125_760


def test_between_rejects_more_than_max_days():
    start = datetime(2026, 1, 5, 8, 0)
    with pytest.raises(ValueError):
        business_minutes_between(start, start + timedelta(days=367))


@pytest.mark.parametrize("start_minute", ["08:00", "09:30", "15:00", "16:00", "17:30"])
@pytest.mark.parametrize("minutes", [0, 1, 59, 60, 480, 1000])
def test_between_is_the_inverse_of_add(start_minute, minutes):
    hour, minute = (int(part) for part in start_minute.split(":"))
    start = datetime(2026, 1, 9, hour, minute)  # a Friday, so the weekend is exercised
    due = add_business_minutes(start, minutes)
    assert business_minutes_between(start, due) == minutes


# --- escalation_tier -----------------------------------------------------------

@pytest.mark.parametrize(
    "priority, breached, reopens, expected",
    [
        ("P1", False, 0, 1),
        ("P2", False, 0, 1),
        ("P3", False, 0, 0),
        ("P4", False, 0, 0),
        ("P1", True, 0, 3),
        ("P2", True, 0, 2),
        ("P3", True, 0, 1),
        ("P4", True, 0, 1),
        ("P1", False, 1, 1),
        ("P1", False, 2, 2),
        ("P2", False, 2, 2),
        ("P3", False, 2, 1),
        ("P4", False, 5, 1),
        ("P1", True, 2, 3),
        ("P2", True, 2, 3),
        ("P3", True, 2, 2),
        ("P4", True, 2, 2),
        ("P1", True, 100, 3),
        ("P4", False, 100, 1),
    ],
)
def test_escalation_tiers(priority, breached, reopens, expected):
    assert escalation_tier(priority, breached, reopens) == expected


def test_escalation_rejects_unknown_priority():
    with pytest.raises(ValueError):
        escalation_tier("P5", False, 0)


def test_escalation_rejects_negative_reopens():
    with pytest.raises(ValueError):
        escalation_tier("P1", False, -1)


# --- parse_duration ------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("90m", 90),
        ("4h", 240),
        ("1h30m", 90),
        ("2d", 2880),
        ("1d4h", 1680),
        ("1d0h5m", 1445),
        ("1d2h3m", 1563),
        ("1h59m", 119),
        ("60m", 60),
        ("0h60m", 60),
        ("0d0h5m", 5),
        (" 1h30m ", 90),
        ("999m", 999),
    ],
)
def test_parse_duration_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "0m", "0d", "0h0m", "1h60m", "1d60m", "1.5h", "30m1h", "-5m", "1 h", "1H", "1h 30m", "h", "1d2d"],
)
def test_parse_duration_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_module_constant_targets_are_used():
    assert slaclock.TARGETS["P1"] == targets("P1")
    assert len(slaclock.TARGETS) == 4
