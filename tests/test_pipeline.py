"""Isolated verification of the real-data path: raw chunks -> clean -> aggregate."""
import json
import shutil
import tempfile
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis import aggregate as agg
from analysis import clean as cln
from analysis import download as dl

TMP = Path(tempfile.mkdtemp(prefix="bd-fireops_fixture_"))
if TMP.exists():
    shutil.rmtree(TMP)
RAW = TMP / "raw"
PROC = TMP / "processed"
RAW.mkdir(parents=True)
PROC.mkdir(parents=True)

dl.RAW_DIR = RAW
agg.RAW_DIR = RAW
agg.PROCESSED = PROC
cln.PROCESSED = PROC

MODIS_COLS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument",
              "confidence", "version", "type", "scan", "track", "frp", "daynight"]
VIIRS_COLS = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument",
              "version", "type", "confidence", "scan", "track", "frp", "daynight"]

m_dir = RAW / "modis"
m_dir.mkdir(parents=True)
modis_rows = [
    {"latitude": 22.19, "longitude": 92.22, "acq_date": "2002-07-02", "acq_time": 510,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 80, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 12.5, "daynight": "D"},
    # exact duplicate -> dropped
    {"latitude": 22.19, "longitude": 92.22, "acq_date": "2002-07-02", "acq_time": 510,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 80, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 12.5, "daynight": "D"},
    # low confidence -> dropped
    {"latitude": 22.5, "longitude": 92.4, "acq_date": "2002-07-03", "acq_time": 600,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 10, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 4.0, "daynight": "D"},
    # Terra -> dropped by the Aqua reference gate
    {"latitude": 22.6, "longitude": 92.5, "acq_date": "2002-07-04", "acq_time": 300,
     "satellite": "Terra", "instrument": "MODIS", "confidence": 90, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 20.0, "daynight": "D"},
    # outside bbox -> dropped
    {"latitude": 30.0, "longitude": 95.0, "acq_date": "2002-07-05", "acq_time": 700,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 95, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 30.0, "daynight": "D"},
    # inside bbox but outside the CHT district polygons -> dropped by the region gate
    {"latitude": 22.3, "longitude": 92.1, "acq_date": "2002-07-02", "acq_time": 800,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 85, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 9.0, "daynight": "D"},
]
pd.DataFrame(modis_rows, columns=MODIS_COLS).to_csv(m_dir / "2002-07-01_2002-07-05.csv", index=False)
pd.DataFrame(columns=MODIS_COLS).to_csv(m_dir / "2002-07-06_2002-07-10.csv", index=False)
# later zero chunk, leaving a coverage GAP between 2002-08 and 2011-11
pd.DataFrame(columns=MODIS_COLS).to_csv(m_dir / "2011-12-01_2011-12-05.csv", index=False)
# out-of-window straggler: chunk name is inside coverage, but the API sometimes
# returns a day past the study edge (real 2022-01-01 case in VIIRS). The
# study-window clamp must drop it loudly instead of aggregating it silently.
pd.DataFrame([{"latitude": 22.19, "longitude": 92.22, "acq_date": "2030-05-01", "acq_time": 510,
     "satellite": "Aqua", "instrument": "MODIS", "confidence": 90, "version": "6.1",
     "type": 0, "scan": 1.0, "track": 1.0, "frp": 20.0, "daynight": "D"}],
    columns=MODIS_COLS).to_csv(m_dir / "2011-12-06_2011-12-10.csv", index=False)

