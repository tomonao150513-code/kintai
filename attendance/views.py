from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance.exceptions import TimerError
from attendance.models import Task
from attendance.services import aggregation
from attendance.services import timer as timer_service
from attendance.services.formatting import greeting_message


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
