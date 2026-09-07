"""集計。docs/domain-logic.md §4。

対象は完了記録のみ（`end_at IS NOT NULL`）。基準日は開始時刻の JST 日付（ADR-0003）。
P2 では period_bounds / total_seconds / daily_totals のみ使う。by_project / by_task は P4。
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from attendance.models import TimeEntry

JST = ZoneInfo("Asia/Tokyo")


def period_bounds(kind, ref=None):
    """`kind` に対応する [date_from, date_to]（両端含む）を返す。週は月曜〜日曜。"""
    ref = ref or timezone.localdate()
    if kind == "today":
        return ref, ref
    if kind == "week":
        monday = ref - timedelta(days=ref.weekday())
        return monday, monday + timedelta(days=6)
    if kind == "month":
        first = ref.replace(day=1)
        if first.month == 12:
            nxt = first.replace(year=first.year + 1, month=1)
        else:
            nxt = first.replace(month=first.month + 1)
        return first, nxt - timedelta(days=1)
    raise ValueError(f"unknown period kind: {kind!r}")


def datetime_range(date_from, date_to):
    """[date_from 00:00 JST, date_to+1 00:00 JST) の半開区間（aware datetime のタプル）。"""
    return (
        datetime.combine(date_from, time.min, tzinfo=JST),
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=JST),
    )


def _completed_in_range(user, date_from, date_to):
    start_dt, end_dt = datetime_range(date_from, date_to)
    return TimeEntry.objects.filter(
        user=user,
        end_at__isnull=False,
        start_at__gte=start_dt,
        start_at__lt=end_dt,
    )


def total_seconds(user, date_from, date_to):
    """期間内（開始日基準）の完了記録の実働秒合計。丸めなし。"""
    return sum(e.duration_seconds for e in _completed_in_range(user, date_from, date_to))


def daily_totals(user, date_from, date_to):
    """日別合計。記録ゼロの日も 0 で埋める。[{"date": date, "seconds": int}, ...]。"""
    buckets: dict = {}
    for entry in _completed_in_range(user, date_from, date_to):
        d = entry.work_date
        buckets[d] = buckets.get(d, 0) + entry.duration_seconds
    out = []
    cur = date_from
    while cur <= date_to:
        out.append({"date": cur, "seconds": buckets.get(cur, 0)})
        cur += timedelta(days=1)
    return out


def _breakdown(rows):
    """rows（seconds を持つ dict のリスト）を seconds 降順にし ratio を付けて返す。"""
    total = sum(r["seconds"] for r in rows)
    if not total:
        return {"total_seconds": 0, "items": []}
    items = sorted(rows, key=lambda r: r["seconds"], reverse=True)
    for r in items:
        r["ratio"] = round(r["seconds"] / total, 4)
    return {"total_seconds": total, "items": items}


def by_project(user, date_from, date_to):
    """プロジェクト別内訳（docs/api-charts.md）。"""
    buckets: dict = {}
    qs = _completed_in_range(user, date_from, date_to).select_related("task__project")
    for entry in qs:
        project = entry.task.project
        row = buckets.setdefault(
            project.id,
            {
                "project_id": project.id,
                "name": project.name,
                "color": project.color,
                "seconds": 0,
            },
        )
        row["seconds"] += entry.duration_seconds
    return _breakdown(list(buckets.values()))


def by_task(user, date_from, date_to, project=None):
    """タスク別内訳。project 指定で当該プロジェクト内に限定。"""
    qs = _completed_in_range(user, date_from, date_to).select_related("task__project")
    if project is not None:
        qs = qs.filter(task__project=project)
    buckets: dict = {}
    for entry in qs:
        task = entry.task
        row = buckets.setdefault(
            task.id,
            {
                "task_id": task.id,
                "name": task.name,
                "project_id": task.project_id,
                "project_name": task.project.name,
                "color": task.project.color,
                "seconds": 0,
            },
        )
        row["seconds"] += entry.duration_seconds
    return _breakdown(list(buckets.values()))
