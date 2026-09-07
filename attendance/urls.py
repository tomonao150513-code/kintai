from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("timer/start/", views.timer_start, name="timer_start"),
    path("timer/stop/", views.timer_stop, name="timer_stop"),
    path("timer/switch/", views.timer_switch, name="timer_switch"),
    # プロジェクト
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:pk>/archive/", views.project_archive, name="project_archive"),
    # タスク
    path("projects/<int:project_pk>/tasks/", views.task_list, name="task_list"),
    path("projects/<int:project_pk>/tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/archive/", views.task_archive, name="task_archive"),
    # 勤怠記録
    path("entries/", views.entry_list, name="entry_list"),
    path("entries/new/", views.entry_create, name="entry_create"),
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
    # レポート / グラフ API
    path("report/", views.report, name="report"),
    path("api/stats/daily/", views.stats_daily, name="stats_daily"),
    path("api/stats/by-project/", views.stats_by_project, name="stats_by_project"),
    path("api/stats/by-task/", views.stats_by_task, name="stats_by_task"),
    # エクスポート
    path("export/", views.export_page, name="export_page"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/xlsx/", views.export_xlsx, name="export_xlsx"),
]
