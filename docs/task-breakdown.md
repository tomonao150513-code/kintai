# 実装タスク分解（P0〜P7）

要件定義書 §11 のマイルストーンを、ファイル単位のチェックリストに落としたもの。上から順に進める。

---

## P0 環境構築 ✅ 完了（2026-09-07）

- [x] `git init`、`.gitignore`（`.venv/`, `db.sqlite3`, `.env`, `__pycache__/`, `*.pyc`, `/static/collected/`）
- [x] `.venv` 作成、`requirements.txt` 作成（[dev-setup.md](dev-setup.md) の一覧）
- [x] `django-admin startproject config .`
- [x] `python manage.py startapp accounts`
- [x] `python manage.py startapp attendance`
- [x] `accounts/models.py` に `class User(AbstractUser)`（[adr/0002](adr/0002-auth-user-model.md)）
- [x] `config/settings.py`: `django-environ` 読み込み、`INSTALLED_APPS`（accounts, attendance）、`AUTH_USER_MODEL="accounts.User"`、`TIME_ZONE="Asia/Tokyo"`、`USE_TZ=True`、`LANGUAGE_CODE="ja"`、`LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL`、`LoginRequiredMiddleware` 追加、テンプレート/静的の設定、`MESSAGE_TAGS`（Bootstrap 色）
- [x] `.env.example` 作成（+ `.env` を生成、`SECRET_KEY` は `secrets.token_urlsafe`）
- [x] `config/urls.py`: `admin/`、`accounts.urls`（login/logout）、`attendance.urls`
- [x] `accounts/templates/registration/login.html`（Bootstrap）
- [x] `attendance/templates/attendance/base.html`（ナビ + messages 枠）
- [x] 仮 `dashboard` ビュー（「ようこそ」だけ）＋ URL `dashboard`
- [x] `migrate` → `createsuperuser` → `runserver` でログイン〜ダッシュボード表示を確認
- [x] `pyproject.toml`（pytest-django / black / ruff 設定、migrations は lint 除外）
- **完了条件**: ログインしてダッシュボードが表示される → ✅ 確認済み（未認証で `/` → `/login/` リダイレクト、ログイン後 `/` でダッシュボード表示）

> 開発用 superuser: `admin` / `admin12345`（ローカルのみ。必要なら各自変更・再作成）。
> 起動: `.\.venv\Scripts\Activate.ps1` → `python manage.py runserver`。品質チェック: `ruff check .` / `black --check .` / `pytest`。

## P1 モデル + 管理画面 ✅ 完了（2026-09-07、ブランチ `feature/p1-models`）

- [x] `attendance/models.py`: `TimeStampedModel` / `Project` / `Task` / `TimeEntry`（[data-model.md](data-model.md) のとおり。制約名も固定）
- [x] `hex_color_validator`
- [x] `makemigrations`（`attendance/migrations/0001_initial.py`）→ 生成物レビュー → `migrate`
- [x] `attendance/admin.py`: 3 モデル登録（list_display, list_filter, search_fields, `TimeEntry` は `task`/`user`/`start_at`/実働時間/`source` を表示、`duration`/`work_date`/日時を read-only。`owner`/`user` は現在ユーザーを初期値に）
- [x] `attendance/tests/`（パッケージ化）+ `test_models_constraints.py`: 実行中タイマー 1 件制約 / `end_at>start_at` チェック制約 / 重複・境界の `clean()` / ユニーク制約 / `is_selectable` / `duration_seconds` 丸めなし（12 tests, all green）
- **完了条件**: 管理画面で 3 モデルの CRUD ができ、制約テストが green → ✅ 確認済み（admin で Project→Task→TimeEntry を作成、changelist に実働時間 `1:30:24` 表示、重複エントリは admin でも `clean()` で拒否）

## P2 打刻 + ダッシュボード ✅ 完了（2026-09-07、ブランチ `feature/p2-timer`）

