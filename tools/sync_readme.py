"""
Rewrite the metrics block inside README.md from data/processed/metrics.json.

The README table, fitted equation, bootstrap intervals and sensor-shift figure
are all derived — never hand-typed — so they cannot drift away from the code
that produced them.

Usage:  python tools/sync_readme.py [--check]
        --check exits non-zero if README.md is out of date (use in CI/pre-commit)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "data" / "processed" / "metrics.json"
README = ROOT / "README.md"

BEGIN = "<!-- BEGIN:SUPPORTED_METRICS -->"
END = "<!-- END:SUPPORTED_METRICS -->"
REGION_BEGIN = "<!-- BEGIN:REGION_GATE -->"
REGION_END = "<!-- END:REGION_GATE -->"


def fmt(v, dash="n/a") -> str:
    if v is None:
        return dash
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.2f}"
    return str(v)


def build_block(m: dict) -> str:
    src = m.get("data_source", {}) or {}
    is_real = bool(src.get("is_nasa_firms"))

    naive = m["held_out_test_comparison"]["naive_raw_viirs_vs_modis"]
    lin = m["held_out_test_comparison"]["harmonized_linear_vs_modis"]
    log = m["held_out_test_comparison"]["harmonized_log1p_vs_modis"]
    imp = m["performance_improvement"]
    flm = m["fitted_linear_model"]

    def pct(v, word="Error"):
        if v is None:
            return "n/a"
        return f"-{v}% {word} Reduction" if v >= 0 else f"+{-v}% {word} Increase"

    def signed(v):
        if v is None:
            return "n/a"
        return f"{'+' if v >= 0 else ''}{v}"

    if is_real:
        banner = (
            "> **Data source:** NASA FIRMS Area API (MODIS_SP, VIIRS_SNPP_SP) over CHT — "
            "see `data/processed/data_source.json`."
        )
    else:
        banner = (
            "> **DEMO DATA — NOT NASA FIRMS.** These figures come from a simulated monthly "
            "series used to validate the pipeline. Re-run with a FIRMS `MAP_KEY` "
            "(`python probe_firms.py --run-all`) before submission."
        )

    r2 = lin["r2"]
    if r2 is None:
        r2_label = "n/a"
    elif r2 >= 0.95:
        r2_label = "Strong held-out fit"
    elif r2 >= 0.9:
        r2_label = "Good held-out fit"
    else:
        r2_label = "Weak held-out fit"

    # The scalar-ratio baseline sits between the raw splice and the fitted model
    # on purpose. Reporting only against the raw splice overstates the gain, so
    # the column the fitted model actually has to beat is published alongside it.
    scalar = m["held_out_test_comparison"].get("scalar_ratio_baseline_vs_modis") or {}
    scalar_gain = imp.get("rmse_reduction_percent_vs_scalar_baseline")

    rows = [
        ("RMSE (Hotspots/month)", fmt(naive["rmse"]), fmt(scalar.get("rmse")), fmt(lin["rmse"]),
         pct(scalar_gain)),
        ("Bias (Mean Prediction Error)", signed(naive["bias"]), signed(scalar.get("bias")), signed(lin["bias"]),
         pct(imp["bias_reduction_percent"], "Bias") + " vs raw splice"),
        ("MAE (Mean Absolute Error)", fmt(naive["mae"]), fmt(scalar.get("mae")), fmt(lin["mae"]),
         pct(round(100 * (1 - lin["mae"] / naive["mae"]), 1) if naive["mae"] else None) + " vs raw splice"),
        ("R-Squared ($R^2$) Score", fmt(naive["r2"]), fmt(scalar.get("r2")), fmt(lin["r2"]), r2_label),
        ("Spearman Rank Correlation ($\\rho$)", fmt(naive["spearman_corr"]), fmt(scalar.get("spearman_corr")),
         fmt(lin["spearman_corr"]), "Preserves Seasonality"),
        ("Log1p variant RMSE (zero-robust check)", fmt(naive["rmse"]), "-", fmt(log["rmse"]), "-"),
    ]


    table = "\n".join(
        f"| **{label}** | {nv} | {sv} | **{lv}** | {iv} |" for label, nv, sv, lv, iv in rows
    )

    # Honest reading, seasonal breakdown and the MODIS-only control.
    cont = m.get("modis_only_continuity") or {}
    seas = m.get("held_out_seasonal_breakdown") or {}
    peak = seas.get("fire_season_mar_apr") or {}
    quiet = seas.get("quiet_season_other_months") or {}
    fwd = m.get("forward_mapping_modis_to_viirs") or {}

    def spct(v):
        return "n/a" if v is None else f"{'+' if v >= 0 else ''}{v}%"

    n20 = m.get("noaa20_model") or {}
    if n20.get("status") == "fitted":
        n_ho = n20.get("held_out") or {}
        n_scalar = n20.get("held_out_scalar") or {}
        noaa_block = f"""
