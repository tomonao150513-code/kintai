"""実働時間の表示整形。丸めは一切しない（要件 §5.8 F-FMT / ADR-0004）。

入力は常に「秒（int, 0 以上）」。テンプレートは kintai_extras フィルタ経由で使う。
"""


def _hms(seconds: int) -> tuple[int, int, int]:
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    return seconds // 3600, seconds // 60 % 60, seconds % 60


def format_hms(seconds: int) -> str:
    """`1時間30分24秒` / `5分0秒` / `24秒`。上位の 0 単位だけ落とす（§3.2）。"""
    h, m, s = _hms(seconds)
    if h > 0:
        return f"{h}時間{m}分{s}秒"
    if m > 0:
        return f"{m}分{s}秒"
    return f"{s}秒"


def format_hms_colon(seconds: int) -> str:
    """`1:30:24`。時は桁数可変（26時間 → `26:00:00`）、分秒はゼロ詰め 2 桁。"""
    h, m, s = _hms(seconds)
    return f"{h}:{m:02d}:{s:02d}"


def format_hours_decimal(seconds: int) -> float:
    """`5424` 秒 → `1.51`（時間、小数 2 桁）。表示用の丸めのみ。"""
    if seconds < 0:
        raise ValueError("seconds must be >= 0")
    return round(seconds / 3600, 2)


def greeting_message(seconds: int) -> str:
    """終了打刻直後のねぎらい文言（要件 F-PUNCH-13）。"""
    return f"お疲れ様でした！ {format_hms(seconds)} 作業しました！"
