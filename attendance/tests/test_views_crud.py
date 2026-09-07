"""ビューのハッピーパス / 画面挙動（0 件・不正入力・例外時）。"""

from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.models import Project, Task, TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="u1", password="pw")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def project(user):
    return Project.objects.create(owner=user, name="P")


@pytest.fixture
def task(project):
    return Task.objects.create(project=project, name="T", status=Task.Status.DOING)


def test_dashboard_renders_for_empty_account(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 200
    assert "計測できるタスクがありません" in resp.content.decode()


def test_project_create_and_archive_flow(auth_client, user):
    resp = auth_client.post(
        "/projects/new/", {"name": "新規PJ", "description": "", "color": "#4F46E5"}, follow=True
    )
    assert resp.status_code == 200
    project = Project.objects.get(name="新規PJ")
    assert project.owner == user
    auth_client.post(f"/projects/{project.pk}/archive/")
    project.refresh_from_db()
    assert project.is_archived is True
    auth_client.post(f"/projects/{project.pk}/archive/")
    project.refresh_from_db()
    assert project.is_archived is False


def test_task_create_and_archive_flow(auth_client, project):
    auth_client.post(
        f"/projects/{project.pk}/tasks/new/",
        {"name": "新規タスク", "description": "", "status": "todo"},
    )
    task = Task.objects.get(name="新規タスク")
    assert task.project == project
    auth_client.post(f"/tasks/{task.pk}/archive/")
    task.refresh_from_db()
    assert task.is_archived is True


def test_timer_start_stop_via_views(auth_client, user, task):
    auth_client.post("/timer/start/", {"task": task.pk})
    assert TimeEntry.objects.filter(user=user, end_at__isnull=True).count() == 1
    resp = auth_client.post("/timer/stop/", follow=True)
    body = resp.content.decode()
    assert "お疲れ様でした" in body
    assert TimeEntry.objects.filter(user=user, end_at__isnull=True).count() == 0


def test_timer_start_without_task_shows_error(auth_client):
    resp = auth_client.post("/timer/start/", {}, follow=True)
    assert "タスクを選択してください" in resp.content.decode()


def test_manual_entry_create_happy_path(auth_client, user, task):
    start = timezone.localtime(timezone.now() - timedelta(hours=2))
    end = start + timedelta(hours=1)
    resp = auth_client.post(
        "/entries/new/",
        {
            "task": task.pk,
            "start_at": start.strftime("%Y-%m-%dT%H:%M"),
            "end_at": end.strftime("%Y-%m-%dT%H:%M"),
            "note": "テスト",
        },
        follow=True,
    )
    assert resp.status_code == 200
    assert TimeEntry.objects.filter(user=user, source=TimeEntry.Source.MANUAL).count() == 1


def test_manual_entry_overlap_shows_form_error(auth_client, user, task):
    base = timezone.now() - timedelta(hours=5)
    TimeEntry.objects.create(user=user, task=task, start_at=base, end_at=base + timedelta(hours=2))
    s = timezone.localtime(base + timedelta(hours=1))
    resp = auth_client.post(
        "/entries/new/",
        {
            "task": task.pk,
            "start_at": s.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (s + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "note": "",
        },
    )
    assert resp.status_code == 200
    assert "同じ時間帯に別の記録があります" in resp.content.decode()


def test_entry_list_empty_period(auth_client):
    resp = auth_client.get("/entries/?date_from=2000-01-01&date_to=2000-01-31")
    assert resp.status_code == 200
    assert resp.context["result_count"] == 0
    assert "記録がありません" in resp.content.decode()


def test_report_renders_with_no_data(auth_client):
    resp = auth_client.get("/report/?preset=month")
    assert resp.status_code == 200
    assert resp.context["total_seconds"] == 0
    assert "この期間の記録はありません" in resp.content.decode()


def test_report_bad_dates_fall_back_to_month(auth_client):
    resp = auth_client.get("/report/?from=not-a-date")
    assert resp.status_code == 200
    assert resp.context["date_from"].day == 1


def test_timer_switch_via_view(auth_client, user, project):
    t1 = Task.objects.create(project=project, name="s1", status=Task.Status.DOING)
    t2 = Task.objects.create(project=project, name="s2", status=Task.Status.DOING)
    auth_client.post("/timer/start/", {"task": t1.pk})
    resp = auth_client.post("/timer/switch/", {"task": t2.pk}, follow=True)
    body = resp.content.decode()
    assert "お疲れ様でした" in body  # 旧タイマーの終了メッセージ
    running = TimeEntry.objects.get(user=user, end_at__isnull=True)
    assert running.task == t2
    assert TimeEntry.objects.filter(user=user).count() == 2


def test_entry_edit_and_delete_via_view(auth_client, user, task):
    base = timezone.now() - timedelta(hours=4)
    entry = TimeEntry.objects.create(
        user=user, task=task, start_at=base, end_at=base + timedelta(hours=1)
    )
    s = timezone.localtime(base)
    auth_client.post(
        f"/entries/{entry.pk}/edit/",
        {
            "task": task.pk,
            "start_at": s.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (s + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
            "note": "編集後",
        },
        follow=True,
    )
    entry.refresh_from_db()
    assert entry.duration_seconds == 3 * 3600
    assert entry.note == "編集後"
    auth_client.post(f"/entries/{entry.pk}/delete/")
    assert not TimeEntry.objects.filter(pk=entry.pk).exists()


def test_edit_forms_render(auth_client, project, task):
    assert auth_client.get(f"/projects/{project.pk}/edit/").status_code == 200
    assert auth_client.get(f"/tasks/{task.pk}/edit/").status_code == 200


def test_running_entry_delete_blocked(auth_client, user, task):
    running = TimeEntry.objects.create(
        user=user, task=task, start_at=timezone.now() - timedelta(minutes=5)
    )
    resp = auth_client.post(f"/entries/{running.pk}/delete/", follow=True)
    assert TimeEntry.objects.filter(pk=running.pk).exists()
    assert "計測中の記録は削除できません" in resp.content.decode()
