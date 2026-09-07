"""services/aggregation.py（docs/domain-logic.md §4、ADR-0003 開始日基準）。"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from attendance.models import Project, Task, TimeEntry
from attendance.services import aggregation

JST = ZoneInfo("Asia/Tokyo")
pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="u1", password="pw")


@pytest.fixture
def task(user):
    project = Project.objects.create(owner=user, name="P")
    return Task.objects.create(project=project, name="T")


def _entry(user, task, start, minutes):
    return TimeEntry.objects.create(
        user=user, task=task, start_at=start, end_at=start + timedelta(minutes=minutes)
    )


def test_period_bounds_today():
    assert aggregation.period_bounds("today", date(2026, 9, 7)) == (
        date(2026, 9, 7),
        date(2026, 9, 7),
    )


def test_period_bounds_week_is_monday_to_sunday():
    # 2026-09-07 は月曜
    assert aggregation.period_bounds("week", date(2026, 9, 7)) == (
        date(2026, 9, 7),
        date(2026, 9, 13),
    )
    # 2026-09-09 は水曜 -> 同じ週
    assert aggregation.period_bounds("week", date(2026, 9, 9)) == (
        date(2026, 9, 7),
        date(2026, 9, 13),
    )


def test_period_bounds_month():
    assert aggregation.period_bounds("month", date(2026, 9, 20)) == (
        date(2026, 9, 1),
        date(2026, 9, 30),
    )
    assert aggregation.period_bounds("month", date(2026, 12, 5)) == (
        date(2026, 12, 1),
        date(2026, 12, 31),
    )


def test_period_bounds_unknown_raises():
    with pytest.raises(ValueError):
        aggregation.period_bounds("year")


def test_daily_totals_zero_fills_empty_days(user, task):
    _entry(user, task, datetime(2026, 9, 7, 9, 0, tzinfo=JST), 60)
    _entry(user, task, datetime(2026, 9, 9, 13, 0, tzinfo=JST), 30)
    result = aggregation.daily_totals(user, date(2026, 9, 7), date(2026, 9, 10))
    assert result == [
        {"date": date(2026, 9, 7), "seconds": 3600},
        {"date": date(2026, 9, 8), "seconds": 0},
        {"date": date(2026, 9, 9), "seconds": 1800},
        {"date": date(2026, 9, 10), "seconds": 0},
    ]


def test_day_crossing_entry_counts_on_start_date(user, task):
    # 23:30 JST 開始、翌 01:00 JST 終了（90 分）
    start = datetime(2026, 9, 7, 23, 30, tzinfo=JST)
    _entry(user, task, start, 90)
    result = aggregation.daily_totals(user, date(2026, 9, 7), date(2026, 9, 8))
    assert result[0] == {"date": date(2026, 9, 7), "seconds": 5400}
    assert result[1] == {"date": date(2026, 9, 8), "seconds": 0}


def test_total_seconds_excludes_running(user, task):
    _entry(user, task, datetime(2026, 9, 7, 9, 0, tzinfo=JST), 60)
    TimeEntry.objects.create(
        user=user, task=task, start_at=timezone.now() - timedelta(minutes=10)
    )  # 実行中
    assert aggregation.total_seconds(user, date(2026, 9, 7), date(2026, 9, 7)) == 3600


def test_total_seconds_range_is_inclusive_of_both_ends(user, task):
    _entry(user, task, datetime(2026, 9, 1, 0, 0, tzinfo=JST), 60)
    _entry(user, task, datetime(2026, 9, 30, 23, 0, tzinfo=JST), 30)
    assert aggregation.total_seconds(user, date(2026, 9, 1), date(2026, 9, 30)) == 3600 + 1800
    # 範囲外
    assert aggregation.total_seconds(user, date(2026, 9, 2), date(2026, 9, 29)) == 0
