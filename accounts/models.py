from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """プロジェクト独自のユーザーモデル。

    当面は Django 標準の AbstractUser と同一。将来のチーム対応（表示名・所属など）や
    AUTH_USER_MODEL 差し替えコスト回避のため、最初からこのモデルを使う。
    詳細: docs/adr/0002-auth-user-model.md
    """

    class Meta(AbstractUser.Meta):
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
