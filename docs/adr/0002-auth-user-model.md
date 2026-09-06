# ADR-0002: 初回から `accounts.User`（AbstractUser 空サブクラス）を使う

- ステータス: 承認（2026-09-07）
- 関連要件: §4、§11 P7、付録

## 背景

当面はユーザー 1 人だが、要件で「将来チーム対応」が明示されている。Django プロジェクト開始後に
`AUTH_USER_MODEL` を差し替えるのは、マイグレーションが非常に面倒（既存 `auth.User` への外部キーが絡む）。

## 決定

P0 の時点で `accounts` アプリを作り、

```python
class User(AbstractUser):
    pass
```

を定義して `AUTH_USER_MODEL = "accounts.User"` を設定する。**初回 `migrate` の前に**行う。
モデルからの参照は常に `settings.AUTH_USER_MODEL`（`get_user_model()`）経由にする。

## 理由

- 後からのユーザーモデル差し替えコストを回避。
- 空サブクラスなら当面コストゼロ。将来フィールド追加（表示名、所属など）も無痛。
- チーム対応（`ProjectMembership`、権限）を `accounts` に足す土台になる。

## 影響

- P0 の手順に「`accounts.User` を作ってから初回 migrate」を含める（[../task-breakdown.md](../task-breakdown.md)）。
- `admin` にカスタム User を登録する（`UserAdmin` 継承）。
