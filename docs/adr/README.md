# アーキテクチャ決定記録（ADR）

重要な設計判断とその理由の記録。決定を覆すときは新しい ADR を追加し、古い方を「Superseded by ADR-XXXX」にする。

| # | タイトル | ステータス |
| --- | --- | --- |
| [0001](0001-frontend-django-templates.md) | フロントは Django テンプレート + Bootstrap + Chart.js（SPA 不採用） | 承認 |
| [0002](0002-auth-user-model.md) | 初回から `accounts.User`（AbstractUser 空サブクラス） | 承認 |
| [0003](0003-day-crossing-aggregation.md) | 日跨ぎ記録は開始日に全計上（案A） | 承認 |
| [0004](0004-time-rounding-second-precision.md) | 実働時間は丸めなし・秒精度、「◯時間◯分◯秒」表示 | 承認 |
| [0005](0005-single-running-timer-constraint.md) | 実行中タイマーは DB 部分ユニーク制約で 1 件強制 | 承認 |