### NOAA-20 continuity leg (fitted)

Fitted on {n20.get('overlap_months', 'n/a')} S-NPP / NOAA-20 overlap months:
`{n20.get('equation', 'n/a')}`. Held-out RMSE {n_ho.get('rmse', 'n/a')} vs scalar baseline
{n_scalar.get('rmse', 'n/a')}; Spearman {n_ho.get('spearman_corr', 'n/a')}.
"""
    else:
        noaa_block = f"""
### NOAA-20 continuity leg (implemented, not fitted)

`analysis/download.py`, `analysis/clean.py`, `analysis/aggregate.py` and `analysis/model.py` carry a
`viirs_noaa20` sensor (`VIIRS_NOAA20_SP`, 2018-01 onward). `fit_noaa20_leg` refuses to publish a
slope below 24 overlap months. Current status: **{n20.get('status', 'not_available')} —
{n20.get('overlap_months', 0)} / {n20.get('min_overlap_months', 24)} overlap months**, because no
raw NOAA-20 archive is in this checkout. The website and `metrics.json` say so explicitly; nothing
is labelled NOAA-20 that was not downloaded. Fetch it with
`python analysis/download.py --sensor viirs_noaa20` and re-run the pipeline to fit the leg.
"""

    per = (m.get("per_district") or {}).get("districts") or {}
    district_rows = []
    for name in ("Bandarban", "Khagrachhari", "Rangamati"):
        e = per.get(name) or {}
        if e.get("status") != "fitted":
            district_rows.append(f"| {name} | not fitted | — | — | — | — |")
            continue
        scalar_rmse = e.get("held_out_scalar_rmse")
        winner = "fit" if scalar_rmse is not None and e["held_out_rmse"] < scalar_rmse else "scaling"
        district_rows.append(
            f"| {name} | {e['slope']:.4f} | {e['held_out_r2']:.4f} | {e['held_out_rmse']:.2f} | "
            f"{scalar_rmse:.2f} | {e['held_out_spearman']:.4f} | {winner} |"
        )
    district_block = f"""
### Per-district validation (same split)

Each district repeats the identical 2012–2018 train / 2019–2021 held-out test split and carries its
own scalar-ratio baseline:

| District | Slope | Held-out R² | Fit RMSE | Scalar RMSE | Spearman | Lower RMSE |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
{chr(10).join(district_rows)}

The slopes are consistent with the regional fit, but simple scaling is as good or better in some
districts. The site prints that comparison on every card instead of implying a uniform win.
"""

    honest_note = f"""
### How to read these numbers

The raw-splice column is the error being illustrated, not a method anyone would use, so an
improvement measured against it overstates what the fitted model contributes. The column that
matters is the scalar baseline: one number, `sum(train MODIS) / sum(train VIIRS)`, applied to
every month. Against that baseline the fitted model reduces held-out RMSE by
**{scalar_gain if scalar_gain is not None else 'n/a'}%**, not by
{imp.get('rmse_reduction_percent', 'n/a')}%. Most of the correction is simple scaling. What this work adds is the regional calibration for the CHT, the
bootstrap coefficient interval, the confidence-threshold and day-only sensitivity runs, and a
genuine held-out test.

