"""
BD-FireOps: FIRMS Raw-Detection Cleaning
Plan v3 §5 — cleaning gate that must run BEFORE any model is fit.

Rules:
  * MODIS  : confidence >= 30 (percent)
  * VIIRS  : confidence in {n, h}; low-confidence 'l' dropped for the baseline
             (kept only in the sensitivity run)
  * Reference-sensor gate: MODIS_SP carries Terra AND Aqua. We filter to AQUA
    so the reference shares an afternoon ~13:30 equator crossing with S-NPP
    VIIRS. If no Aqua row exists, the scope is relabelled to a combined
    Terra/Aqua reference instead of silently fitting.
  * drop invalid/out-of-bbox coordinates, drop exact duplicate detections
  * acq_date parsed as UTC; FRP retained for reporting, never fed to the model
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from analysis.download import CHT_BBOX, RAW_DIR, load_raw
except ImportError:  # running as `python analysis/clean.py`
    from download import CHT_BBOX, RAW_DIR, load_raw

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

BBOX_W, BBOX_S, BBOX_E, BBOX_N = (float(v) for v in CHT_BBOX.split(","))

MODIS_CONF_MIN = 30
VIIRS_DROP_CONF = {"l"}

# Study-period clamp (plan v3 §2 scope lock, matches download.py WINDOWS).
# FIRMS can return a straggler day past the window edge (e.g. 2022-01-01 inside
# a 2021-12-29_2021-12-31 chunk). Without this gate that row sits in clean_*.csv
# while the monthly grid ends at 2021-12, so aggregate drops it SILENTLY and the
# audit last_date disagrees with data_source.json windows. Clamp loudly instead.
STUDY_WINDOWS = {
    "modis": ("2002-07-01", "2021-12-31"),
    "viirs": ("2012-01-01", "2021-12-31"),
}

# True-study-area gate: the download bbox is a rectangle that also covers parts of
# India (Mizoram) and Myanmar (Rakhine). We keep only detections inside the three
# CHT district polygons (BBS/OCHA ADM2 via geoBoundaries, CC BY 3.0).
REGION_NAME = "CHT districts (Bandarban, Khagrachhari, Rangamati)"
REGION_GEOJSON = ROOT / "data" / "reference" / "geoBoundaries-BGD-ADM2_simplified.geojson"
REGION_DISTRICTS = ("Bandarban", "Khagrachhari", "Rangamati")
REGION_SOURCE = ("geoBoundaries BGD-ADM2 (BBS / OCHA ROAP), CC BY 3.0, "
                 "data/reference/geoBoundaries-BGD-ADM2_simplified.geojson")
_region_cache: list | None = None


def region_paths() -> list:
    """Cached matplotlib Paths of the three CHT district outer rings."""
    global _region_cache
    if _region_cache is not None:
        return _region_cache
    if not REGION_GEOJSON.exists():
        raise FileNotFoundError(
            f"Region boundary file missing: {REGION_GEOJSON} — the CHT district "
            "filter cannot run without it (refusing to silently keep bbox-only rows)."
        )
    from matplotlib.path import Path as MplPath  # matplotlib already required for charts

    gj = json.loads(REGION_GEOJSON.read_text(encoding="utf-8"))
    paths: list = []
    found: set = set()
    for feat in gj.get("features", []):
        name = feat.get("properties", {}).get("shapeName")
        if name not in REGION_DISTRICTS:
            continue
        found.add(name)
        geom = feat.get("geometry") or {}
        gtype, coords = geom.get("type"), geom.get("coordinates")
        if gtype == "Polygon":
            polys = [coords]
        elif gtype == "MultiPolygon":
            polys = coords
        else:
            continue
        for poly in polys:
            if len(poly) > 1:
                # Interior rings (holes) need even-odd containment logic this gate
                # does not implement - fail loudly rather than counting points
                # inside a hole as inside the district.
                raise NotImplementedError(
                    f"{name}: polygon has {len(poly)} rings (holes unsupported) - "
                    "update region_paths() before re-running."
                )
            paths.append(MplPath(np.asarray(poly[0], dtype=float)))
    if not paths:
        raise RuntimeError(f"No CHT district polygons found in {REGION_GEOJSON.name}")
    missing = set(REGION_DISTRICTS) - found
    if missing:
        # A renamed/renamed-away district would otherwise silently drop its
        # detections as "outside region" forever.
        raise RuntimeError(
            f"District(s) {sorted(missing)} not found in {REGION_GEOJSON.name} - "
            "refusing to treat their detections as outside the study area."
        )
    _region_cache = paths
    return paths


def _drop_outside_region(df: pd.DataFrame, audit: dict) -> pd.DataFrame:
    """Keep only detections inside the CHT district polygons; record the drop."""
    audit["region_filter"] = {"name": REGION_NAME, "source": REGION_SOURCE}
    if df.empty:
        audit["dropped_outside_region"] = 0
        return df
    pts = np.column_stack([
        df["longitude"].to_numpy(dtype=float),
        df["latitude"].to_numpy(dtype=float),
    ])
    keep = np.zeros(len(df), dtype=bool)
    for p in region_paths():
        keep |= p.contains_points(pts)
    audit["dropped_outside_region"] = int((~keep).sum())
    return df[keep]


def _norm_confidence(series: pd.Series) -> pd.Series:
    """FIRMS ships MODIS confidence as a percent number and VIIRS as l/n/h.

    Per-element coercion: a mostly-numeric column with a few letter codes still
    resolves every row (the old whole-column heuristic mapped everything to NaN).
    Unrecognised values stay NaN and are counted as dropped by the caller.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    mapping = {"l": 0.0, "low": 0.0, "n": 50.0, "nominal": 50.0, "h": 100.0, "high": 100.0}
    lowered = series.astype(str).str.strip().str.lower()
    return numeric.fillna(lowered.map(mapping))


