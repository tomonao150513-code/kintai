from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from attendance.exceptions import TimerError
from attendance.exports import csv_response, xlsx_response
from attendance.exports.rows import completed_entries
from attendance.forms import (
    EntryFilterForm,
    ExportForm,
    ProjectForm,
    TaskForm,
    TimeEntryForm,
)
from attendance.models import Project, Task, TimeEntry
from attendance.services import aggregation
from attendance.services import timer as timer_service
from attendance.services.formatting import greeting_message

# --- ダッシュボード / 打刻（P2） ---------------------------------------------------------


def dashboard(request):
    """ダッシュボード（S-02）。実行中タイマー / 今日・今週の合計 / 開始フォーム。"""
    running = timer_service.get_running(request.user)
    today = aggregation.period_bounds("today")
    week = aggregation.period_bounds("week")

    tasks = (
        Task.objects.filter(project__owner=request.user)
        .select_related("project")
        .order_by("project__name", "-created_at")
    )
    task_groups: dict = {}
    for task in tasks:
        if task.is_selectable:
            task_groups.setdefault(task.project, []).append(task)

    context = {
        "running": running,
        "running_elapsed_seconds": running.duration_seconds if running else 0,
        "today_seconds": aggregation.total_seconds(request.user, *today),
        "week_seconds": aggregation.total_seconds(request.user, *week),
        "week_from": week[0].isoformat(),
        "week_to": week[1].isoformat(),
        "task_groups": task_groups,
    }
    return render(request, "attendance/dashboard.html", context)


def _get_selected_task(request):
    task_id = (request.POST.get("task") or "").strip()
    if not task_id.isdigit():
        return None
    return get_object_or_404(Task, pk=int(task_id), project__owner=request.user)


@require_POST
def timer_start(request):
    task = _get_selected_task(request)
    if task is None:
        messages.error(request, "タスクを選択してください。")
        return redirect("dashboard")
    try:
        timer_service.start(request.user, task)
    except TimerError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"「{task.name}」の計測を開始しました。")
    return redirect("dashboard")


@require_POST
def timer_stop(request):
    try:
        entry = timer_service.stop(request.user)
    except TimerError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, greeting_message(entry.duration_seconds))
    return redirect("dashboard")


@require_POST
def timer_switch(request):
    task = _get_selected_task(request)
    if task is None:
        messages.error(request, "タスクを選択してください。")
        return redirect("dashboard")
    try:
        stopped, _started = timer_service.switch(request.user, task)
    except TimerError as exc:
        messages.error(request, str(exc))
    else:
        if stopped is not None:
            messages.info(request, greeting_message(stopped.duration_seconds))
        messages.success(request, f"「{task.name}」の計測を開始しました。")
    return redirect("dashboard")


# --- プロジェクト（S-03 / S-04） -------------------------------------------------------


def project_list(request):
    state = request.GET.get("state", "active")
    projects = (
        Project.objects.filter(owner=request.user)
        .annotate(
            task_count=Count("tasks", distinct=True),
            entry_count=Count("tasks__time_entries", distinct=True),
        )
        .order_by("name")
    )
    if state == "active":
        projects = projects.filter(is_archived=False)
    elif state == "archived":
        projects = projects.filter(is_archived=True)
    return render(request, "attendance/project_list.html", {"projects": projects, "state": state})


def project_create(request):
    form = ProjectForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "プロジェクトを作成しました。")
        return redirect("project_list")
    return render(request, "attendance/project_form.html", {"form": form, "is_create": True})


def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    form = ProjectForm(request.POST or None, instance=project, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "プロジェクトを更新しました。")
        return redirect("project_list")
    return render(request, "attendance/project_form.html", {"form": form, "project": project})


