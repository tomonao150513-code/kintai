"""TimeEntry の制約・バリデーション（docs/data-model.md §3、coding-guidelines §6）。"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from attendance.models import Project, Task, TimeEntry

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(username="u1", password="pw")


@pytest.fixture
def task(user):
    project = Project.objects.create(owner=user, name="P")
    return Task.objects.create(project=project, name="T")


def test_only_one_running_timer_per_user(user, task):
    now = timezone.now()
    TimeEntry.objects.create(user=user, task=task, start_at=now - timedelta(minutes=10))
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TimeEntry.objects.create(user=user, task=task, start_at=now)


def test_second_running_timer_allowed_for_other_user(user, task):
    other = User.objects.create_user(username="u2", password="pw")
    now = timezone.now()
    TimeEntry.objects.create(user=user, task=task, start_at=now - timedelta(minutes=10))
    # 別ユーザーなら実行中タイマーを持てる
    TimeEntry.objects.create(user=other, task=task, start_at=now)


def test_multiple_completed_entries_allowed(user, task):
    now = timezone.now()
    TimeEntry.objects.create(
        user=user,
        task=task,
        start_at=now - timedelta(hours=3),
        end_at=now - timedelta(hours=2),
    )
    TimeEntry.objects.create(
        user=user,
        task=task,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
    )


def test_end_before_start_rejected_by_check_constraint(user, task):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TimeEntry.objects.create(
                user=user, task=task, start_at=now, end_at=now - timedelta(minutes=5)
            )


def test_clean_rejects_end_equal_to_start(user, task):
    now = timezone.now()
    entry = TimeEntry(user=user, task=task, start_at=now, end_at=now)
    with pytest.raises(ValidationError):
        entry.full_clean()


def test_clean_rejects_overlap_with_existing_entry(user, task):
    now = timezone.now()
    TimeEntry.objects.create(
        user=user,
        task=task,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
    )
    overlapping = TimeEntry(
        user=user,
        task=task,
        start_at=now - timedelta(minutes=90),
        end_at=now - timedelta(minutes=30),
    )
    with pytest.raises(ValidationError):
        overlapping.full_clean()


def test_clean_allows_adjacent_non_overlapping_entry(user, task):
    now = timezone.now()
    TimeEntry.objects.create(
        user=user,
        task=task,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
    )
    adjacent = TimeEntry(
        user=user,
        task=task,
        start_at=now - timedelta(hours=1),
        end_at=now,
    )
    adjacent.full_clean()  # 例外が出なければ OK


def test_duration_seconds_is_not_rounded(user, task):
    start = timezone.now()
    entry = TimeEntry(user=user, task=task, start_at=start, end_at=start + timedelta(seconds=5424))
    assert entry.duration_seconds == 5424
    assert entry.is_running is False


def test_running_entry_duration_uses_now(user, task):
    entry = TimeEntry.objects.create(
        user=user, task=task, start_at=timezone.now() - timedelta(seconds=30)
    )
    assert entry.is_running is True
    assert entry.duration_seconds >= 30


def test_project_name_unique_per_owner(user):
    Project.objects.create(owner=user, name="dup")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Project.objects.create(owner=user, name="dup")


def test_task_name_unique_per_project(user):
    project = Project.objects.create(owner=user, name="P2")
    Task.objects.create(project=project, name="dup")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Task.objects.create(project=project, name="dup")


def test_task_is_selectable(user):
    project = Project.objects.create(owner=user, name="P3")
    todo = Task.objects.create(project=project, name="todo")
    done = Task.objects.create(project=project, name="done", status=Task.Status.DONE)
    archived = Task.objects.create(project=project, name="arch", is_archived=True)
    assert todo.is_selectable is True
    assert done.is_selectable is False
    assert archived.is_selectable is False