def _drop_bad_coords(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    ok = (
        df["latitude"].between(BBOX_S, BBOX_N)
        & df["longitude"].between(BBOX_W, BBOX_E)
    )
    return df[ok.fillna(False)]


def _clamp_study_window(df: pd.DataFrame, audit: dict, sensor: str) -> pd.DataFrame:
    """Drop detections outside the plan scope window; count them loudly.

    Must run AFTER acq_date is parsed to UTC (NaT rows are already gone) and
    BEFORE clean_rows is recorded, so clean_rows + dropped counts reconcile
    and aggregate.py never silently ignores a clean row outside its grid.
    """
    start_s, end_s = STUDY_WINDOWS[sensor]
    audit["study_window"] = f"{start_s} .. {end_s}"
    if df.empty:
        audit["dropped_outside_window"] = 0
        return df
    start = pd.Timestamp(start_s, tz="UTC")
    # End-of-day inclusive: a 2021-12-31 detection is in-scope, 2022-01-01 is not.
    end = pd.Timestamp(end_s, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    ok = (df["acq_date"] >= start) & (df["acq_date"] <= end)
    audit["dropped_outside_window"] = int((~ok.fillna(False)).sum())
    if audit["dropped_outside_window"]:
        bad = df.loc[~ok.fillna(False), "acq_date"]
        audit["outside_window_range"] = [str(bad.min().date()), str(bad.max().date())]
        print(f"[CLEAN] {sensor}: dropped {audit['dropped_outside_window']} row(s) "
              f"outside study window {audit['study_window']}")
    return df[ok.fillna(False)]


def clean_modis(df: pd.DataFrame, keep_low_conf: bool = False) -> tuple[pd.DataFrame, dict]:
    audit: dict = {"sensor": "modis", "raw_rows": int(len(df))}
    if df.empty:
        audit["error"] = "empty raw frame"
        return df, audit

    df = df.copy()
    # MODIS raw split is counted BEFORE the confidence gate: aqua_rows/terra_rows
    # below are post-filter, so raw != aqua+terra when low-confidence rows were
    # removed first (audit note added to stop readers mis-adding them).
    if "satellite" in df.columns:
        _raw_sat = df["satellite"].astype(str)
        audit["raw_aqua_rows"] = int(_raw_sat.str.contains("AQUA", case=False, na=False).sum())
        audit["raw_terra_rows"] = int(_raw_sat.str.contains("TERRA", case=False, na=False).sum())
    if "confidence" in df.columns:
        df["confidence_num"] = _norm_confidence(df["confidence"])
        if keep_low_conf:
            n_drop_conf = 0
        else:
            # Remove-and-count: rows with unparseable confidence (NaN) are dropped
            # too, so the audit sum always reconciles with raw_rows -> clean_rows.
            before_conf = len(df)
            df = df[df["confidence_num"] >= MODIS_CONF_MIN]
            n_drop_conf = before_conf - int(len(df))
        audit["dropped_low_confidence"] = n_drop_conf
    else:
        # Cannot filter what the API did not send — say so instead of dropping rows.
        audit["confidence_col_missing"] = True
        audit["dropped_low_confidence"] = 0

    # Reference-sensor gate: Aqua only (afternoon crossing, matches S-NPP VIIRS)
    sat_col = "satellite" if "satellite" in df.columns else None
    inst_col = "instrument" if "instrument" in df.columns else None
    probe = df[sat_col].astype(str) if sat_col else (df[inst_col].astype(str) if inst_col else pd.Series(dtype=str))
    aqua_mask = probe.str.contains("AQUA", case=False, na=False)
    n_aqua = int(aqua_mask.sum())
    n_terra = int(probe.str.contains("TERRA", case=False, na=False).sum())
    audit["aqua_rows"] = n_aqua
    audit["terra_rows"] = n_terra
    audit["aqua_terra_note"] = ("post-confidence-filter split; raw_aqua_rows/raw_terra_rows "
                                "are the pre-filter split")

    if n_aqua > 0:
        df = df[aqua_mask]
        audit["reference_sensor"] = "Aqua MODIS"
        audit["aqua_filter_applied"] = True
    else:
        audit["reference_sensor"] = (
            "Terra-only MODIS (no Aqua rows present)" if n_terra
            else "MODIS (satellite/instrument column not usable)"
        )
        audit["aqua_filter_applied"] = False

    before_coords = int(len(df))
    df = _drop_bad_coords(df)
    audit["dropped_bad_coords"] = before_coords - int(len(df))

    df = _drop_outside_region(df, audit)

    before = len(df)
    dup_keys = ["latitude", "longitude", "acq_date", "acq_time"] + ([sat_col] if sat_col else [])
    df = df.drop_duplicates(subset=dup_keys)
    audit["dropped_duplicates"] = before - int(len(df))

    before = len(df)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce", utc=True)
    df = df[df["acq_date"].notna()]
    audit["dropped_bad_dates"] = before - int(len(df))

    df = _clamp_study_window(df, audit, "modis")

    audit["clean_rows"] = int(len(df))
    return df.reset_index(drop=True), audit



def clean_viirs(df: pd.DataFrame, keep_low_conf: bool = False) -> tuple[pd.DataFrame, dict]:
    audit: dict = {"sensor": "viirs", "raw_rows": int(len(df)), "aqua_filter_applied": False}
    if df.empty:
        audit["error"] = "empty raw frame"
        return df, audit

    df = df.copy()
    # Source is VIIRS_SNPP_SP; FIRMS codes Suomi-NPP as "N" and NOAA-20 as "N20".
    if "satellite" in df.columns:
        audit["satellites"] = {str(k): int(v) for k, v in df["satellite"].value_counts().items()}

    if "confidence" in df.columns:
        raw_conf = df["confidence"].astype(str).str.strip().str.lower()
        if keep_low_conf:
            audit["dropped_low_confidence"] = 0
        else:
            drop_set = set(VIIRS_DROP_CONF) | {"low"}
            mask = ~raw_conf.isin(drop_set)
            audit["dropped_low_confidence"] = int((~mask).sum())
            df = df[mask]
            # A numeric/'unknown' confidence column would silently disable this
            # gate (baseline == sensitivity) - surface it instead.
            known = drop_set | {"n", "nominal", "h", "high"}
            unknown = sorted(v for v in raw_conf.unique() if v not in known)
            if unknown:
                audit["unrecognised_confidence_values"] = unknown[:10]
                print(f"[CLEAN] viirs: WARNING unrecognised confidence values {unknown[:5]} "
                      "- low-confidence gate may not be filtering anything")
    else:
        audit["confidence_col_missing"] = True
        audit["dropped_low_confidence"] = 0

    before_coords = int(len(df))
    df = _drop_bad_coords(df)
    audit["dropped_bad_coords"] = before_coords - int(len(df))

    df = _drop_outside_region(df, audit)

    before = int(len(df))
    dup_keys = ["latitude", "longitude", "acq_date", "acq_time"]
    if "satellite" in df.columns:
        dup_keys.append("satellite")
    df = df.drop_duplicates(subset=dup_keys)
    audit["dropped_duplicates"] = before - int(len(df))

    before = int(len(df))
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce", utc=True)
    df = df[df["acq_date"].notna()]
    audit["dropped_bad_dates"] = before - int(len(df))

    df = _clamp_study_window(df, audit, "viirs")

    audit["clean_rows"] = int(len(df))
    return df.reset_index(drop=True), audit


def run_clean(keep_low_conf: bool = False) -> dict:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    audits = {}

    for sensor, cleaner in (("modis", clean_modis), ("viirs", clean_viirs)):
        raw = load_raw(sensor)
        if raw.empty:
            audits[sensor] = {"sensor": sensor, "raw_rows": 0, "error": "no raw chunks in data/raw/"}
            # A stale clean file from an earlier run must not be re-aggregated
            # as if it were fresh - delete it so downstream sees "no data".
            stale = [PROCESSED / "clean_modis.csv", PROCESSED / "clean_viirs.csv",
                     PROCESSED / "clean_modis_lowconf.csv", PROCESSED / "clean_viirs_lowconf.csv"]
            removed = [p.name for p in stale if p.name.startswith(f"clean_{sensor}") and p.exists()]
            for name in removed:
                (PROCESSED / name).unlink()
            if removed:
                print(f"[CLEAN] {sensor}: removed stale {', '.join(removed)} (raw input is gone)")
            print(f"[CLEAN] {sensor}: no raw data (run analysis/download.py first)")
            continue
        clean, audit = cleaner(raw, keep_low_conf=keep_low_conf)
        if audit["clean_rows"]:
            audit["first_date"] = str(clean["acq_date"].min().date())
            audit["last_date"] = str(clean["acq_date"].max().date())
        out = PROCESSED / f"clean_{sensor}{'_lowconf' if keep_low_conf else ''}.csv"

        # Atomic write: the full 285k-row run exceeds the tool runner's 30 s
        # limit, which once left a truncated 48k-row clean_viirs.csv in place
        # (silent data corruption). Write to .tmp then atomically replace, so a
        # kill can never publish a half-written CSV. Same-directory tmp keeps
        # the replace atomic; delete=False + explicit replace afterwards.
        tmp = out.with_suffix(".csv.tmp")
        if clean.empty:
            pd.DataFrame(columns=raw.columns).to_csv(tmp, index=False)
        else:
            with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                             dir=str(PROCESSED), newline="",
                                             encoding="utf-8") as _tf:
                tmp = Path(_tf.name)
                clean.to_csv(_tf, index=False)
                _tf.flush()
                try:
                    os.fsync(_tf.fileno())
                except OSError:
                    pass  # e.g. synthetic FS in tests without a real fd
        os.replace(tmp, out)
        audits[sensor] = audit
        print(f"[CLEAN] {sensor}: {audit['raw_rows']} -> {audit['clean_rows']} rows "
              f"(ref={audit.get('reference_sensor', 'VIIRS S-NPP')})")
        if audit["clean_rows"] == 0:
            print(f"[CLEAN] {sensor}: WARNING — nothing survived cleaning; check confidence/bbox rules.")

    tag = "lowconf-kept" if keep_low_conf else "baseline"
    (PROCESSED / f"clean_audit_{tag}.json").write_text(json.dumps(audits, indent=2, default=str), encoding="utf-8")
    return audits



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BD-FireOps FIRMS cleaner")
    parser.add_argument("--sensitivity", action="store_true",
                        help="Keep low-confidence detections (confidence-threshold sensitivity run)")
    args = parser.parse_args(argv)
    run_clean(keep_low_conf=args.sensitivity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
