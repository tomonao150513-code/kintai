# タスク別勤怠システム (kinntai)

タスク（作業内容）ごとに実働時間を打刻ベースで記録し、集計・可視化・エクスポートする Django アプリ。
当面は本人ひとり専用。将来のチーム対応を見据えたデータモデルにしている。

- 要件定義: [docs/requipuments.md](docs/requipuments.md)（正）
- 設計・規約: [docs/README.md](docs/README.md)
- 実装フェーズ: [docs/task-breakdown.md](docs/task-breakdown.md)（P0〜P5 完了、P6 = 本整備、P7 = 将来のチーム対応）

## セットアップ（Windows / PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# .env の DJANGO_SECRET_KEY を設定:
#   python -c "import secrets; print(secrets.token_urlsafe(64))"

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # http://127.0.0.1:8000/
```

詳細・トラブルシュートは [docs/dev-setup.md](docs/dev-setup.md)。

## よく使うコマンド

```powershell
python manage.py runserver              # 開発サーバ
python manage.py migrate                # マイグレーション適用
python manage.py makemigrations         # モデル変更 → マイグレーション生成

pytest -q                               # テスト一式
pytest attendance/tests/test_timer.py   # 1 ファイル
pytest attendance/tests/test_timer.py::test_stop_when_idle_raises   # 1 テスト
pytest -q --cov --cov-report=term-missing   # カバレッジ付き

ruff check .                            # リンタ
black --check .                         # フォーマッタ（整形は black . ）
```

## 構成

| ディレクトリ | 役割 |
| --- | --- |
| `config/` | プロジェクト設定・ルーティング |
| `accounts/` | カスタム `User`、ログイン/ログアウト |
| `attendance/` | 本体（models / views / forms / services / exports / templates / templatetags / tests） |
| `attendance/services/` | 業務ロジック（打刻・集計・整形）。ビューはここを呼ぶだけ |
| `docs/` | 要件・設計・ADR |

レイヤは `templates → views → services → models` の一方向。詳細は [docs/architecture.md](docs/architecture.md)。

## 主な画面

ダッシュボード（打刻・今日/今週の合計・週次バー）／プロジェクト・タスク管理／勤怠記録の一覧・手動追加・編集・削除／
集計レポート（日別バー・構成比ドーナツ）／CSV・Excel エクスポート／Django 管理画面（`/admin/`）。
