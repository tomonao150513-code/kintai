"""可視範囲の判定（チーム対応、docs/task-breakdown.md P7）。

- 管理者（is_staff / is_superuser）: 全件。
- 一般ユーザー: 自分の記録 + 自分がメンバーのプロジェクトの記録。
既存の個人向け画面（ダッシュボード・CRUD）は従来どおり本人のみを対象にする。
レポートと勤怠一覧だけがこのスコープを使う。
"""

from django.db.models import Q

from attendance.models import Project, TimeEntry


def is_admin(user) -> bool:
    return bool(user.is_superuser or user.is_staff)


def visible_projects(user):
    if is_admin(user):
        return Project.objects.all()
    return Project.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()


def visible_entries(user):
    if is_admin(user):
        return TimeEntry.objects.all()
    return TimeEntry.objects.filter(
        Q(user=user) | Q(task__project__owner=user) | Q(task__project__memberships__user=user)
    ).distinct()


def can_see_team(user) -> bool:
    """レポートに「メンバー別」軸を出してよいか。"""
    return is_admin(user) or user.project_memberships.exists()
