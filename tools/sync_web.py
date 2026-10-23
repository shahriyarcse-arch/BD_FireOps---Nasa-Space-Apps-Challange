"""
Regenerate the browser dashboard's numbers from the pipeline outputs.

  * app.js      -> CHT_SERIES block from data/processed/monthly_harmonized.csv
  * app.js      -> MODEL_PARAMS block from data/processed/metrics.json
  * app.js      -> MAP_CELLS block from data/processed/clean_{modis,viirs}.csv
  * app.js      -> CHT_BOUNDARY block from data/reference/ geoBoundaries ADM2
  * index.html  -> held-out validation section from data/processed/metrics.json
  * index.html  -> naive-spike callout from the measured sensor-shift ratio
  * index.html  -> per-district cards from metrics.per_district
  * index.html  -> sensor custody strip from metrics.sensor_custody
  * index.html  -> NOAA-20 status panel from metrics.noaa20_model

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
from analysis.window import study_years  # noqa: E402


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
        # Study window from analysis/window.py; drops download-boundary rows
        # without freezing the map at a hardcoded final year.
        year_lo, year_hi = study_years()
        d = d[(d["year"] >= year_lo) & (d["year"] <= year_hi)]
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


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "n/a"


def build_district_panel(m: dict) -> str:
    """Per-district fits (F6/P4) generated from metrics.json.

    Each card repeats the identical split and carries its own scalar-ratio
    baseline, because simple scaling beats the fitted line in some districts and
    hiding that would repeat the original headline mistake one level down.
    """
    block = m.get("per_district") or {}
    districts = block.get("districts") or {}
    regional_slope = _finite((m.get("fitted_linear_model") or {}).get("slope"))
    if not districts:
        return '<p class="muted">Per-district fits unavailable for this run.</p>'

    cards = []
    for name in REGION_DISTRICTS:
        e = districts.get(name) or {}
        status = e.get("status", "unavailable")
        det = e.get("clean_detections") or {}
        det_total = (det.get("modis") or 0) + (det.get("viirs") or 0)
        if status != "fitted":
            cards.append(f"""          <div class="district-card">
            <div class="district-card-header">
              <strong>{name}</strong>
              <span class="font-mono text-amber small">Not fitted</span>
            </div>
            <p class="district-stat font-mono">Indicative only</p>
            <p class="district-sub">Detections: {_fmt_int(det_total)}</p>
            <p class="district-status text-amber small">{e.get("reason", e.get("note", "insufficient overlap"))}</p>
          </div>""")
            continue

        slope = e.get("slope")
        r2 = e.get("held_out_r2")
        rmse = e.get("held_out_rmse")
        bias = e.get("held_out_bias")
        rho = e.get("held_out_spearman")
        scalar_rmse = e.get("held_out_scalar_rmse")
        ci = e.get("bootstrap_slope_95_ci") or []
        ci_s = f"[{ci[0]}, {ci[1]}]" if len(ci) == 2 else "n/a"
        consistent = (
            regional_slope is not None and slope is not None
            and abs(slope - regional_slope) <= 0.15 * abs(regional_slope)
        )
        beat_scalar = (
            rmse is not None and scalar_rmse is not None and rmse < scalar_rmse
        )
        if beat_scalar:
            scalar_line = (
                f'<p class="district-sub text-green">Fit beats simple scaling: {rmse:.2f} vs {scalar_rmse:.2f}</p>'
            )
        else:
            delta = None if (rmse is None or scalar_rmse is None) else abs(scalar_rmse - rmse)
            scalar_line = (
                f'<p class="district-sub text-amber">Simple scaling is as good or better: '
                f'{scalar_rmse:.2f} vs {rmse:.2f}' + (f" ({delta:.2f} lower RMSE)" if delta is not None else "") + '</p>'
            )
        cards.append(f"""          <div class="district-card">
            <div class="district-card-header">
              <strong>{name}</strong>
              <span class="font-mono text-blue small">Slope: {slope:.4f}</span>
            </div>
            <p class="district-stat font-mono">Held-out R²: {r2:.4f}</p>
            <p class="district-sub">RMSE: {rmse:.2f} · Bias: {bias:+.2f} · Detections: {_fmt_int(det_total)}</p>
            <p class="district-sub">Slope 95% CI: {ci_s}</p>
            {scalar_line}
            <p class="district-status text-green small">✓ Spearman {rho:.4f} · {'consistent' if consistent else 'distinct'} vs regional slope {regional_slope:.4f}</p>
          </div>""")

    note = ('Each district repeats the identical 2012–2018 train / 2019–2021 held-out test split and '
            'carries its own scalar-ratio baseline. Where simple scaling matches or beats the fitted '
            'line, the card says so rather than implying a uniform win.')
    return f"""      <div class="district-panel-wrapper">
        <div class="district-panel-header">
          <span class="chart-title">Spatial Validation · Per-District Calibration Fits</span>
          <span class="chart-badge good">3-DISTRICT INDEPENDENT FIT</span>
        </div>
        <p class="small muted" style="margin-bottom: 12px;">
          To verify that the regional calibration is not driven by an outlier district, each
          administrative district is fitted and tested independently on the same split.
        </p>
        <div class="district-grid">
{chr(10).join(cards)}
        </div>
        <p class="small muted" style="margin-top: 12px;">{note}</p>
      </div>"""


def _month_index(month: str) -> int:
    year, mon = (int(p) for p in month.split("-")[:2])
    return year * 12 + mon


def _attr(value) -> str:
    return str(value).replace("&", "&amp;").replace('"', "&quot;")


def build_custody_strip(m: dict) -> str:
    """The sensor-provenance strip, generated from metrics.sensor_custody.

    Every record month must belong to exactly one leg. The undownloaded archive
    after the record edge is shown as a gap, never as NOAA-20 observations.
    """
    custody = m.get("sensor_custody") or {}
    legs = custody.get("legs") or []
    if not legs:
        return '<p class="muted">Sensor custody unavailable for this run.</p>'

    active_key = None
    for leg in legs:
        if leg.get("start", "") <= "2014-07" and (leg.get("end") or "9999-12") >= "2014-07":
            active_key = leg.get("key")
            break

    segments = []
    for leg in legs:
        start = leg.get("start", "")
        end = leg.get("end") or "2030-12"
        months = max(1, _month_index(end) - _month_index(start) + 1)
        flex = months if leg.get("end") else 60
        label = leg.get("label") or leg.get("sensor", "")
        title = (f"{start}–{leg.get('end') or 'present'}: {leg.get('sensor')} "
                 f"({leg.get('resolution')}) · {leg.get('role')}")
        active = " active" if leg.get("key") == active_key else ""
        sensor_label = f"{leg.get('sensor')} ({leg.get('resolution')}) · {leg.get('role')}"
        segments.append(
            f'              <div class="provenance-segment {leg.get("css", "")}{active}" '
            f'data-start="{start}" data-end="{leg.get("end") or "2099-12"}" '
            f'data-label="{_attr(sensor_label)}" style="flex: {flex};" title="{_attr(title)}">\n'
            f'                <span class="seg-label">{label}</span>\n'
            f'              </div>'
        )
    return "\n".join(segments)


def build_custody_legend(m: dict) -> str:
    """Legend for the custody strip, with the NOAA leg's real status."""
    legs = (m.get("sensor_custody") or {}).get("legs") or []
    if not legs:
        return ""
    seen = set()
    legend = []
    short = {
        "modis": "Aqua MODIS (1 km)",
        "snpp_train": "S-NPP VIIRS Train",
        "snpp_test": "S-NPP VIIRS Test",
        "gap": "No archive downloaded",
        "noaa20": "NOAA-20 / 21 (next leg)",
    }
    for leg in legs:
        key = leg.get("key")
        if key in seen:
            continue
        seen.add(key)
        name = short.get(key, f'{leg.get("sensor")} ({leg.get("resolution")})')
        if key == "noaa20" and (m.get("noaa20_model") or {}).get("status") != "fitted":
            name += " — not fitted"
        legend.append(f'              <span><i class="dot {leg.get("dot", "")}"></i> {name}</span>')
    legend.append('              <span class="small text-amber" style="margin-left: auto;">'
                  '⚡ S-NPP Science Sunset: 1 Nov 2026</span>')
    return "\n".join(legend)


