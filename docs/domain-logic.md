# ドメインロジック仕様（services 層）

`attendance/services/` に置く業務ロジックの仕様。ビュー・テンプレートはここを呼ぶだけにする。

---

## 1. 打刻 — `services/timer.py`

### 1.1 状態

ユーザーごとに 2 状態のみ。

| 状態 | 定義 |
| --- | --- |
| IDLE | `end_at IS NULL` の `TimeEntry` が存在しない |
| RUNNING | `end_at IS NULL` の `TimeEntry` がちょうど 1 件存在する（DB 制約で 2 件以上は不可） |

### 1.2 API

```python
def get_running(user) -> TimeEntry | None
def start(user, task, *, now=None) -> TimeEntry
def stop(user, *, now=None) -> TimeEntry
def switch(user, task, *, now=None) -> tuple[TimeEntry | None, TimeEntry]  # (stopped, started)
```

- `now` 引数はテスト用。未指定なら `django.utils.timezone.now()`。
- すべて `@transaction.atomic`。`get_running` は書き込み系の中では `select_for_update()` で取得。

### 1.3 挙動

| 関数 | 前提 | 動作 | 例外 |
| --- | --- | --- | --- |
| `start` | IDLE | `TimeEntry(user, task, start_at=now, source=TIMER)` を `full_clean()` → `save()` | RUNNING のとき `TimerAlreadyRunning`。`task` がアーカイブ済みなら `TaskNotStartable` |
| `stop` | RUNNING | 実行中 entry の `end_at=now` をセット、`full_clean()` → `save()`、返す | IDLE のとき `TimerNotRunning` |
| `switch` | 任意 | RUNNING なら `stop()` してから `start(task)`。IDLE なら `start(task)` のみ | `start` 側の例外を伝播 |

- **タスク切り替え（要件 F-PUNCH-04）**: 画面側で「実行中のタイマーを終了して切り替えますか？」の確認ダイアログを出し、OK なら `POST /timer/switch/`（`task` 指定）→ `switch()`。キャンセルなら何もしない。
- `start` で `end_at=now` を持つ即完了レコードは作らない（必ず実行中で作られ、`stop` で確定）。手動追加は別関数（§2）。
- `stop` が返した entry を使ってビューが「お疲れ様でした！ …」を表示（§3.4）。

### 1.4 例外階層 — `attendance/exceptions.py`

```python
class TimerError(Exception): ...
class TimerAlreadyRunning(TimerError): ...
class TimerNotRunning(TimerError): ...
class TaskNotStartable(TimerError): ...
class EntryValidationError(TimerError): ...   # full_clean の ValidationError をラップ
```

ビューは `TimerError` を捕捉して `messages.error()` に日本語文言を積み、元画面へリダイレクトする。

---

## 2. 手動追加・編集 — `services/timer.py`（続き）

```python
def create_manual_entry(user, task, start_at, end_at, note="") -> TimeEntry
def update_entry(entry, *, task=None, start_at=None, end_at=None, note=None) -> TimeEntry
def delete_entry(entry) -> None
```

- `source=MANUAL` で作成（`update_entry` は既存 `source` を維持）。
- 必ず `full_clean()` を通す → 重複・`end_at <= start_at` は `ValidationError`。
- `start_at` を過去日時にできる（要件 F-PUNCH-09）。未来日時は不可（`start_at <= now` を検証）。
- `end_at=None`（実行中に戻す）は許可しない。手動編集では両方必須。
- 削除は確認付き（画面側）。関連は無いので物理削除。

---

## 3. 時間フォーマット — `services/formatting.py`

要件 §5.8（F-FMT）。**丸めは一切しない。** 入力は常に「秒（int, 0 以上）」。

### 3.1 関数

```python
def format_hms(seconds: int) -> str          # "1時間30分24秒" / "5分0秒" / "24秒"
def format_hms_colon(seconds: int) -> str    # "1:30:24"（時は桁数可変、分秒はゼロ詰め2桁）
def format_hours_decimal(seconds: int) -> float  # round(seconds / 3600, 2) → 1.51
def greeting_message(seconds: int) -> str    # "お疲れ様でした！ 1時間30分24秒 作業しました！"
```

