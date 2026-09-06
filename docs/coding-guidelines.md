# コーディング規約・開発方針

## 1. スタイル

- フォーマッタ: `black`（行長 100）。リンタ: `ruff`（`E`, `F`, `I`, `UP`, `DJ` 有効）。
- 文字列は原則ダブルクォート。
- 型ヒントは services / 純粋関数には付ける。ビュー・モデルメソッドは任意。
- import 順: 標準 → サードパーティ → Django → ローカル（`ruff` の isort に従う）。

## 2. 言語の使い分け

| 対象 | 言語 |
| --- | --- |
| コード識別子（変数・関数・クラス・モジュール） | 英語 |
| モデルの `verbose_name` / `help_text` / choices ラベル | 日本語 |
| テンプレートの表示文字列・メッセージ | 日本語 |
| docstring・コメント | 日本語で可（簡潔に） |
| コミットメッセージ | 日本語で可 |

## 3. Django の書き方

- **ビューは関数ベース（FBV）** で統一。`@login_required` は使わず、認証は `LoginRequiredMiddleware`（Django 5.1+）で一括。ログイン画面のみ設定で除外。
- 業務ロジックはビューに書かない。`attendance/services/` に置き、ビューは「取り出す・呼ぶ・返す」だけ。
- ORM で他人のデータに触れない。取得は必ず `user=request.user` / `owner=request.user` で絞り、`get_object_or_404` を使う。
- 状態変更は POST のみ。テンプレートのフォームに `{% csrf_token %}`。
- 保存経路（services・forms・admin）は必ず `full_clean()` を通してから `save()`。`Model.save()` だけで済ませない。
- `datetime.now()` / `datetime.today()` 禁止。`django.utils.timezone.now()` を使う。日付は `timezone.localdate()`。
- 時刻の表示変換は `timezone.localtime()`。テンプレートでは `{% load tz %}` ではなく整形フィルタ経由。
- マイグレーションはモデル変更ごとに 1 つ。生成後に中身を確認してからコミット。制約名・インデックス名は [data-model.md](data-model.md) で固定済み。

## 4. 時間・数値の扱い

- 実働時間は「秒（int）」で持ち回る。丸め・切り上げは一切しない（[ADR-0004](adr/0004-time-rounding-second-precision.md)）。
- 表示整形は `services/formatting.py` とテンプレートフィルタのみ。ビュー/テンプレートで直接 `//3600` などしない。
- 実働時間の算出は `TimeEntry.duration` と `services` に集約（将来の休憩控除に備える。[data-model.md](data-model.md) §3.3）。

## 5. 例外・エラー表示

- services はドメイン例外（`attendance/exceptions.py` の `TimerError` 系）を送出。
- ビューが捕捉して `django.contrib.messages` に日本語で積み、元画面へリダイレクト。
- フォーム由来の `ValidationError` は `form.add_error` に載せてフォーム再表示。

## 6. テスト

- フレームワーク: `pytest-django`（`pytest.ini` / `pyproject.toml` に `DJANGO_SETTINGS_MODULE=config.settings`）。Django 標準 `TestCase` でも可だがどちらかに統一。
- 必須カバレッジ:
  | ファイル | 観点 |
  | --- | --- |
  | `test_timer.py` | start（IDLE→RUNNING）、stop（RUNNING→IDLE、返り値の秒）、switch（自動終了→新規開始）、RUNNING で start は例外 |
  | `test_models_constraints.py` | 実行中タイマー 1 件制約、`end_at > start_at` チェック制約、時間帯重複の `clean()` |
  | `test_aggregation.py` | 日別合計（ゼロ埋め）、プロジェクト別（降順・ratio）、週/月の期間境界、日跨ぎが開始日に計上される |
  | `test_formatting.py` | `format_hms` の整形表（h>0 / m>0 / それ以外）、`0秒`、負値エラー、`format_hms_colon` の 24 超 |
  | `test_exports.py` | 列順・ヘッダ、BOM、合計行、実行中除外、ファイル名 |
- 時刻を使うテストは `services` の `now=` 引数か `freezegun` 相当で固定。
- テストは JST 前提（`settings.TIME_ZONE = "Asia/Tokyo"`）。

## 7. 設定・秘密情報

- `SECRET_KEY` / `DEBUG` / `DATABASE_URL` / `ALLOWED_HOSTS` は環境変数（`django-environ`）。
- `.env` はコミットしない。`.env.example` を用意してコミットする。
- `DEBUG=True` は開発のみ。既定は `False`。

## 8. Git

- 作業ブランチを切ってから作業（`main` に直接コミットしない）。
- コミットは小さく、フェーズ / 機能単位。メッセージ末尾に:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```
- マイグレーションファイルは対応するモデル変更と同じコミットに含める。

## 9. フロント

- Bootstrap 5 + Chart.js。ビルドツールは入れない（CDN もしくは `static/` に配置）。
- JS は最小限（実行中タイマーの経過秒カウントアップ、確認ダイアログ、グラフ fetch/描画）。
- テンプレートにロジックを書かない。整形はフィルタ、データ整形はビュー/サービス。
