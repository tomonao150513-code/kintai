# エクスポート仕様（CSV / Excel）

要件 F-EXP-01〜06、F-FMT-03。実装は `attendance/exports/`。

## 対象データ

- ログインユーザー本人の **完了記録のみ**（`end_at IS NOT NULL`）。実行中タイマーは含めない。
- 絞り込み: `date_from`〜`date_to`（必須、`work_date` = 開始時刻の JST 日付で判定）、`project`（任意）、`task`（任意）。
- 並び順: `start_at` 昇順。

## 明細の列（CSV / Excel 共通、この順序）

| # | 列名 | 内容 | 例 |
| --- | --- | --- | --- |
| 1 | `日付` | 開始時刻の JST 日付 `YYYY-MM-DD` | `2026-09-07` |
| 2 | `開始時刻` | JST `HH:MM:SS` | `09:00:00` |
| 3 | `終了時刻` | JST `HH:MM:SS` | `10:30:24` |
| 4 | `実働秒数` | 整数（`duration_seconds`、丸めなし） | `5424` |
| 5 | `実働時間(HH:MM:SS)` | `format_hms_colon` | `1:30:24` |
| 6 | `実働時間(h)` | `format_hours_decimal`（小数2桁） | `1.51` |
| 7 | `プロジェクト` | プロジェクト名 | `社内システム開発` |
| 8 | `タスク` | タスク名 | `ログイン画面実装` |
| 9 | `タスク状態` | `未着手` / `進行中` / `完了`（表示ラベル） | `進行中` |
| 10 | `メモ` | `note`（改行はスペースに置換） | `詳細設計まで` |
| 11 | `入力元` | `打刻` / `手動` | `打刻` |

行組み立ては `exports/rows.py` の 1 関数に集約し、CSV/Excel から共用する。

## 合計

- 明細の最後に合計行（またはシート）: 列1〜3 は空、`実働秒数` = 総和、`実働時間(HH:MM:SS)` = 総和の整形、`実働時間(h)` = 総和/3600、以降は空。ラベルは列7に `合計`。

## CSV（`GET /export/csv/`）

- 文字コード: **UTF-8 BOM 付き**（`﻿` を先頭に）。Excel で文字化けしないため（F-EXP-04）。
- 改行: CRLF。区切り: カンマ。全セルを `csv.writer` の既定クォートで出力。
- 1 行目にヘッダ、最終行に合計行。
- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename="kintai_{from}_{to}.csv"`
  - 例: `kintai_2026-09-01_2026-09-30.csv`
  - `project` / `task` で絞った場合もファイル名は期間のみ（シンプルに）。必要なら末尾に `_p{project_id}` を付けてよい。

## Excel（`GET /export/xlsx/`）

- ライブラリ: `openpyxl`。
- シート1 `勤怠明細`: 1行目ヘッダ（太字・背景色）、2行目以降に明細、最終行に合計行（太字）。
  - `実働秒数`・`実働時間(h)` 列は数値型で書き込む（集計しやすさ優先）。`実働時間(HH:MM:SS)` は文字列。
  - 日付・時刻列は文字列で可（表計算側の型トラブル回避）。列幅は内容に合わせて自動調整。
  - ウィンドウ枠固定: ヘッダ行（`freeze_panes="A2"`）。オートフィルタ ON。
- シート2 `集計`: プロジェクト別の合計（`プロジェクト` / `実働秒数` / `実働時間(HH:MM:SS)` / `実働時間(h)` / `割合(%)`）、最終行に総合計。
- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="kintai_{from}_{to}.xlsx"`
- メモリ上で `openpyxl.Workbook` → `BytesIO` に保存 → `HttpResponse` で返す。

## エラー

- `date_from` / `date_to` 未指定 or 不正 → S-10 にフォームエラーを出して戻す（ダウンロードしない）。
- `date_from > date_to` → フォームエラー。
- 該当 0 件 → ヘッダ + 合計 0 の空ファイルを返す（エラーにしない）。

## テスト観点（`test_exports.py`）

- 列の順序・ヘッダ名が仕様どおり。
- BOM が先頭にある / 改行 CRLF。
- `実働秒数` が丸めなしで一致。
- 合計行の値が明細の総和と一致。
- 実行中記録が除外される。
- ファイル名に期間が入る。
- xlsx が openpyxl で読み戻せて、数値セルが数値型。
