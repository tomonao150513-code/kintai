# データモデル

要件定義書 §7 を実装可能レベルまで具体化したもの。`attendance/models.py` にほぼこのまま落とせる。

## 0. 共通: TimeStampedModel（抽象）

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        abstract = True
```

全モデルがこれを継承する（監査用、要件 §6）。

## 1. Project（プロジェクト）

| フィールド | Django 定義 | 備考 |
| --- | --- | --- |
| `owner` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="projects")` | 作成者。将来のチーム集計の絞り込みキー |
| `name` | `CharField("プロジェクト名", max_length=100)` | |
| `description` | `TextField("説明", blank=True, default="")` | |
| `color` | `CharField("表示色", max_length=7, default="#4F46E5", validators=[hex_color_validator])` | `#RRGGBB`。グラフ配色に使用 |
| `is_archived` | `BooleanField("アーカイブ", default=False, db_index=True)` | 物理削除しない |

```python
class Meta:
    verbose_name = "プロジェクト"
    verbose_name_plural = "プロジェクト"
    ordering = ["name"]
    constraints = [
        models.UniqueConstraint(fields=["owner", "name"], name="uniq_project_owner_name"),
    ]

def __str__(self):
    return self.name
```

- `hex_color_validator`: `RegexValidator(r"^#(?:[0-9a-fA-F]{3}){1,2}$")`
- 削除ポリシー: 記録が1件以上あるプロジェクトは UI から物理削除させない（アーカイブのみ）。`Task.project` が `PROTECT` のため、タスクがあると DB でも削除不可。

## 2. Task（タスク）

| フィールド | Django 定義 | 備考 |
| --- | --- | --- |
| `project` | `ForeignKey(Project, on_delete=PROTECT, related_name="tasks")` | |
| `name` | `CharField("タスク名", max_length=150)` | |
| `description` | `TextField("説明", blank=True, default="")` | |
| `status` | `CharField("状態", max_length=10, choices=Status.choices, default=Status.TODO, db_index=True)` | |
| `is_archived` | `BooleanField("アーカイブ", default=False, db_index=True)` | |

```python
class Status(models.TextChoices):
    TODO = "todo", "未着手"
    DOING = "doing", "進行中"
    DONE = "done", "完了"

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
```

- 打刻フォームのタスク選択肢は既定で `is_selectable` のものだけ表示。「すべて表示」チェックで解除可（F-TSK-05）。

## 3. TimeEntry（勤怠記録 / タイムエントリ）

| フィールド | Django 定義 | 備考 |
| --- | --- | --- |
| `user` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="time_entries")` | 記録者 |
| `task` | `ForeignKey(Task, on_delete=PROTECT, related_name="time_entries")` | 対象タスク |
| `start_at` | `DateTimeField("開始時刻", db_index=True)` | aware（UTC 保存） |
| `end_at` | `DateTimeField("終了時刻", null=True, blank=True)` | `NULL` = 実行中タイマー |
| `note` | `TextField("メモ", blank=True, default="")` | |
| `source` | `CharField("入力元", max_length=10, choices=Source.choices, default=Source.TIMER)` | |

```python
class Source(models.TextChoices):
    TIMER = "timer", "打刻"
    MANUAL = "manual", "手動"

class Meta:
    verbose_name = "勤怠記録"
    verbose_name_plural = "勤怠記録"
    ordering = ["-start_at"]
    indexes = [models.Index(fields=["user", "start_at"], name="idx_entry_user_start")]
    constraints = [
        # 実行中タイマーは 1 ユーザー 1 件（要件 F-PUNCH-03）
        models.UniqueConstraint(
            fields=["user"],
            condition=models.Q(end_at__isnull=True),
            name="uniq_running_timer_per_user",
        ),
        # 終了は開始より後（要件 F-PUNCH-10）
        models.CheckConstraint(
            check=models.Q(end_at__isnull=True) | models.Q(end_at__gt=models.F("start_at")),
            name="timeentry_end_after_start",
        ),
    ]
```

### 3.1 派生値（DB 非保持、プロパティ）

```python
@property
def is_running(self) -> bool:
    return self.end_at is None

@property
def effective_end(self):
    return self.end_at or timezone.now()

@property
def duration(self) -> timedelta:
    return self.effective_end - self.start_at

@property
def duration_seconds(self) -> int:
    return int(self.duration.total_seconds())   # 丸めなし・切り捨てのみ（要件 F-PUNCH-12）

@property
def work_date(self):
    """集計の基準日 = 開始時刻の JST 日付（要件 §7.2 案A）。"""
    return timezone.localtime(self.start_at).date()
```

### 3.2 アプリ層バリデーション（clean）

DB 制約で表現できない **同一ユーザー内の時間帯重複禁止**（要件 F-PUNCH-10）を `clean()` で検証する。

```python
def clean(self):
    super().clean()
    if self.end_at and self.end_at <= self.start_at:
        raise ValidationError({"end_at": "終了時刻は開始時刻より後にしてください。"})
    end = self.effective_end
    overlap = TimeEntry.objects.filter(user=self.user).exclude(pk=self.pk).filter(
        start_at__lt=end,
    ).filter(models.Q(end_at__isnull=True) | models.Q(end_at__gt=self.start_at))
    if overlap.exists():
        raise ValidationError("同じ時間帯に別の記録があります。時刻を調整してください。")
```

- 保存経路（services / forms / admin）はすべて `full_clean()` を通す。詳細は [coding-guidelines.md](coding-guidelines.md)。

### 3.3 将来対応: 休憩控除（要件 §3.3）

今回は実装しないが、移行しやすいよう次を守る:

- 実働時間の算出は **`duration` プロパティと `services` に集約**し、テンプレート/ビューで直接引き算しない。
- 後日の追加候補（どちらでも移行可）:
  - 案1: `TimeEntry.break_seconds = PositiveIntegerField(default=0)` を足し、`duration = (end - start) - break_seconds` に変更。
  - 案2: `Break(time_entry=FK, start_at, end_at)` テーブルを足し、`duration` から休憩合計を引く。

## 4. ER 図

```
User(accounts) 1 ──< Project 1 ──< Task 1 ──< TimeEntry >── 1 User(accounts)
   owner                project        task              user (記録者)
                                                  end_at IS NULL = 実行中
```

## 5. マイグレーション方針

- P0 で `accounts.User`（空の `AbstractUser` サブクラス）を先に作ってから初回 migrate（[ADR-0002](adr/0002-auth-user-model.md)）。
- モデル変更ごとに 1 マイグレーション。手書きデータ移行は MVP では行わない。
- `UniqueConstraint(condition=...)` / `CheckConstraint` は SQLite・PostgreSQL 双方で動く（Django が生成）。
- インデックス名・制約名は上記で固定（衝突・差分レビューを楽にするため）。

## 6. 初期データ（任意）

開発用に fixture かデータ移行で 1 プロジェクト・数タスクを入れておくと打刻確認が楽。MVP では手動 or 管理画面で作成。
