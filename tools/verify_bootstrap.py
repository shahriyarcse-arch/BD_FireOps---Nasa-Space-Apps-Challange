"""
Verify the moving-block bootstrap claim in data/processed/metrics.json.

The bootstrap interval is produced inside analysis/model.py. This tool
independently re-derives it from data/processed/monthly.csv (same train split,
same 12-month moving-block scheme, same seed) and compares the result with what
the repository actually ships. It exists because an interval that cannot be
recomputed is a claim, not evidence.

Usage:  python tools/verify_bootstrap.py
Exit 0 = shipped CI matches the recomputation; 1 = mismatch or missing inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TRAIN_END = "2019-01"      # same hard cut-off as analysis/model.py
BLOCK = 12                 # one full seasonal cycle
N_BOOT = 500
SEED = 42
TOL = 1e-9                 # exact match expected: same data, same RNG, same maths


def recompute() -> dict:
    monthly = pd.read_csv(PROCESSED / "monthly.csv")
    ov = monthly[monthly["viirs"].notna()].copy()
    ov["modis"] = ov["modis"].astype(float)
    ov["viirs"] = ov["viirs"].astype(float)
    train = ov[ov["month"] < TRAIN_END]

    train_vals = train[["viirs", "modis"]].to_numpy(dtype=float)
    n_obs = len(train_vals)
    if n_obs < BLOCK:
        raise SystemExit(f"[VERIFY] train split too small ({n_obs} months) to block-bootstrap.")

    rng = np.random.default_rng(SEED)
    starts = np.arange(0, n_obs - BLOCK + 1)
    n_blocks = int(np.ceil(n_obs / BLOCK))

    slopes, intercepts = [], []
    for _ in range(N_BOOT):
        picks = rng.choice(starts, size=n_blocks, replace=True)
        idx = (picks[:, None] + np.arange(BLOCK)).ravel()[:n_obs]
        sample = train_vals[idx]
        m = LinearRegression().fit(sample[:, 0].reshape(-1, 1), sample[:, 1])
        slopes.append(m.coef_[0])
        intercepts.append(m.intercept_)

    return {
        "train_months": int(n_obs),
        "slope_ci": [round(float(np.percentile(slopes, 2.5)), 4),
                     round(float(np.percentile(slopes, 97.5)), 4)],
        "intercept_ci": [round(float(np.percentile(intercepts, 2.5)), 2),
                         round(float(np.percentile(intercepts, 97.5)), 2)],
    }


def main() -> int:
    metrics_path = PROCESSED / "metrics.json"
    if not metrics_path.exists() or not (PROCESSED / "monthly.csv").exists():
        print("[VERIFY] metrics.json / monthly.csv missing — run the pipeline first.")
        return 1

    shipped = json.loads(metrics_path.read_text(encoding="utf-8"))["fitted_linear_model"]
    fresh = recompute()

    checks = {
        "slope CI": (shipped.get("bootstrap_slope_95_ci"), fresh["slope_ci"]),
        "intercept CI": (shipped.get("bootstrap_intercept_95_ci"), fresh["intercept_ci"]),
    }
    ok = True
    for name, (a, b) in checks.items():
        same = (isinstance(a, list) and len(a) == 2
                and abs(float(a[0]) - b[0]) <= TOL and abs(float(a[1]) - b[1]) <= TOL)
        print(f"[VERIFY] {name:<13} shipped={a} recomputed={b} -> {'MATCH' if same else 'MISMATCH'}")
        ok = ok and same

    method = str(shipped.get("bootstrap_method", ""))
    method_ok = "moving-block" in method and "12-month" in method
    print(f"[VERIFY] method string -> {'OK' if method_ok else 'MISSING/UNEXPECTED'}: {method!r}")
    ok = ok and method_ok

    print(f"[VERIFY] train months used: {fresh['train_months']} (expected 84)")
    ok = ok and fresh["train_months"] == 84

    print("[VERIFY] PASSED — shipped interval is reproducible from monthly.csv"
          if ok else "[VERIFY] FAILED — shipped interval does not match the recomputation")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