- [x] `attendance/exceptions.py`（`TimerError` 系 + `EntryValidationError`）
- [x] `attendance/services/timer.py`: `get_running` / `start` / `stop` / `switch`（[domain-logic.md](domain-logic.md) §1、atomic + `select_for_update`、`IntegrityError` → `TimerAlreadyRunning`）
- [x] `attendance/services/formatting.py`: `format_hms` / `format_hms_colon` / `format_hours_decimal` / `greeting_message`（§3）
- [x] `attendance/templatetags/kintai_extras.py`: `hms` / `hms_colon` フィルタ
- [x] `attendance/services/aggregation.py`: `period_bounds`（today/week/month）/ `total_seconds` / `daily_totals`（P2 は today・week のみ使用。by_project/by_task は P4）
- [x] ビュー: `dashboard` / `timer_start` / `timer_stop` / `timer_switch`（`require_POST`、messages、`redirect("dashboard")`、他人のタスクは 404）
- [x] テンプレート: `dashboard.html` / `_running_timer.html`（開始フォーム = optgroup、実行中枠、今日/今週合計。RUNNING 時は開始ボタンが「切り替え」に）
- [x] JS: 経過秒カウントアップ（`data-elapsed` 起点）、切り替え確認ダイアログ（`confirm()` → OK で action を switch URL に）
- [x] `test_timer.py`（8）/ `test_formatting.py`（parametrize 含む）→ 全 36 tests green
- **完了条件**: タスクを選んで開始 → 終了で実働時間が記録され、「お疲れ様でした！ ◯時間◯分◯秒 作業しました！」が出る → ✅ 確認済み（start/stop/switch を runserver で実操作。start-while-running / stop-while-idle のエラー、POST-only の 405、switch で旧タイマー終了メッセージ + 新タイマー開始も確認）

## P3 一覧・手修正・手動追加・期間フィルタ ✅ 完了（2026-09-07、ブランチ `feature/p3-entries`）

- [x] `attendance/forms.py`: `ProjectForm` / `TaskForm` / `TimeEntryForm`（datetime-local、JST 変換、prefill）/ `EntryFilterForm`。`(owner,name)` `(project,name)` 重複はフォームエラー
- [x] `services/timer.py`: `create_manual_entry`（source=MANUAL、未来不可、両端必須）/ `update_entry`（source 維持、実行中に戻せない）/ `delete_entry`
- [x] `aggregation.datetime_range` を追加（entry_list と共用）
- [x] ビュー + テンプレート: プロジェクト（list/create/edit/archive、状態フィルタ、タスク数/記録数）、タスク（list/create/edit/archive、状態フィルタ、アーカイブ表示切替）、勤怠記録（list/create/edit/delete）
- [x] `entry_list`: 期間フィルタ（既定=今月、`period_bounds`）、合計時間、件数、ページネーション（50件）、実行中は「計測中」表示で編集/削除不可
- [x] 他ユーザーデータへのアクセスは 404（`get_object_or_404(..., owner/user=request.user)`）
- [x] `base.html` ナビに「プロジェクト」「勤怠記録」追加
- [x] tests: `test_aggregation.py`（period_bounds today/week/month、ゼロ埋め、日跨ぎ=開始日計上、範囲両端）/ `test_manual_entry.py` / `test_views_scoping.py`（login必須・404・日付フィルタ・実行中編集不可）→ **全 57 tests green**
- **完了条件**: 一覧で絞り込み・合計表示・行編集・削除・手動追加ができる → ✅ 確認済み（runserver で project/task 作成・重複エラー、manual entry 追加（`2時間15分30秒`）・編集（`3時間0分0秒`、prefill）・削除、未来日時エラー）

## P4 集計レポート + グラフ ✅ 完了（2026-09-07、ブランチ `feature/p4-report`）

- [x] `services/aggregation.py`: `by_project` / `by_task`（`_breakdown` で seconds 降順・ratio 4桁、total=0 で items=[]）。`daily_totals` ゼロ埋めは P2 実装済み
- [x] ビュー: `report`（preset today/week/month/last_month + from/to + axis project/task + project 絞り込み、サマリ=合計/稼働日数/1日平均）、`stats_daily` / `stats_by_project` / `stats_by_task`（[api-charts.md](api-charts.md) 準拠、`Cache-Control: no-store`、不正日付→400、本人分のみ）
- [x] テンプレート: `report.html`（期間プリセット、日別バー、構成比ドーナツ + 内訳テーブル（サーバーレンダリング、合計行））
- [x] JS: `stats_daily` を fetch して Chart.js 棒グラフ、`json_script` で埋めた内訳を Chart.js ドーナツ。色は API の `color`
- [x] ダッシュボードの週次バーを `stats_daily`（今週の月〜日）に接続
- [x] `base.html` ナビに「レポート」追加
- [x] tests: `test_aggregation.py` 拡充（by_project 降順/ratio/色、空、by_task の project 絞り込み）/ `test_stats_api.py`（login必須、zero-fill、no-store、400、本人スコープ）→ **全 65 tests green**
- **完了条件**: 期間指定でプロジェクト別・日別が数値とグラフで見える → ✅ 確認済み（runserver で report ページ、`/api/stats/daily/`（zero-fill・no-store）、`/api/stats/by-project/`、不正日付 400、ダッシュボード週次バー）

