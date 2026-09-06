# アーキテクチャ

## 1. 全体像

サーバーレンダリング型の Django モノリス。SPA は採用しない（[ADR-0001](adr/0001-frontend-django-templates.md)）。

```
ブラウザ (Bootstrap 5 + Chart.js)
      │  HTML フォーム POST / GET、一部 fetch で JSON 取得（グラフ）
      ▼
Django views  ── 薄い。認証チェック・入力パース・services 呼び出し・テンプレート描画のみ
      │
      ▼
services      ── 業務ロジックの単一の置き場（打刻・集計・時間整形・エクスポート組み立て）
      │
      ▼
models (ORM)  ── Project / Task / TimeEntry。制約・派生値プロパティを持つ
      │
      ▼
SQLite (開発)  ── 将来 PostgreSQL。切替は環境変数 DATABASE_URL
```

## 2. レイヤと責務

| レイヤ | 置き場 | やること | やらないこと |
| --- | --- | --- | --- |
| プレゼンテーション | `templates/`, テンプレートフィルタ | 表示、整形の呼び出し | 業務判断、ORM クエリ |
| ビュー | `attendance/views.py`, `accounts/views.py` | 認証確認、フォーム処理、services 呼び出し、リダイレクト/描画 | 実働時間の計算、集計 SQL、重複判定 |
| サービス | `attendance/services/` | 打刻の状態遷移、集計、時間整形、エクスポート行組み立て、ドメイン例外の送出 | HTTP・リクエスト/レスポンスの知識 |
| モデル | `attendance/models.py` | 永続化、DB 制約、派生値（`duration` 等）、`clean()` バリデーション | 期間集計・レポート整形 |

**依存の向き**: templates → views → services → models。逆流させない。services は Django の `timezone` / ORM は使ってよいが `request` を受け取らない。

## 3. ディレクトリ構成

```
kinntai/
├── manage.py
├── requirements.txt
├── .env.example                # コミットする。実値は .env（コミットしない）
├── docs/                       # 本ドキュメント群 + requipuments.md（要件定義書＝正）
├── config/                     # プロジェクト設定
│   ├── __init__.py
│   ├── settings.py             # 環境変数から読む（django-environ）
│   ├── urls.py                 # ルート URLconf
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                   # 認証・ユーザー
│   ├── models.py               # User(AbstractUser) 空サブクラス（ADR-0002）
│   ├── views.py                # ログイン/ログアウトは django.contrib.auth.views を利用
│   ├── urls.py
│   └── templates/registration/login.html
├── attendance/                 # 本体アプリ
│   ├── models.py               # Project / Task / TimeEntry / TimeStampedModel
│   ├── admin.py                # Django 管理画面登録
│   ├── forms.py                # ProjectForm / TaskForm / TimeEntryForm / 期間フィルタフォーム
│   ├── views.py                # ダッシュボード、CRUD、レポート、エクスポート、stats API
│   ├── urls.py
│   ├── exceptions.py           # TimerError 等のドメイン例外
│   ├── services/
│   │   ├── __init__.py
│   │   ├── timer.py            # start / stop / switch
│   │   ├── aggregation.py      # daily_totals / by_project / by_task / period ヘルパ
│   │   └── formatting.py       # format_hms / format_hms_colon / greeting_message ほか
│   ├── exports/
│   │   ├── __init__.py
│   │   ├── rows.py             # 明細行の共通組み立て（CSV/Excel 共用）
│   │   ├── csv.py              # UTF-8 BOM CSV レスポンス
│   │   └── xlsx.py             # openpyxl による .xlsx レスポンス
│   ├── templatetags/
│   │   └── kintai_extras.py    # {{ seconds|hms }} など整形フィルタ
│   ├── templates/attendance/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── _running_timer.html # 実行中タイマー部分テンプレート
│   │   ├── project_list.html / project_form.html
│   │   ├── task_list.html / task_form.html
│   │   ├── entry_list.html / entry_form.html
│   │   ├── report.html
│   │   └── export.html
│   ├── migrations/
│   └── tests/
│       ├── test_timer.py
│       ├── test_models_constraints.py
│       ├── test_aggregation.py
│       ├── test_formatting.py
│       └── test_exports.py
└── static/                     # Bootstrap / Chart.js はローカル配置または CDN
```

## 4. アプリの責務分割

| アプリ | 責務 |
| --- | --- |
| `config` | 設定、ルーティング集約、WSGI/ASGI |
| `accounts` | カスタム `User` モデル、ログイン/ログアウト画面。将来のチーム対応（メンバー・権限）もここ |
| `attendance` | プロジェクト・タスク・打刻・集計・レポート・エクスポート。アプリの本体 |

## 5. 設定方針（config/settings.py）

- `django-environ` で `.env` / OS 環境変数から読む。
- 必須変数: `SECRET_KEY`、`DEBUG`（既定 False）、`DATABASE_URL`（既定 `sqlite:///db.sqlite3`）、`ALLOWED_HOSTS`。
- `TIME_ZONE = "Asia/Tokyo"`、`USE_TZ = True`、`LANGUAGE_CODE = "ja"`。
- `AUTH_USER_MODEL = "accounts.User"`。
- `LOGIN_URL = "login"`、`LOGIN_REDIRECT_URL = "dashboard"`、`LOGOUT_REDIRECT_URL = "login"`。
- 認証必須は `LoginRequiredMiddleware`（Django 5.1+）またはビュー個別の `@login_required`。本プロジェクトは **ミドルウェアで一括 + `login_not_required` は使わない**方針（ログイン画面のみ例外）。
- 設定分割はしない（単一 `settings.py` + 環境変数）。規模が小さいため。

## 6. 依存ライブラリ（requirements.txt 予定）

| パッケージ | 用途 |
| --- | --- |
| `Django>=5.1,<6.0` | 本体 |
| `django-environ` | 環境変数管理 |
| `openpyxl` | Excel(.xlsx) 出力 |
| `pytest`, `pytest-django` | テスト（Django 標準 TestCase でも可。どちらかに統一） |
| `ruff`, `black` | 静的解析・整形（任意だが推奨） |

DRF は使わない。グラフ用 JSON は素の `JsonResponse` で返す（[api-charts.md](api-charts.md)）。

## 7. リクエストの流れ（例: 「終了」ボタン）

1. `POST /timer/stop/` → `views.timer_stop`
2. ビューは `request.user` を取り出し `services.timer.stop(user=request.user)` を呼ぶ
3. `stop()` は `transaction.atomic` 内で実行中 `TimeEntry` を `select_for_update` で取得、`end_at = timezone.now()` をセット、`full_clean()` → `save()`。確定した entry を返す
4. 実行中タイマーが無ければ `TimerNotRunning` を送出 → ビューが messages に警告を積む
5. ビューは `services.formatting.greeting_message(entry.duration_seconds)` を messages(success) に積み、ダッシュボードへリダイレクト
6. ダッシュボードが「お疲れ様でした！ 1時間30分24秒 作業しました！」を表示
