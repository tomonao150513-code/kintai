"""打刻の状態遷移。docs/domain-logic.md §1。

状態は IDLE（実行中タイマー無し）/ RUNNING（`end_at IS NULL` がちょうど 1 件）のみ。
すべて transaction.atomic。書き込み系は実行中行を select_for_update で取得して直列化する。
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from attendance.exceptions import (
    EntryValidationError,
    TaskNotStartable,
    TimerAlreadyRunning,
    TimerNotRunning,
)
from attendance.models import TimeEntry


def get_running(user, *, for_update=False):
    """実行中タイマー（`end_at IS NULL`）を返す。無ければ None。"""
    qs = TimeEntry.objects.filter(user=user, end_at__isnull=True)
    if for_update:
        qs = qs.select_for_update()
    return qs.first()


def _full_clean(entry):
    try:
        entry.full_clean()
    except ValidationError as exc:
        raise EntryValidationError(
            "; ".join(m for msgs in exc.message_dict.values() for m in msgs)
            or "入力内容に問題があります。",
            errors=exc.message_dict,
        ) from exc


@transaction.atomic
def start(user, task, *, now=None):
    """IDLE のとき実行中タイマーを作る。RUNNING なら TimerAlreadyRunning。"""
    if get_running(user, for_update=True) is not None:
        raise TimerAlreadyRunning()
    if not task.is_selectable:
        raise TaskNotStartable()
    entry = TimeEntry(
        user=user,
        task=task,
        start_at=now or timezone.now(),
        source=TimeEntry.Source.TIMER,
    )
    _full_clean(entry)
    try:
        entry.save()
    except IntegrityError as exc:  # 実行中タイマーの競合（ADR-0005）
        raise TimerAlreadyRunning() from exc
    return entry


@transaction.atomic
def stop(user, *, now=None):
    """RUNNING のとき実行中タイマーを確定して返す。IDLE なら TimerNotRunning。"""
    entry = get_running(user, for_update=True)
    if entry is None:
        raise TimerNotRunning()
    entry.end_at = now or timezone.now()
    _full_clean(entry)
    entry.save()
    return entry


@transaction.atomic
def switch(user, task, *, now=None):
    """RUNNING なら stop してから start、IDLE なら start のみ。戻り値 (stopped|None, started)。"""
    moment = now or timezone.now()
    stopped = None
    if get_running(user, for_update=True) is not None:
        stopped = stop(user, now=moment)
    started = start(user, task, now=moment)
    return stopped, started


# --- 手動追加・編集（docs/domain-logic.md §2） ---


def create_manual_entry(user, task, start_at, end_at, note="", *, break_seconds=0):
    """打刻し忘れ対応。source=MANUAL で作成。start_at/end_at とも必須、未来不可。"""
    if end_at is None or start_at is None:
        raise EntryValidationError("開始時刻と終了時刻の両方を入力してください。")
    if start_at > timezone.now():
        raise EntryValidationError("開始時刻に未来の日時は指定できません。")
    entry = TimeEntry(
        user=user,
        task=task,
        start_at=start_at,
        end_at=end_at,
        break_seconds=break_seconds or 0,
        note=note or "",
        source=TimeEntry.Source.MANUAL,
    )
    _full_clean(entry)
    entry.save()
    return entry


def update_entry(entry, *, task=None, start_at=None, end_at=None, note=None, break_seconds=None):
    """指定フィールドのみ差し替えて保存。source は維持。実行中に戻すことは不可。"""
    if task is not None:
        entry.task = task
    if start_at is not None:
        entry.start_at = start_at
    if end_at is not None:
        entry.end_at = end_at
    if note is not None:
        entry.note = note
    if break_seconds is not None:
        entry.break_seconds = break_seconds
    if entry.end_at is None:
        raise EntryValidationError("終了時刻は必須です（実行中には戻せません）。")
    if entry.start_at > timezone.now():
        raise EntryValidationError("開始時刻に未来の日時は指定できません。")
    _full_clean(entry)
    entry.save()
    return entry


def delete_entry(entry):
    """物理削除（関連は無い）。"""
    entry.delete()
