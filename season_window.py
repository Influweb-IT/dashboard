"""Season-window primitives shared by export.py and DataTreatment.py.

A "season" runs from Nov 1 of YEAR_MIN through May 1 of YEAR_MAX = YEAR_MIN + 1.
Stdlib only — no pandas, no numpy — so it's safe to import from contexts that
shouldn't pull in the analysis stack.
"""

from __future__ import annotations

import datetime as _dt

SEASON_START_MONTH = 11   # Nov 1 — start of the influenza season
SEASON_END_MONTH = 5      # May 1 — end of the influenza season


def _today() -> _dt.date:
    return _dt.date.today()


def _compute_year_min(today: _dt.date) -> int:
    if today >= _dt.date(today.year, SEASON_START_MONTH, 1):
        return today.year
    return today.year - 1


def _to_unix(d: _dt.date) -> int:
    return int(_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc).timestamp())


def _iso_week_label(d: _dt.date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


_today_d = _today()

YEAR_MIN: int = _compute_year_min(_today_d)
YEAR_MAX: int = YEAR_MIN + 1
current_season: str = f"{YEAR_MIN}-{YEAR_MAX}"

season_start_date: _dt.date = _dt.date(YEAR_MIN, SEASON_START_MONTH, 1)
season_end_date: _dt.date = _dt.date(YEAR_MAX, SEASON_END_MONTH, 1)

season_start_unix: int = _to_unix(season_start_date)
season_end_unix: int = _to_unix(season_end_date)

last_week_in_season: str = _iso_week_label(min(_today_d, season_end_date))


def iso_week_dir_label(d: _dt.date | None = None) -> str:
    """Label used for raw-bucket prefixes: '2026-W19'."""
    d = d or _today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"
