"""
Regenerate the browser dashboard's numbers from the pipeline outputs.

  * app.js      -> CHT_SERIES block from data/processed/monthly_harmonized.csv
  * app.js      -> MODEL_PARAMS block from data/processed/metrics.json
  * app.js      -> MAP_CELLS block from data/processed/clean_{modis,viirs}.csv
  * app.js      -> CHT_BOUNDARY block from data/reference/ geoBoundaries ADM2
  * index.html  -> held-out validation section from data/processed/metrics.json
  * index.html  -> naive-spike callout from the measured sensor-shift ratio

Same idea as tools/sync_readme.py: the HTML/JS never carries a metric that was
typed by hand, so the UI cannot drift from metrics.json (enforced by --check in CI).

Usage:  python tools/sync_web.py [--check]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "processed" / "monthly_harmonized.csv"
METRICS = ROOT / "data" / "processed" / "metrics.json"
APPJS = ROOT / "app.js"
INDEX = ROOT / "index.html"


def _num(v, digits=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), digits)


CLEAN_MODIS = ROOT / "data" / "processed" / "clean_modis.csv"
CLEAN_VIIRS = ROOT / "data" / "processed" / "clean_viirs.csv"

sys.path.insert(0, str(ROOT))
from analysis.clean import REGION_DISTRICTS, REGION_GEOJSON  # noqa: E402


def _round_nested(node, nd: int = 4):
    """Round GeoJSON coordinate pairs to ~11 m precision (keeps the file small)."""
    if node and isinstance(node[0], (int, float)):
        return [round(float(node[0]), nd), round(float(node[1]), nd)]
    return [_round_nested(x, nd) for x in node]


def build_cht_boundary() -> str:
    """The three CHT district polygons (geoBoundaries BGD-ADM2) for the Leaflet map."""
    gj = json.loads(REGION_GEOJSON.read_text(encoding="utf-8"))
    feats = []
    for f in gj.get("features", []):
        name = (f.get("properties") or {}).get("shapeName")
        if name not in REGION_DISTRICTS:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"shapeName": name},
            "geometry": {
                "type": f["geometry"]["type"],
                "coordinates": _round_nested(f["geometry"]["coordinates"]),
            },
        })
    got = {f["properties"]["shapeName"] for f in feats}
    if got != set(REGION_DISTRICTS):
        raise SystemExit(f"[SYNC-WEB] boundary: expected {sorted(REGION_DISTRICTS)}, got {sorted(got)}")
    fc = {"type": "FeatureCollection", "features": feats}
    return "const CHT_BOUNDARY = " + json.dumps(fc, separators=(",", ":")) + ";"
CELL_DEG = 0.05          # ~5 km display grid for the map
CELL_TOP_N = 30          # busiest cells drawn per sensor-year


def build_map_cells() -> str:
    """Top real detection cells per year (0.05° grid) straight from the clean CSVs.

    The map draws these instead of any hand-listed 'hotspot' points, so every
    circle the user sees is an actual NASA FIRMS detection aggregate.
    """
    cells: dict[str, list] = {"modis": [], "viirs": []}
    for sensor, path in (("modis", CLEAN_MODIS), ("viirs", CLEAN_VIIRS)):
        if not path.exists():
            continue
        d = pd.read_csv(path, usecols=["latitude", "longitude", "acq_date"])
        d["year"] = d["acq_date"].astype(str).str.slice(0, 4).astype(int)
        d = d[(d["year"] >= 2002) & (d["year"] <= 2021)]   # study window; drop download-boundary rows
        d["clat"] = (d["latitude"] / CELL_DEG).round() * CELL_DEG
        d["clon"] = (d["longitude"] / CELL_DEG).round() * CELL_DEG
        g = d.groupby(["year", "clat", "clon"]).size().reset_index(name="n")
        g = g.sort_values("n", ascending=False).groupby("year").head(CELL_TOP_N)
        for _, r in g.iterrows():
            cells[sensor].append(
                (int(r["year"]), round(float(r["clat"]), 3), round(float(r["clon"]), 3), int(r["n"]))
            )

    lines = ["const MAP_CELLS = {"]
    for sensor in ("modis", "viirs"):
        lines.append(f"  {sensor}: [")
        rows = [
            f"    {{y:{y}, lat:{la}, lon:{lo}, n:{n}}}"
            for y, la, lo, n in sorted(cells[sensor])
        ]
        if rows:
            lines.append(",\n".join(rows) + ",")
        lines.append("  ],")
    lines.append("};")
    return "\n".join(line for line in lines if line != "")


def build_series() -> str:
    df = pd.read_csv(CSV)
    lines = ["const CHT_SERIES = ["]
    last_year = None
    for _, r in df.iterrows():
        y = int(r["year"])
        if last_year is not None and y != last_year:
            lines.append(f"  // {y}")
        last_year = y

        modis = _num(r["modis"], 0)
        viirs = _num(r["viirs"], 0)
        harm = _num(r.get("harmonized_splice"), 1)

        def js(v):
            """NaN means "no data" — never coerce it to 0 in the UI."""
            return "null" if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))

        parts = [
            f'm:"{r["month"]}"',
            f"y:{y}",
            f"mn:{int(r['month_num'])}",
            f"modis:{js(modis)}",
            f"viirs:{js(viirs)}",
            f"harm:{js(harm)}",
        ]
        lines.append("  {" + ",".join(parts) + "},")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("];")
    return "\n".join(lines)


def _finite(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def build_model_params(m: dict) -> str:
    """Fitted linear model + bootstrap coefficient intervals for the JS playground."""
    f = m.get("fitted_linear_model", {}) or {}
    slope = float(f["slope"])
    intercept = float(f["intercept"])
    slope_ci = [float(v) for v in f["bootstrap_slope_95_ci"]]
    int_ci = [float(v) for v in f["bootstrap_intercept_95_ci"]]
    step = _finite(m.get("observed_sensor_shift_ratio"))
    ovl = _finite(m.get("overlap_viirs_to_modis_ratio"))
    lines = [
        "const MODEL_PARAMS = {",
        f"  slope: {slope},",
        f"  intercept: {intercept},",
        f"  slopeCI: [{slope_ci[0]}, {slope_ci[1]}],",
        f"  interceptCI: [{int_ci[0]}, {int_ci[1]}]",
    ]
    extra = []
    if step is not None:
        extra.append(f"  stepRatio: {step}")
    if ovl is not None:
        extra.append(f"  overlapRatio: {ovl}")
    if extra:
        lines[4] += ","
        lines.extend([f"{e}," for e in extra[:-1]] + [extra[-1]])
    lines.append("};")
    return "\n".join(lines)


def build_validation(m: dict) -> str:
    src = m.get("data_source", {}) or {}
    imp = m.get("performance_improvement", {})
    naive = m["held_out_test_comparison"]["naive_raw_viirs_vs_modis"]
    lin = m["held_out_test_comparison"]["harmonized_linear_vs_modis"]

    region = m.get("region_filter") or {}
    if src.get("is_nasa_firms"):
        region_note = ""
        if region.get("name"):
            dropped = region.get("dropped_outside_region") or {}
            modis_dropped = dropped.get('modis', 0)
            viirs_dropped = dropped.get('viirs', 0)
            region_note = (
                f" Detections restricted to <strong>{region['name']}</strong> "
                f"polygons (geoBoundaries BGD-ADM2); {modis_dropped:,} MODIS and "
                f"{viirs_dropped:,} VIIRS rows outside the CHT dropped."
            )
        prov = ("<strong>Data source: NASA FIRMS Area API</strong> (MODIS_SP, VIIRS_SNPP_SP) "
                "over the CHT window — recorded in <code>data/processed/data_source.json</code>."
                + region_note)
    else:
        prov = ("<strong>⚠ DEMO DATA — not NASA FIRMS.</strong> These figures come from a "
                "simulated monthly series used to exercise the pipeline. Run "
                "<code>python probe_firms.py --run-all</code> with a FIRMS <code>MAP_KEY</code> "
                "before submission.")

    def pct(v, dash="n/a"):
        if v is None:
            return dash
        return f"-{v}%" if v >= 0 else f"+{-v}%"

    def chip(v, dash="n/a"):
        if v is None:
            return dash
        return f"▼ -{v}%" if v >= 0 else f"▲ +{-v}%"

    def signed(v):
        return "n/a" if v is None else f"{'+' if v >= 0 else ''}{v}"

    rmse_imp = imp.get("rmse_reduction_percent")
    bias_imp = imp.get("bias_reduction_percent")
    r2 = lin.get("r2")
    naive_r2 = naive.get("r2")
    rho = lin.get("spearman_corr")
    rho_pct = None if rho is None else round(rho * 100, 1)
    r2_pct = None if r2 is None else round(r2 * 100, 1)

    # Same verdict thresholds as README §2 (sync_readme.py): >=0.95 strong,
    # >=0.90 good, else fair — one vocabulary across every surface.
    if r2 is None:
        r2_chip = "N/A"
    elif r2 >= 0.95:
        r2_chip = "STRONG"
    elif r2 >= 0.9:
        r2_chip = "GOOD"
    else:
        r2_chip = "FAIR"

    step = m.get("observed_sensor_shift_ratio")
    ovl = m.get("overlap_viirs_to_modis_ratio")
    step_s = "n/a" if step is None or step != step else f"{step}×"
    ovl_s = "n/a" if ovl is None or ovl != ovl else f"{ovl}×"

    sens_path = ROOT / "data" / "processed" / "sensitivity.json"
    sens_line = ""
    if sens_path.exists():
        try:
            sens = json.loads(sens_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sens = None
        d = (sens or {}).get("delta") or {}
        if d.get("slope_percent") is not None:
            sens_line = (
                f"<br>Confidence-threshold sensitivity: keeping low-confidence detections moves the slope "
                f"by <strong>{d.get('slope_percent')}%</strong> and <strong>increases</strong> held-out RMSE by "
                f"<strong>{d.get('test_rmse_percent')}%</strong> — baseline thresholds are reported."
            )



    return f"""      <div id="proof-cards" class="proof-grid" aria-live="polite">
        <div class="proof-card">
          <p class="proof-num">{lin.get("rmse", "n/a")}</p>
          <p class="proof-label">Wrong guesses per month (lower is better)</p>
          <p class="proof-hint">Wrong join was {naive.get("rmse", "n/a")} → we cut it by {imp.get("rmse_reduction_percent", "n/a")}%.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{signed(lin.get("bias"))}</p>
          <p class="proof-label">Always-too-high problem (0 is fair)</p>
          <p class="proof-hint">Wrong join was {signed(naive.get("bias"))} → cut by {imp.get("bias_reduction_percent", "n/a")}%.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{r2 if r2 is not None else "n/a"}</p>
          <p class="proof-label">How well it follows real ups and downs (1.0 = perfect)</p>
          <p class="proof-hint">{("Scored " + str(r2_pct) + " out of 100 against the real record." if r2_pct is not None else "")} Wrong join: {naive_r2}.</p>
        </div>
      </div>
      <p class="proof-note">{prov}
      Learned on 2012–2018, tested on 2019–2021. Full formula &amp; confidence intervals: see the “Wrong Join” section above.</p>"""


def build_naive_callout(m: dict) -> str:
    shift = m.get("observed_sensor_shift_ratio")
    if shift is None or shift != shift:
        return '<strong>Wrong join: much too high after 2012.</strong>'
    return f'<strong>Wrong join: almost {shift}× too high after 2012.</strong>'


def build_naive_copy(m: dict) -> str:
    shift = m.get("observed_sensor_shift_ratio")
    if shift is None or shift != shift:
        claim = "much higher"
    else:
        claim = f"almost {shift}\u00d7 higher"
    return (
        f"If we join the two cameras directly, fires look {claim} after 2012 — "
        "but only the camera changed, not the forest."
    )


SIM_BASELINE = 300   # default slider position in index.html


def build_sim_defaults(m: dict) -> dict[str, str]:
    """Static pre-JS values for the calibration playground, at the default slider input.

    The JS recomputes on load, but these must never contradict the fitted model
    (they are what a reader sees before scripts run, or if scripts fail).
    Mirrors updateSimulator() in app.js exactly, including its CI envelope.
    """
    f = m.get("fitted_linear_model", {}) or {}
    slope = float(f["slope"])
    intercept = float(f["intercept"])
    s_ci = [float(v) for v in f["bootstrap_slope_95_ci"]]
    i_ci = [float(v) for v in f["bootstrap_intercept_95_ci"]]

    x = SIM_BASELINE
    pred = max(0.0, slope * x + intercept)
    lo = max(0.0, s_ci[0] * x + min(i_ci[0], i_ci[1]))
    hi = s_ci[1] * x + max(i_ci[0], i_ci[1])
    mit = (1.0 - pred / x) * 100 if x > 0 else 0.0

    return {
        "SIM_DEFAULT_MODIS":
            f'<span id="sim-out-modis" class="sim-out-val font-mono text-green">{pred:.1f}</span>',
        "SIM_DEFAULT_CI":
            f'<span id="sim-out-ci" class="sim-out-val font-mono">[{lo:.1f}, {hi:.1f}]</span>',
        "SIM_DEFAULT_MITIGATION":
            f'<span id="sim-out-mitigation" class="sim-out-val font-mono text-amber">-{mit:.1f}%</span>',
    }


def replace_block(text: str, begin: str, end: str, body: str) -> str:
    if begin not in text or end not in text:
        raise RuntimeError(f"markers not found: {begin} / {end}")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError(
            f"marker must appear exactly once (found {text.count(begin)}x/{text.count(end)}x): "
            f"{begin} / {end}"
        )
    if text.index(begin) > text.index(end):
        raise RuntimeError(f"marker order reversed: {begin} after {end}")
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(lambda _: begin + "\n" + body + "\n" + end, text, count=1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync app.js and index.html from pipeline outputs")
    parser.add_argument("--check", action="store_true", help="Exit 1 if either file is out of date")
    args = parser.parse_args(argv)

    if not CSV.exists() or not METRICS.exists():
        print(f"[SYNC-WEB] Missing {CSV.name}/{METRICS.name} — run the pipeline first "
              "(python probe_firms.py --run-all or --demo).")
        return 1

    metrics = json.loads(METRICS.read_text(encoding="utf-8"))

    js = APPJS.read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")

    new_js = replace_block(js, "// BEGIN:CHT_SERIES", "// END:CHT_SERIES", build_series())
    new_js = replace_block(new_js, "// BEGIN:MODEL_PARAMS", "// END:MODEL_PARAMS", build_model_params(metrics))
    new_js = replace_block(new_js, "// BEGIN:MAP_CELLS", "// END:MAP_CELLS", build_map_cells())
    new_js = replace_block(new_js, "// BEGIN:CHT_BOUNDARY", "// END:CHT_BOUNDARY", build_cht_boundary())
    new_html = replace_block(html, "<!-- BEGIN:VALIDATION_METRICS -->", "<!-- END:VALIDATION_METRICS -->",
                             build_validation(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:NAIVE_CALLOUT -->", "<!-- END:NAIVE_CALLOUT -->",
                             build_naive_callout(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:NAIVE_COPY -->", "<!-- END:NAIVE_COPY -->",
                             build_naive_copy(metrics))
    for key, body in build_sim_defaults(metrics).items():
        new_html = replace_block(new_html, f"<!-- BEGIN:{key} -->", f"<!-- END:{key} -->", body)


    changed = (new_js != js) or (new_html != html)
    if args.check:
        if changed:
            print("[SYNC-WEB] app.js / index.html are OUT OF DATE — run: python tools/sync_web.py")
            return 1
        print("[SYNC-WEB] app.js and index.html are up to date.")
        return 0

    if not changed:
        print("[SYNC-WEB] app.js and index.html already up to date.")
        return 0

    APPJS.write_text(new_js, encoding="utf-8")
    INDEX.write_text(new_html, encoding="utf-8")
    print("[SYNC-WEB] app.js CHT_SERIES + MODEL_PARAMS + MAP_CELLS + CHT_BOUNDARY regenerated from pipeline outputs")
    print("[SYNC-WEB] index.html validation section + spike callout regenerated from metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