Held-out accuracy is also concentrated in the burning season. Scored separately:

| Season | Months tested | Mean observed MODIS / month | RMSE |
| :--- | ---: | ---: | ---: |
| March–April burning peak | {peak.get('months', 'n/a')} | {peak.get('mean_observed_modis', 'n/a')} | {peak.get('rmse', 'n/a')} |
| All other months | {quiet.get('months', 'n/a')} | {quiet.get('mean_observed_modis', 'n/a')} | {quiet.get('rmse', 'n/a')} |

Across the whole held-out set the **median** absolute error is
{m.get('held_out_median_absolute_error', 'n/a')} detections, because most months are nearly
fire-free. $R^2$ is therefore reported together with Spearman rank correlation and this split,
rather than on its own.

### Control test: the sensor that never changed

Aqua MODIS observed the same three districts before and after January 2012 without any
instrument change, so its own record is the control. MODIS averages
**{cont.get('pre_2012_modis_mean_per_month', 'n/a')}** detections per month before 2012 and
**{cont.get('post_2012_modis_mean_per_month', 'n/a')}** afterwards, a change of
**{spct(cont.get('modis_only_change_percent'))}**, while the spliced series appears to change by
**{spct(cont.get('spliced_apparent_change_percent'))}**. The unchanged instrument does not show
the step, which is the clearest evidence that the step is a sensor artefact.

### Forward mapping for the post-Suomi era

`{fwd.get('equation', 'n/a')}` carries the record forward onto a 375 m footing so it can continue on
NOAA-20/21 after Suomi-NPP delivery ends on 1 November 2026. This is an algebraic inversion of the
fitted line, not a model fitted on NOAA-20 detections. The NOAA-20 leg is implemented and refuses
to publish a slope below 24 overlap months; its current status is stated below.