### 3.2 `format_hms` の整形ルール

`h, m, s = seconds//3600, seconds//60%60, seconds%60` として:

| 条件 | 出力例 | 形式 |
| --- | --- | --- |
| `h > 0` | `1時間30分24秒`、`10時間0分5秒` | `{h}時間{m}分{s}秒` |
| `h == 0 and m > 0` | `30分24秒`、`5分0秒` | `{m}分{s}秒` |
| `h == 0 and m == 0` | `24秒`、`0秒` | `{s}秒` |

- 上位の 0 の単位だけ落とす（下位は常に表示）。`90分` のような 60 以上繰り上げ前表示はしない。
- 負値は `ValueError`。`0` は `"0秒"`。

### 3.3 `format_hms_colon`

`f"{h}:{m:02d}:{s:02d}"`。`h` は 24 を超えても桁数据え置き（例: 26 時間 → `26:00:00`）。CSV/Excel の `HH:MM:SS` 列に使う（[export-spec.md](export-spec.md)）。

### 3.4 テンプレートからの利用

`attendance/templatetags/kintai_extras.py` にフィルタを用意し、テンプレートは整形ロジックを持たない。

```django
{% load kintai_extras %}
{{ entry.duration_seconds|hms }}          {# 1時間30分24秒 #}
{{ total_seconds|hms_colon }}             {# 12:34:56 #}
```

---

## 4. 集計 — `services/aggregation.py`

要件 §5.6（F-AGG）。グラフ API（[api-charts.md](api-charts.md)）とレポート画面（S-09）が使う。

### 4.1 対象データ

- **完了記録のみ**: `TimeEntry.objects.filter(user=user, end_at__isnull=False)`。
  実行中タイマーは合計・レポート・エクスポートに含めない。
- ダッシュボードの「今日 / 今週の合計」だけは、表示時点で実行中タイマーの経過秒を **別枠で加算表示**してよい（合計値そのものには混ぜない）。

### 4.2 基準日

`work_date = 開始時刻の JST 日付`（要件 §7.2 案A、按分しない）。SQL では:

```python
from django.db.models.functions import TruncDate
qs.annotate(d=TruncDate("start_at", tzinfo=ZoneInfo("Asia/Tokyo")))
```

### 4.3 API

```python
def period_bounds(kind: str, ref: date | None = None) -> tuple[date, date]
#   kind: "today" | "week"(月〜日) | "month"

def daily_totals(user, date_from, date_to) -> list[DayTotal]
#   DayTotal = {"date": date, "seconds": int}  ※ 記録ゼロの日も 0 で埋める（グラフの連続性）

def by_project(user, date_from, date_to) -> Breakdown
def by_task(user, date_from, date_to, project=None) -> Breakdown
#   Breakdown = {
#     "total_seconds": int,
#     "items": [
#       {"id": int, "name": str, "color": str, "seconds": int, "ratio": float},  # ratio 0..1
#       ...  # seconds 降順。ratio は total=0 のとき 0.0
#     ],
#   }
```

- 期間は「日付」で受け取り、内部で `[date_from 00:00 JST, date_to+1 00:00 JST)` の半開区間に変換して `start_at` で絞る。
- 実働秒の集計は MVP では **`duration_seconds` を Python 側で合算**してよい（記録件数が小さい前提）。パフォーマンス問題が出たら `ExpressionWrapper(F("end_at") - F("start_at"))` + `Sum` へ移行。方針は [ADR-0004](adr/0004-time-rounding-second-precision.md) 準拠（DB 側でも秒切り捨て以外の丸めを入れない）。
- 「週」は月曜始まり・日曜終わり。

---

## 5. エクスポート組み立て — `services`/`exports`

明細行の組み立ては [export-spec.md](export-spec.md) に列仕様を定義。`exports/rows.py` に「クエリ → 行 dict のリスト」を実装し、`csv.py` / `xlsx.py` はそれを整形して `HttpResponse` にするだけにする。
