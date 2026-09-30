"""
BD-FireOps: NASA FIRMS Area API Downloader
Challenge: Harmonization of MODIS and VIIRS Hot Spots (NASA Space Apps 2026)
Team: Claude Fable 7.0
Study Area: Chittagong Hill Tracts (CHT) — bbox 91.9,21.4,92.9,23.8 (w,s,e,n)

Routes (plan v3 §3):
  main   -> FIRMS Area API, 5-day chunks (max DAY_RANGE is 5, verified on the
            official /api/area page), SP (standard processing) sources.
  backup -> FIRMS Archive Download request (email delivery; submit first thing
            on hackathon day, process in parallel if it arrives).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional at import time
    pass

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

# CHT bounding box from the study definition (paper range, rounded outward)
CHT_BBOX = "91.9,21.4,92.9,23.8"

API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# FIRMS Area API accepts DAY_RANGE 1..5 only (verified on /api/area)
MAX_DAY_RANGE = 5
REQUEST_GAP_S = 0.15          # stay far below the 5000 transactions / 10 min limit
HTTP_TIMEOUT_S = 40
MAX_RETRIES = 4
BACKOFF_BASE_S = 2.0

SOURCES = {
    "modis": "MODIS_SP",
    "viirs": "VIIRS_SNPP_SP",
}

# Standard-processing coverage used by this study (plan v3 §2 scope lock)
WINDOWS = {
    # Aqua MODIS starts July 2002; end of the study period is 2021-12
    "modis": ("2002-07-01", "2021-12-31"),
    # S-NPP VIIRS 375 m starts 2012-01-20; we take 2012-01-01 for a clean year grid
    "viirs": ("2012-01-01", "2021-12-31"),
}


def get_map_key(explicit: str | None = None) -> str:
    key = explicit or os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key or key == "your_firms_map_key_here":
        raise SystemExit(
            "[DOWNLOAD] FIRMS_MAP_KEY missing.\n"
            "  1) Register free: https://firms.modaps.eosdis.nasa.gov/api/map_key/\n"
            "  2) Copy .env.example to .env and set FIRMS_MAP_KEY=<your key>\n"
            "  3) Re-run: python probe_firms.py --run-all\n"
            "  (Never commit the .env file.)"
        )
    return key


def fetch_firms_chunk(
    map_key: str,
    source: str,
    bbox: str = CHT_BBOX,
    day_range: int = MAX_DAY_RANGE,
    date_str: str | None = None,
) -> pd.DataFrame:
    """
    Fetch one chunk of active fire records from the NASA FIRMS Area API.

    URL: /api/area/csv/[MAP_KEY]/[SOURCE]/[w,s,e,n]/[DAY_RANGE]/[DATE]
    Returns data for [DATE] .. [DATE + DAY_RANGE - 1].
    Raises on HTTP errors after bounded retries (timeout + backoff).
    """
    if not map_key or map_key == "your_firms_map_key_here":
        raise ValueError("Valid FIRMS_MAP_KEY is required to query the live API.")
    if not 1 <= day_range <= MAX_DAY_RANGE:
        raise ValueError(f"DAY_RANGE must be 1..{MAX_DAY_RANGE} (FIRMS Area API limit).")

    parts = [API_BASE, map_key, source, bbox, str(day_range)]
    if date_str:
        parts.append(date_str)
    url = "/".join(parts)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT_S)
        except requests.RequestException as exc:  # timeout / connection error
            last_error = exc
            time.sleep(BACKOFF_BASE_S * (2 ** attempt))
            continue

        if resp.status_code == 401:
            raise SystemExit(f"[DOWNLOAD] Invalid MAP_KEY for source {source} (HTTP 401).")
        if resp.status_code == 429 or resp.status_code >= 500:
            last_error = RuntimeError(f"HTTP {resp.status_code}")
            time.sleep(BACKOFF_BASE_S * (2 ** attempt))
            continue

        resp.raise_for_status()

        body = resp.text.strip()
        if not body:
            # Empty body is a legitimate "no detections in window" answer.
            return pd.DataFrame()
        if body.startswith(("Invalid", "Error")):
            # Never silently treat an API error message as "zero fires".
            raise RuntimeError(f"[DOWNLOAD] {source} {date_str}: API said {body[:200]!r}")

        return pd.read_csv(StringIO(resp.text))


    raise RuntimeError(f"[DOWNLOAD] {source} {date_str} failed after {MAX_RETRIES} tries: {last_error}")


def _daterange(start: dt.date, end: dt.date, step: int):
    cur = start
    while cur <= end:
        chunk_end = min(cur + dt.timedelta(days=step - 1), end)
        yield cur, chunk_end
        cur = chunk_end + dt.timedelta(days=1)


def download_source(
    key: str,
    sensor: str,
    start: str,
    end: str,
    day_range: int = MAX_DAY_RANGE,
    resume: bool = True,
) -> Path:
    """
    Download every 5-day chunk for one sensor into data/raw/<sensor>/.
    Chunk files are written even when a window has zero detections, so a re-run
    resumes instead of re-downloading (idempotent).
    """
    source = SOURCES[sensor]
    out_dir = RAW_DIR / sensor
    out_dir.mkdir(parents=True, exist_ok=True)

    start_d = dt.date.fromisoformat(start)
    end_d = dt.date.fromisoformat(end)
    windows = list(_daterange(start_d, end_d, day_range))

    total_rows = 0
    fetched = 0
    resumed = 0
    for i, (w_start, w_end) in enumerate(windows, start=1):
        fname = f"{w_start.isoformat()}_{w_end.isoformat()}.csv"
        fpath = out_dir / fname
        if resume and fpath.exists() and fpath.stat().st_size > 0:
            resumed += 1
            continue

        # The last chunk can be shorter than 5 days: request exactly its span so
        # the API never returns days past the declared window (defence-in-depth
        # filter below). DAY_RANGE=5 on a 3-day tail previously leaked rows
        # dated past `end` (e.g. 2022-01-01 in a 2021-12-31 window).
        span = (w_end - w_start).days + 1
        df = fetch_firms_chunk(key, source, day_range=span, date_str=w_start.isoformat())
        if not df.empty and "acq_date" in df.columns:
            dates = pd.to_datetime(df["acq_date"], errors="coerce").dt.date
            df = df[(dates >= w_start) & (dates <= w_end)]
        # Atomic write: a crash mid-write must not leave a truncated chunk that
        # resume= would then treat as complete (missing days would read as zeros).
        tmp = fpath.with_suffix(".csv.tmp")
        df.to_csv(tmp, index=False)
        tmp.replace(fpath)
        fetched += 1
        total_rows += len(df)

        if fetched % 50 == 0 or i == len(windows):
            print(
                f"  [{sensor}] {i}/{len(windows)} windows · "
                f"{fetched} fetched this run · {resumed} resumed · {total_rows} new rows",
                flush=True,
            )
        time.sleep(REQUEST_GAP_S)

    print(
        f"[DOWNLOAD] {sensor} ({source}) -> {out_dir} "
        f"({len(windows)} windows · {fetched} fetched · {resumed} resumed · {total_rows} new rows)"
    )
    return out_dir



def probe_one_day(key: str) -> None:
    """Plan v3 §3: first run a 1-day test and print status code + columns."""
    print("[PROBE] 1-day test against FIRMS Area API ...")
    source = SOURCES["viirs"]
    url = f"{API_BASE}/{key}/{source}/{CHT_BBOX}/1/2021-03-15"
    resp = requests.get(url, timeout=HTTP_TIMEOUT_S)
    print(f"[PROBE] status={resp.status_code}")
    print(f"[PROBE] first 200 chars: {resp.text[:200]!r}")
    resp.raise_for_status()
    if resp.text.strip():
        cols = pd.read_csv(StringIO(resp.text)).columns.tolist()
        print(f"[PROBE] columns ({len(cols)}): {cols}")


def load_raw(sensor: str) -> pd.DataFrame:
    """Concatenate every chunk file for one sensor (used by clean.py)."""
    out_dir = RAW_DIR / sensor
    files = sorted(out_dir.glob("*.csv")) if out_dir.exists() else []
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            frame = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            continue
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def generate_demo_benchmark(seed: int = 42) -> pd.DataFrame:
    """
    EXPLICIT DEMO DATA — NOT NASA FIRMS OBSERVATIONS.

    Only used when --demo is passed explicitly, or as a labelled fallback so the
    dashboard can be developed before a MAP_KEY is available. Every consumer of
    this frame must surface the "demo" flag (metrics.json data_source field,
    chart watermark, README note).
    """
    import numpy as np

    np.random.seed(seed)
    months = pd.date_range(start="2002-07-01", end="2021-12-01", freq="MS")
    weights = [0.25, 0.95, 2.80, 2.10, 0.70, 0.05, 0.01, 0.01, 0.02, 0.04, 0.10, 0.18]
    anomalies = {
        2002: 0.9, 2003: 1.1, 2004: 1.3, 2005: 0.8, 2006: 1.0,
        2007: 0.9, 2008: 1.2, 2009: 1.0, 2010: 1.1, 2011: 0.8,
        2012: 1.2, 2013: 0.9, 2014: 1.4, 2015: 1.0, 2016: 1.5,
        2017: 0.8, 2018: 1.1, 2019: 1.0, 2020: 1.4, 2021: 1.2,
    }
    base = 85.0
    rows = []
    for stamp in months:
        mu = base * weights[stamp.month - 1] * anomalies.get(stamp.year, 1.0)
        modis = int(max(0, round(np.random.normal(mu, np.sqrt(mu) * 1.2)))) if mu >= 1 else int(np.random.poisson(mu))
        if stamp >= pd.Timestamp("2012-01-01"):
            mult = np.random.uniform(3.2, 4.0)
            if modis == 0:
                viirs = int(np.random.poisson(0.8 * weights[stamp.month - 1]))
            else:
                viirs = int(max(0, round(modis * mult + np.random.normal(0, np.sqrt(modis) * 1.5))))
        else:
            viirs = None
        rows.append(
            {
                "month": stamp.strftime("%Y-%m"),
                "year": stamp.year,
                "month_num": stamp.month,
                "modis": modis,
                "viirs": viirs,
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BD-FireOps FIRMS downloader")
    parser.add_argument("--test", action="store_true", help="1-day API probe: status code + columns")
    parser.add_argument("--demo", action="store_true", help="Write explicitly-labelled DEMO monthly series (no NASA data)")
    parser.add_argument("--sensor", choices=[*SOURCES, "all"], default="all")
    parser.add_argument("--since", type=dt.date.fromisoformat,
                        help="Override window start (YYYY-MM-DD); default is the plan scope")
    parser.add_argument("--until", type=dt.date.fromisoformat,
                        help="Override window end (YYYY-MM-DD); default is the plan scope")
    parser.add_argument("--no-resume", action="store_true", help="Re-fetch chunks that already exist")
    args = parser.parse_args(argv)


    if args.demo:
        out = ROOT / "data" / "processed"
        out.mkdir(parents=True, exist_ok=True)
        df = generate_demo_benchmark()
        df.to_csv(out / "monthly.csv", index=False)
        (out / "data_source.json").write_text(
            '{\n  "kind": "demo",\n  "note": "SIMULATED monthly series. Not NASA FIRMS observations."\n}\n',
            encoding="utf-8",
        )
        print("[DOWNLOAD] DEMO series written to data/processed/monthly.csv (NOT NASA DATA)")
        return 0

    key = get_map_key()

    if args.test:
        probe_one_day(key)
        return 0

    sensors = list(SOURCES) if args.sensor == "all" else [args.sensor]
    if args.since and args.until and args.since > args.until:
        parser.error("--since must be on or before --until")
    for sensor in sensors:
        d_start, d_end = WINDOWS[sensor]
        start = (args.since or dt.date.fromisoformat(d_start)).isoformat()
        end = (args.until or dt.date.fromisoformat(d_end)).isoformat()
        if args.since or args.until:
            print(f"[DOWNLOAD] {sensor}: window override {start} -> {end}")
        download_source(key, sensor, start, end, resume=not args.no_resume)
    print("[DOWNLOAD] Done. Next: python analysis/clean.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
