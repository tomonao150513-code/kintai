from django.shortcuts import render


def dashboard(request):
    """ダッシュボード（S-02）。P0 では仮表示のみ。打刻・集計は P2 以降で実装する。"""
    return render(request, "attendance/dashboard.html")