def build_noaa20_panel(m: dict) -> str:
    """The NOAA-20 continuity leg (F2/P2): fitted numbers or an honest refusal."""
    n = m.get("noaa20_model") or {}
    status = n.get("status", "not_available")
    months = n.get("overlap_months", 0)
    need = n.get("min_overlap_months", 24)

    if status == "fitted":
        ho = n.get("held_out") or {}
        scalar = n.get("held_out_scalar") or {}
        ci = n.get("bootstrap_slope_95_ci") or []
        ci_s = f"[{ci[0]}, {ci[1]}]" if len(ci) == 2 else "n/a"
        scalar_note = ""
        if scalar.get("rmse") is not None and ho.get("rmse") is not None:
            if ho["rmse"] < scalar["rmse"]:
                scalar_note = f"Fit beats simple scaling ({ho['rmse']} vs {scalar['rmse']})."
            else:
                scalar_note = (f"Simple scaling is as good or better "
                               f"({scalar['rmse']} vs {ho['rmse']}).")
        return f"""      <div class="proof-grid">
        <div class="proof-card">
          <p class="proof-num font-mono">{n.get("equation")}</p>
          <p class="proof-label">NOAA-20 → S-NPP-equivalent (fitted on the overlap)</p>
          <p class="proof-hint">Slope 95% CI: {ci_s} · {months} overlap months</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{ho.get("rmse")}</p>
          <p class="proof-label">Held-out monthly error (NOAA-20 → S-NPP)</p>
          <p class="proof-hint">Spearman {ho.get("spearman_corr")}</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{scalar.get("rmse")}</p>
          <p class="proof-label">Scalar-ratio baseline</p>
          <p class="proof-hint">{scalar_note}</p>
        </div>
      </div>
      <p class="proof-note">Learned on {n.get("train_period", "n/a")}, tested on {n.get("test_period", "n/a")}.
      The leg converts NOAA-20 counts into S-NPP-equivalent counts; the published
      S-NPP → MODIS line then carries them into the record's units. {n.get("caveat", "")}</p>"""

    return f"""      <div class="proof-grid">
        <div class="proof-card">
          <p class="proof-num text-amber" style="font-size: 1.35rem;">Not fitted</p>
          <p class="proof-label">NOAA-20 calibration leg</p>
          <p class="proof-hint">Status: {status}</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{months} / {need}</p>
          <p class="proof-label">S-NPP / NOAA-20 overlap months downloaded</p>
          <p class="proof-hint">The code refuses to publish a slope below {need}.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">0</p>
          <p class="proof-label">Months of record extended past the archive</p>
          <p class="proof-hint">No NOAA-20 fit is claimed on the page.</p>
        </div>
      </div>
      <p class="proof-note"><strong>Honest status:</strong> the NOAA-20 leg is not fitted — {n.get("reason", "NOAA-20 archive not downloaded")}.
      The forward mapping above is still an algebraic inversion, not a validated NOAA-20 model.
      Fetch the archive (<code>VIIRS_NOAA20_SP</code>) and re-run the pipeline;
      the leg fits automatically once at least {need} overlap months exist.</p>"""


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



    # The scalar-ratio baseline is shown beside the raw splice on purpose: the
    # raw splice alone would flatter the fitted model (see metrics.json
    # performance_improvement.honest_reading).
    scalar = (m["held_out_test_comparison"].get("scalar_ratio_baseline_vs_modis") or {})
    scalar_gain = imp.get("rmse_reduction_percent_vs_scalar_baseline")
    scalar_defs = (m.get("baseline_definitions") or {}).get("scalar_ratio_baseline_vs_modis", "")
    scalar_factor = re.search(r"=\s*([0-9.]+)", scalar_defs)
    scalar_factor = scalar_factor.group(1) if scalar_factor else "n/a"
    train_period = m.get("training_period", "")
    test_period = m.get("held_out_test_period", "")
    rho_s = "n/a" if rho is None else str(rho)

    return f"""      <div id="proof-cards" class="proof-grid" aria-live="polite">
        <div class="proof-card">
          <p class="proof-num">{lin.get("rmse", "n/a")}</p>
          <p class="proof-label">Typical monthly error, fitted model (lower is better)</p>
          <p class="proof-hint">Simple scaling (×{scalar_factor}) already gets {scalar.get("rmse", "n/a")}. Our fit improves on that by {scalar_gain if scalar_gain is not None else "n/a"}%.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{signed(lin.get("bias"))}</p>
          <p class="proof-label">Running too high or too low (0 is fair)</p>
          <p class="proof-hint">Scaling baseline: {signed(scalar.get("bias"))}. Unscaled splice: {signed(naive.get("bias"))}.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{rho_s}</p>
          <p class="proof-label">Rank agreement with the real record (Spearman, 1.0 = perfect)</p>
          <p class="proof-hint">R² is {r2 if r2 is not None else "n/a"}, but it is set mostly by the burning peak, so rank agreement is the fairer single number.</p>
        </div>
      </div>
      <p class="proof-note"><strong>Read this honestly:</strong> most of the correction comes from simple scaling, not from our equation.
      An unscaled splice scores RMSE {naive.get("rmse", "n/a")}, bias {signed(naive.get("bias"))} and R² {naive_r2}, so measured against it the error falls {imp.get("rmse_reduction_percent", "n/a")}% and the bias falls {imp.get("bias_reduction_percent", "n/a")}%.
      That is the wrong yardstick. Measured against a one-number scaling baseline, the error falls only {scalar_gain if scalar_gain is not None else "n/a"}%.
      What this project adds is the regional calibration for the CHT, the bootstrap confidence range, the confidence-threshold and day-only sensitivity runs, and a genuine held-out test.</p>
      <p class="proof-note">{prov}
      Learned on {train_period}, tested on {test_period}. Full formula &amp; confidence intervals: see the “Wrong Join” section above.{sens_line}</p>"""


