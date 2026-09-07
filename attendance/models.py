from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

hex_color_validator = RegexValidator(
    r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    message="色は #RRGGBB または #RGB 形式で入力してください。",
)


class TimeStampedModel(models.Model):
    """作成 / 更新日時を持つ抽象基底（監査用、要件 §6）。"""

    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        abstract = True


class Project(TimeStampedModel):
    """タスクの上位分類。docs/data-model.md §1。"""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="作成者",
    )
    name = models.CharField("プロジェクト名", max_length=100)
    description = models.TextField("説明", blank=True, default="")
    color = models.CharField(
        "表示色", max_length=7, default="#4F46E5", validators=[hex_color_validator]
    )
    is_archived = models.BooleanField("アーカイブ", default=False, db_index=True)

    class Meta:
        verbose_name = "プロジェクト"
        verbose_name_plural = "プロジェクト"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="uniq_project_owner_name"),
        ]

    def __str__(self):
        return self.name


class Task(TimeStampedModel):
    """プロジェクトに属する作業単位。docs/data-model.md §2。"""

    class Status(models.TextChoices):
        TODO = "todo", "未着手"
        DOING = "doing", "進行中"
        DONE = "done", "完了"

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="tasks",
        verbose_name="プロジェクト",
    )
    name = models.CharField("タスク名", max_length=150)
    description = models.TextField("説明", blank=True, default="")
    status = models.CharField(
        "状態",
        max_length=10,
        choices=Status.choices,
        default=Status.TODO,
        db_index=True,
    )
    is_archived = models.BooleanField("アーカイブ", default=False, db_index=True)

    class Meta:
        verbose_name = "タスク"
        verbose_name_plural = "タスク"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_task_project_name"),
        ]

    def __str__(self):
        return f"{self.project.name} / {self.name}"

    @property
    def is_selectable(self) -> bool:
        """打刻対象の既定選択肢に出すか（要件 F-TSK-05）。"""
        return not self.is_archived and self.status != self.Status.DONE


class TimeEntry(TimeStampedModel):
    """1 回の「開始〜終了」= 1 レコード。docs/data-model.md §3。

    end_at が NULL のものが「実行中タイマー」。実働時間は保存せず、duration 系プロパティで算出する
    （丸めなし・秒精度、要件 F-PUNCH-12 / ADR-0004）。
    """

    class Source(models.TextChoices):
        TIMER = "timer", "打刻"
        MANUAL = "manual", "手動"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="記録者",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,
        related_name="time_entries",
        verbose_name="タスク",
    )
    start_at = models.DateTimeField("開始時刻", db_index=True)
    end_at = models.DateTimeField("終了時刻", null=True, blank=True)
    break_seconds = models.PositiveIntegerField("休憩秒数", default=0)
    note = models.TextField("メモ", blank=True, default="")
    source = models.CharField(
        "入力元",
        max_length=10,
        choices=Source.choices,
        default=Source.TIMER,
    )

    class Meta:
        verbose_name = "勤怠記録"
        verbose_name_plural = "勤怠記録"
        ordering = ["-start_at"]
        indexes = [models.Index(fields=["user", "start_at"], name="idx_entry_user_start")]
        constraints = [
            # 実行中タイマーは 1 ユーザー 1 件（要件 F-PUNCH-03 / ADR-0005）
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(end_at__isnull=True),
                name="uniq_running_timer_per_user",
            ),
            # 終了は開始より後（要件 F-PUNCH-10）
            models.CheckConstraint(
                condition=(
                    models.Q(end_at__isnull=True) | models.Q(end_at__gt=models.F("start_at"))
                ),
                name="timeentry_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.task} {timezone.localtime(self.start_at):%Y-%m-%d %H:%M}"

    @property
    def is_running(self) -> bool:
        return self.end_at is None

    @property
    def effective_end(self):
        return self.end_at or timezone.now()

    @property
    def gross_seconds(self) -> int:
        # 休憩控除前の経過秒。丸めなし（マイクロ秒だけ切り捨て）。
        return int((self.effective_end - self.start_at).total_seconds())

    @property
    def duration_seconds(self) -> int:
        # 実働秒 = 経過秒 − 休憩秒（0 未満にはしない）。ADR-0004 / data-model §3.3 案1。
        return max(0, self.gross_seconds - self.break_seconds)

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    @property
    def work_date(self):
        """集計の基準日 = 開始時刻の JST 日付（要件 §7.2 案A / ADR-0003）。"""
        return timezone.localtime(self.start_at).date()

    def clean(self):
        super().clean()
        if self.start_at is None or self.user_id is None:
            return
        if self.end_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "終了時刻は開始時刻より後にしてください。"})
        if self.end_at and self.break_seconds > self.gross_seconds:
            raise ValidationError({"break_seconds": "休憩時間が実働時間を超えています。"})
        # 同一ユーザー内の時間帯重複禁止（DB 制約では表現できないため clean で検証）
        overlap = (
            TimeEntry.objects.filter(user=self.user)
            .exclude(pk=self.pk)
            .filter(start_at__lt=self.effective_end)
            .filter(models.Q(end_at__isnull=True) | models.Q(end_at__gt=self.start_at))
        )
        if overlap.exists():
            raise ValidationError("同じ時間帯に別の記録があります。時刻を調整してください。")


class ProjectMembership(TimeStampedModel):
    """プロジェクトのメンバー（将来のチーム対応、docs/task-breakdown.md P7）。

    owner は常に管理者相当。ここに追加されたユーザーはそのプロジェクトの記録を閲覧・集計できる。
    """

    class Role(models.TextChoices):
        MEMBER = "member", "メンバー"
        MANAGER = "manager", "マネージャー"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="プロジェクト",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        verbose_name="ユーザー",
    )
    role = models.CharField("役割", max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        verbose_name = "プロジェクトメンバー"
        verbose_name_plural = "プロジェクトメンバー"
        ordering = ["project__name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="uniq_project_membership"),
        ]

    def __str__(self):
        return f"{self.project.name} / {self.user}"