@require_POST
def project_archive(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.is_archived = not project.is_archived
    project.save(update_fields=["is_archived", "updated_at"])
    label = "アーカイブしました" if project.is_archived else "アーカイブを解除しました"
    messages.success(request, f"「{project.name}」を{label}。")
    return redirect("project_list")


# --- タスク（S-05 / S-06） -----------------------------------------------------------


def task_list(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    status = request.GET.get("status", "all")
    include_archived = request.GET.get("archived") == "1"
    tasks = project.tasks.all().order_by("-created_at")
    if not include_archived:
        tasks = tasks.filter(is_archived=False)
    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    return render(
        request,
        "attendance/task_list.html",
        {
            "project": project,
            "tasks": tasks,
            "status": status,
            "include_archived": include_archived,
        },
    )


def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    form = TaskForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "タスクを作成しました。")
        return redirect("task_list", project_pk=project.pk)
    return render(
        request,
        "attendance/task_form.html",
        {"form": form, "project": project, "is_create": True},
    )


def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    form = TaskForm(request.POST or None, instance=task, project=task.project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "タスクを更新しました。")
        return redirect("task_list", project_pk=task.project_id)
    return render(
        request, "attendance/task_form.html", {"form": form, "project": task.project, "task": task}
    )


@require_POST
def task_archive(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    task.is_archived = not task.is_archived
    task.save(update_fields=["is_archived", "updated_at"])
    label = "アーカイブしました" if task.is_archived else "アーカイブを解除しました"
    messages.success(request, f"「{task.name}」を{label}。")
    return redirect("task_list", project_pk=task.project_id)


# --- 勤怠記録一覧 / 手動追加 / 編集 / 削除（S-07 / S-08） -------------------------------


def entry_list(request):
    form = EntryFilterForm(request.GET or None, user=request.user)
    project = task = status = None
    date_from = date_to = None
    if form.is_valid():
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        project = form.cleaned_data.get("project")
        task = form.cleaned_data.get("task")
        status = form.cleaned_data.get("status")

    if not date_from and not date_to:
        date_from, date_to = aggregation.period_bounds("month")
    elif not date_from:
        date_from = date_to
    elif not date_to:
        date_to = date_from

    start_dt, end_dt = aggregation.datetime_range(date_from, date_to)
    entries = (
        TimeEntry.objects.filter(user=request.user, start_at__gte=start_dt, start_at__lt=end_dt)
        .select_related("task", "task__project")
        .order_by("-start_at")
    )
    if project:
        entries = entries.filter(task__project=project)
    if task:
        entries = entries.filter(task=task)
    if status:
        entries = entries.filter(task__status=status)

    entries = list(entries)
    total_seconds = sum(e.duration_seconds for e in entries if not e.is_running)
    running_count = sum(1 for e in entries if e.is_running)

    paginator = Paginator(entries, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "attendance/entry_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "entries": page_obj.object_list,
            "total_seconds": total_seconds,
            "result_count": paginator.count,
            "running_count": running_count,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


def entry_create(request):
    form = TimeEntryForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            timer_service.create_manual_entry(
                request.user,
                form.cleaned_data["task"],
                form.cleaned_data["start_at"],
                form.cleaned_data["end_at"],
                form.cleaned_data.get("note", ""),
            )
        except TimerError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "勤怠記録を追加しました。")
            return redirect("entry_list")
    return render(request, "attendance/entry_form.html", {"form": form, "is_create": True})


def entry_edit(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk, user=request.user)
    if entry.is_running:
        messages.error(
            request, "計測中の記録は編集できません。先にダッシュボードで終了してください。"
        )
        return redirect("entry_list")
    form = TimeEntryForm(request.POST or None, instance=entry, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            timer_service.update_entry(
                entry,
                task=form.cleaned_data["task"],
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                note=form.cleaned_data.get("note", ""),
            )
        except TimerError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "勤怠記録を更新しました。")
            return redirect("entry_list")
    return render(request, "attendance/entry_form.html", {"form": form, "entry": entry})


@require_POST
def entry_delete(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk, user=request.user)
    if entry.is_running:
        messages.error(request, "計測中の記録は削除できません。")
    else:
        timer_service.delete_entry(entry)
        messages.success(request, "勤怠記録を削除しました。")
    return redirect("entry_list")


# --- 集計レポート / グラフ API（S-09 / P4） ------------------------------------------


def _resolve_period(request):
    """レポート画面用: preset / from / to から (date_from, date_to) を決める。"""
    today = timezone.localdate()
    preset = request.GET.get("preset")
    if preset in ("today", "week", "month"):
        return aggregation.period_bounds(preset, today)
    if preset == "last_month":
        return aggregation.period_bounds("month", today.replace(day=1) - timedelta(days=1))
    try:
        raw_from = request.GET.get("from")
        raw_to = request.GET.get("to")
        date_from = date.fromisoformat(raw_from) if raw_from else today.replace(day=1)
        date_to = date.fromisoformat(raw_to) if raw_to else today
    except ValueError:
        return today.replace(day=1), today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def report(request):
    date_from, date_to = _resolve_period(request)
    axis = request.GET.get("axis", "project")
    if axis not in ("project", "task"):
        axis = "project"

    raw_project = request.GET.get("project", "")
    project = None
    if raw_project.isdigit():
        project = Project.objects.filter(pk=int(raw_project), owner=request.user).first()

    daily = aggregation.daily_totals(request.user, date_from, date_to)
    total = sum(d["seconds"] for d in daily)
    worked_days = sum(1 for d in daily if d["seconds"] > 0)

    if axis == "task":
        breakdown = aggregation.by_task(request.user, date_from, date_to, project=project)
    else:
        breakdown = aggregation.by_project(request.user, date_from, date_to)

    context = {
        "date_from": date_from,
        "date_to": date_to,
        "axis": axis,
        "project": project,
        "projects": Project.objects.filter(owner=request.user).order_by("name"),
        "total_seconds": total,
        "worked_days": worked_days,
        "avg_seconds": round(total / worked_days) if worked_days else 0,
        "breakdown": breakdown,
    }
    return render(request, "attendance/report.html", context)


def _stats_bounds(request):
    """stats API 用: from/to をパース。不正なら JsonResponse(400) を返す。"""
    today = timezone.localdate()
    raw_from = request.GET.get("from")
    raw_to = request.GET.get("to")
    try:
        date_from = date.fromisoformat(raw_from) if raw_from else today.replace(day=1)
        date_to = date.fromisoformat(raw_to) if raw_to else today
    except ValueError:
        return JsonResponse({"error": "invalid date"}, status=400)
    if date_from > date_to:
        return JsonResponse({"error": "invalid date"}, status=400)
    return date_from, date_to


def _json_no_store(payload):
    resp = JsonResponse(payload)
    resp["Cache-Control"] = "no-store"
    return resp


def stats_daily(request):
    bounds = _stats_bounds(request)
    if isinstance(bounds, JsonResponse):
        return bounds
    date_from, date_to = bounds
    series = [
        {"date": row["date"].isoformat(), "seconds": row["seconds"]}
        for row in aggregation.daily_totals(request.user, date_from, date_to)
    ]
    return _json_no_store(
        {
            "unit": "day",
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "total_seconds": sum(s["seconds"] for s in series),
            "series": series,
        }
    )


def stats_by_project(request):
    bounds = _stats_bounds(request)
    if isinstance(bounds, JsonResponse):
        return bounds
    date_from, date_to = bounds
    data = aggregation.by_project(request.user, date_from, date_to)
    data["from"] = date_from.isoformat()
    data["to"] = date_to.isoformat()
    return _json_no_store(data)


def stats_by_task(request):
    bounds = _stats_bounds(request)
    if isinstance(bounds, JsonResponse):
        return bounds
    date_from, date_to = bounds
    raw_project = request.GET.get("project", "")
    project = None
    if raw_project.isdigit():
        project = Project.objects.filter(pk=int(raw_project), owner=request.user).first()
    data = aggregation.by_task(request.user, date_from, date_to, project=project)
    data["from"] = date_from.isoformat()
    data["to"] = date_to.isoformat()
    data["project_id"] = project.pk if project else None
    return _json_no_store(data)


# --- エクスポート（S-10 / P5） -----------------------------------------------------


def export_page(request):
    form = ExportForm(request.GET or None, user=request.user)
    return render(request, "attendance/export.html", {"form": form})


def _export(request, responder):
    form = ExportForm(request.GET or None, user=request.user)
    if not form.is_valid():
        return render(request, "attendance/export.html", {"form": form})
    entries = completed_entries(
        request.user,
        form.cleaned_data["date_from"],
        form.cleaned_data["date_to"],
        project=form.cleaned_data.get("project"),
        task=form.cleaned_data.get("task"),
    )
    return responder(entries, form.cleaned_data["date_from"], form.cleaned_data["date_to"])


def export_csv(request):
    return _export(request, csv_response)


def export_xlsx(request):
    return _export(request, xlsx_response)
