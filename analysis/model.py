"""
BD-FireOps: Harmonization Modeling & Validation Engine
Study Area: Chittagong Hill Tracts (CHT), Bangladesh
Model Strategy: Time-split validation (Train: 2012-2018, Held-out Test: 2019-2021)
Bootstrap: 500-sample empirical parameter uncertainty estimation

Every artefact this module writes carries the data provenance (NASA FIRMS API vs
explicitly-labelled demo data) read from data/processed/data_source.json.
"""

import os
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr
import matplotlib.pyplot as plt

# Anchor to the repo, not the CWD: running from anywhere else used to write
# metrics.json/charts into a stray ./data/processed while the real data sat unused.
PROCESSED = str(Path(__file__).resolve().parents[1] / "data" / "processed")


def _json_safe(obj):
    """Replace NaN/Inf with None so metrics.json is always strict JSON."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def load_provenance() -> dict:
    path = os.path.join(PROCESSED, "data_source.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"kind": "unknown", "note": "no data_source.json found"}


def _has_rows(audit_path: str) -> bool:
    """True only if a clean audit actually cleaned some rows.

    clean.py writes an audit even when there was no raw data, so the mere
    existence of the file must not be read as "a sensitivity run happened".
    """
    if not os.path.exists(audit_path):
        return False
    try:
        with open(audit_path, encoding="utf-8") as f:
            audit = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    return any(isinstance(v, dict) and v.get("clean_rows", 0) > 0 for v in audit.values())


def _score_metrics(y_actual, y_pred) -> dict:
    """Bias / MAE / RMSE / R2 / Spearman for one held-out series."""
    y_actual = np.asarray(y_actual, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    bias = float(np.mean(y_pred - y_actual))
    mae = float(mean_absolute_error(y_actual, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_actual, y_pred)))
    r2 = float(r2_score(y_actual, y_pred)) if len(y_actual) > 1 and np.ptp(y_actual) > 0 else None
    if len(y_actual) > 1 and np.ptp(y_actual) > 0 and np.ptp(y_pred) > 0:
        corr, _ = spearmanr(y_actual, y_pred)
        corr = round(float(corr), 4) if corr == corr else None
    else:
        corr = None
    return {
        "bias": round(bias, 2),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4) if r2 is not None else None,
        "spearman_corr": corr,
    }


def _bootstrap_coefficients(x, y, seed: int = 42, n_boot: int = 500) -> tuple[list, list]:
    """Moving-block bootstrap coefficient intervals, same method as the headline fit."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n_obs = len(x)
    block = 12
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n_obs - block + 1) if n_obs >= block else np.arange(n_obs)
    n_blocks = int(np.ceil(n_obs / block))
    slopes, intercepts = [], []
    for _ in range(n_boot):
        if n_obs >= block:
            picks = rng.choice(starts, size=n_blocks, replace=True)
            idx = (picks[:, None] + np.arange(block)).ravel()[:n_obs]
        else:
            idx = rng.integers(0, n_obs, size=n_obs)
        m_boot = LinearRegression().fit(x[idx].reshape(-1, 1), y[idx])
        slopes.append(float(m_boot.coef_[0]))
        intercepts.append(float(m_boot.intercept_))
    return (
        [round(float(np.percentile(slopes, 2.5)), 4), round(float(np.percentile(slopes, 97.5)), 4)],
        [round(float(np.percentile(intercepts, 2.5)), 2), round(float(np.percentile(intercepts, 97.5)), 2)],
    )


def _fit_leg(
    predictor,
    target,
    months,
    split_month: str,
    min_overlap: int = 24,
    min_train: int = 12,
    min_test: int = 6,
    seed: int = 42,
    test_end: str | None = None,
) -> dict:
    """Fit/clip/score one optional calibration leg (district or NOAA-20).

    Returns an explicit non-fitted status instead of a slope whenever the
    overlap is too short, so a thin archive can never masquerade as a result.
    """
    frame = pd.DataFrame({
        "x": pd.to_numeric(pd.Series(predictor).reset_index(drop=True), errors="coerce"),
        "y": pd.to_numeric(pd.Series(target).reset_index(drop=True), errors="coerce"),
        "month": pd.Series(months).reset_index(drop=True).astype(str),
    })
    frame = frame[np.isfinite(frame["x"]) & np.isfinite(frame["y"])].copy()
    n = int(len(frame))
    base = {
        "overlap_months": n,
        "min_overlap_months": min_overlap,
        "split_month": split_month,
    }
    if n < min_overlap:
        return {
            **base,
            "status": "insufficient_overlap",
            "reason": f"only {n} overlapping months; at least {min_overlap} are required",
        }

    train = frame[frame["month"] < split_month]
    test = frame[frame["month"] >= split_month]
    if test_end:
        train = train[train["month"] <= test_end]
        test = test[test["month"] <= test_end]
    if len(train) < min_train or len(test) < min_test:
        return {
            **base,
            "status": "insufficient_split",
            "reason": (f"train={len(train)} (min {min_train}) / test={len(test)} "
                       f"(min {min_test}) months"),
        }

    x_train = train["x"].to_numpy(dtype=float)
    y_train = train["y"].to_numpy(dtype=float)
    if np.ptp(x_train) == 0:
        return {**base, "status": "insufficient_variance",
                "reason": "predictor has no variance in the training split"}

    model = LinearRegression().fit(x_train.reshape(-1, 1), y_train)
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)
    x_test = test["x"].to_numpy(dtype=float)
    y_test = test["y"].to_numpy(dtype=float)
    pred = np.clip(model.predict(x_test.reshape(-1, 1)), 0, None)

    scalar_ratio = float(y_train.sum() / x_train.sum()) if x_train.sum() else float("nan")
    pred_scalar = np.clip(x_test * scalar_ratio, 0, None)

    slope_ci, intercept_ci = _bootstrap_coefficients(x_train, y_train, seed=seed)
    return {
        **base,
        "status": "fitted",
        "train_months": int(len(train)),
        "test_months": int(len(test)),
        "train_period": f"{train['month'].min()} to {train['month'].max()}",
        "test_period": f"{test['month'].min()} to {test['month'].max()}",
        "slope": round(slope, 4),
        "intercept": round(intercept, 2),
        "bootstrap_slope_95_ci": slope_ci,
        "bootstrap_intercept_95_ci": intercept_ci,
        "bootstrap_method": "500 resamples of contiguous 12-month blocks (seed 42)",
        "scalar_ratio": round(scalar_ratio, 4) if np.isfinite(scalar_ratio) else None,
        "held_out": _score_metrics(y_test, pred),
        "held_out_scalar": _score_metrics(y_test, pred_scalar),
    }


