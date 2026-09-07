"""テンプレート用の整形フィルタ。ロジックは services/formatting.py に集約。"""

from django import template

from attendance.services import formatting

register = template.Library()


@register.filter
def hms(seconds):
    """{{ seconds|hms }} → `1時間30分24秒`。"""
    try:
        return formatting.format_hms(int(seconds))
    except (TypeError, ValueError):
        return ""


@register.filter
def hms_colon(seconds):
    """{{ seconds|hms_colon }} → `1:30:24`。"""
    try:
        return formatting.format_hms_colon(int(seconds))
    except (TypeError, ValueError):
        return ""
