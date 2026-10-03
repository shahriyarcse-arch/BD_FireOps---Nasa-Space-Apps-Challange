"""
Confidence-threshold sensitivity (plan v3 §5).

Question: does keeping low-confidence detections change the fitted relationship?

It re-aggregates the alternative cleaning outputs (`clean_*_lowconf.csv`, written
by `python analysis/clean.py --sensitivity`), refits the SAME time-split model,
and writes data/processed/sensitivity.json. The main metrics.json / charts are
never touched.

Usage:  python tools/sensitivity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.aggregate import (_monthly_counts, _month_grid, _sensor_column,  # noqa: E402
                                covered_months, default_months, DEFAULT_WINDOWS)

PROCESSED = ROOT / "data" / "processed"
TRAIN_END = "2019-01"


def build_monthly(suffix: str, day_only: bool = False) -> pd.DataFrame | None:
    """Baseline comes straight from the pipeline's own monthly.csv (single
    source of truth); alternative scenarios are rebuilt from clean_* CSVs the
    same way analysis/aggregate.py builds the main grid."""
    if suffix == "" and not day_only:
        p = PROCESSED / "monthly.csv"
        if not p.exists():
            return None
        return pd.read_csv(p)[["month", "year", "month_num", "modis", "viirs"]]

    paths = {s: PROCESSED / f"clean_{s}{suffix}.csv" for s in ("modis", "viirs")}
    if not all(p.exists() for p in paths.values()):
        return None

    cleans = {}
    for s, p in paths.items():
        try:
            cleans[s] = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            cleans[s] = pd.DataFrame()
        # Day-only scenario: both sensors restricted to daytime detections so
        # the diurnal mix (VIIRS carries ~9% night rows here) cannot drive the
        # fitted relationship.
        if day_only and not cleans[s].empty and "daynight" in cleans[s].columns:
            cleans[s] = cleans[s][cleans[s]["daynight"].astype(str).str.upper() == "D"]

    coverage = {}
    for s in ("modis", "viirs"):
        months = covered_months(s)
        coverage[s] = months if months is not None else default_months(DEFAULT_WINDOWS[s])

    grid = _month_grid(list(coverage.values()))
    out = pd.DataFrame({"month": grid.astype(str), "year": grid.year, "month_num": grid.month})
    out["modis"] = _sensor_column(_monthly_counts(cleans["modis"]), grid, coverage["modis"]).values
    out["viirs"] = _sensor_column(_monthly_counts(cleans["viirs"]), grid, coverage["viirs"]).values
    return out


def fit_split(monthly: pd.DataFrame) -> dict:
    ov = monthly[monthly["viirs"].notna()].copy()
    ov["modis"] = ov["modis"].astype(float)
    ov["viirs"] = ov["viirs"].astype(float)
    train = ov[ov["month"] < TRAIN_END]
    test = ov[ov["month"] >= TRAIN_END]
    if len(train) < 12 or len(test) < 6:
        return {"error": f"split too small (train={len(train)}, test={len(test)})"}

    m = LinearRegression().fit(train[["viirs"]], train["modis"])
    # Same post-processing as analysis/model.py: negative counts are impossible.
    pred = np.clip(m.predict(test[["viirs"]]), 0, None)

    bias = float(np.mean(pred - test["modis"].to_numpy()))
    return {
        "slope": round(float(m.coef_[0]), 4),
        "intercept": round(float(m.intercept_), 2),
        "test_months": int(len(test)),
        "test_rmse": round(float(np.sqrt(mean_squared_error(test["modis"], pred))), 2),
        "test_bias": round(bias, 2),
        "test_r2": round(float(r2_score(test["modis"], pred)), 4),
    }


def row_count(suffix: str, sensor: str) -> int | None:
    p = PROCESSED / f"clean_{sensor}{suffix}.csv"
    if not p.exists():
        return None
    try:
        return int(len(pd.read_csv(p)))
    except pd.errors.EmptyDataError:
        return 0


def main() -> int:
    baseline = build_monthly("")
    lowconf = build_monthly("_lowconf")
    day_only = build_monthly("", day_only=True)

    if baseline is None:
        print("[SENS] monthly.csv missing — run the pipeline first.")
        return 1
    if lowconf is None:
        print("[SENS] low-confidence outputs missing — run: python analysis/clean.py --sensitivity")
        return 1

    result = {
        "question": "does keeping low-confidence detections (or night rows) change the fitted relationship?",
        "baseline": {"modis_rows": row_count("", "modis"), "viirs_rows": row_count("", "viirs"),
                     **fit_split(baseline)},
        "low_confidence_kept": {"modis_rows": row_count("_lowconf", "modis"),
                                "viirs_rows": row_count("_lowconf", "viirs"),
                                **fit_split(lowconf)},
    }

    b, l = result["baseline"], result["low_confidence_kept"]
    if "slope" in b and "slope" in l:
        d_slope = round(100 * (l["slope"] - b["slope"]) / b["slope"], 2) if b["slope"] else None
        d_rmse = round(100 * (l["test_rmse"] - b["test_rmse"]) / b["test_rmse"], 2) if b["test_rmse"] else None
        result["delta"] = {"slope_percent": d_slope, "test_rmse_percent": d_rmse}

    # Day-only scenario: same grid and split, but detections restricted to
    # daytime (daynight == "D") on both sensors.
    if day_only is not None and "month" in day_only.columns:
        day_fit = fit_split(day_only)
        result["day_only"] = dict(day_fit)
        # Row numbers: count daytime rows from the clean CSVs (the monthly
        # grid holds months, not detections).
        for s in ("modis", "viirs"):
            p = PROCESSED / f"clean_{s}.csv"
            if p.exists():
                try:
                    d = pd.read_csv(p, usecols=["daynight"])
                    result["day_only"][f"{s}_rows"] = int(
                        (d["daynight"].astype(str).str.upper() == "D").sum())
                except (pd.errors.EmptyDataError, ValueError):
                    pass
        db, dd = result["baseline"], result["day_only"]
        if "slope" in db and "slope" in dd and db.get("slope"):
            result["delta_day"] = {
                "slope_percent": round(100 * (dd["slope"] - db["slope"]) / db["slope"], 2),
                "test_rmse_percent": (round(100 * (dd["test_rmse"] - db["test_rmse"]) / db["test_rmse"], 2)
                                      if db.get("test_rmse") else None),
            }

    (PROCESSED / "sensitivity.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("[SENS] baseline        :", json.dumps(b))
    print("[SENS] low-conf kept   :", json.dumps(l))
    if "delta" in result:
        print(f"[SENS] slope change: {result['delta']['slope_percent']}% · "
              f"test RMSE change: {result['delta']['test_rmse_percent']}%")
    if "day_only" in result:
        print("[SENS] day-only        :", json.dumps(result["day_only"]))
    if "delta_day" in result:
        print(f"[SENS] day-only slope change: {result['delta_day']['slope_percent']}% · "
              f"test RMSE change: {result['delta_day']['test_rmse_percent']}%")
    print("[SENS] wrote data/processed/sensitivity.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