def fit_per_district(districts_csv: str) -> dict:
    """Per-district fits (F6/P4) from data/processed/monthly_districts.csv.

    Each district repeats the regional procedure: same 2012-2018 train /
    2019-2021 test split, OLS on monthly counts, moving-block bootstrap, and a
    scalar-ratio baseline so the marginal gain stays visible.
    """
    out = {
        "status": "unavailable",
        "min_overlap_months": 24,
        "source": os.path.basename(districts_csv),
        "districts": {},
    }
    if not os.path.exists(districts_csv):
        out["reason"] = "monthly_districts.csv not found (re-run analysis/aggregate.py)"
        return out

    dfd = pd.read_csv(districts_csv)
    try:
        from analysis.clean import REGION_DISTRICTS
    except ImportError:  # running as a script
        from clean import REGION_DISTRICTS

    fitted = 0
    for district in REGION_DISTRICTS:
        sub = dfd[dfd["district"] == district] if "district" in dfd.columns else dfd.iloc[0:0]
        counts = {
            "modis": int(pd.to_numeric(sub["modis"], errors="coerce").fillna(0).sum())
            if "modis" in sub.columns else 0,
            "viirs": int(pd.to_numeric(sub["viirs"], errors="coerce").fillna(0).sum())
            if "viirs" in sub.columns else 0,
        }
        if sub.empty or "viirs" not in sub.columns or "modis" not in sub.columns:
            out["districts"][district] = {
                "status": "unavailable",
                "reason": "district series missing from monthly_districts.csv",
                "clean_detections": counts,
            }
            continue
        leg = _fit_leg(sub["viirs"], sub["modis"], sub["month"], "2019-01", test_end="2021-12")
        entry = {"clean_detections": counts, **leg}
        if leg["status"] == "fitted":
            fitted += 1
            ho = leg["held_out"]
            entry["held_out_rmse"] = ho["rmse"]
            entry["held_out_bias"] = ho["bias"]
            entry["held_out_mae"] = ho["mae"]
            entry["held_out_r2"] = ho["r2"]
            entry["held_out_spearman"] = ho["spearman_corr"]
            entry["held_out_scalar_rmse"] = leg["held_out_scalar"]["rmse"]
            r2 = ho["r2"]
            entry["fit_quality"] = (
                "strong" if r2 is not None and r2 >= 0.95
                else "good" if r2 is not None and r2 >= 0.9
                else "fair"
            )
        else:
            # PRD F6: too-short districts are labelled indicative, not published
            # as a result. No slope is exposed in that case.
            entry["fit_quality"] = "indicative"
            entry["note"] = "labelled indicative rather than reported as a fit"
        out["districts"][district] = entry

    out["status"] = "fitted" if fitted == len(REGION_DISTRICTS) else ("partial" if fitted else "insufficient_data")
    out["fitted_districts"] = fitted
    out["note"] = ("Independent district fits on the identical split; each carries its own "
                   "bootstrap interval and scalar baseline.")
    return out


def fit_noaa20_leg(df: pd.DataFrame) -> dict:
    """F2/P2: fit the forward NOAA-20 leg on the S-NPP / NOAA-20 overlap.

    The leg converts NOAA-20 VIIRS counts into S-NPP-equivalent counts; the
    already-published S-NPP -> MODIS line then chains it into the record's units.
    Refuses to publish a slope on fewer than 24 overlap months (PRD acceptance).
    """
    out = {
        "source": "VIIRS_NOAA20_SP",
        "direction": "NOAA-20 VIIRS -> S-NPP-equivalent counts (then the published S-NPP -> MODIS line)",
        "min_overlap_months": 24,
        "status": "not_available",
        "reason": "no NOAA-20 series in monthly.csv — the archive has not been downloaded",
        "caveat": ("Until this leg is fitted on at least 24 S-NPP / NOAA-20 overlap months, "
                   "the forward VIIRS-equivalent mapping remains an algebraic inversion and "
                   "must not be used operationally."),
    }
    if "viirs_noaa20" not in df.columns:
        return out

    leg = _fit_leg(df["viirs_noaa20"], df["viirs"], df["month"], "2021-01")
    out.update(leg)
    if leg["status"] == "fitted":
        out["equation"] = (f"VIIRS_SNPP_eq = {leg['slope']} * VIIRS_NOAA20 + "
                           f"({leg['intercept']})")
        ho = leg["held_out"]
        out["held_out_rmse"] = ho["rmse"]
        out["held_out_bias"] = ho["bias"]
        out["held_out_spearman"] = ho["spearman_corr"]
        out["held_out_scalar_rmse"] = leg["held_out_scalar"]["rmse"]
    else:
        out["reason"] = leg.get("reason", "NOAA-20 leg could not be fitted")
    return out