def build_continuity_panel(m: dict) -> str:
    """The MODIS-only control: the unchanged sensor does not show the step.

    This is the strongest single piece of evidence that the apparent rise is an
    instrument artefact, so it belongs on the page rather than only in
    metrics.json.
    """
    c = m.get("modis_only_continuity") or {}
    pre = c.get("pre_2012_modis_mean_per_month")
    post = c.get("post_2012_modis_mean_per_month")
    change = c.get("modis_only_change_percent")
    apparent = c.get("spliced_apparent_change_percent")
    if pre is None or post is None:
        return '<p class="muted">MODIS-only continuity check unavailable for this run.</p>'

    def signed_pct(v):
        return "n/a" if v is None else f"{'+' if v >= 0 else ''}{v}%"

    return f"""      <div class="proof-grid">
        <div class="proof-card">
          <p class="proof-num">{pre}</p>
          <p class="proof-label">MODIS fires per month before 2012</p>
          <p class="proof-hint">Same camera, same three districts.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num">{post}</p>
          <p class="proof-label">MODIS fires per month from 2012</p>
          <p class="proof-hint">The one camera that never changed reads {signed_pct(change)}.</p>
        </div>
        <div class="proof-card">
          <p class="proof-num text-amber">{signed_pct(apparent)}</p>
          <p class="proof-label">What the wrong join claims instead</p>
          <p class="proof-hint">Two cameras joined raw. Nothing in the forest changed this much.</p>
        </div>
      </div>
      <p class="proof-note"><strong>This is the control test.</strong> Aqua MODIS flew across the whole period without changing.
      If burning had really tripled in 2012, MODIS would have seen it rise too. MODIS reads {signed_pct(change)} instead, so the step belongs to the sensor, not to the fires.</p>"""


