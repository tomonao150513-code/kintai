# 用語集（日本語 ↔ コード識別子）

命名を揺らさないための対応表。

| 日本語 | コード / モデル | 補足 |
| --- | --- | --- |
| プロジェクト | `Project` | タスクの上位分類。`owner` を持つ |
| タスク | `Task` | `Project` に属する作業単位 |
| タスク状態 | `Task.status` = `todo` / `doing` / `done` | ラベル: 未着手 / 進行中 / 完了 |
| 勤怠記録 / タイムエントリ | `TimeEntry` | 1 回の「開始〜終了」= 1 レコード |
| 打刻 | timer / punch | 「開始」「終了」操作。`services/timer.py` |
| 開始（打刻） | `services.timer.start()` | IDLE → RUNNING |
| 終了（打刻） | `services.timer.stop()` | RUNNING → IDLE、実働時間確定 |
| 切り替え | `services.timer.switch()` | 実行中を終了して別タスクで開始（要件 F-PUNCH-04） |
| 実行中タイマー | running timer / `TimeEntry.is_running` | `end_at IS NULL`。1 ユーザー 1 件 |
| 実働時間 | `TimeEntry.duration` (`timedelta`) / `duration_seconds` (`int`) | `end_at - start_at`。丸めなし |
| 基準日 | `TimeEntry.work_date` | 開始時刻の JST 日付。集計はこれで日に割り当て（案A） |
| 入力元 | `TimeEntry.source` = `timer` / `manual` | 打刻 / 手動 |
| 手動追加 | `services.timer.create_manual_entry()` | 打刻し忘れ対応（F-PUNCH-09） |
| 集計 | aggregation / `services/aggregation.py` | 期間・軸ごとの合計 |
| 内訳 | breakdown / `by_project()` `by_task()` | 名称・時間・割合 |
| 日別合計 | `daily_totals()` → `series` | グラフの棒。ゼロ日も埋める |
| 期間 | `date_from` / `date_to`（両端含む、日付） | 内部で半開区間 `[from, to+1)` に変換 |
| 今日 / 今週 / 今月 | `period_bounds("today"/"week"/"month")` | 週は月曜始まり |
| ねぎらい文言 | `greeting_message()` | 「お疲れ様でした！ 1時間30分24秒 作業しました！」 |
| 時分秒表記 | `format_hms()` | `1時間30分24秒` / `5分0秒` / `24秒` |
| HH:MM:SS 表記 | `format_hms_colon()` | `1:30:24`。時は桁可変 |
| エクスポート | export / `attendance/exports/` | CSV(UTF-8 BOM) / Excel(openpyxl) |
| アーカイブ | `is_archived` | 物理削除の代わり。プロジェクト/タスク |
| ユーザー | `accounts.User`（`AbstractUser` 空サブクラス） | 参照は `settings.AUTH_USER_MODEL` 経由 |
| ダッシュボード | `dashboard`（URL name / view） | トップ画面 S-02 |
| レポート | `report` | 集計画面 S-09 |