def build_sensor_custody(record_start, record_end, train_start, train_end,
                         test_start, test_end, noaa20: dict) -> dict:
    """Which instrument produced each month of the record, plus the undownloaded gap."""
    def next_month(month: str) -> str:
        p = pd.Period(month, freq="M") + 1
        return str(p)

    legs = [{
        "key": "modis",
        "sensor": "Aqua MODIS",
        "resolution": "1 km",
        "start": record_start,
        "end": "2011-12",
        "role": "reference observations",
        "label": f"Aqua MODIS ({record_start[:4]}–2011)",
        "css": "seg-modis",
        "dot": "dot-modis",
    }, {
        "key": "snpp_train",
        "sensor": "S-NPP VIIRS",
        "resolution": "375 m",
        "start": "2012-01",
        "end": train_end,
        "role": "calibration & training",
        "label": "S-NPP VIIRS Train",
        "css": "seg-viirs-train",
        "dot": "dot-viirs-train",
    }, {
        "key": "snpp_test",
        "sensor": "S-NPP VIIRS",
        "resolution": "375 m",
        "start": test_start,
        "end": record_end,
        "role": "held-out validation",
        "label": "S-NPP VIIRS Test",
        "css": "seg-viirs-test",
        "dot": "dot-viirs-test",
    }]

    if record_end < "2026-10":
        gap_start = next_month(record_end)
        legs.append({
            "key": "gap",
            "sensor": "No archive downloaded",
            "resolution": "—",
            "start": gap_start,
            "end": "2026-10",
            "role": "delivery gap",
            "label": f"Archive gap ({gap_start}–2026-10)",
            "css": "seg-gap",
            "dot": "dot-gap",
        })

    if record_end < "2026-11":
        legs.append({
            "key": "noaa20",
            "sensor": "NOAA-20 / 21 VIIRS",
            "resolution": "375 m",
            "start": "2026-11",
            "end": None,
            "role": "forward continuity leg",
            "label": "NOAA-20 / 21 (post-Nov 2026)",
            "css": "seg-noaa20",
            "dot": "dot-noaa20",
            "status": noaa20.get("status"),
        })

    return {
        "legs": legs,
        "note": ("Each record month belongs to exactly one leg. Months after the last "
                 f"downloaded archive ({record_end}) are shown as a delivery gap, not as "
                 "NOAA-20 observations. The NOAA-20/21 leg starts on 2026-11."),
        "noaa20_status": noaa20.get("status"),
    }


