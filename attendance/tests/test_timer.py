"""services/timer.py の状態遷移（docs/domain-logic.md §1、coding-guidelines §6）。"""

from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.exceptions import (
    TaskNotStartable,
    TimerAlreadyRunning,
    TimerNotRunning,
)
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


@pytest.fixture
def task2(project):
    return Task.objects.create(project=project, name="T2")


def test_start_creates_running_entry(user, task):
    entry = timer.start(user, task)
    assert entry.is_running
    assert entry.source == TimeEntry.Source.TIMER
    assert timer.get_running(user) == entry


def test_start_when_already_running_raises(user, task, task2):
    timer.start(user, task)
    with pytest.raises(TimerAlreadyRunning):
        timer.start(user, task2)
    assert TimeEntry.objects.filter(user=user).count() == 1


def test_start_rejects_done_task(user, project):
    done = Task.objects.create(project=project, name="done", status=Task.Status.DONE)
    with pytest.raises(TaskNotStartable):
        timer.start(user, done)


def test_stop_confirms_entry_and_returns_it(user, task):
    t0 = timezone.now() - timedelta(hours=1, minutes=30, seconds=24)
    timer.start(user, task, now=t0)
    entry = timer.stop(user, now=t0 + timedelta(hours=1, minutes=30, seconds=24))
    assert not entry.is_running
    assert entry.duration_seconds == 5424
    assert timer.get_running(user) is None


def test_stop_when_idle_raises(user):
    with pytest.raises(TimerNotRunning):
        timer.stop(user)


def test_switch_stops_current_and_starts_new(user, task, task2):
    t0 = timezone.now() - timedelta(minutes=20)
    timer.start(user, task, now=t0)
    stopped, started = timer.switch(user, task2, now=t0 + timedelta(minutes=20))
    assert stopped.task == task
    assert not stopped.is_running
    assert stopped.duration_seconds == 20 * 60
    assert started.task == task2
    assert started.is_running
    assert timer.get_running(user) == started
    assert TimeEntry.objects.filter(user=user).count() == 2


def test_switch_when_idle_just_starts(user, task):
    stopped, started = timer.switch(user, task)
    assert stopped is None
    assert started.is_running
    assert TimeEntry.objects.filter(user=user).count() == 1


def test_switch_to_bad_task_rolls_back_stop(user, task, project):
    """切り替え先が開始不可なら、現在のタイマー終了ごとロールバックされる（atomic）。"""
    done = Task.objects.create(project=project, name="done", status=Task.Status.DONE)
    running = timer.start(user, task)
    with pytest.raises(TaskNotStartable):
        timer.switch(user, done)
    running.refresh_from_db()
    assert running.is_running  # 終了が取り消されている
