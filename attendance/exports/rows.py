"""明細行の組み立て（CSV / Excel 共用）。docs/export-spec.md。"""

from django.utils import timezone

from attendance.models import TimeEntry
from attendance.services import aggregation
from attendance.services.formatting import format_hms_colon, format_hours_decimal

COLUMNS = [
    "日付",
    "開始時刻",
    "終了時刻",
    "実働秒数",
    "実働時間(HH:MM:SS)",
    "実働時間(h)",
    "プロジェクト",
    "タスク",
    "タスク状態",
    "メモ",
    "入力元",
]

NUMERIC_COLUMNS = {"実働秒数", "実働時間(h)"}


def completed_entries(user, date_from, date_to, *, project=None, task=None):
    """対象データ: 本人の完了記録のみ、開始日で期間絞り、start_at 昇順。"""
    start_dt, end_dt = aggregation.datetime_range(date_from, date_to)
    qs = (
        TimeEntry.objects.filter(
            user=user,
            end_at__isnull=False,
            start_at__gte=start_dt,
            start_at__lt=end_dt,
        )
        .select_related("task", "task__project")
        .order_by("start_at")
    )
    if project is not None:
        qs = qs.filter(task__project=project)
    if task is not None:
        qs = qs.filter(task=task)
    return qs


def _entry_row(entry):
    local_start = timezone.localtime(entry.start_at)
    local_end = timezone.localtime(entry.end_at)
    seconds = entry.duration_seconds
    return {
        "日付": local_start.strftime("%Y-%m-%d"),
        "開始時刻": local_start.strftime("%H:%M:%S"),
        "終了時刻": local_end.strftime("%H:%M:%S"),
        "実働秒数": seconds,
        "実働時間(HH:MM:SS)": format_hms_colon(seconds),
        "実働時間(h)": format_hours_decimal(seconds),
        "プロジェクト": entry.task.project.name,
        "タスク": entry.task.name,
        "タスク状態": entry.task.get_status_display(),
        "メモ": entry.note.replace("\r", " ").replace("\n", " "),
        "入力元": entry.get_source_display(),
    }


def build_rows(entries):
    """(明細行のリスト, 合計行) を返す。合計行は列1〜3 空・列7 に "合計"。"""
    rows = [_entry_row(e) for e in entries]
    total = sum(r["実働秒数"] for r in rows)
    total_row = dict.fromkeys(COLUMNS, "")
    total_row["実働秒数"] = total
    total_row["実働時間(HH:MM:SS)"] = format_hms_colon(total)
    total_row["実働時間(h)"] = format_hours_decimal(total)
    total_row["プロジェクト"] = "合計"
    return rows, total_row


def project_summary(rows):
    """集計シート用: プロジェクト別合計秒（seconds 降順）と総合計。"""
    per_project: dict = {}
    for r in rows:
        per_project[r["プロジェクト"]] = per_project.get(r["プロジェクト"], 0) + r["実働秒数"]
    grand = sum(per_project.values())
    ordered = sorted(per_project.items(), key=lambda kv: kv[1], reverse=True)
    return ordered, grand
