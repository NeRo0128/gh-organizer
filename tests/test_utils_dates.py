# tests/test_utils_dates.py
"""Tests de format_date con tiempo congelado."""

from datetime import UTC, datetime

import pytest

import github_organizer.utils.dates as dates_module
from github_organizer.utils.dates import format_date


@pytest.fixture
def freeze_time(monkeypatch: pytest.MonkeyPatch):
    """Congela datetime.now() a 2025-06-15 12:00 UTC."""
    fixed_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(dates_module, "datetime", FakeDateTime)
    return fixed_now


def test_empty_string_returns_dash() -> None:
    assert format_date("") == "—"


def test_invalid_iso_returns_input() -> None:
    assert format_date("no es fecha") == "no es fecha"


def test_minutes_ago(freeze_time) -> None:
    assert format_date("2025-06-15T11:50:00+00:00") == "hace unos minutos"


def test_hours_ago(freeze_time) -> None:
    assert format_date("2025-06-15T07:00:00+00:00") == "hace 5h"


def test_yesterday(freeze_time) -> None:
    assert format_date("2025-06-14T12:00:00+00:00") == "ayer"


def test_days_ago(freeze_time) -> None:
    assert format_date("2025-06-10T12:00:00+00:00") == "hace 5 días"


def test_one_month_singular(freeze_time) -> None:
    # 35 días → 1 mes
    assert format_date("2025-05-11T12:00:00+00:00") == "hace 1 mes"


def test_months_plural(freeze_time) -> None:
    # 120 días → 4 meses
    assert format_date("2025-02-15T12:00:00+00:00") == "hace 4 meses"


def test_one_year_singular(freeze_time) -> None:
    # 400 días → 1 año
    assert format_date("2024-05-11T12:00:00+00:00") == "hace 1 año"


def test_years_plural(freeze_time) -> None:
    # 800 días → 2 años
    assert format_date("2023-04-07T12:00:00+00:00") == "hace 2 años"
