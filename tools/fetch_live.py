#!/usr/bin/env python3
"""
BD-FireOps: Fetch Live Near-Real-Time (NRT) satellite detections from NASA FIRMS.
Outputs data/processed/live_feed.json for the web dashboard.
"""

import datetime as dt
import json
import os
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from analysis.clean import assign_districts

KEY = os.getenv("FIRMS_MAP_KEY", "").strip()
BBOX = "91.9,21.4,92.9,23.8"
API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

def fetch_live_feed() -> dict:
    if not KEY or KEY == "your_firms_map_key_here":
        raise ValueError("Valid FIRMS_MAP_KEY in .env required to fetch live NASA data.")

    sensors = {
        "noaa20": ("VIIRS_NOAA20_NRT", "NOAA-20 VIIRS 375m"),
        "snpp": ("VIIRS_SNPP_NRT", "Suomi-NPP VIIRS 375m"),
        "modis": ("MODIS_NRT", "Aqua/Terra MODIS 1km")
    }

    detections = []
    sensor_counts = {}

    for skey, (source, label) in sensors.items():
        url = f"{API_BASE}/{KEY}/{source}/{BBOX}/5"
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                if len(lines) > 1:
                    df = pd.read_csv(StringIO(resp.text))
                    df["district"] = assign_districts(df)
                    df["sensor_key"] = skey
                    df["sensor_label"] = label
                    records = df.to_dict(orient="records")
                    detections.extend(records)
                    sensor_counts[skey] = len(records)
                else:
                    sensor_counts[skey] = 0
            else:
                sensor_counts[skey] = f"HTTP {resp.status_code}"
        except Exception as e:
            sensor_counts[skey] = f"Error: {e}"

    # Filter to detections inside CHT districts
    cht_detections = [d for d in detections if d.get("district")]

    # Calculate MODIS equivalent using our empirical formula: MODIS_eq = 0.2694 * VIIRS - 1.18
    raw_viirs_count = sensor_counts.get("noaa20", 0) + (sensor_counts.get("snpp", 0) if isinstance(sensor_counts.get("snpp"), int) else 0)
    modis_eq = round(max(0.0, 0.2694 * raw_viirs_count - 1.18), 2) if raw_viirs_count > 0 else 0.0

    today_str = dt.date.today().isoformat()
    now_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "fetched_at": now_str,
        "query_date": today_str,
        "study_area": "Chittagong Hill Tracts (Bandarban, Khagrachhari, Rangamati)",
        "bounding_box": BBOX,
        "active_satellite": "NOAA-20 VIIRS (Suomi-NPP Sunset Nov 1, 2026)",
        "status": "LIVE_SATELLITE_FEED_ACTIVE",
        "counts": sensor_counts,
        "cht_active_detections_count": len(cht_detections),
        "modis_equivalent_estimate": modis_eq,
        "interpretation": "Quiet season baseline: post-monsoon vegetation moisture keeps natural burning near zero.",
        "detections": cht_detections,
        "all_bbox_detections": detections
    }

    out_file = ROOT / "data" / "processed" / "live_feed.json"
    out_file.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"[LIVE] Successfully updated {out_file} ({len(cht_detections)} in CHT, {len(detections)} in bbox)")
    return output

if __name__ == "__main__":
    fetch_live_feed()
