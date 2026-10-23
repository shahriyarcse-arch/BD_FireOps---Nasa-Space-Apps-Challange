"""
BD-FireOps: single source of truth for the study time window.

Why this module exists
----------------------
The study end date used to be typed as "2021-12-31" in three separate files
(download.py, clean.py, aggregate.py) plus a year filter in tools/sync_web.py.
That froze the record almost five years behind the present, which is awkward for
a project whose headline argument is the Suomi-NPP shutdown on 1 November 2026.

The end date is now computed once, here, as the last COMPLETE calendar month
before today. A partial current month would otherwise enter the monthly grid as
a genuine low-count month and drag the regression down.

Override it for a frozen, citable re-run:

    BDFIREOPS_STUDY_END=2021-12-31 python probe_firms.py --run-all

Start dates stay fixed: Aqua MODIS standard processing begins July 2002 and the
S-NPP VIIRS 375 m product begins 20 January 2012 (taken as 2012-01-01 for a
clean year grid).
"""

from __future__ import annotations

import datetime as dt
import os

MODIS_START = "2002-07-01"
VIIRS_START = "2012-01-01"
NOAA20_START = "2018-01-01"

ENV_VAR = "BDFIREOPS_STUDY_END"


def last_complete_month_end(today: dt.date | None = None) -> str:
    """Last day of the last fully elapsed calendar month, as YYYY-MM-DD."""
    today = today or dt.date.today()
    first_of_this_month = today.replace(day=1)
    return (first_of_this_month - dt.timedelta(days=1)).isoformat()


def study_end(today: dt.date | None = None) -> str:
    """Study end date: the env override if set, else the last complete month."""
    override = os.getenv(ENV_VAR, "").strip()
    if override:
        try:
            dt.date.fromisoformat(override)
        except ValueError as exc:
            raise SystemExit(
                f"[WINDOW] {ENV_VAR}={override!r} is not a YYYY-MM-DD date."
            ) from exc
        return override
    return last_complete_month_end(today)


def study_windows(today: dt.date | None = None) -> dict[str, tuple[str, str]]:
    """Per-sensor (start, end) download and scope windows."""
    end = study_end(today)
    return {
        "modis": (MODIS_START, end),
        "viirs": (VIIRS_START, end),
        # NOAA-20 VIIRS standard processing begins in 2018, so the leg can be
        # fitted on the S-NPP / NOAA-20 overlap (target: at least 24 months).
        "viirs_noaa20": (NOAA20_START, end),
    }


def study_years(today: dt.date | None = None) -> tuple[int, int]:
    """First and last year in scope, for display grids and map filters."""
    windows = study_windows(today)
    return int(MODIS_START[:4]), int(windows["modis"][1][:4])
