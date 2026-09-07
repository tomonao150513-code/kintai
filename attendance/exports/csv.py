"""CSV 出力（UTF-8 BOM 付き / CRLF）。docs/export-spec.md。"""

import csv as _csv
import io

from django.http import HttpResponse

from .rows import COLUMNS, build_rows

BOM = "﻿"  # U+FEFF


def csv_response(entries, date_from, date_to):
    rows, total_row = build_rows(entries)

    buffer = io.StringIO()
    buffer.write(BOM)  # Excel の文字化け防止（F-EXP-04）
    writer = _csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    writer.writerow(total_row)

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="kintai_{date_from.isoformat()}_{date_to.isoformat()}.csv"'
    )
    return response
