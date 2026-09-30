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
    print(f"[MODEL] Pre-2012 MODIS mean={pre_mean:.1f} · overlap MODIS mean={ov_modis_mean:.1f} · "
          f"overlap VIIRS mean={post_mean:.1f}")

    # Time-split validation
    train = overlap[overlap["month"] < "2019-01"].copy()
    test = overlap[overlap["month"] >= "2019-01"].copy()

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
    
    # Bootstrap Parameter Uncertainty (500 resamples on train set)
    np.random.seed(42)
    boot_slopes = []
    boot_intercepts = []
    for _ in range(500):
        sample = train.sample(n=len(train), replace=True)
        m_boot = LinearRegression().fit(sample[["viirs"]], sample["modis"])
        boot_slopes.append(m_boot.coef_[0])
        boot_intercepts.append(m_boot.intercept_)
        
    slope_ci = [round(float(np.percentile(boot_slopes, 2.5)), 4), round(float(np.percentile(boot_slopes, 97.5)), 4)]
    intercept_ci = [round(float(np.percentile(boot_intercepts, 2.5)), 2), round(float(np.percentile(boot_intercepts, 97.5)), 2)]
    
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

    summary_metrics = {
        "data_source": {
            "kind": data_kind,
            "is_nasa_firms": not is_demo,
            "note": prov.get("note", ""),
        },
        "study_area": "Bangladesh Chittagong Hill Tracts (CHT), district polygons",
        "bounding_box": [91.9, 21.4, 92.9, 23.8],
        "region_filter": region_info,
        "training_period": f"2012-01 to 2018-12 ({len(train)} months)",
        "held_out_test_period": f"2019-01 to 2021-12 ({len(test)} months)",
        "observed_sensor_shift_ratio": step_ratio,
        "observed_sensor_shift_ratio_definition":
            "mean raw VIIRS (2012+) / mean MODIS (2002-2011), zero months counted on both sides — "
            "the discontinuity drawn in Chart A",
        "overlap_viirs_to_modis_ratio": overlap_ratio,
        "overlap_viirs_to_modis_ratio_definition":
            "mean raw VIIRS / mean MODIS over the same 2012-2021 months (the sensor sensitivity difference)",

        "zero_month_handling": zero_diag,
        "confidence_threshold_sensitivity_run": sensitivity_available,
        "fitted_linear_model": {
            "equation": f"MODIS_eq = {lin_slope:.4f} * VIIRS + ({lin_intercept:.2f})",
            "slope": round(lin_slope, 4),
            "intercept": round(lin_intercept, 2),
            "bootstrap_slope_95_ci": slope_ci,
            "bootstrap_intercept_95_ci": intercept_ci,
            "interpretation": "fitted regional empirical relationship (monthly counts), not a universal MODIS-VIIRS conversion"
        },
        "fitted_log1p_model": {
            "equation": f"ln(MODIS_eq + 1) = {log_slope:.4f} * ln(VIIRS + 1) + ({log_intercept:.2f})",
            "slope": round(log_slope, 4),
            "intercept": round(log_intercept, 2)
        },
        "held_out_test_comparison": {
            "naive_raw_viirs_vs_modis": metrics_naive,
            "harmonized_linear_vs_modis": metrics_lin,
            "harmonized_log1p_vs_modis": metrics_log
        },
        "performance_improvement": {
            "rmse_reduction_percent": rmse_reduction,
            "bias_reduction_percent": bias_reduction
        },
        "limitations": [
            "Region-specific held-out-tested prototype: not a universal MODIS-VIIRS conversion, not a fire-cause classifier, not proof of fire absence.",
            "Regional monthly counts, not paired fire-level detections.",
            "No overpass-time, scan-angle, exact administrative boundary, land-cover or FRP modeling.",
            "FIRMS reports positive detections; non-detection does not prove absence of fire (cloud cover, orbital gaps).",
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

    test = df[df["month"] >= "2019-01"].dropna(subset=["modis", "viirs", "pred_linear"])

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