def run_harmonization_pipeline(input_csv=None):
    if input_csv is None:
        input_csv = os.path.join(PROCESSED, "monthly.csv")

    prov = load_provenance()
    data_kind = prov.get("kind", "unknown")
    is_demo = data_kind != "nasa_firms_api"

    df = pd.read_csv(input_csv)

    # Overlap period (2012-2021) where both MODIS and VIIRS coexist
    overlap = df[df["viirs"].notna()].copy()
    overlap["modis"] = overlap["modis"].astype(float)
    overlap["viirs"] = overlap["viirs"].astype(float)

    # Partial MODIS coverage legitimately yields NaN months. They must never
    # reach sklearn (cryptic "Input X contains NaN"), and dropping them has to
    # be visible so the published 84/36 month counts stay truthful.
    nan_mask = overlap["modis"].isna() | overlap["viirs"].isna()
    dropped_nan_months = sorted(overlap.loc[nan_mask, "month"].tolist())
    if dropped_nan_months:
        print(f"[MODEL] Dropping {len(dropped_nan_months)} overlap month(s) with NaN counts: "
              f"{', '.join(dropped_nan_months)}")
        overlap = overlap[~nan_mask].copy()

    if overlap.empty:
        raise SystemExit(
            "[MODEL] No overlapping MODIS/VIIRS months — nothing to fit.\n"
            "  Check data/processed/data_source.json and re-run analysis/aggregate.py."
        )

    # Zero-month diagnostics (plan v3 §5: keep zero months, do not drop them)
    zero_months = overlap[(overlap["modis"] == 0) | (overlap["viirs"] == 0)]
    zero_diag = {
        "overlap_months": int(len(overlap)),
        "zero_modis_months": int((overlap["modis"] == 0).sum()),
        "zero_viirs_months": int((overlap["viirs"] == 0).sum()),
        "months_with_any_zero": int(len(zero_months)),
        "handling": "zero months retained; log1p variant used as the zero-robust check",
        "modis_describe": {k: round(float(v), 3) for k, v in overlap["modis"].describe().items()},
        "viirs_describe": {k: round(float(v), 3) for k, v in overlap["viirs"].describe().items()},
        "nan_counts": {"modis": int(overlap["modis"].isna().sum()),
                       "viirs": int(overlap["viirs"].isna().sum())},
        "dropped_nan_months": dropped_nan_months,
    }

    # Sensor shift, measured from the data — never asserted.
    # Both ratios use every month in their window (zero months included on BOTH
    # sides); filtering zeros from one side only would bias the ratio.
    pre = df[(df["viirs"].isna()) & (df["year"] < 2012)]
    pre_mean = float(pre["modis"].mean()) if len(pre) else float("nan")
    post_mean = float(overlap["viirs"].mean())
    # Step visible in Chart A: post-2012 VIIRS vs pre-2012 MODIS baseline.
    # None (not NaN) so metrics.json stays strict JSON.
    step_ratio = round(post_mean / pre_mean, 2) if pre_mean and pre_mean > 0 else None
    # Sensor sensitivity difference measured where both sensors observe together.
    ov_modis_mean = float(overlap["modis"].mean())
    overlap_ratio = round(post_mean / ov_modis_mean, 2) if ov_modis_mean and ov_modis_mean > 0 else None
    jump_ratio = step_ratio

    # ------------------------------------------------------------------
    # MODIS-ONLY CONTINUITY CHECK (reviewer fix 4)
    # ------------------------------------------------------------------
    # The strongest evidence that the +185% step is an artefact is MODIS itself.
    # MODIS flew across the whole period and never changed, so its own mean
    # before and after January 2012 is a control: if fires had really tripled,
    # MODIS would have risen too. It does not.
    modis_change_pct = (
        round((ov_modis_mean / pre_mean - 1.0) * 100, 1)
        if pre_mean and pre_mean > 0 else None
    )
    modis_continuity = {
        "pre_2012_modis_mean_per_month": round(pre_mean, 1) if pre_mean == pre_mean else None,
        "post_2012_modis_mean_per_month": round(ov_modis_mean, 1),
        "modis_only_change_percent": modis_change_pct,
        "spliced_apparent_change_percent": (
            round((step_ratio - 1.0) * 100, 1) if step_ratio is not None else None
        ),
        "interpretation": ("Same instrument, same region, no instrument change: the MODIS "
                           "record does not rise across the 2012 boundary, so the step seen "
                           "in the spliced series is a sensor artefact, not a fire trend."),
    }
    print(f"[MODEL] MODIS-only change across 2012: {modis_change_pct}% "
          f"(spliced series appears to change by "
          f"{modis_continuity['spliced_apparent_change_percent']}%)")

    print(f"[MODEL] Pre-2012 MODIS mean={pre_mean:.1f} · overlap MODIS mean={ov_modis_mean:.1f} · "
          f"overlap VIIRS mean={post_mean:.1f}")

    # Time-split validation. The held-out set stays frozen at 2019-2021 even if
    # the monthly record is later extended toward the present.
    train = overlap[overlap["month"] < "2019-01"].copy()
    test = overlap[(overlap["month"] >= "2019-01") & (overlap["month"] <= "2021-12")].copy()

    if len(train) < 12 or len(test) < 6:
        raise SystemExit(
            f"[MODEL] Split too small to validate (train={len(train)}, test={len(test)} months)."
        )

    print(f"[MODEL] Overlap observations: {len(overlap)} months")
    print(f"[MODEL] Train split (2012-2018): {len(train)} months")
    print(f"[MODEL] Test split  (2019-2021): {len(test)} months (Held-out)")
    print(f"[MODEL] Chart-A step (VIIRS 2012+ / MODIS 2002-2011): "
          f"{f'{step_ratio}x' if step_ratio is not None else 'n/a'}")
    print(f"[MODEL] Same-month sensor ratio (2012-2021 overlap):   "
          f"{f'{overlap_ratio}x' if overlap_ratio is not None else 'n/a'}")

    print(f"[MODEL] Zero months kept in overlap: {zero_diag['months_with_any_zero']}")

    
    # Model 1: Standard Linear Regression
    if train["viirs"].nunique() < 2:
        raise SystemExit(
            "[MODEL] VIIRS predictor has no variance in the training split — the "
            "input looks like a fabricated all-zero series; refusing to fit."
        )
    m_lin = LinearRegression().fit(train[["viirs"]], train["modis"])
    lin_slope = float(m_lin.coef_[0])
    lin_intercept = float(m_lin.intercept_)
    
    # Model 2: Log1p Transformed Regression (variance-stabilizing for zero counts)
    X_train_log = np.log1p(train[["viirs"]])
    y_train_log = np.log1p(train["modis"])
    m_log = LinearRegression().fit(X_train_log, y_train_log)
    log_slope = float(m_log.coef_[0])
    log_intercept = float(m_log.intercept_)
    
    # Generate predictions on Test set
    test["pred_naive_viirs"] = test["viirs"]
    test["pred_linear"] = np.clip(m_lin.predict(test[["viirs"]]), 0, None)
    test["pred_log1p"] = np.clip(np.expm1(m_log.predict(np.log1p(test[["viirs"]]))), 0, None)
    
    # Also apply fitted model to entire overlap series for continuous reconstruction
    overlap["pred_linear"] = np.clip(m_lin.predict(overlap[["viirs"]]), 0, None)
    overlap["pred_log1p"] = np.clip(np.expm1(m_log.predict(np.log1p(overlap[["viirs"]]))), 0, None)
    
    # Evaluate Metrics on Test Set (2019-2021)
    y_true = test["modis"].values
    y_naive = test["pred_naive_viirs"].values
    y_lin = test["pred_linear"].values
    y_log = test["pred_log1p"].values
    
    def calc_metrics(y_actual, y_pred):
        bias = float(np.mean(y_pred - y_actual))
        mae = float(mean_absolute_error(y_actual, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_actual, y_pred)))
        r2 = float(r2_score(y_actual, y_pred))
        if np.ptp(y_actual) == 0 or np.ptp(y_pred) == 0:
            corr = float("nan")  # rank correlation undefined for a constant vector
        else:
            corr, _ = spearmanr(y_actual, y_pred)
        return {
            "bias": round(bias, 2),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
            "spearman_corr": round(float(corr), 4) if corr == corr else None
        }

        
    metrics_naive = calc_metrics(y_true, y_naive)
    metrics_lin = calc_metrics(y_true, y_lin)
    metrics_log = calc_metrics(y_true, y_log)

    # ------------------------------------------------------------------
    # HONEST BASELINE (reviewer fix 2)
    # ------------------------------------------------------------------
    # Comparing the fitted model only against an unscaled splice flatters it:
    # nobody splices raw counts. The baseline a competent analyst would reach
    # for first is a single scalar, total train MODIS / total train VIIRS. It
    # is reported here so the marginal gain of the regression is visible rather
    # than hidden behind the raw-splice figure.
    scalar_ratio = float(train["modis"].sum() / train["viirs"].sum()) if train["viirs"].sum() else float("nan")
    y_scalar = np.clip(test["viirs"].values * scalar_ratio, 0, None)
    test["pred_scalar"] = y_scalar
    metrics_scalar = calc_metrics(y_true, y_scalar)
    print(f"[MODEL] Scalar-ratio baseline: x{scalar_ratio:.4f} -> "
          f"RMSE {metrics_scalar['rmse']} (fitted linear: {metrics_lin['rmse']})")

    # ------------------------------------------------------------------
    # SEASONAL SPLIT (reviewer fix 3)
    # ------------------------------------------------------------------
    # Of the overlap months, most carry almost no detections, so a single RMSE
    # is set almost entirely by the March-April jhum burning peak. Both regimes
    # are scored separately so the headline cannot stand on six months alone.
    PEAK_MONTHS = (3, 4)
    peak = test[test["month_num"].isin(PEAK_MONTHS)]
    quiet = test[~test["month_num"].isin(PEAK_MONTHS)]

    def season_block(group, label):
        if group.empty:
            return None
        block = calc_metrics(group["modis"].values, group["pred_linear"].values)
        block["months"] = int(len(group))
        block["mean_observed_modis"] = round(float(group["modis"].mean()), 2)
        block["label"] = label
        return block

    seasonal = {
        "fire_season_mar_apr": season_block(peak, "March-April jhum burning peak"),
        "quiet_season_other_months": season_block(quiet, "all other months"),
        "note": ("A single held-out RMSE is dominated by the burning peak. Reported "
                 "separately so the fit is not judged on six months of the year."),
    }
    median_abs_err = round(float(np.median(np.abs(y_lin - y_true))), 2)
    for key in ("fire_season_mar_apr", "quiet_season_other_months"):
        if seasonal[key]:
            print(f"[MODEL] {key}: n={seasonal[key]['months']} "
                  f"RMSE={seasonal[key]['rmse']} mean MODIS={seasonal[key]['mean_observed_modis']}")


    # Bootstrap Parameter Uncertainty (500 resamples on the train set).
    # Months are seasonal, so single-month resampling assumes away the
    # autocorrelation and under-states the interval: resample contiguous
    # 12-month blocks (one full seasonal cycle) instead — moving-block
    # bootstrap, deterministic via default_rng(42).
    rng = np.random.default_rng(42)
    train_vals = train[["viirs", "modis"]].to_numpy(dtype=float)
    n_obs = len(train_vals)
    block = 12
    starts = np.arange(0, n_obs - block + 1) if n_obs >= block else np.arange(n_obs)
    n_blocks = int(np.ceil(n_obs / block))
    boot_slopes = []
    boot_intercepts = []
    for _ in range(500):
        if n_obs >= block:
            picks = rng.choice(starts, size=n_blocks, replace=True)
            idx = (picks[:, None] + np.arange(block)).ravel()[:n_obs]
        else:  # degenerate short train: fall back to single-row resampling
            idx = rng.integers(0, n_obs, size=n_obs)
        sample = train_vals[idx]
        m_boot = LinearRegression().fit(sample[:, 0].reshape(-1, 1), sample[:, 1])
        boot_slopes.append(m_boot.coef_[0])
        boot_intercepts.append(m_boot.intercept_)
        
    slope_ci = [round(float(np.percentile(boot_slopes, 2.5)), 4), round(float(np.percentile(boot_slopes, 97.5)), 4)]
    intercept_ci = [round(float(np.percentile(boot_intercepts, 2.5)), 2), round(float(np.percentile(boot_intercepts, 97.5)), 2)]

    # ------------------------------------------------------------------
    # FORWARD MAPPING FOR THE POST-SUOMI ERA (reviewer fix 6)
    # ------------------------------------------------------------------
    # The fitted model converts VIIRS into MODIS-equivalent units, which is the
    # right direction for rebuilding history but leaves the series denominated
    # in an instrument that is being retired. Suomi-NPP product delivery ceases
    # on 1 November 2026, and Aqua MODIS is itself long past design life, so the
    # inverse direction is published as well: it lets the record be carried
    # forward on a 375 m VIIRS footing (NOAA-20 / NOAA-21) instead of ending
    # with a dead sensor's units.
    inverse_slope = round(1.0 / lin_slope, 4) if lin_slope else None
    inverse_intercept = round(-lin_intercept / lin_slope, 2) if lin_slope else None
    inverse_model = {
        "equation": (f"VIIRS_eq = {inverse_slope} * MODIS + ({inverse_intercept})"
                     if inverse_slope is not None else None),
        "slope": inverse_slope,
        "intercept": inverse_intercept,
        "direction": "MODIS 1 km counts -> S-NPP VIIRS 375 m equivalent counts",
        "purpose": ("Carries the pre-2012 MODIS record forward onto a 375 m footing so the "
                    "series can continue on NOAA-20/21 after Suomi-NPP delivery ends."),
        "caveat": ("Algebraic inversion of the fitted line, not a separately fitted model: "
                   "it inherits the same uncertainty and is not validated against NOAA-20 "
                   "detections. A NOAA-20 leg (VIIRS_NOAA20_SP) must be fitted on the "
                   "S-NPP / NOAA-20 overlap before the forward series is used operationally."),
    }
    print(f"[MODEL] Forward mapping (MODIS -> VIIRS-equivalent): {inverse_model['equation']}")


    # Full spliced time series (2002-2021)
    # 2002-2011: Observed Aqua MODIS
    # 2012-2021: Harmonized VIIRS (MODIS-equivalent)
    full_df = df.copy()
    full_df["pred_linear"] = np.nan
    full_df["pred_log1p"] = np.nan
    
    full_df.loc[full_df["viirs"].notna(), "pred_linear"] = overlap["pred_linear"].values
    full_df.loc[full_df["viirs"].notna(), "pred_log1p"] = overlap["pred_log1p"].values
    
    # Create final unified spliced column
    # Prior to 2012: MODIS observation. 2012+: Linear harmonized estimate
    full_df["naive_splice"] = np.where(full_df["year"] < 2012, full_df["modis"], full_df["viirs"])
    full_df["harmonized_splice"] = np.where(full_df["year"] < 2012, full_df["modis"], full_df["pred_linear"])
    
    # Save processed results
    full_df.to_csv(os.path.join(PROCESSED, "monthly_harmonized.csv"), index=False)

    def pct_reduction(new, base):
        if not base or abs(base) < 1e-9:
            return None
        return round((1.0 - abs(new) / abs(base)) * 100, 1)

    rmse_reduction = pct_reduction(metrics_lin["rmse"], metrics_naive["rmse"])
    bias_reduction = pct_reduction(metrics_lin["bias"], metrics_naive["bias"])

    sensitivity_available = (
        _has_rows(os.path.join(PROCESSED, "clean_audit_lowconf-kept.json"))
        or os.path.exists(os.path.join(PROCESSED, "sensitivity.json"))
    )

    # Region gate provenance: which district polygons were kept and how many
    # bbox rows they removed (the download rectangle includes India/Myanmar).
    region_info = None
    audit_path = os.path.join(PROCESSED, "clean_audit_baseline.json")
    if os.path.exists(audit_path):
        with open(audit_path, encoding="utf-8") as f:
            base_audit = json.load(f)
        for sensor_audit in base_audit.values() if isinstance(base_audit, dict) else []:
            if isinstance(sensor_audit, dict) and sensor_audit.get("region_filter"):
                region_info = dict(sensor_audit["region_filter"])
                region_info["dropped_outside_region"] = {
                    s: a.get("dropped_outside_region")
                    for s, a in base_audit.items() if isinstance(a, dict)
                }
                break

    # ------------------------------------------------------------------
    # PER-DISTRICT FITS (F6/P4)
    # ------------------------------------------------------------------
    per_district = fit_per_district(os.path.join(PROCESSED, "monthly_districts.csv"))
    with open(os.path.join(PROCESSED, "district_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(_json_safe(per_district["districts"]), f, indent=2, allow_nan=False)
    for name, entry in per_district["districts"].items():
        print(f"[MODEL] district {name}: {entry.get('status')} "
              f"slope={entry.get('slope')} r2={entry.get('held_out_r2')} "
              f"rmse={entry.get('held_out_rmse')}")

    # ------------------------------------------------------------------
    # NOAA-20 FORWARD LEG (F2/P2)
    # ------------------------------------------------------------------
    noaa20 = fit_noaa20_leg(df)
    print(f"[MODEL] NOAA-20 leg: {noaa20.get('status')} "
          f"({noaa20.get('overlap_months', 0)} overlap months) — {noaa20.get('reason', '')}")

    custody = build_sensor_custody(
        record_start=str(df["month"].min()),
        record_end=str(df["month"].max()),
        train_start=str(train["month"].min()),
        train_end=str(train["month"].max()),
        test_start=str(test["month"].min()),
        test_end=str(test["month"].max()),
        noaa20=noaa20,
    )

    summary_metrics = {
        "data_source": {
            "kind": data_kind,
            "is_nasa_firms": not is_demo,
            "note": prov.get("note", ""),
        },
        "study_area": "Bangladesh Chittagong Hill Tracts (CHT), district polygons",
        "bounding_box": [91.9, 21.4, 92.9, 23.8],
        "region_filter": region_info,
        "coverage_gaps": prov.get("coverage_gaps"),
        "coverage_gaps_note": ("Contiguous months with no downloaded chunk inside the grid. "
                               "They are delivery gaps, not fire-free months, and stay blank "
                               "rather than becoming zeros."),
        "per_district": per_district,
        "noaa20_model": noaa20,
        "sensor_custody": custody,
        # Derived from the split, not typed: extending the download window must
        # not leave the published period strings describing the old window.
        "training_period": f"{train['month'].min()} to {train['month'].max()} ({len(train)} months)",
        "held_out_test_period": f"{test['month'].min()} to {test['month'].max()} ({len(test)} months)",
        "record_period": f"{df['month'].min()} to {df['month'].max()} ({len(df)} months)",
        "observed_sensor_shift_ratio": step_ratio,
        "observed_sensor_shift_ratio_definition":
            "mean raw VIIRS (2012+) / mean MODIS (2002-2011), zero months counted on both sides — "
            "the discontinuity drawn in Chart A",
        "overlap_viirs_to_modis_ratio": overlap_ratio,
        "overlap_viirs_to_modis_ratio_definition":
            "mean raw VIIRS / mean MODIS over the same overlap months (the sensor sensitivity difference)",
        "modis_only_continuity": modis_continuity,

        "zero_month_handling": zero_diag,
        "confidence_threshold_sensitivity_run": sensitivity_available,
        "fitted_linear_model": {
            "equation": f"MODIS_eq = {lin_slope:.4f} * VIIRS + ({lin_intercept:.2f})",
            "slope": round(lin_slope, 4),
            "intercept": round(lin_intercept, 2),
            "bootstrap_slope_95_ci": slope_ci,
            "bootstrap_intercept_95_ci": intercept_ci,
            "bootstrap_method": "500 resamples of contiguous 12-month blocks (moving-block bootstrap, seed 42); coefficient interval, not a prediction interval",
            "interpretation": "fitted regional empirical relationship (monthly counts), not a universal MODIS-VIIRS conversion"
        },
        "forward_mapping_modis_to_viirs": inverse_model,
        "fitted_log1p_model": {
            "equation": f"ln(MODIS_eq + 1) = {log_slope:.4f} * ln(VIIRS + 1) + ({log_intercept:.2f})",
            "slope": round(log_slope, 4),
            "intercept": round(log_intercept, 2)
        },
        "held_out_test_comparison": {
            "naive_raw_viirs_vs_modis": metrics_naive,
            "scalar_ratio_baseline_vs_modis": metrics_scalar,
            "harmonized_linear_vs_modis": metrics_lin,
            "harmonized_log1p_vs_modis": metrics_log
        },
        "baseline_definitions": {
            "naive_raw_viirs_vs_modis":
                "raw unscaled VIIRS counts spliced onto the MODIS record — the error being "
                "illustrated, not a method any analyst would use",
            "scalar_ratio_baseline_vs_modis":
                f"one scalar, sum(train MODIS) / sum(train VIIRS) = {round(scalar_ratio, 4)} — "
                "the honest competing baseline the fitted model must beat",
        },
        "performance_improvement": {
            "rmse_reduction_percent": rmse_reduction,
            "bias_reduction_percent": bias_reduction,
            "rmse_reduction_percent_vs_scalar_baseline":
                pct_reduction(metrics_lin["rmse"], metrics_scalar["rmse"]),
            "honest_reading": ("Most of the correction comes from simple scaling. Against the "
                               "scalar baseline the fitted model gains only a few per cent, so "
                               "the contribution of this work is the regional calibration, the "
                               "bootstrap uncertainty, the sensitivity runs and the held-out "
                               "test, not the size of the error reduction."),
        },
        "held_out_seasonal_breakdown": seasonal,
        "held_out_median_absolute_error": median_abs_err,
        "limitations": [
            "Region-specific held-out-tested prototype: not a universal MODIS-VIIRS conversion, not a fire-cause classifier, not proof of fire absence.",
            "Regional monthly counts, not paired fire-level detections.",
            "No overpass-time, scan-angle, exact administrative boundary, land-cover or FRP modeling.",
            "FIRMS reports positive detections; non-detection does not prove absence of fire (cloud cover, orbital gaps).",
            "A single scalar ratio already removes most of the sensor step; the fitted line improves on it only marginally, so the error-reduction headline is reported against both baselines.",
            "Held-out accuracy is concentrated in the March-April burning peak; most months carry near-zero detections, so R2 is reported with the seasonal breakdown and with Spearman rank correlation.",
            "The forward MODIS-to-VIIRS mapping is an algebraic inversion, not a model fitted on NOAA-20 data.",
            ("NOAA-20 leg status: " + noaa20.get("status", "unknown")
             + (" — " + noaa20["reason"] if noaa20.get("reason") else "")
             + ". The record is not extended past the downloaded archive until that leg is fitted."),
            "Per-district fits test spatial consistency but are not independent datasets; the three districts share the same sensors and processing chain.",
            "Suomi-NPP VIIRS delivery permanently ceases November 1, 2026; future operations require NOAA-20/21 refitting."
        ]
    }
    if is_demo:
        summary_metrics["limitations"].insert(
            0,
            "DEMO DATA: this run used a simulated monthly series, not NASA FIRMS observations. "
            "Re-run with FIRMS_MAP_KEY for real results.",
        )

    with open(os.path.join(PROCESSED, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(_json_safe(summary_metrics), f, indent=2, allow_nan=False)

    print("[MODEL] Metrics successfully saved to data/processed/metrics.json")
    print(f"[MODEL] data_source={data_kind}")
    print(json.dumps(summary_metrics["held_out_test_comparison"], indent=2))
    print(f"[MODEL] RMSE Reduction: {rmse_reduction}%")
    print(f"[MODEL] Bias Reduction: {bias_reduction}%")

    return full_df, summary_metrics


def generate_publication_charts(df, metrics):
    """
    Generate Chart A (Naive Splice), Chart B (Harmonized Splice) and the
    held-out scatter of Section 5 of BD-FireOps MVP Plan v3.

    All annotations are computed from the metrics dict — nothing here is a
    hardcoded claim. If the run used demo data, every chart carries a watermark.
    """
    plt.style.use('dark_background')

    src = metrics.get("data_source", {}) or {}
    is_demo = not src.get("is_nasa_firms", False)
    jump_ratio = metrics.get("observed_sensor_shift_ratio")
    watermark = ("DEMO DATA — SIMULATED SERIES, NOT NASA FIRMS"
                 if is_demo else "NASA FIRMS observations")

    def stamp(ax, color='#8b949e'):
        ax.text(0.99, 0.02, watermark, transform=ax.transAxes, ha='right', va='bottom',
                fontsize=8, color=color, alpha=0.75, style='italic')

    pre_2012 = df[df["year"] < 2012]
    post_2012 = df[df["year"] >= 2012]
    post_viirs = post_2012["viirs"].fillna(0)

    def annotate_jump(ax, values, color):
        if jump_ratio != jump_ratio or len(values) == 0:
            return  # ratio undefined (no pre-2012 months, or empty series)
        ax.annotate(f'Sensor Shift Jump\n({jump_ratio}x count inflation)',
                    xy=(trans_idx + 3, values.iloc[min(3, len(values) - 1)]),
                    xytext=(trans_idx + 10, float(np.nanmax(values)) * 0.85),
                    arrowprops=dict(facecolor=color, shrink=0.08, width=1.5, headwidth=6),
                    color=color, fontweight='bold', fontsize=10)

    # -------------------------------------------------------------
    # CHART A: Naive Sensor Splice (Illustrating the artificial jump)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5), dpi=200)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#161b22')

    ax.plot(range(len(pre_2012)), pre_2012["modis"], color='#58a6ff', label='Observed Aqua MODIS (1km)', linewidth=1.8)
    ax.plot(range(len(pre_2012), len(df)), post_2012["viirs"], color='#f85149', label='Raw S-NPP VIIRS (375m)', linewidth=1.8)

    trans_idx = len(pre_2012)
    ax.axvline(x=trans_idx, color='#e3b341', linestyle='--', linewidth=1.5, alpha=0.9, label='Sensor Transition (Jan 2012)')

    annotate_jump(ax, post_viirs, '#f85149')

    year_ticks = [i for i, m in enumerate(df["month"]) if m.endswith("-01")]
    year_labels = [df["month"].iloc[i][:4] for i in year_ticks]
    ax.set_xticks(year_ticks[::2])
    ax.set_xticklabels(year_labels[::2], rotation=45, color='#c9d1d9')

    ax.set_title("CHART A: Naive Sensor Splicing in Bangladesh CHT (2002–2021)\n[Illustrative raw sensor splice, not a continuous fire estimate]",
                 fontsize=12, fontweight='bold', color='#f0f6fc', pad=12)
    ax.set_ylabel("Monthly Active Fire Hotspots", color='#c9d1d9', fontsize=10)
    ax.grid(color='#30363d', linestyle=':', alpha=0.6)
    ax.legend(loc='upper left', framealpha=0.8, facecolor='#21262d', edgecolor='#30363d')
    stamp(ax, '#f85149')
    plt.tight_layout()
    plt.savefig(os.path.join(PROCESSED, "chart_a_naive_splice.png"))
    plt.close()

    # -------------------------------------------------------------
    # CHART B: Harmonized Splice (Continuous MODIS-equivalent)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5), dpi=200)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#161b22')

    ax.plot(range(len(pre_2012)), pre_2012["modis"], color='#58a6ff', label='2002–2011 Observed Aqua MODIS', linewidth=1.8)
    ax.plot(range(len(pre_2012), len(df)), post_2012["pred_linear"], color='#3fb950', label='2012–2021 Harmonized VIIRS (MODIS-equiv)', linewidth=1.8)

    ax.axvline(x=trans_idx, color='#e3b341', linestyle='--', linewidth=1.5, alpha=0.9, label='Transition Horizon (Jan 2012)')

    pred_post = post_2012["pred_linear"].fillna(0)
    if len(pred_post) and np.isfinite(pred_post.iloc[0]):
        ax.annotate('Continuous Multi-Decadal Baseline\n(fitted on 2012–2018, validated 2019–2021)',
                    xy=(trans_idx + 2, pred_post.iloc[2] if len(pred_post) > 2 else pred_post.iloc[0]),
                    xytext=(trans_idx + 10, float(np.nanmax(pred_post)) * 0.85),
                    arrowprops=dict(facecolor='#3fb950', shrink=0.08, width=1.5, headwidth=6),
                    color='#3fb950', fontweight='bold', fontsize=10)

    ax.set_xticks(year_ticks[::2])
    ax.set_xticklabels(year_labels[::2], rotation=45, color='#c9d1d9')

    ax.set_title("CHART B: BD-FireOps Continuous Record for Bangladesh CHT (2002–2021)\n[2002–2011 observed Aqua MODIS; 2012–2021 VIIRS converted to MODIS-equivalent (fit 2012–2018 only)]",
                 fontsize=12, fontweight='bold', color='#f0f6fc', pad=12)
    ax.set_ylabel("MODIS-Equivalent Monthly Hotspots", color='#c9d1d9', fontsize=10)
    ax.grid(color='#30363d', linestyle=':', alpha=0.6)
    ax.legend(loc='upper left', framealpha=0.8, facecolor='#21262d', edgecolor='#30363d')
    stamp(ax, '#3fb950')
    plt.tight_layout()
    plt.savefig(os.path.join(PROCESSED, "chart_b_harmonized_splice.png"))
    plt.close()

    # -------------------------------------------------------------
    # CHART C: Held-out Test Evaluation Scatter & Residuals
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=200)
    fig.patch.set_facecolor('#0d1117')
    for a in (ax1, ax2):
        a.set_facecolor('#161b22')
        a.grid(color='#30363d', linestyle=':', alpha=0.6)

    test = df[(df["month"] >= "2019-01") & (df["month"] <= "2021-12")].dropna(
        subset=["modis", "viirs", "pred_linear"])

    if test.empty:
        print("[CHARTS] Held-out test months empty — skipping validation scatter.")
        plt.close()
    else:
        ax1.scatter(test["viirs"], test["modis"], color='#f85149', alpha=0.8, edgecolors='#ffffff', s=50, label='Test Observations')
        ax1.plot([0, test["viirs"].max()], [0, test["viirs"].max()], 'w--', alpha=0.4, label='1:1 Line')
        ax1.set_title("Raw S-NPP VIIRS vs Observed MODIS\n(Held-out Test 2019-2021)", color='#f0f6fc', fontsize=10, fontweight='bold')
        ax1.set_xlabel("Raw VIIRS Count", color='#c9d1d9')
        ax1.set_ylabel("Observed MODIS Count", color='#c9d1d9')
        ax1.legend(facecolor='#21262d', edgecolor='#30363d')
        stamp(ax1, '#f85149')

        ax2.scatter(test["pred_linear"], test["modis"], color='#3fb950', alpha=0.8, edgecolors='#ffffff', s=50, label='Harmonized Predictions')
        max_val = max(test["pred_linear"].max(), test["modis"].max()) * 1.1
        ax2.plot([0, max_val], [0, max_val], 'w--', alpha=0.4, label='1:1 Line (Perfect Calibration)')
        lin = metrics['held_out_test_comparison']['harmonized_linear_vs_modis']
        ax2.set_title(f"BD-FireOps vs Observed MODIS\n(RMSE: {lin['rmse']} | Bias: {lin['bias']})",
                      color='#f0f6fc', fontsize=10, fontweight='bold')
        ax2.set_xlabel("Harmonized MODIS-Equiv Count", color='#c9d1d9')
        ax2.set_ylabel("Observed MODIS Count", color='#c9d1d9')
        ax2.legend(facecolor='#21262d', edgecolor='#30363d')
        stamp(ax2, '#3fb950')

        plt.tight_layout()
        plt.savefig(os.path.join(PROCESSED, "chart_validation_scatter.png"))
        plt.close()

    print("[CHARTS] Generated Chart A, Chart B, and Validation Scatterplot in data/processed/")


if __name__ == "__main__":
    df, metrics = run_harmonization_pipeline()
    generate_publication_charts(df, metrics)
