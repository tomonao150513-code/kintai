"""kintai_extras フィルタ。"""

import pytest

from attendance.services.formatting import format_hours_decimal
from attendance.templatetags.kintai_extras import hms, hms_colon


def test_hms_filter():
    assert hms(5424) == "1時間30分24秒"
    assert hms("3600") == "1時間0分0秒"


def test_hms_filter_bad_input_returns_empty():
    assert hms(None) == ""
    assert hms("abc") == ""


def test_hms_colon_filter():
    assert hms_colon(5424) == "1:30:24"
    assert hms_colon(None) == ""


def test_format_hours_decimal_rejects_negative():
    with pytest.raises(ValueError):
        format_hours_decimal(-1)