## P5 CSV / Excel エクスポート ✅ 完了（2026-09-07、ブランチ `feature/p5-export`）

- [x] `attendance/exports/rows.py`（`completed_entries` クエリ、`build_rows` = 11 列の行 dict + 合計行、`project_summary`）
- [x] `attendance/exports/csv.py`（UTF-8 BOM、CRLF、`text/csv; charset=utf-8`、`kintai_{from}_{to}.csv`）
- [x] `attendance/exports/xlsx.py`（openpyxl、`勤怠明細` シート（ヘッダ太字+塗り、freeze A2、オートフィルタ、実働秒数/実働時間h は数値型、合計行太字）+ `集計` シート（プロジェクト別 + 総合計）、列幅自動）
- [x] `forms.ExportForm`（date_from/date_to 必須、project/task 任意、初期値=今月、from>to はエラー）
- [x] ビュー: `export_page` / `export_csv` / `export_xlsx`（不正入力は `export.html` を再表示してダウンロードしない、0 件でもヘッダ+合計行を返す）、`export.html`（`formaction` で CSV/Excel を出し分け）
- [x] `base.html` ナビに「エクスポート」追加
- [x] `test_exports.py`（列順・BOM(EF BB BF)・CRLF・合計・実行中除外・ファイル名・xlsx 読み戻し（sheet 名・数値型）・0 件DL・不正範囲）→ **全 72 tests green**
- **完了条件**: 期間・プロジェクト・タスク指定で CSV / Excel がダウンロードできる（[export-spec.md](export-spec.md) 準拠）→ ✅ 確認済み（runserver で CSV（先頭 3 バイト 239,187,191、合計行 `,,,15300,4:15:00,4.25,合計,,,,`）・XLSX（PK 署名、2 シート、実働秒数=int）・不正範囲は HTML フォーム）

## P6 テスト整備・リファクタ ✅ 完了（2026-09-07、ブランチ `feature/p6-hardening`）

- [x] `pytest-cov` を追加、`pyproject.toml` に coverage 設定（migrations/tests 除外）。`pytest -q --cov` で計測（全体 87%、services は aggregation 100% / timer 92% / formatting 95% / exports 94–100%）
- [x] `ruff` / `black` / `pytest`（単一テスト指定含む）をローカル手順として明記（[README.md](../README.md)・[CLAUDE.md](../CLAUDE.md)）、既存コードは整形済み
- [x] リポジトリ直下に `README.md`（セットアップ・コマンド・構成・画面）
- [x] `CLAUDE.md` の status/commands を現状（P0–P5 完了）に更新、`.env` は BOM なしにする注意を明記
- [x] 例外時・0 件時・不正入力時の画面挙動テスト: `test_views_crud.py`（ダッシュボード空、project/task の作成・アーカイブ往復、timer start/stop/switch、手動追加のハッピー/重複エラー、entry 編集・削除、実行中削除ブロック、レポート 0 件・不正日付フォールバック）/ `test_templatetags.py`
- **完了条件**: 主要ロジックにテストがあり、`pytest` / `ruff` が green → ✅（90 tests green、ruff/black クリーン、カバレッジ 87%）

## P7（将来）チーム対応

- [ ] `accounts` に `ProjectMembership`（中間テーブル）
- [ ] 一覧・集計クエリの「本人絞り込み」を「管理者=全件 / 一般=本人」に分岐
- [ ] レポートに「メンバー別」軸
- [ ] 休憩控除（[data-model.md](data-model.md) §3.3 の案1 or 案2）
- **完了条件**: 他メンバー分を管理者が集計できる

---

## 進め方のルール

- フェーズ完了ごとにコミット（ブランチ `feature/pN-...`）。
- 各フェーズの「完了条件」を満たしてから次へ。
- 要件と食い違いが出たら [`requipuments.md`](requipuments.md) を正として調整し、docs を更新。
