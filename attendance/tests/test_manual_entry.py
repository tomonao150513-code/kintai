"""services/timer.py の手動追加・編集・削除（docs/domain-logic.md §2）。"""

from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.exceptions import EntryValidationError
from attendance.models import Project, Task, TimeEntry
from attendance.services import timer

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="u1", password="pw")


@pytest.fixture
def project(user):
    return Project.objects.create(owner=user, name="P")


@pytest.fixture
def task(project):
    return Task.objects.create(project=project, name="T1")


def test_create_manual_entry(user, task):
    start = timezone.now() - timedelta(hours=2)
    end = start + timedelta(hours=1, minutes=30, seconds=24)
    entry = timer.create_manual_entry(user, task, start, end, note="あとから入力")
    assert entry.pk is not None
    assert entry.source == TimeEntry.Source.MANUAL
    assert entry.duration_seconds == 5424
    assert entry.note == "あとから入力"


def test_create_manual_entry_rejects_future_start(user, task):
    start = timezone.now() + timedelta(hours=1)
    with pytest.raises(EntryValidationError):
        timer.create_manual_entry(user, task, start, start + timedelta(hours=1))


def test_create_manual_entry_rejects_end_before_start(user, task):
    start = timezone.now() - timedelta(hours=1)
    with pytest.raises(EntryValidationError):
        timer.create_manual_entry(user, task, start, start - timedelta(minutes=1))


def test_create_manual_entry_rejects_overlap(user, task):
    base = timezone.now() - timedelta(hours=5)
    timer.create_manual_entry(user, task, base, base + timedelta(hours=1))
    with pytest.raises(EntryValidationError):
        timer.create_manual_entry(
            user, task, base + timedelta(minutes=30), base + timedelta(hours=2)
        )


def test_update_entry(user, task):
    start = timezone.now() - timedelta(hours=3)
    entry = timer.create_manual_entry(user, task, start, start + timedelta(hours=1))
    updated = timer.update_entry(entry, end_at=start + timedelta(hours=2), note="のばした")
    assert updated.duration_seconds == 7200
    assert updated.note == "のばした"
    assert updated.source == TimeEntry.Source.MANUAL


def test_update_entry_cannot_clear_end(user, task):
    start = timezone.now() - timedelta(hours=3)
    entry = timer.create_manual_entry(user, task, start, start + timedelta(hours=1))
    entry.end_at = None
    with pytest.raises(EntryValidationError):
        timer.update_entry(entry)


def test_delete_entry(user, task):
    start = timezone.now() - timedelta(hours=3)
    entry = timer.create_manual_entry(user, task, start, start + timedelta(hours=1))
    timer.delete_entry(entry)
    assert not TimeEntry.objects.filter(pk=entry.pk).exists()