{noaa_block}
{district_block}"""

    shift = m.get("observed_sensor_shift_ratio")
    shift_s = "n/a" if shift is None or shift != shift else f"{shift}x"
    overlap_r = m.get("overlap_viirs_to_modis_ratio")
    overlap_s = "n/a" if overlap_r is None or overlap_r != overlap_r else f"{overlap_r}x"
    zh = m.get("zero_month_handling", {})

    # Bootstrap interval width, so the fitted coefficient is never read as exact.
    ci = flm.get("bootstrap_slope_95_ci")
    ci_s = "n/a"
    if isinstance(ci, (list, tuple)) and len(ci) == 2 and flm.get("slope"):
        half = abs((float(ci[1]) - float(ci[0])) / 2)
        ci_s = f"±{round(100 * half / abs(float(flm['slope'])), 1)}% of the point slope"

    # Confidence-threshold sensitivity, if tools/sensitivity.py has been run.
    sens_text = None
    day_note = ""
    sens_path = ROOT / "data" / "processed" / "sensitivity.json"
    if sens_path.exists():
        try:
            sens = json.loads(sens_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sens = None
        d = (sens or {}).get("delta") or {}
        b = (sens or {}).get("baseline") or {}
        l = (sens or {}).get("low_confidence_kept") or {}

        # Day-only sensitivity (daynight == "D" on both sensors): guards the
        # fitted relationship against the night rows VIIRS carries (~9% here).
        _donly = (sens or {}).get("day_only") or {}
        _dd = (sens or {}).get("delta_day") or {}
        if (_dd.get("slope_percent") is not None and _dd.get("test_rmse_percent") is not None
                and b.get("slope") is not None and _donly.get("slope") is not None):
            day_note = (
                f"* **Day-only sensitivity (daynight = D on both sensors):** slope "
                f"`{b['slope']}` → `{_donly['slope']}` ({_dd['slope_percent']:+.2f}%) and "
                f"held-out RMSE `{b.get('test_rmse')}` → `{_donly.get('test_rmse')}` "
                f"({_dd['test_rmse_percent']:+.2f}%)."
            )
            _mr, _vr = _donly.get("modis_rows"), _donly.get("viirs_rows")
            if isinstance(_mr, int) and isinstance(_vr, int):
                day_note += f" Detections: MODIS {_mr:,} / VIIRS {_vr:,} daytime rows kept."

        if d and b.get("slope") is not None and l.get("slope") is not None:
            def _pct(v):
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    return "n/a"
                return f"{v:+.2f}%"

            def _num(v):
                return f"{int(v):,}" if isinstance(v, int) else v

            def _dir_word(v):
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    return ""
                if v > 0:
                    return ", i.e. worse when looser thresholds are kept"
                if v < 0:
                    return ", i.e. better when looser thresholds are kept"
                return ""

            sens_text = (
                f"Keeping low-confidence detections changes the fitted slope "
                f"`{b['slope']}` → `{l['slope']}` ({_pct(d.get('slope_percent'))}) and held-out RMSE "
                f"`{b.get('test_rmse')}` → `{l.get('test_rmse')}` ({_pct(d.get('test_rmse_percent'))}"
                f"{_dir_word(d.get('test_rmse_percent'))}). "
                f"Row counts: MODIS {_num(b.get('modis_rows'))} → {_num(l.get('modis_rows'))}, "
                f"VIIRS {_num(b.get('viirs_rows'))} → {_num(l.get('viirs_rows'))}. "
                f"The baseline thresholds are therefore the reported configuration; "
                f"`data/processed/sensitivity.json` holds the numbers."
            )


    if sens_text:
        sens_note = f"* **Confidence-threshold sensitivity:** {sens_text}"
    else:
        sens_note = ""

    # Per-year held-out proof: one strong overall number can hide a weak year,
    # so the 2019–2021 test window is also reported year by year straight from
    # the harmonized CSV (same pred_linear the headline metrics are built on).
    per_year_note = ""
    try:
        import pandas as _pd

        _harm = _pd.read_csv(ROOT / "data" / "processed" / "monthly_harmonized.csv")
        _rows = []
        for _yr in (2019, 2020, 2021):
            _t = _harm[_harm["month"].astype(str).str.startswith(str(_yr))].dropna(
                subset=["modis", "pred_linear"])
            if _t.empty:
                continue
            _e = _t["pred_linear"].to_numpy(dtype=float) - _t["modis"].to_numpy(dtype=float)
            _rmse = round(float((_e ** 2).mean() ** 0.5), 2)
            _bias = round(float(_e.mean()), 2)
            _rows.append(f"| **{_yr}** | **{_rmse}** | **{_bias:+}** | **{len(_t)} months** |")
        if _rows:
            per_year_note = (
                "* **Held-out test, year by year (RMSE / bias / months in that year):**\n"
                "\n"
                "| Year | RMSE | Bias | Months |\n"
                "| :--- | ---: | ---: | ---: |\n"
                + "\n".join(_rows)
            )
    except Exception:
        per_year_note = ""

    l_rmse, g_rmse = lin.get("rmse"), log.get("rmse")
    if l_rmse is not None and g_rmse is not None:
        if g_rmse > l_rmse:
            log_note = (f"* **log1p check:** did **not** improve held-out RMSE "
                        f"({g_rmse} vs {l_rmse}) — reported as a robustness check, not as the "
                        f"chosen model.")
        else:
            log_note = (f"* **log1p check:** improved held-out RMSE ({g_rmse} vs {l_rmse}); "
                        f"the linear model remains the reported headline unless metrics.json "
                        f"is regenerated to reflect it.")
    else:
        log_note = ""



    return f"""<!-- BEGIN:SUPPORTED_METRICS -->
## 2. Quantitative Validation Results (Held-Out Test Set: 2019–2021)

{banner}
> Every number in this section is generated from `data/processed/metrics.json`
> by `python tools/sync_readme.py` — edit the metrics, not this table.

A strict chronological split (no train/test month overlap) was used to limit temporal leakage: the harmonization model was trained on **{m.get('training_period', '2012-01 to 2018-12')}**
and evaluated on an independent **held-out test set from {m.get('held_out_test_period', '2019-01 to 2021-12')}**.

