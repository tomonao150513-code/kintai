"""チーム対応（P7）: ProjectMembership / scoping / by_user / 休憩控除。"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from attendance.models import Project, ProjectMembership, Task, TimeEntry
from attendance.services import aggregation, scoping

JST = ZoneInfo("Asia/Tokyo")
pytestmark = pytest.mark.django_db


@pytest.fixture
def alice(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pw")


@pytest.fixture
def bob(django_user_model):
    return django_user_model.objects.create_user(username="bob", password="pw")


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_user(username="admin", password="pw", is_staff=True)


def _entry(user, task, day, minutes, break_seconds=0):
    s = datetime(2026, 9, day, 9, 0, tzinfo=JST)
    return TimeEntry.objects.create(
        user=user,
        task=task,
        start_at=s,
        end_at=s + timedelta(minutes=minutes),
        break_seconds=break_seconds,
    )


# --- 休憩控除 ---------------------------------------------------------------------


def test_duration_deducts_break(alice):
    project = Project.objects.create(owner=alice, name="P")
    task = Task.objects.create(project=project, name="T")
    entry = _entry(alice, task, 7, 120, break_seconds=1800)  # 2h - 30m = 1.5h
    assert entry.gross_seconds == 7200
    assert entry.duration_seconds == 5400


def test_clean_rejects_break_longer_than_elapsed(alice):
    project = Project.objects.create(owner=alice, name="P")
    task = Task.objects.create(project=project, name="T")
    s = timezone.now() - timedelta(hours=1)
    entry = TimeEntry(
        user=alice, task=task, start_at=s, end_at=s + timedelta(minutes=30), break_seconds=3600
    )
    with pytest.raises(ValidationError):
        entry.full_clean()


# --- scoping --------------------------------------------------------------------


def test_visible_entries_for_member_and_stranger(alice, bob):
    p_alice = Project.objects.create(owner=alice, name="A")
    t_alice = Task.objects.create(project=p_alice, name="ta")
    _entry(alice, t_alice, 7, 60)

    # bob は無関係 -> alice の記録は見えない
    assert scoping.visible_entries(bob).count() == 0

    # bob をメンバーに追加 -> 見えるようになる
    ProjectMembership.objects.create(project=p_alice, user=bob)
    assert scoping.visible_entries(bob).count() == 1
    assert set(scoping.visible_projects(bob).values_list("name", flat=True)) == {"A"}


def test_visible_entries_for_admin_is_everything(admin, alice):
    p = Project.objects.create(owner=alice, name="A")
    t = Task.objects.create(project=p, name="ta")
    _entry(alice, t, 7, 60)
    assert scoping.is_admin(admin) is True
    assert scoping.visible_entries(admin).count() == 1


def test_can_see_team(alice, bob, admin):
    assert scoping.can_see_team(admin) is True
    assert scoping.can_see_team(alice) is False
    p = Project.objects.create(owner=alice, name="A")
    ProjectMembership.objects.create(project=p, user=bob)
    assert scoping.can_see_team(bob) is True


# --- by_user 集計 --------------------------------------------------------------


def test_by_user_breakdown(alice, bob):
    p = Project.objects.create(owner=alice, name="A")
    t = Task.objects.create(project=p, name="ta")
    ProjectMembership.objects.create(project=p, user=bob)
    _entry(alice, t, 7, 180)  # 10800
    _entry(bob, t, 7, 60)  # 3600
    result = aggregation.by_user(scoping.visible_entries(alice), date(2026, 9, 7), date(2026, 9, 7))
    assert result["total_seconds"] == 14400
    assert [i["name"] for i in result["items"]] == ["alice", "bob"]
    assert result["items"][0]["ratio"] == round(10800 / 14400, 4)


# --- レポート / API のチーム表示 ----------------------------------------------


def test_report_team_view_user_axis(client, admin, alice):
    p = Project.objects.create(owner=alice, name="A")
    t = Task.objects.create(project=p, name="ta")
    _entry(alice, t, 7, 60)
    client.force_login(admin)
    resp = client.get("/report/?scope=team&axis=user&from=2026-09-01&to=2026-09-30")
    assert resp.status_code == 200
    assert resp.context["axis"] == "user"
    assert resp.context["team_view"] is True
    assert resp.context["breakdown"]["items"][0]["name"] == "alice"


def test_report_user_axis_denied_without_team_scope(client, alice):
    client.force_login(alice)
    resp = client.get("/report/?axis=user")
    assert resp.context["axis"] == "project"  # 非チームでは user 軸は無効


def test_stats_by_user_endpoint(client, admin, alice):
    p = Project.objects.create(owner=alice, name="A")
    t = Task.objects.create(project=p, name="ta")
    _entry(alice, t, 7, 120)
    client.force_login(admin)
    body = client.get("/api/stats/by-user/?from=2026-09-01&to=2026-09-30").json()
    assert body["total_seconds"] == 7200
    assert body["items"][0]["name"] == "alice"
    assert "from" in body
