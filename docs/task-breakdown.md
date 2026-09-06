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

## P2 打刻 + ダッシュボード

- [ ] `attendance/exceptions.py`
- [ ] `attendance/services/timer.py`: `get_running` / `start` / `stop` / `switch`（[domain-logic.md](domain-logic.md) §1）
- [ ] `attendance/services/formatting.py`: `format_hms` / `format_hms_colon` / `format_hours_decimal` / `greeting_message`（§3）
- [ ] `attendance/templatetags/kintai_extras.py`: `hms` / `hms_colon` フィルタ
- [ ] `attendance/services/aggregation.py`: `period_bounds` / `daily_totals`（まず today・week だけ使う）
- [ ] ビュー: `dashboard` / `timer_start` / `timer_stop` / `timer_switch`（POST、messages、リダイレクト）
- [ ] テンプレート: `dashboard.html` / `_running_timer.html`（開始フォーム = optgroup、実行中枠、今日/今週合計）
- [ ] JS: 経過秒カウントアップ、切り替え確認ダイアログ
- [ ] `test_timer.py` / `test_formatting.py`
- **完了条件**: タスクを選んで開始 → 終了で実働時間が記録され、「お疲れ様でした！ 1時間30分24秒 作業しました！」が出る

## P3 一覧・手修正・手動追加・期間フィルタ

- [ ] `attendance/forms.py`: `ProjectForm` / `TaskForm` / `TimeEntryForm` / `EntryFilterForm`
- [ ] `services/timer.py`: `create_manual_entry` / `update_entry` / `delete_entry`
- [ ] ビュー + テンプレート: プロジェクト（list/create/edit/archive）、タスク（list/create/edit/archive）、勤怠記録（list/create/edit/delete）
- [ ] `entry_list`: 期間フィルタ（既定=今月）、合計、ページネーション、実行中は編集/削除不可
- [ ] 他ユーザーデータへのアクセスは 404
- [ ] `test_aggregation.py`（期間境界・日跨ぎ）
- **完了条件**: 一覧で絞り込み・合計表示・行編集・削除・手動追加ができる

## P4 集計レポート + グラフ

- [ ] `services/aggregation.py`: `by_project` / `by_task` 仕上げ、`daily_totals` ゼロ埋め
- [ ] ビュー: `report`、`stats_daily` / `stats_by_project` / `stats_by_task`（[api-charts.md](api-charts.md)）
- [ ] テンプレート: `report.html`（期間プリセット、日別バー、構成比円グラフ + 内訳テーブル）
- [ ] JS: fetch → Chart.js（棒・円）。色は API の `color`
- [ ] ダッシュボードの週次バーを `stats_daily` に接続
- [ ] `test_aggregation.py` 拡充（ratio、降順）
- **完了条件**: 期間指定でプロジェクト別・日別が数値とグラフで見える

## P5 CSV / Excel エクスポート

- [ ] `attendance/exports/rows.py`（クエリ → 行 dict、合計行）
- [ ] `attendance/exports/csv.py`（UTF-8 BOM、CRLF、ファイル名 `kintai_{from}_{to}.csv`）
- [ ] `attendance/exports/xlsx.py`（openpyxl、明細シート + 集計シート、freeze_panes、オートフィルタ）
- [ ] ビュー: `export_page` / `export_csv` / `export_xlsx`、`export.html`
- [ ] `test_exports.py`（列順・BOM・合計・実行中除外・ファイル名・xlsx 読み戻し）
- **完了条件**: 期間・プロジェクト・タスク指定で CSV / Excel がダウンロードできる（[export-spec.md](export-spec.md) 準拠）

## P6 テスト整備・リファクタ

- [ ] カバレッジ確認（services はほぼ全パス）
- [ ] `ruff` / `black` を CI ではなくローカル手順に明記、既存コード整形
- [ ] `README.md`（リポジトリ直下）に起動方法を追記
- [ ] 例外時・0 件時・不正入力時の画面挙動を一通り確認
- **完了条件**: 主要ロジックにテストがあり、`pytest` / `ruff` が green

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