def build_seasonal_breakdown(m: dict) -> str:
    """Peak-season vs quiet-season error, so one RMSE cannot carry the claim."""
    s = m.get("held_out_seasonal_breakdown") or {}
    peak = s.get("fire_season_mar_apr") or {}
    quiet = s.get("quiet_season_other_months") or {}
    med = m.get("held_out_median_absolute_error")
    if not peak or not quiet:
        return '<p class="muted">Seasonal breakdown unavailable for this run.</p>'
    return f"""      <table class="heldout-table" aria-label="Held-out error by season">
        <thead>
          <tr><th>Season</th><th>Months tested</th><th>Average real fires / month</th><th>Typical error (RMSE)</th></tr>
        </thead>
        <tbody>
          <tr><td>March–April burning peak</td><td>{peak.get("months")}</td><td>{peak.get("mean_observed_modis")}</td><td>{peak.get("rmse")}</td></tr>
          <tr><td>All other months</td><td>{quiet.get("months")}</td><td>{quiet.get("mean_observed_modis")}</td><td>{quiet.get("rmse")}</td></tr>
        </tbody>
      </table>
      <p class="proof-note">The burning peak carries nearly all of the error and nearly all of the R². Across the whole held-out set the median monthly error is {med if med is not None else "n/a"} detections, because most months are almost fire-free. Both regimes are published so the fit is not judged on six months of the year.</p>"""


