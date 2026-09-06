# 画面仕様

要件定義書 §8 の各画面を、URL・テンプレート・表示項目・遷移まで具体化。

## URL 一覧（`config/urls.py` + 各アプリ `urls.py`）

| URL name | パス | メソッド | ビュー | 画面 |
| --- | --- | --- | --- | --- |
| `login` | `/login/` | GET/POST | `django.contrib.auth.views.LoginView` | S-01 |
| `logout` | `/logout/` | POST | `LogoutView` | - |
| `dashboard` | `/` | GET | `dashboard` | S-02 |
| `timer_start` | `/timer/start/` | POST | `timer_start` | S-02 から |
| `timer_stop` | `/timer/stop/` | POST | `timer_stop` | S-02 から |
| `timer_switch` | `/timer/switch/` | POST | `timer_switch` | S-02 から |
| `project_list` | `/projects/` | GET | `project_list` | S-03 |
| `project_create` | `/projects/new/` | GET/POST | `project_create` | S-04 |
| `project_edit` | `/projects/<int:pk>/edit/` | GET/POST | `project_edit` | S-04 |
| `project_archive` | `/projects/<int:pk>/archive/` | POST | `project_archive` | S-03 から |
| `task_list` | `/projects/<int:project_pk>/tasks/` | GET | `task_list` | S-05 |
| `task_create` | `/projects/<int:project_pk>/tasks/new/` | GET/POST | `task_create` | S-06 |
| `task_edit` | `/tasks/<int:pk>/edit/` | GET/POST | `task_edit` | S-06 |
| `task_archive` | `/tasks/<int:pk>/archive/` | POST | `task_archive` | S-05 から |
| `entry_list` | `/entries/` | GET | `entry_list` | S-07 |
| `entry_create` | `/entries/new/` | GET/POST | `entry_create` | S-07（手動追加） |
| `entry_edit` | `/entries/<int:pk>/edit/` | GET/POST | `entry_edit` | S-08 |
| `entry_delete` | `/entries/<int:pk>/delete/` | POST | `entry_delete` | S-07 から |
| `report` | `/report/` | GET | `report` | S-09 |
| `export_page` | `/export/` | GET | `export_page` | S-10 |
| `export_csv` | `/export/csv/` | GET | `export_csv` | S-10 から |
| `export_xlsx` | `/export/xlsx/` | GET | `export_xlsx` | S-10 から |
| `stats_daily` | `/api/stats/daily/` | GET | `stats_daily` | グラフ用 JSON |
| `stats_by_project` | `/api/stats/by-project/` | GET | `stats_by_project` | グラフ用 JSON |
| `stats_by_task` | `/api/stats/by-task/` | GET | `stats_by_task` | グラフ用 JSON |

- 状態変更（start/stop/switch/archive/delete）は必ず **POST + CSRF**。GET では副作用を起こさない。
- 全 URL 認証必須（`login` 除く）。他ユーザーのレコードには 404 を返す（`get_object_or_404(..., user=request.user)` / `owner=request.user`）。

---

## S-01 ログイン

- テンプレート: `accounts/templates/registration/login.html`
- 項目: ユーザー名、パスワード、ログインボタン。エラー時メッセージ。
- 成功 → `dashboard`。

## S-02 ダッシュボード

- テンプレート: `attendance/templates/attendance/dashboard.html`（+ `_running_timer.html`）
- コンテキスト:
  | 変数 | 内容 |
  | --- | --- |
  | `running` | 実行中 `TimeEntry` または `None`（`services.timer.get_running`） |
  | `running_elapsed_seconds` | `running.duration_seconds`（表示時点）。JS で 1 秒ごとに加算表示 |
  | `today_seconds` | 今日の合計（完了記録のみ、`aggregation`） |
  | `week_seconds` | 今週（月〜日）の合計 |
  | `selectable_tasks` | 打刻対象タスク一覧（`Task.is_selectable`、プロジェクトでグルーピング） |
- 要素:
  - **実行中タイマー枠**: RUNNING のとき「◯◯（プロジェクト / タスク）を計測中 / 経過 1時間30分24秒 / [終了]」。IDLE のとき非表示。
  - **開始フォーム**: タスク選択（`<optgroup>` でプロジェクト別）+ [開始]。
    - IDLE のとき → `POST timer_start`。
    - RUNNING のとき → JS で確認ダイアログ「実行中のタイマーを終了して切り替えますか？」→ OK で `POST timer_switch`。
  - **サマリ**: 「今日の合計 X時間Y分Z秒」「今週の合計 …」。RUNNING 中は「(+実行中 …)」を併記。
  - **週次バー**: 直近 7 日の日別合計を Chart.js 棒グラフ（`stats_daily` を fetch）。
