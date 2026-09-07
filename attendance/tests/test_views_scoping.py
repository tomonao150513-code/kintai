"""ビューのアクセス制御（他ユーザーのレコードは 404、認証必須）。docs/screens.md。"""

from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.models import Project, Task, TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user(username="owner", password="pw")


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(username="other", password="pw")


@pytest.fixture
def project(owner):
    return Project.objects.create(owner=owner, name="P")


@pytest.fixture
def task(project):
    return Task.objects.create(project=project, name="T")


def test_login_required_redirects(client):
    resp = client.get("/entries/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


def test_other_users_project_is_404(client, other, project):
    client.force_login(other)
    assert client.get(f"/projects/{project.pk}/edit/").status_code == 404
    assert client.get(f"/projects/{project.pk}/tasks/").status_code == 404


def test_other_users_task_is_404(client, other, task):
    client.force_login(other)
    assert client.get(f"/tasks/{task.pk}/edit/").status_code == 404


def test_other_users_entry_is_404(client, owner, other, task):
    entry = TimeEntry.objects.create(
        user=owner,
        task=task,
        start_at=timezone.now() - timedelta(hours=2),
        end_at=timezone.now() - timedelta(hours=1),
    )
    client.force_login(other)
    assert client.get(f"/entries/{entry.pk}/edit/").status_code == 404


def test_entry_list_filters_by_date(client, owner, task):
    client.force_login(owner)
    TimeEntry.objects.create(
        user=owner,
        task=task,
        start_at=timezone.datetime(2026, 1, 15, 9, 0, tzinfo=timezone.get_current_timezone()),
        end_at=timezone.datetime(2026, 1, 15, 10, 0, tzinfo=timezone.get_current_timezone()),
    )
    in_range = client.get("/entries/?date_from=2026-01-01&date_to=2026-01-31")
    assert in_range.status_code == 200
    assert in_range.context["result_count"] == 1
    out_range = client.get("/entries/?date_from=2026-02-01&date_to=2026-02-28")
    assert out_range.context["result_count"] == 0


def test_running_entry_cannot_be_edited(client, owner, task):
    client.force_login(owner)
    running = TimeEntry.objects.create(
        user=owner, task=task, start_at=timezone.now() - timedelta(minutes=5)
    )
    resp = client.get(f"/entries/{running.pk}/edit/", follow=True)
    assert resp.redirect_chain
    assert resp.request["PATH_INFO"] == "/entries/"