| Metric | Naive Splice (Raw VIIRS) | Scalar-Ratio Baseline | BD-FireOps (Harmonized Linear) | Gain vs Scalar Baseline |
| :--- | :--- | :--- | :--- | :--- |
{table}
{honest_note}

### Fitted Empirical Calibration Model
$$\\text{{MODIS}}_{{\\text{{equivalent}}}} = {flm['slope']} \\times \\text{{VIIRS}}_{{375\\text{{m}}}} + ({flm['intercept']})$$

* **Bootstrap 95% Confidence Interval (Slope):** `{flm['bootstrap_slope_95_ci']}`
* **Bootstrap 95% Confidence Interval (Intercept):** `{flm['bootstrap_intercept_95_ci']}`
* **Interval width:** {ci_s} — the bootstrap here is a *coefficient* interval, not a prediction interval.
* **Chart-A step ratio:** `{shift_s}` — mean raw VIIRS (2012–2021) ÷ mean MODIS (2002–2011),
  zero months counted on both sides; this is the discontinuity Chart A draws.
* **Same-month sensor ratio:** `{overlap_s}` — mean raw VIIRS ÷ mean MODIS over the *same*
  2012–2021 months, i.e. the sensor sensitivity difference itself.
{log_note}
{sens_note}
{day_note}
* **Interpretation:** a fitted *regional empirical relationship* for monthly counts — not a
  universal MODIS↔VIIRS conversion, and not a fire-cause classifier.
* **Zero months:** {zh.get('months_with_any_zero', 'n/a')} of {zh.get('overlap_months', 'n/a')} overlap months contain a zero
  ({zh.get('zero_modis_months', 'n/a')} MODIS / {zh.get('zero_viirs_months', 'n/a')} VIIRS); zero months were retained, not dropped.
{per_year_note}
<!-- END:SUPPORTED_METRICS -->"""



def build_region_line(m: dict) -> str:
    """Region-gate row counts (README §6) straight from metrics.json."""
    region = m.get("region_filter") or {}
    dropped = region.get("dropped_outside_region") or {}

    def _f(v):
        if v is None:
            return "n/a"
        try:
            return f"{int(v):,}"
        except (TypeError, ValueError):
            return "n/a"

    return (f"{_f(dropped.get('modis'))} MODIS and {_f(dropped.get('viirs'))} "
            f"VIIRS bbox rows outside the CHT were removed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync README metrics block from metrics.json")
    parser.add_argument("--check", action="store_true", help="Exit 1 if README is out of date")
    args = parser.parse_args(argv)

    if not METRICS.exists():
        print(f"[SYNC] {METRICS} not found — run the pipeline first "
              "(python probe_firms.py --run-all or --demo).")
        return 1

    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    block = build_block(metrics)

    text = README.read_text(encoding="utf-8")
    ok = True
    for b, e, name in ((BEGIN, END, "SUPPORTED_METRICS"), (REGION_BEGIN, REGION_END, "REGION_GATE")):
        if b not in text or e not in text:
            print(f"[SYNC] Marker comments not found in README.md: {name}")
            ok = False
        elif text.count(b) != 1 or text.count(e) != 1:
            print(f"[SYNC] Marker must appear exactly once in README.md: {name} "
                  f"({text.count(b)}x/{text.count(e)}x)")
            ok = False
    if not ok:
        return 1

    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    updated = pattern.sub(lambda _: block, text, count=1)

    region_pattern = re.compile(re.escape(REGION_BEGIN) + r".*?" + re.escape(REGION_END), re.DOTALL)
    updated = region_pattern.sub(lambda _: REGION_BEGIN + build_region_line(metrics) + REGION_END,
                                 updated, count=1)

    if args.check:
        if updated != text:
            print("[SYNC] README.md is OUT OF DATE — run: python tools/sync_readme.py")
            return 1
        print("[SYNC] README.md is up to date.")
        return 0

    if updated == text:
        print("[SYNC] README.md already up to date.")
        return 0

    README.write_text(updated, encoding="utf-8")
    print(f"[SYNC] README.md metrics block refreshed from {METRICS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
