#!/usr/bin/env python3
"""
BD-FireOps · latest near-real-time (NRT) snapshot from NASA FIRMS.

Writes data/processed/live_feed.json, which tools/sync_web.py embeds in app.js
(so the page also works from file:// and offline) and which the deployed page
re-reads at runtime when it is served over HTTP.

Scientific rules (kept deliberately strict):
  * NRT detections are provisional and are NEVER mixed into the fitted record.
  * The MODIS<->VIIRS calibration is fitted on MONTHLY regional totals. It is not
    applied to a 5-day window or to single detections, so no "MODIS-equivalent"
    number is produced here. The page compares the window with the archive's
    typical month instead, and says so.
  * Suomi-NPP stopped delivering on 1 Nov 2026, so the VIIRS legs are NOAA-20 and
    NOAA-21. MODIS NRT is kept as a separate, unconverted count.
  * Same confidence gates as analysis/clean.py: VIIRS low-confidence ('l') and
    MODIS confidence < 30 are dropped.

Usage:  python tools/fetch_live.py [--days 1-5]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from analysis.clean import assign_districts  # noqa: E402

BBOX = "91.9,21.4,92.9,23.8"
API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
OUT = ROOT / "data" / "processed" / "live_feed.json"

SOURCES = {
    # key: (FIRMS source, label, family)
    "noaa20": ("VIIRS_NOAA20_NRT", "NOAA-20 VIIRS 375 m", "viirs"),
    "noaa21": ("VIIRS_NOAA21_NRT", "NOAA-21 VIIRS 375 m", "viirs"),
    "modis": ("MODIS_NRT", "Terra/Aqua MODIS 1 km", "modis"),
}
KEEP_COLS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence",
             "frp", "daynight", "district", "sensor_key", "sensor_label"]


def _redact(text: str, key: str) -> str:
    """Never let the MAP_KEY reach the JSON, the console or git."""
    text = str(text)
    if key:
        text = text.replace(key, "***")
    return re.sub(r"/csv/[^/]+/", "/csv/***/", text)


def _confident(df: pd.DataFrame, family: str) -> pd.DataFrame:
    if "confidence" not in df.columns:
        return df
    if family == "viirs":
        return df[df["confidence"].astype(str).str.lower() != "l"]
    conf = pd.to_numeric(df["confidence"], errors="coerce")
    return df[conf >= 30]


def fetch_live_feed(days: int = 5) -> dict:
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key or key == "your_firms_map_key_here":
        raise ValueError("Set a valid FIRMS_MAP_KEY in .env to fetch the NRT snapshot.")
    days = max(1, min(5, int(days)))

    sources, inside, outside = {}, [], []
    for skey, (source, label, family) in SOURCES.items():
        url = f"{API_BASE}/{key}/{source}/{BBOX}/{days}"
        try:
            resp = requests.get(url, timeout=25)
        except requests.RequestException as exc:
            sources[skey] = {"label": label, "status": "error", "detail": _redact(exc, key)}
            continue
        if resp.status_code != 200:
            sources[skey] = {"label": label, "status": "error", "detail": f"HTTP {resp.status_code}"}
            continue
        body = resp.text.strip()
        if not body or "latitude" not in body.splitlines()[0]:
            sources[skey] = {"label": label, "status": "error", "detail": _redact(body[:120], key)}
            continue
        df = pd.read_csv(StringIO(body))
        raw = len(df)
        df = _confident(df, family)
        df["district"] = assign_districts(df)
        df["sensor_key"] = skey
        df["sensor_label"] = label
        cols = [c for c in KEEP_COLS if c in df.columns]
        rows = df[cols].to_dict(orient="records")
        n_in = sum(1 for r in rows if r.get("district"))
        sources[skey] = {"label": label, "family": family, "status": "ok",
                         "raw_rows": raw, "kept_rows": len(rows), "cht_rows": n_in}
        for r in rows:
            (inside if r.get("district") else outside).append(r)

    ok = [s for s in sources.values() if s["status"] == "ok"]
    status = "error" if not ok else ("ok" if inside else "empty")
    today = dt.datetime.now(dt.timezone.utc)
    by_district: dict[str, int] = {}
    for r in inside:
        by_district[r["district"]] = by_district.get(r["district"], 0) + 1
    dates = sorted({str(r.get("acq_date")) for r in inside + outside if r.get("acq_date")})

    output = {
        "kind": "firms_nrt_snapshot",
        "status": status,                       # ok | empty | error
        "fetched_at": today.strftime("%Y-%m-%dT%H:%MZ"),
        "window_days": days,
        "window_end": today.date().isoformat(),
        "latest_acq_date": dates[-1] if dates else None,
        "bbox": BBOX,
        "study_area": "Chittagong Hill Tracts (Bandarban, Khagrachhari, Rangamati)",
        "sources": sources,
        "cht_count": len(inside),
        "cht_viirs_count": sum(1 for r in inside if r["sensor_key"] != "modis"),
        "cht_modis_count": sum(1 for r in inside if r["sensor_key"] == "modis"),
        "by_district": by_district,
        "note": ("Provisional near-real-time detections. Not converted to MODIS-equivalent: "
                 "the BD-FireOps calibration applies to monthly regional totals only."),
        "detections": inside,
        "outside_cht": outside,
    }
    OUT.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"[LIVE] {status}: {len(inside)} CHT detections, {len(outside)} outside CHT -> {OUT.relative_to(ROOT)}")
    return output


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--days", type=int, default=5, help="Window length in days (FIRMS allows 1-5)")
    fetch_live_feed(ap.parse_args().days)