- 遷移: 終了打刻後は `dashboard` にリダイレクトし、`messages.success` に `greeting_message(...)` を表示。

## S-03 プロジェクト一覧

- コンテキスト: `projects`（`owner=request.user`）、フィルタ `state`（`active`(既定) / `archived` / `all`）
- 各行: 色スウォッチ、名称、タスク数、記録数、[タスク一覧][編集][アーカイブ/解除]
- 記録数が 1 以上のプロジェクトは物理削除ボタンを出さない（アーカイブのみ）。
- [新規作成] → S-04

## S-04 プロジェクト作成 / 編集

- フォーム `ProjectForm`: `name`（必須）、`description`、`color`（カラーピッカー `<input type="color">`）
- `(owner, name)` 重複はフォームエラー。
- 保存 → S-03

## S-05 タスク一覧

- URL に `project_pk`。コンテキスト: `project`、`tasks`、フィルタ `status`（`all` 既定 / `todo` / `doing` / `done`）、`include_archived`（既定 false）
- 各行: 状態バッジ、名称、累計実働時間（任意）、[編集][アーカイブ/解除]
- [新規作成] → S-06

## S-06 タスク作成 / 編集

- フォーム `TaskForm`: `name`（必須）、`description`、`status`（ラジオ / セレクト）
- `project` は URL 固定（作成時）。編集時のプロジェクト移動は不可（MVP）。
- `(project, name)` 重複はフォームエラー。
- 保存 → S-05

## S-07 勤怠記録一覧

- コンテキスト:
  | 変数 | 内容 |
  | --- | --- |
  | `form` | 期間フィルタフォーム（`date_from`, `date_to`, `project`, `task`, `status`） |
  | `entries` | 絞り込み結果（`user=request.user`、`start_at` 降順、ページネーション） |
  | `total_seconds` | 絞り込み結果の合計（完了記録のみ） |
  | `page_obj` | ページネーション |
- 既定期間: 今月（`period_bounds("month")`）。
- 各行: 日付、開始〜終了（`HH:MM`）、実働（`1時間30分24秒`）、プロジェクト / タスク、状態、`source`（打刻/手動）、メモ抜粋、[編集][削除]
- 実行中の記録は「計測中」と表示し、実働・削除は不可（先にダッシュボードで終了）。
- ヘッダに「合計 X時間Y分Z秒（N件）」。
- [手動追加] → S-07 内モーダル or S-08 相当のフォーム（`entry_create`）。
- 削除は `POST entry_delete` + 確認ダイアログ。

## S-08 勤怠記録 編集

- フォーム `TimeEntryForm`: `task`、`start_at`（`datetime-local`）、`end_at`（`datetime-local`、必須）、`note`
- バリデーション: `end_at > start_at`、`start_at <= now`、同ユーザー時間帯の重複なし（`services.update_entry` 経由 → `ValidationError` をフォームエラーに変換）。
- 保存 → S-07（元のフィルタ条件を保持できると望ましい）。

## S-09 集計レポート

- コンテキスト: `form`（`date_from`, `date_to`, 既定=今月）、`axis`（`project` / `task`、既定 `project`）、`project`（axis=task 時の絞り込み、任意）
- 表示:
  - サマリ: 期間合計、稼働日数、1日平均。
  - **日別バー**: `stats_daily` を fetch → Chart.js 棒グラフ。
  - **構成比**: `stats_by_project`（または `by_task`）を fetch → Chart.js 円グラフ + 内訳テーブル（名称 / 時間 / 割合%）。
- 期間プリセット: 今日 / 今週 / 今月 / 先月 / 任意。

## S-10 エクスポート

- テンプレート: `export.html`。フォーム: `date_from`, `date_to`（必須）、`project`（任意）、`task`（任意）。
- [CSV でダウンロード] → `GET export_csv?...`、[Excel でダウンロード] → `GET export_xlsx?...`
- 仕様は [export-spec.md](export-spec.md)。実行中記録は含めない。

---

## 共通レイアウト（`attendance/base.html`）

- ナビ: ダッシュボード / プロジェクト / 勤怠記録 / レポート / エクスポート / （右）ユーザー名・ログアウト
- `messages` 表示領域（success/error/warning）
- Bootstrap 5、Chart.js は必要ページのみ読み込み
- 実行中タイマーがあるときはナビにミニ表示（経過時間）を出すと便利（任意）
