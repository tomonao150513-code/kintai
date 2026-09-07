from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("timer/start/", views.timer_start, name="timer_start"),
    path("timer/stop/", views.timer_stop, name="timer_stop"),
    path("timer/switch/", views.timer_switch, name="timer_switch"),
]
