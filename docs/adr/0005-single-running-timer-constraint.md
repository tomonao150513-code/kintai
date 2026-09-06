# ADR-0005: 実行中タイマーは DB 部分ユニーク制約で 1 ユーザー 1 件に強制

- ステータス: 承認（2026-09-07）
- 関連要件: F-PUNCH-03、F-PUNCH-04

## 背景

「実行中タイマー」= `end_at IS NULL` の `TimeEntry`。二重開始・レース（ダブルクリック、複数タブ）で
2 件以上できると集計・表示が壊れる。

## 決定

`TimeEntry.Meta.constraints` に条件付きユニーク制約を置く:

```python
models.UniqueConstraint(
    fields=["user"],
    condition=models.Q(end_at__isnull=True),
    name="uniq_running_timer_per_user",
)
```

さらに `services/timer.py` の書き込みは `transaction.atomic` + 実行中行の `select_for_update()` で直列化する。
タスク切り替え（`switch`）は「stop してから start」を同一トランザクションで行う。

## 理由

- アプリ側チェックだけだとレースで破れる。DB 制約が最終防波堤。
- SQLite / PostgreSQL 両対応（Django が partial unique index を生成）。

## 影響

- 二重開始時は `IntegrityError` になり得る → `services` で捕捉して `TimerAlreadyRunning` に変換。
- 手動追加（`create_manual_entry`）は必ず `end_at` を持つのでこの制約に触れない。
