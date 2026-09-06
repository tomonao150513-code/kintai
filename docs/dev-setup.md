# ローカル開発環境 セットアップ（Windows / PowerShell）

対象: Windows 11 + PowerShell。Python 3.12 以上。

## 1. 前提の確認

```powershell
python --version   # 3.12.x 以上であること（無ければ https://www.python.org/ から導入）
git --version
```

## 2. 仮想環境

プロジェクトルート（`c:\Users\Tomon_ftu0pk2\Downloads\kinntai`）で:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> `Activate.ps1` が実行ポリシーで拒否される場合:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## 3. 依存インストール

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt`（P0 で作成予定）の想定:

```
Django>=5.1,<6.0
django-environ
openpyxl
pytest
pytest-django
ruff
black
```

## 4. 環境変数

```powershell
Copy-Item .env.example .env
```

`.env` を編集:

```
DJANGO_SECRET_KEY=（ランダムな50文字程度）
DJANGO_DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
```

SECRET_KEY 生成:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## 5. DB 初期化・管理ユーザー作成

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## 6. 起動

```powershell
python manage.py runserver
```

- アプリ: http://127.0.0.1:8000/
- 管理画面: http://127.0.0.1:8000/admin/

## 7. テスト・静的解析

```powershell
pytest
ruff check .
black --check .
```

## 8. よくあるトラブル

| 症状 | 対処 |
| --- | --- |
| `Activate.ps1` が実行できない | 実行ポリシー変更（§2 の注記） |
| `django` が見つからない | 仮想環境が有効か確認（プロンプト先頭に `(.venv)`）。`pip install -r requirements.txt` 再実行 |
| CSV が Excel で文字化け | 実装が UTF-8 BOM 付きになっているか（[export-spec.md](export-spec.md)） |
| 時刻が 9 時間ずれる | `USE_TZ=True` かつ `TIME_ZONE="Asia/Tokyo"`、表示は `timezone.localtime` 経由か確認 |
| マイグレーション衝突 | `accounts.User` を先に作ってから初回 `migrate` したか（[adr/0002](adr/0002-auth-user-model.md)） |

## 9. ブランチ運用

```powershell
git switch -c feature/p0-setup
# 作業 → コミット（メッセージ末尾に Co-Authored-By 行）
```
