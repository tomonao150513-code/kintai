# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Design phase. **No application code exists yet** — the repo currently contains only specs under `docs/`.
The next step is implementing **P0** from [docs/task-breakdown.md](docs/task-breakdown.md).

This is a task-based time-tracking ("勤怠") system to be built with Django: record how long you work
on each task via start/stop punches, then aggregate / chart / export the results. Single-user for now,
designed so it can later extend to a team. UI and stored labels are Japanese; code identifiers are English.

## Source of truth

1. [docs/requipuments.md](docs/requipuments.md) — the agreed requirements spec (v0.2). **Wins any conflict.**
   (Filename is a misspelling of "requirements" but is intentional — keep it.)
2. [docs/](docs/) — design that turns the spec into code. Start with [docs/README.md](docs/README.md),
   then [docs/task-breakdown.md](docs/task-breakdown.md).
3. [docs/adr/](docs/adr/) — binding decisions (see "Non-negotiable decisions" below).

When you change behavior that the spec or docs describe, update those files in the same change.

## Workflow

- **Consult `docs/` before and during any work.** For whatever you touch, read the matching file
  first — models → [docs/data-model.md](docs/data-model.md), punch/aggregation/formatting →
  [docs/domain-logic.md](docs/domain-logic.md), screens/URLs → [docs/screens.md](docs/screens.md),
  exports → [docs/export-spec.md](docs/export-spec.md), chart APIs → [docs/api-charts.md](docs/api-charts.md),
  conventions → [docs/coding-guidelines.md](docs/coding-guidelines.md), phase steps →
  [docs/task-breakdown.md](docs/task-breakdown.md). Don't work from memory of them — re-open them.
- **Confirm with the user when a task finishes.** After completing a task or a task-breakdown phase,
  stop and report: what changed, what was run/verified (tests, `runserver`), and anything left open.
  Wait for the user's go-ahead before starting the next task or phase — don't chain phases automatically.
  Tick the checkbox in [docs/task-breakdown.md](docs/task-breakdown.md) as part of that report.

## Planned commands

Once P0 scaffolds the Django project (Windows / PowerShell — see [docs/dev-setup.md](docs/dev-setup.md)):

```powershell
.\.venv\Scripts\Activate.ps1        # activate venv (create once: python -m venv .venv)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # http://127.0.0.1:8000/

pytest                               # full test suite (pytest-django)
pytest attendance/tests/test_timer.py            # one file
pytest attendance/tests/test_timer.py::test_stop # one test
ruff check .
black --check .
```

`requirements.txt` target: `Django>=5.1,<6.0`, `django-environ`, `openpyxl`, `pytest`, `pytest-django`, `ruff`, `black`.
Settings read from `.env` via `django-environ`; copy `.env.example` to `.env` first. No frontend build tooling.

## Architecture (big picture)

Server-rendered Django monolith. No SPA, no DRF. Bootstrap 5 templates; Chart.js reads plain
`JsonResponse` endpoints for graphs. Full rationale + directory tree in [docs/architecture.md](docs/architecture.md).

**Strict layering — do not bypass:** `templates → views → services → models`

- **views** (`attendance/views.py`, function-based): parse input, call a service, render/redirect. No business
  logic, no aggregation SQL, no time math. Auth is enforced globally via `LoginRequiredMiddleware`
  (only the login page is exempt) — individual `@login_required` is not used.
- **services** (`attendance/services/`): the only place business logic lives.
  - `timer.py` — punch state machine: `get_running` / `start` / `stop` / `switch` / `create_manual_entry` / `update_entry` / `delete_entry`. All writes are `transaction.atomic` + `select_for_update()` on the running row. Raises domain exceptions from `attendance/exceptions.py` (`TimerError` subclasses); views catch these and push `messages`.
  - `aggregation.py` — `period_bounds` / `daily_totals` / `by_project` / `by_task`. Operates on **completed entries only** (`end_at IS NOT NULL`).
  - `formatting.py` — `format_hms` / `format_hms_colon` / `format_hours_decimal` / `greeting_message`. Also exposed to templates via `attendance/templatetags/kintai_extras.py` filters (`hms`, `hms_colon`).
- **models** (`attendance/models.py`): `Project` → `Task` → `TimeEntry`, all inheriting `TimeStampedModel`.
  `TimeEntry` with `end_at IS NULL` is "the running timer". Duration is a **property** (`duration`,
  `duration_seconds`), never stored. Exact field/constraint definitions: [docs/data-model.md](docs/data-model.md).

Two Django apps: `accounts` (custom `User`, login/logout, future team features) and `attendance`
(everything else). `config/` holds settings/urls.

## Non-negotiable decisions (from docs/adr/ and the spec)

- **Custom user model from day one**: create `accounts.User(AbstractUser)` (empty) and set
  `AUTH_USER_MODEL = "accounts.User"` *before the first migrate*. ([ADR-0002](docs/adr/0002-auth-user-model.md))
- **One running timer per user**, enforced by a partial `UniqueConstraint` on `TimeEntry`
  (`fields=["user"], condition=Q(end_at__isnull=True)`), not just app-level checks. Switching tasks =
  `stop()` then `start()` in one transaction, after a JS confirm dialog. ([ADR-0005](docs/adr/0005-single-running-timer-constraint.md))
- **No time rounding.** Work time is `end_at - start_at` at second precision, passed around as `int`
  seconds. Display as `1時間30分24秒` (`format_hms` trims only leading zero units). After a stop,
  show `お疲れ様でした！ {hms} 作業しました！`. ([ADR-0004](docs/adr/0004-time-rounding-second-precision.md))
- **Day-crossing entries count entirely on their start date** (`work_date = localdate(start_at)`);
  no splitting across the midnight boundary. ([ADR-0003](docs/adr/0003-day-crossing-aggregation.md))
- **Break-time deduction is deferred** but must stay easy to add: keep all duration math in
  `TimeEntry.duration` + services, never inline in views/templates. ([docs/data-model.md](docs/data-model.md) §3.3)
- `TIME_ZONE = "Asia/Tokyo"`, `USE_TZ = True`. Never use `datetime.now()` — use `django.utils.timezone`.
  Store UTC, display via `timezone.localtime`.
- Every save path (services, forms, admin) must call `full_clean()` before `save()` — the same-user
  time-overlap rule lives in `TimeEntry.clean()` and DB constraints won't catch it.
- State-changing routes are POST + CSRF only. Always scope queries to `request.user` / `owner=request.user`
  and use `get_object_or_404`; other users' rows must 404.

## Exports & chart APIs

- CSV/Excel column order, UTF-8 BOM requirement, total row, filename pattern (`kintai_{from}_{to}.csv`):
  [docs/export-spec.md](docs/export-spec.md). Row assembly is shared via `attendance/exports/rows.py`.
- Chart JSON endpoints (`/api/stats/daily/`, `/by-project/`, `/by-task/`) params and response shapes:
  [docs/api-charts.md](docs/api-charts.md). `daily_totals` zero-fills empty days.

## Screens & URLs

10 screens (S-01 dashboard … S-10 export) with their URL names, context variables, and transitions
are specified in [docs/screens.md](docs/screens.md). Term ↔ identifier mapping: [docs/glossary.md](docs/glossary.md).