def build_hero_kpi(m: dict) -> str:
    """Hero tiles, generated so they cannot drift from metrics.json."""
    lin = m["held_out_test_comparison"]["harmonized_linear_vs_modis"]
    scalar = m["held_out_test_comparison"].get("scalar_ratio_baseline_vs_modis") or {}
    imp = m.get("performance_improvement", {})
    c = m.get("modis_only_continuity") or {}
    record = m.get("record_period", "")
    months = re.search(r"\((\d+) months\)", record)
    months = months.group(1) if months else "n/a"
    span = record.split(" (")[0] if record else "n/a"
    years = "n/a"
    if span and "to" in span:
        a, b = [p.strip()[:4] for p in span.split("to")]
        years = f"{int(b) - int(a) + 1} Yrs"
    change = c.get("modis_only_change_percent")
    gain = imp.get("rmse_reduction_percent_vs_scalar_baseline")
    rho = lin.get("spearman_corr")
    return f"""          <div class="kpi-tile">
            <span class="kpi-val blue">{years}</span>
            <span class="kpi-label">Continuous Coverage</span>
            <span class="kpi-sub">{span.replace("to", "–")} · {months} monthly records</span>
          </div>
          <div class="kpi-tile">
            <span class="kpi-val green">{lin.get("rmse")}</span>
            <span class="kpi-label">Monthly Error, Held-Out Test</span>
            <span class="kpi-sub">Scaling baseline {scalar.get("rmse")} · we gain {gain if gain is not None else "n/a"}%</span>
          </div>
          <div class="kpi-tile">
            <span class="kpi-val amber">{"n/a" if change is None else f"{'+' if change >= 0 else ''}{change}%"}</span>
            <span class="kpi-label">MODIS-Only Change Across 2012</span>
            <span class="kpi-sub">The unchanged camera sees no rise</span>
          </div>
          <div class="kpi-tile">
            <span class="kpi-val green">{rho if rho is not None else "n/a"}</span>
            <span class="kpi-label">Rank Agreement (Spearman)</span>
            <span class="kpi-sub">Tracks real ups &amp; downs</span>
          </div>"""


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
    new_html = replace_block(new_html, "<!-- BEGIN:CONTINUITY_PANEL -->", "<!-- END:CONTINUITY_PANEL -->",
                             build_continuity_panel(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:SEASONAL_BREAKDOWN -->", "<!-- END:SEASONAL_BREAKDOWN -->",
                             build_seasonal_breakdown(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:HERO_KPI -->", "<!-- END:HERO_KPI -->",
                             build_hero_kpi(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:DISTRICT_PANEL -->", "<!-- END:DISTRICT_PANEL -->",
                             build_district_panel(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:SENSOR_CUSTODY -->", "<!-- END:SENSOR_CUSTODY -->",
                             build_custody_strip(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:SENSOR_CUSTODY_LEGEND -->", "<!-- END:SENSOR_CUSTODY_LEGEND -->",
                             build_custody_legend(metrics))
    new_html = replace_block(new_html, "<!-- BEGIN:NOAA20_PANEL -->", "<!-- END:NOAA20_PANEL -->",
                             build_noaa20_panel(metrics))
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
    print("[SYNC-WEB] index.html validation + districts + custody + NOAA-20 panels regenerated from metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
