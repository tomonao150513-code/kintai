"""services/formatting.py（docs/domain-logic.md §3、要件 §5.8 F-FMT）。"""

import pytest

from attendance.services.formatting import (
    format_hms,
    format_hms_colon,
    format_hours_decimal,
    greeting_message,
)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (5424, "1時間30分24秒"),
        (36005, "10時間0分5秒"),
        (3600, "1時間0分0秒"),
        (1824, "30分24秒"),
        (300, "5分0秒"),
        (60, "1分0秒"),
        (59, "59秒"),
        (24, "24秒"),
        (0, "0秒"),
    ],
)
def test_format_hms(seconds, expected):
    assert format_hms(seconds) == expected


def test_format_hms_rejects_negative():
    with pytest.raises(ValueError):
        format_hms(-1)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (5424, "1:30:24"),
        (93600, "26:00:00"),
        (61, "0:01:01"),
        (0, "0:00:00"),
    ],
)
def test_format_hms_colon(seconds, expected):
    assert format_hms_colon(seconds) == expected


def test_format_hours_decimal():
    assert format_hours_decimal(5424) == 1.51
    assert format_hours_decimal(3600) == 1.0
    assert format_hours_decimal(0) == 0.0


def test_greeting_message():
    assert greeting_message(5424) == "お疲れ様でした！ 1時間30分24秒 作業しました！"
    assert greeting_message(0) == "お疲れ様でした！ 0秒 作業しました！"
