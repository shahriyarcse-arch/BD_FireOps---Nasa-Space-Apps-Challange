#!/usr/bin/env python3
"""
BD-FireOps: Master CLI & Pipeline Runner
Challenge: Harmonization of MODIS and VIIRS Hot Spots (NASA Space Apps 2026)
Team: Claude Fable 7.0
Study Area: Bangladesh Chittagong Hill Tracts (CHT: 91.9-92.9E, 21.4-23.8N)

  python probe_firms.py --run-all    real NASA FIRMS run (needs FIRMS_MAP_KEY in .env)
  python probe_firms.py --demo       SIMULATED data run, labelled end-to-end
  python probe_firms.py --test       1-day API probe (status code + columns)
  python probe_firms.py --metrics    print the saved metrics.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

from analysis import aggregate, clean, download, model

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"


def print_banner():
    print("""
================================================================================
   BD-FIREOPS: UNCERTAINTY-AWARE MODIS-VIIRS HARMONIZATION ENGINE
   NASA Space Apps Challenge 2026 | Team: Claude Fable 7.0
   Operational Context: Terra/Aqua MODIS Sunset & Suomi-NPP Transition
================================================================================""")


def run_pipeline(demo: bool = False):
    print_banner()
    (ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    if demo:
        print("[1/4] DEMO SERIES — SIMULATED DATA, NOT NASA FIRMS OBSERVATIONS")
        download.main(["--demo"])
        # Isolation: demo writes monthly.csv directly. Running clean/aggregate
        # after it would either rebuild real outputs from stale raw files or mix
        # demo and NASA rows — both break the "labelled end-to-end" promise.
        print("\n[2-3/4] SKIPPED for demo — clean/aggregate would re-aggregate real "
              "or stale raw files and destroy the demo label.")
    else:
        print("[1/4] Downloading CHT fire baseline from NASA FIRMS (2002-2021)...")
        download.main([])

        print("\n[2/4] Cleaning detections (confidence, reference sensor, bbox, duplicates)...")
        clean.run_clean()

        print("\n[3/4] Aggregating to regional monthly counts (zero months kept)...")
        aggregate.run_aggregate()

    print("\n[4/4] Fitting harmonization models + generating charts...")
    df_harm, metrics = model.run_harmonization_pipeline(str(PROCESSED / "monthly.csv"))
    model.generate_publication_charts(df_harm, metrics)

    print_summary(metrics)


def print_summary(metrics: dict):
    src = metrics.get("data_source", {})
    print("\n" + "=" * 88)
    label = "NASA FIRMS OBSERVATIONS" if src.get("is_nasa_firms") else "DEMO DATA — NOT NASA FIRMS"
    print(f"   DATA SOURCE: {label}")
    if src.get("note"):
        print(f"   {src['note']}")
    print("=" * 88)
    print("   HELD-OUT TEST EVALUATION SUMMARY (Period: 2019-2021)")
    print("=" * 88)

    naive = metrics["held_out_test_comparison"]["naive_raw_viirs_vs_modis"]
    lin = metrics["held_out_test_comparison"]["harmonized_linear_vs_modis"]
    log = metrics["held_out_test_comparison"]["harmonized_log1p_vs_modis"]

    def cell(v, width=20):
        return f"{('n/a' if v is None else str(v)):<{width}}"

    hdr = f"  {'Metric':<21} | {'Naive (raw VIIRS)':<20} | {'Harmonized (linear)':<21} | {'Harmonized (log1p)'}"
    print(hdr)
    print(f"  {'-' * 21} | {'-' * 20} | {'-' * 21} | {'-' * 19}")
    for label, key in (
        ("RMSE (hotspots/mo)", "rmse"),
        ("Bias (mean error)", "bias"),
        ("MAE (mean abs err)", "mae"),
        ("R-squared (R2)", "r2"),
        ("Spearman corr (rho)", "spearman_corr"),
    ):
        print(f"  {label:<21} | {cell(naive[key])} | {cell(lin[key], 21)} | {cell(log[key], 19)}")
    print(f"  {'-' * 21} | {'-' * 20} | {'-' * 21} | {'-' * 19}")


    imp = metrics["performance_improvement"]

    def _pct(v):
        return "n/a" if v is None else f"{v}%"

    print("-" * 88)
    print(f"  RMSE reduction vs naive: {_pct(imp['rmse_reduction_percent'])}   "
          f"Bias reduction vs naive: {_pct(imp['bias_reduction_percent'])}")
    print("=" * 88)

    flm = metrics["fitted_linear_model"]
    print("\nFitted regional empirical relationship:")
    print(f"  {flm['equation']}")
    print(f"  Bootstrap 95% CI slope:     {flm['bootstrap_slope_95_ci']}")
    print(f"  Bootstrap 95% CI intercept: {flm['bootstrap_intercept_95_ci']}")
    print(f"  Chart-A step ratio (VIIRS 2012+ / MODIS 2002-2011): {metrics.get('observed_sensor_shift_ratio')}x")
    print(f"  Same-month sensor ratio (2012-2021 overlap):          {metrics.get('overlap_viirs_to_modis_ratio')}x")


    zh = metrics["zero_month_handling"]
    print(f"\nZero months: {zh['months_with_any_zero']} of {zh['overlap_months']} overlap months "
          f"contain a zero ({zh['zero_modis_months']} MODIS / {zh['zero_viirs_months']} VIIRS)")
    print(f"  {zh['handling']}")

    print("\nSaved artifacts:")
    for name in ("monthly_harmonized.csv", "metrics.json", "data_source.json",
                 "chart_a_naive_splice.png", "chart_b_harmonized_splice.png",
                 "chart_validation_scatter.png"):
        print(f"  - data/processed/{name}")
    print("\nDashboard: streamlit run dashboard/app.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="BD-FireOps Master CLI")
    parser.add_argument("--run-all", action="store_true",
                        help="Full real-data pipeline: download -> clean -> aggregate -> model -> charts")
    parser.add_argument("--demo", action="store_true",
                        help="Run the pipeline on explicitly-labelled SIMULATED data")
    parser.add_argument("--test", action="store_true",
                        help="1-day FIRMS API probe (status code + returned columns)")
    parser.add_argument("--metrics", action="store_true", help="Print data/processed/metrics.json")
    args = parser.parse_args()

    if args.metrics:
        path = PROCESSED / "metrics.json"
        if not path.exists():
            print("metrics.json not found — run --run-all or --demo first.")
            return 1
        print(path.read_text(encoding="utf-8"))
        return 0

    if args.test:
        return download.main(["--test"])

    if args.run_all:
        run_pipeline(demo=False)
        return 0

    if args.demo:
        run_pipeline(demo=True)
        return 0

    parser.print_help()
    print("\nStatus:")
    src = PROCESSED / "data_source.json"
    if src.exists():
        print(f"  data_source.json: {json.loads(src.read_text(encoding='utf-8')).get('kind')}")
    else:
        print("  no pipeline run yet")
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key:
        print("  FIRMS_MAP_KEY: not set (register at "
              "https://firms.modaps.eosdis.nasa.gov/api/map_key/ then copy .env.example -> .env)")
    else:
        print("  FIRMS_MAP_KEY: set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
