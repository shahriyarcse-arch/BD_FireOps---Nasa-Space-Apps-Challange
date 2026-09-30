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
    from analysis.download import RAW_DIR, SOURCES
except ImportError:  # running as `python analysis/aggregate.py`
    from download import RAW_DIR, SOURCES

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# Fallback coverage when no raw chunks exist (plan v3 §2 scope)
DEFAULT_WINDOWS = {
    "modis": ("2002-07-01", "2021-12-31"),
    "viirs": ("2012-01-01", "2021-12-31"),
}


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


def _monthly_counts(clean: pd.DataFrame) -> pd.Series:
    if clean.empty or "acq_date" not in clean.columns:
        return pd.Series(dtype="int64")
    dates = pd.to_datetime(clean["acq_date"], errors="coerce", utc=True).dt.tz_localize(None)
    return dates.dt.to_period("M").value_counts().sort_index()


def _month_grid(month_sets: list[set[pd.Period]]) -> pd.PeriodIndex:
    lo = min(min(s) for s in month_sets)
    hi = max(max(s) for s in month_sets)
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



def run_aggregate() -> pd.DataFrame:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    clean_paths = {s: PROCESSED / f"clean_{s}.csv" for s in SOURCES}
    cleans = {}
    for s, p in clean_paths.items():
        try:
            cleans[s] = pd.read_csv(p) if p.exists() else pd.DataFrame()
        except pd.errors.EmptyDataError:
            cleans[s] = pd.DataFrame()


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
    for sensor in SOURCES:
        months = covered_months(sensor)
        if months is None:
            months = default_months(DEFAULT_WINDOWS[sensor])
            print(f"[AGGREGATE] {sensor}: no raw chunks — assuming default window "
                  f"{DEFAULT_WINDOWS[sensor][0]} .. {DEFAULT_WINDOWS[sensor][1]}")
        else:
            print(f"[AGGREGATE] {sensor}: {len(months)} months covered by raw chunks "
                  f"({min(months)} .. {max(months)})")
        coverage[sensor] = months
        windows[sensor] = (str(min(months)), str(max(months)))

    grid = _month_grid(list(coverage.values()))

    out = pd.DataFrame({"month": grid.astype(str)})
    out["year"] = grid.year
    out["month_num"] = grid.month
    out["modis"] = _sensor_column(_monthly_counts(cleans["modis"]), grid, coverage["modis"]).values
    out["viirs"] = _sensor_column(_monthly_counts(cleans["viirs"]), grid, coverage["viirs"]).values

    out.to_csv(PROCESSED / "monthly.csv", index=False)

    prov = {
        "kind": "nasa_firms_api",
        "sources": ["MODIS_SP (reference)", "VIIRS_SNPP_SP (375 m)"],
        "bbox": "91.9,21.4,92.9,23.8",
        "windows": {s: list(w) for s, w in windows.items()},
        "covered_months": {s: len(m) for s, m in coverage.items()},
        "gap_months": {
            s: int(len([p for p in grid if p not in coverage[s]])) for s in SOURCES
        },
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
