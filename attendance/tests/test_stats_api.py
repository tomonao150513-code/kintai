"""グラフ用 JSON API（docs/api-charts.md）。"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from attendance.models import Project, Task, TimeEntry

JST = ZoneInfo("Asia/Tokyo")
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(username="owner", password="pw")


@pytest.fixture
def data(owner):
    project = Project.objects.create(owner=owner, name="A", color="#123456")
    task = Task.objects.create(project=project, name="t1")
    TimeEntry.objects.create(
        user=owner,
        task=task,
        start_at=datetime(2026, 9, 7, 9, 0, tzinfo=JST),
        end_at=datetime(2026, 9, 7, 10, 0, tzinfo=JST),
    )
    return project, task


def test_stats_requires_login(client):
    resp = client.get("/api/stats/daily/")
    assert resp.status_code == 302


def test_stats_daily_zero_fills_and_no_store(client, owner, data):
    client.force_login(owner)
    resp = client.get("/api/stats/daily/?from=2026-09-06&to=2026-09-08")
    assert resp.status_code == 200
    assert resp["Cache-Control"] == "no-store"
    body = resp.json()
    assert body["unit"] == "day"
    assert body["total_seconds"] == 3600
    assert body["series"] == [
        {"date": "2026-09-06", "seconds": 0},
        {"date": "2026-09-07", "seconds": 3600},
        {"date": "2026-09-08", "seconds": 0},
    ]


def test_stats_daily_invalid_date_is_400(client, owner):
    client.force_login(owner)
    assert client.get("/api/stats/daily/?from=nope").status_code == 400
    assert client.get("/api/stats/daily/?from=2026-09-10&to=2026-09-01").status_code == 400


def test_stats_by_project(client, owner, data):
    client.force_login(owner)
    body = client.get("/api/stats/by-project/?from=2026-09-01&to=2026-09-30").json()
    assert body["total_seconds"] == 3600
    assert body["items"][0]["name"] == "A"
    assert body["items"][0]["color"] == "#123456"
    assert body["items"][0]["ratio"] == 1.0


def test_stats_by_task_scoped_to_user(client, owner, data, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="pw")
    client.force_login(other)
    body = client.get("/api/stats/by-task/?from=2026-09-01&to=2026-09-30").json()
    assert body["items"] == []
    assert body["total_seconds"] == 0
