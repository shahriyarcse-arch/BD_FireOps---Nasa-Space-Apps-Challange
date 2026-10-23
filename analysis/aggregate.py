"""
BD-FireOps: Monthly Regional Aggregation
Plan v3 §5 — turns cleaned detections into the model input table.

Output: data/processed/monthly.csv  (month, year, month_num, modis, viirs)

Rules:
  * regional monthly counts — NOT paired fire-level detections
  * zero-detection months are KEPT as 0 inside a sensor's coverage window
    (dropping them would inflate both sensors and bias the regression)
  * months outside a sensor's coverage stay blank (NaN), never 0
  * coverage windows are read from data/raw/<sensor>/ chunk filenames so a
    partial download is never mistaken for a full one
  * provenance lands in data_source.json so every downstream artefact can state
    whether it was built from NASA FIRMS observations or labelled demo data
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

try:
    from analysis.download import RAW_DIR, SOURCES, EXTENDED_SOURCES
except ImportError:  # running as `python analysis/aggregate.py`
    from download import RAW_DIR, SOURCES, EXTENDED_SOURCES

try:
    from analysis.clean import REGION_DISTRICTS, assign_districts
except ImportError:  # running as `python analysis/aggregate.py`
    from clean import REGION_DISTRICTS, assign_districts

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# Fallback coverage when no raw chunks exist. The real grid is still derived from
# the raw chunk filenames, so widening the window never invents empty months.
try:
    from analysis.window import study_windows
except ImportError:  # running as `python analysis/aggregate.py`
    from window import study_windows

DEFAULT_WINDOWS = study_windows()


def covered_months(sensor: str) -> set[pd.Period] | None:
    """
    Which months does data/raw/<sensor>/ actually cover?

    Chunk filenames are <start>_<end>.csv, so a month counts as covered only if
    some chunk overlaps it. A month with no chunk at all is "no data" (NaN), not
    "zero fire" — that distinction is what stops orbital/delivery gaps from
    being read as fire-free months.
    """
    out_dir = RAW_DIR / sensor
    if not out_dir.exists():
        return None
    months: set[pd.Period] = set()
    found = False
    for f in sorted(out_dir.glob("*.csv")):
        try:
            s, e = f.stem.split("_")
            start = dt.date.fromisoformat(s)
            end = dt.date.fromisoformat(e)
        except ValueError:
            continue
        found = True
        months.update(pd.period_range(pd.Period(start, freq="M"), pd.Period(end, freq="M"), freq="M"))
    return months if found else None


def default_months(window: tuple[str, str]) -> set[pd.Period]:
    return set(pd.period_range(pd.Period(window[0], freq="M"), pd.Period(window[1], freq="M"), freq="M"))


def _audit_window(sensor: str) -> tuple[str, str] | None:
    """The study window that actually produced clean_<sensor>.csv.

    With no raw chunks left on disk (a fresh clone ships processed artefacts
    only), falling back to the *current* dynamic window would invent months
    between the last download and today and fill them with zeros. The clean
    audit recorded the real window, so reuse it instead.
    """
    path = PROCESSED / "clean_audit_baseline.json"
    if not path.exists():
        return None
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    entry = audit.get(sensor) if isinstance(audit, dict) else None
    window = (entry or {}).get("study_window", "")
    try:
        start, end = [part.strip() for part in window.split("..")]
        dt.date.fromisoformat(start)
        dt.date.fromisoformat(end)
    except ValueError:
        return None
    return start, end


def _monthly_counts(clean: pd.DataFrame) -> pd.Series:
    if clean.empty or "acq_date" not in clean.columns:
        return pd.Series(dtype="int64")
    dates = pd.to_datetime(clean["acq_date"], errors="coerce", utc=True).dt.tz_localize(None)
    return dates.dt.to_period("M").value_counts().sort_index()


def _month_grid(month_sets: list[set[pd.Period]]) -> pd.PeriodIndex:
    non_empty = [s for s in month_sets if s]
    if not non_empty:
        raise SystemExit(
            "[AGGREGATE] No coverage months found for any sensor — "
            "data/raw/<sensor>/ has no chunks (or they carry no parseable dates). "
            "Re-run analysis/download.py before aggregating."
        )
    lo = min(min(s) for s in non_empty)
    hi = max(max(s) for s in non_empty)
    return pd.period_range(lo, hi, freq="M")


def _sensor_column(counts: pd.Series, grid: pd.PeriodIndex, covered: set[pd.Period]) -> pd.Series:
    """
    0 inside a covered month (a real zero-detection month), NaN outside coverage
    (no data). Reporting 0 outside coverage would claim "no fire" instead of
    "no data".
    """
    values = []
    for p in grid:
        if p in counts.index:
            values.append(int(counts.loc[p]))
        elif p in covered:
            values.append(0)
        else:
            values.append(float("nan"))
    return pd.Series(values, index=grid)


def _sensor_month_counts(clean: pd.DataFrame) -> pd.Series:
    """Monthly detection counts, unchanged from the regional aggregation."""
    return _monthly_counts(clean)


def _district_monthly(cleans: dict, active: list[str], grid: pd.PeriodIndex,
                      coverage: dict[str, set[pd.Period]]) -> pd.DataFrame:
    """One row per (month, district) with one count column per active sensor.

    Uses the same zero-inside-coverage / NaN-outside rule as the regional grid,
    so the per-district series sum back to monthly.csv exactly.
    """
    per_sensor: dict[str, dict] = {}
    for sensor in active:
        clean = cleans[sensor]
        keyed: dict = {}
        if not clean.empty:
            labelled = clean.copy()
            labelled["district"] = assign_districts(labelled)
            labelled = labelled[labelled["district"] != ""]
            dates = pd.to_datetime(labelled["acq_date"], errors="coerce", utc=True).dt.tz_localize(None)
            labelled = labelled[dates.notna()].copy()
            labelled["period"] = dates[dates.notna()].dt.to_period("M")
            for (district, period), n in labelled.groupby(["district", "period"]).size().items():
                keyed[(district, period)] = int(n)
            assigned = int(len(labelled))
            if assigned != int(len(clean)):
                raise SystemExit(
                    f"[AGGREGATE] {sensor.upper()}: district assignment kept {assigned} of "
                    f"{len(clean)} clean rows. Every clean row must fall inside exactly one "
                    "district polygon; per-district series would not sum to the regional total."
                )
        per_sensor[sensor] = keyed

    rows = []
    for period in grid:
        for district in REGION_DISTRICTS:
            row = {"month": str(period), "district": district}
            for sensor in active:
                if (district, period) in per_sensor[sensor]:
                    row[sensor] = per_sensor[sensor][(district, period)]
                elif period in coverage[sensor]:
                    row[sensor] = 0
                else:
                    row[sensor] = float("nan")
            rows.append(row)
    return pd.DataFrame(rows)


def _gap_ranges(grid: pd.PeriodIndex, covered: set[pd.Period]) -> list[list[str]]:
    """Contiguous uncovered month ranges inside the grid (a delivery gap, not a quiet month)."""
    ranges: list[list[str]] = []
    start = None
    prev = None
    for p in grid:
        if p not in covered:
            if start is None:
                start = p
            prev = p
        elif start is not None:
            ranges.append([str(start), str(prev)])
            start = None
            prev = None
    if start is not None:
        ranges.append([str(start), str(prev)])
    return ranges


def run_aggregate() -> pd.DataFrame:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    # Required sensors define the record. The NOAA-20 leg joins only when its
    # cleaned series exists, so a not-yet-downloaded archive is reported as
    # unavailable rather than failing the whole pipeline.
    active = list(SOURCES)
    cleans = {}
    for s in list(SOURCES) + list(EXTENDED_SOURCES):
        p = PROCESSED / f"clean_{s}.csv"
        try:
            frame = pd.read_csv(p) if p.exists() else pd.DataFrame()
        except pd.errors.EmptyDataError:
            frame = pd.DataFrame()
        if s in EXTENDED_SOURCES and frame.empty:
            continue
        cleans[s] = frame
    for s in EXTENDED_SOURCES:
        if s in cleans:
            active.append(s)

    if all(c.empty for c in cleans.values()):
        raw_present = any(
            (RAW_DIR / s).exists() and any((RAW_DIR / s).glob("*.csv")) for s in SOURCES
        )
        # A labelled demo run writes monthly.csv directly and never goes through
        # raw -> clean, so pass it through — but never if real raw data exists,
        # because a demo table surviving a real run would be a silent lie.
        src = PROCESSED / "data_source.json"
        if not raw_present and (PROCESSED / "monthly.csv").exists() and src.exists():
            kind = json.loads(src.read_text(encoding="utf-8")).get("kind")
            if kind != "nasa_firms_api":
                print(f"[AGGREGATE] No raw detections — reusing existing '{kind}' monthly.csv "
                      "(no aggregation applied).")
                return pd.read_csv(PROCESSED / "monthly.csv")
        raise SystemExit(
            "[AGGREGATE] No cleaned detections found.\n"
            "  Real data : put FIRMS_MAP_KEY in .env, then\n"
            "              python probe_firms.py --run-all\n"
            "  Demo data : python probe_firms.py --demo"
        )

    # One sensor with zero clean rows must never be filled with fabricated 0s
    # across its whole window - that would publish an invented all-zero NASA
    # series into monthly.csv -> metrics.json -> README/UI. Fail loudly instead.
    for s, c in cleans.items():
        if c.empty:
            raise SystemExit(
                f"[AGGREGATE] {s.upper()}: 0 clean rows in data/processed/clean_{s}.csv.\n"
                f"  Refusing to fabricate an all-zero {s} series.\n"
                "  Inspect data/processed/clean_audit_*.json, then re-run analysis/clean.py."
            )


    coverage: dict[str, set[pd.Period]] = {}
    windows: dict[str, tuple[str, str]] = {}
    for sensor in active:
        months = covered_months(sensor)
        if months is None:
            audited = _audit_window(sensor)
            fallback = audited or DEFAULT_WINDOWS[sensor]
            months = default_months(fallback)
            note = "from clean_audit_baseline.json" if audited else "assumed default"
            print(f"[AGGREGATE] {sensor}: no raw chunks — coverage {note} "
                  f"{fallback[0]} .. {fallback[1]}")
        else:
            print(f"[AGGREGATE] {sensor}: {len(months)} months covered by raw chunks "
                  f"({min(months)} .. {max(months)})")
        coverage[sensor] = months
        windows[sensor] = (str(min(months)), str(max(months)))

    grid = _month_grid(list(coverage.values()))

    # Defence-in-depth: clean.py clamps to the study window, but if a clean row
    # ever falls outside the monthly grid it would vanish silently here.
    # Fail loudly (or count loudly) instead of publishing a censored series.
    for s in active:
        counts = _monthly_counts(cleans[s])
        outside = [str(p) for p in counts.index if p not in grid]
        if outside:
            raise SystemExit(
                f"[AGGREGATE] {s.upper()}: {len(outside)} clean month(s) outside the monthly grid "
                f"({', '.join(sorted(outside)[:5])}) — clean.py study-window clamp and "
                "data/raw chunk coverage disagree. Refusing to silently drop them."
            )

    out = pd.DataFrame({"month": grid.astype(str)})
    out["year"] = grid.year
    out["month_num"] = grid.month
    for sensor in list(SOURCES) + list(EXTENDED_SOURCES):
        if sensor in active:
            out[sensor] = _sensor_column(_monthly_counts(cleans[sensor]), grid, coverage[sensor]).values
        else:
            # Present but empty: the leg was not downloaded, not "zero fires".
            out[sensor] = float("nan")

    out.to_csv(PROCESSED / "monthly.csv", index=False)

    districts = _district_monthly(cleans, active, grid, coverage)
    districts.to_csv(PROCESSED / "monthly_districts.csv", index=False)

    gap_ranges = {s: _gap_ranges(grid, coverage[s]) for s in active}
    source_labels = {
        "modis": "MODIS_SP (Aqua reference)",
        "viirs": "VIIRS_SNPP_SP (375 m)",
        "viirs_noaa20": "VIIRS_NOAA20_SP (375 m forward leg)",
    }
    prov = {
        "kind": "nasa_firms_api",
        "sources": [source_labels[s] for s in active],
        "active_sensors": active,
        "absent_sensors": [s for s in EXTENDED_SOURCES if s not in active],
        "bbox": "91.9,21.4,92.9,23.8",
        "windows": {s: list(w) for s, w in windows.items()},
        "covered_months": {s: len(m) for s, m in coverage.items()},
        "gap_months": {
            s: int(len([p for p in grid if p not in coverage[s]])) for s in active
        },
        "coverage_gaps": gap_ranges,
        "districts": list(REGION_DISTRICTS),
        "district_aggregation":
            "per-district monthly detection counts (monthly_districts.csv); districts sum to the regional series",
        "clean_detections": {s: int(len(c)) for s, c in cleans.items()},
        "rows": int(len(out)),
        "zero_months_kept": True,
        "aggregation": "regional monthly detection counts (not paired fire-level detections)",
    }
    (PROCESSED / "data_source.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")

    overlap = out[out["viirs"].notna()]
    print(f"[AGGREGATE] monthly.csv: {len(out)} months, overlap {len(overlap)} months")
    print(f"[AGGREGATE] clean detections: MODIS={prov['clean_detections']['modis']}, "
          f"VIIRS={prov['clean_detections']['viirs']}")
    print(f"[AGGREGATE] MODIS zero-months={int((out['modis'] == 0).sum())}, "
          f"VIIRS zero-months={int((overlap['viirs'] == 0).sum())}")
    if prov["gap_months"]["modis"] or prov["gap_months"]["viirs"]:
        print(f"[AGGREGATE] months with NO data (blank, not 0): "
              f"MODIS={prov['gap_months']['modis']}, VIIRS={prov['gap_months']['viirs']}")
    if overlap.empty:
        print("[AGGREGATE] WARNING: no overlapping MODIS/VIIRS months — model step will stop.")
    return out



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BD-FireOps monthly aggregator")
    parser.parse_args(argv)
    run_aggregate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