v_dir = RAW / "viirs"
v_dir.mkdir(parents=True)
viirs_rows = [
    {"latitude": 22.19, "longitude": 92.22, "acq_date": "2012-01-03", "acq_time": 510,
     "satellite": "Suomi-NPP", "instrument": "VIIRS", "version": "2.0", "type": 0,
     "confidence": "h", "scan": 1.0, "track": 1.0, "frp": 8.0, "daynight": "D"},
    {"latitude": 22.19, "longitude": 92.22, "acq_date": "2012-01-04", "acq_time": 550,
     "satellite": "Suomi-NPP", "instrument": "VIIRS", "version": "2.0", "type": 0,
     "confidence": "l", "scan": 1.0, "track": 1.0, "frp": 3.0, "daynight": "D"},  # low -> dropped
    {"latitude": 22.5, "longitude": 92.3, "acq_date": "2012-01-05", "acq_time": 600,
     "satellite": "Suomi-NPP", "instrument": "VIIRS", "version": "2.0", "type": 0,
     "confidence": "n", "scan": 1.0, "track": 1.0, "frp": 6.0, "daynight": "D"},
    # inside bbox but outside CHT district polygons -> region gate
    {"latitude": 22.3, "longitude": 92.1, "acq_date": "2012-01-06", "acq_time": 700,
     "satellite": "Suomi-NPP", "instrument": "VIIRS", "version": "2.0", "type": 0,
     "confidence": "h", "scan": 1.0, "track": 1.0, "frp": 7.0, "daynight": "D"},
]
pd.DataFrame(viirs_rows, columns=VIIRS_COLS).to_csv(v_dir / "2012-01-01_2012-01-05.csv", index=False)

audits = cln.run_clean()
df = agg.run_aggregate()

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"PASS: {name}")
    else:
        failures.append(f"FAIL: {name} {detail}")
        print(f"FAIL: {name} {detail}")


check("modis raw 6 rows", audits["modis"]["raw_rows"] == 7, audits["modis"])
check("modis clean 1 row (dup+lowconf+Terra+bbox+region removed)", audits["modis"]["clean_rows"] == 1, audits["modis"])
check("modis region gate dropped the out-of-CHT row", audits["modis"]["dropped_outside_region"] == 1, audits["modis"])
check("study-window clamp dropped the 2030 straggler", audits["modis"].get("dropped_outside_window") == 1, audits["modis"])
check("study window recorded", audits["modis"].get("study_window") == "2002-07-01 .. 2021-12-31", audits["modis"])
check("raw pre-filter aqua/terra split recorded",
      audits["modis"].get("raw_aqua_rows") == 6 and audits["modis"].get("raw_terra_rows") == 1, audits["modis"])
check("post-filter split recorded with note",
      audits["modis"].get("aqua_rows") == 5 and "post-confidence" in audits["modis"].get("aqua_terra_note", ""))
check("region filter recorded with source", "geoBoundaries" in (audits["modis"].get("region_filter") or {}).get("source", ""), audits["modis"])
check("aqua filter applied", audits["modis"]["aqua_filter_applied"] is True)
check("terra counted but dropped", audits["modis"]["terra_rows"] == 1 and audits["modis"]["aqua_rows"] == 5,
      audits["modis"])
check("viirs raw 4 rows", audits["viirs"]["raw_rows"] == 4, audits["viirs"])
check("viirs clean 2 rows (low conf 'l' + out-of-CHT dropped)", audits["viirs"]["clean_rows"] == 2, audits["viirs"])
check("viirs region gate dropped the out-of-CHT row", audits["viirs"]["dropped_outside_region"] == 1, audits["viirs"])

src = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
check("provenance kind=nasa_firms_api", src["kind"] == "nasa_firms_api")
check("modis window from raw chunks", src["windows"]["modis"] == ["2002-07", "2011-12"], src["windows"])
check("viirs window from raw chunks", src["windows"]["viirs"] == ["2012-01", "2012-01"], src["windows"])
check("modis covered months = 2", src["covered_months"]["modis"] == 2, src["covered_months"])
check("modis gap months reported", src["gap_months"]["modis"] == 113, src["gap_months"])

check("grid = 115 months", len(df) == 115, f"len={len(df)}")
m, v = df["modis"], df["viirs"]
check("2002-07 modis=1", int(m.iloc[0]) == 1, m.iloc[0])
check("2002-08 modis NaN (no chunk = no data)", pd.isna(m.iloc[1]), m.iloc[1])
check("2011-12 modis=0 (covered zero month kept)", int(m.iloc[113]) == 0, m.iloc[113])
check("2011-12 viirs NaN (VIIRS absent)", pd.isna(v.iloc[113]), v.iloc[113])
check("2012-01 viirs=2", int(v.iloc[114]) == 2, v.iloc[114])
check("modis zero-months = 1", int((m == 0).sum()) == 1, int((m == 0).sum()))
check("viirs zero-months = 0", int((v == 0).sum()) == 0, int((v == 0).sum()))

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("\nALL CHECKS PASSED")
