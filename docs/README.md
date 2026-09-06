# kinntai 開発ドキュメント

タスク別勤怠システム（Django）の開発を進めるための設計・仕様ドキュメント群。

## 位置づけ

- **要件の正**: [`requipuments.md`](requipuments.md)（要件定義書 v0.2、合意済み。`docs/` 配下に配置）
- **本 `docs/` 配下**: 要件を実装に落とすための詳細設計・規約・手順。要件と矛盾したら要件定義書が優先。

## 読む順番

| # | ファイル | 内容 |
| --- | --- | --- |
| 1 | [architecture.md](architecture.md) | システム構成、レイヤ設計、ディレクトリ構成、依存ルール |
| 2 | [data-model.md](data-model.md) | モデル定義（フィールド・制約・Meta・派生値）実装可能レベル |
| 3 | [domain-logic.md](domain-logic.md) | 打刻の状態遷移、集計ロジック、時間フォーマット仕様（services 層） |
| 4 | [screens.md](screens.md) | 画面・URL・テンプレート・表示項目・遷移 |
| 5 | [api-charts.md](api-charts.md) | グラフ用の集計 JSON API 仕様 |
| 6 | [export-spec.md](export-spec.md) | CSV / Excel エクスポートの列仕様・ファイル名規則 |
| 7 | [coding-guidelines.md](coding-guidelines.md) | コーディング規約、テスト方針、コミット規約 |
| 8 | [dev-setup.md](dev-setup.md) | Windows / PowerShell でのローカル環境構築手順 |
| 9 | [task-breakdown.md](task-breakdown.md) | P0〜P7 の実装タスク・チェックリスト |
| - | [glossary.md](glossary.md) | 用語集（日本語 ↔ コード識別子） |
| - | [adr/](adr/) | アーキテクチャ決定記録（ADR） |

## 現在のステータス

- 要件定義: 合意済み（v0.2、未決事項ゼロ）
- 実装: 未着手。次は **P0（環境構築）**
- 対象環境: ローカルのみ、日本語 UI、ユーザー1人（将来チーム対応を設計で考慮）
