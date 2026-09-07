# グラフ用 集計 JSON API

Chart.js が fetch する読み取り専用エンドポイント。DRF は使わず素の `JsonResponse`（要件 F-AGG-06、[ADR-0001](adr/0001-frontend-django-templates.md)）。

## 共通仕様

- 認証必須。未ログインは `login` へリダイレクト（AJAX なので 302 を JS 側で検知するか、`403 JSON` を返す。MVP は 302 で可）。
- 返すデータは **常にログインユーザー本人分のみ**（`user=request.user`）。将来チーム対応で管理者は `?user=` を許可する余地を残す（今は無視）。
- クエリパラメータ:
  | 名前 | 形式 | 既定 | 説明 |
  | --- | --- | --- | --- |
  | `from` | `YYYY-MM-DD` | 今月1日 | 期間開始（含む） |
  | `to` | `YYYY-MM-DD` | 今日 | 期間終了（含む） |
  | `project` | int | なし | `by-task` のみ。プロジェクトで絞る |
  | `scope` | `team` | なし | `daily` / `by-project` / `by-task` で、`can_see_team` のとき対象を「本人 + owner/member プロジェクト」に拡大（P7） |
- 期間は内部で `[from 00:00 JST, to+1日 00:00 JST)` に変換して `start_at` で絞る。
- 対象は **完了記録のみ**（`end_at IS NOT NULL`）。
- 不正な日付 → `400 {"error": "invalid date"}`。`from > to` → `400`。
- 秒は整数。丸めなし（[ADR-0004](adr/0004-time-rounding-second-precision.md)）。
- `Cache-Control: no-store`。

---

## GET `/api/stats/daily/`

日別の合計実働秒。記録ゼロの日も `0` で埋める（グラフの連続性）。

**レスポンス**
```json
{
  "unit": "day",
  "from": "2026-09-01",
  "to": "2026-09-07",
  "total_seconds": 96324,
  "series": [
    { "date": "2026-09-01", "seconds": 21600 },
    { "date": "2026-09-02", "seconds": 0 },
    { "date": "2026-09-03", "seconds": 18000 }
  ]
}
```

用途: ダッシュボード週次バー（S-02）、レポート日別バー（S-09）。

---

## GET `/api/stats/by-project/`

期間内のプロジェクト別内訳。`seconds` 降順。

**レスポンス**
```json
{
  "from": "2026-09-01",
  "to": "2026-09-30",
  "total_seconds": 432000,
  "items": [
    { "project_id": 1, "name": "社内システム開発", "color": "#4F46E5", "seconds": 259200, "ratio": 0.6 },
    { "project_id": 2, "name": "顧客A案件",       "color": "#059669", "seconds": 172800, "ratio": 0.4 }
  ]
}
```

- `ratio` = `seconds / total_seconds`（0〜1）。`total_seconds == 0` のとき `items: []`、`ratio` は算出しない。
- 用途: レポート円グラフ + 内訳テーブル（S-09）。

---

## GET `/api/stats/by-task/`

期間内のタスク別内訳。`project` 指定で当該プロジェクト内に限定。

**レスポンス**
```json
{
  "from": "2026-09-01",
  "to": "2026-09-30",
  "project_id": 1,
  "total_seconds": 259200,
  "items": [
    { "task_id": 10, "name": "ログイン画面実装", "project_id": 1, "project_name": "社内システム開発",
      "color": "#4F46E5", "seconds": 144000, "ratio": 0.5556 },
    { "task_id": 11, "name": "モデル設計",       "project_id": 1, "project_name": "社内システム開発",
      "color": "#4F46E5", "seconds": 115200, "ratio": 0.4444 }
  ]
}
```

- `color` はプロジェクト色（タスクに色は持たせない）。円グラフでタスクを分けたいときは JS 側で明度を振る。

---

## 実装メモ

- ビューは `attendance/services/aggregation.py` の `daily_totals` / `by_project` / `by_task` を呼んで `JsonResponse` に詰めるだけ。
- 集計ロジック・期間変換は services に集約（テストは `test_aggregation.py`）。
- JS 側（テンプレート内 `<script>` または `static/js/charts.js`）は fetch → Chart.js 描画のみ。色は API の `color` を使用。
