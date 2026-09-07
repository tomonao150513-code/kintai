"""ドメイン例外。services が送出し、ビューが捕捉して messages に日本語で積む。

docs/domain-logic.md §1.4 / docs/coding-guidelines.md §5。
"""


class TimerError(Exception):
    """打刻まわりのドメイン例外の基底。ユーザー向けメッセージを `str()` に持たせる。"""


class TimerAlreadyRunning(TimerError):
    def __init__(self, message="すでに計測中のタイマーがあります。"):
        super().__init__(message)


class TimerNotRunning(TimerError):
    def __init__(self, message="計測中のタイマーがありません。"):
        super().__init__(message)


class TaskNotStartable(TimerError):
    def __init__(self, message="このタスクは計測を開始できません（アーカイブ済み）。"):
        super().__init__(message)


class EntryValidationError(TimerError):
    """full_clean() の ValidationError をラップする。"""

    def __init__(self, message="入力内容に問題があります。", *, errors=None):
        super().__init__(message)
        self.errors = errors
