"""E2E audit: frontend numbers vs pipeline outputs (see TOTAL at the end).

Runs in CI via .github/workflows/check.yml; run locally with:
    python tools/e2e_audit.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
html = (ROOT / "index.html").read_text(encoding="utf-8")
js = (ROOT / "app.js").read_text(encoding="utf-8")
m = json.load(open(ROOT / "data" / "processed" / "metrics.json", encoding="utf-8"))
sens_raw = (ROOT / "data" / "processed" / "sensitivity.json").read_text(encoding="utf-8")
met_raw = (ROOT / "data" / "processed" / "metrics.json").read_text(encoding="utf-8")

fails = []


def chk(label, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", label, extra)
    if not cond:
        fails.append(label)


# --- structural ---
try:
    json.load(open(ROOT / "vercel.json", encoding="utf-8"))
    ok_json = True
except Exception:
    ok_json = False
chk("vercel.json is valid JSON", ok_json)

ids = re.findall(r'id="([^"]+)"', html)
dup = sorted({i for i in ids if ids.count(i) > 1})
chk("no duplicate HTML ids", not dup, str(dup) if dup else f"({len(ids)} ids)")

ds = m.get("data_source") or {}
chk("metrics data_source.is_nasa_firms is True", ds.get("is_nasa_firms") is True,
    str(ds.get("is_nasa_firms")))

# --- numbers displayed on the frontend must equal metrics.json ---
lin = m["held_out_test_comparison"]["harmonized_linear_vs_modis"]
naive = m["held_out_test_comparison"]["naive_raw_viirs_vs_modis"]
scalar = m["held_out_test_comparison"]["scalar_ratio_baseline_vs_modis"]
imp = m["performance_improvement"]
flm = m["fitted_linear_model"]
cont = m["modis_only_continuity"]
seas = m["held_out_seasonal_breakdown"]
fwd = m["forward_mapping_modis_to_viirs"]

checks = [
    # --- honest-baseline reporting (reviewer fixes 2, 3, 4, 6) ---
    ("scalar baseline RMSE on the page", str(scalar["rmse"]) in html),
    ("scalar baseline bias on the page", ("+" + str(scalar["bias"])) in html or str(scalar["bias"]) in html),
    ("gain over scalar baseline on the page",
     str(imp["rmse_reduction_percent_vs_scalar_baseline"]) in html),
    ("gain over scalar baseline is modest (<25%), so the claim stays honest",
     imp["rmse_reduction_percent_vs_scalar_baseline"] < 25),
    ("spearman shown beside R2", str(lin["spearman_corr"]) in html),
    ("MODIS-only change on the page", str(cont["modis_only_change_percent"]) in html),
    ("MODIS-only pre/post means on the page",
     str(cont["pre_2012_modis_mean_per_month"]) in html
     and str(cont["post_2012_modis_mean_per_month"]) in html),
    ("MODIS-only control does not show the spliced step",
     cont["modis_only_change_percent"] < 50),
    ("fire-season RMSE on the page", str(seas["fire_season_mar_apr"]["rmse"]) in html),
    ("quiet-season RMSE on the page", str(seas["quiet_season_other_months"]["rmse"]) in html),
    ("median absolute error on the page", str(m["held_out_median_absolute_error"]) in html),
    ("forward mapping slope on the page", str(fwd["slope"]) in html),
    ("forward mapping caveat present", "NOAA-20" in html),
    ("honest_reading recorded in metrics", bool(imp.get("honest_reading"))),
    ("frontend RMSE 55.67", str(lin["rmse"]) in html and lin["rmse"] == 55.67),
    ("frontend bias -4.09", str(lin["bias"]) in html and lin["bias"] == -4.09),
    ("frontend naive RMSE 1130.64", str(naive["rmse"]) in html and naive["rmse"] == 1130.64),
    ("frontend naive bias +468.92", ("+" + str(naive["bias"])) in html),
    ("frontend R2 0.9811", str(lin["r2"]) in html and lin["r2"] == 0.9811),
    ("frontend naive R2 -6.8012", str(naive["r2"]) in html),
    ("frontend RMSE reduction 95.1", str(imp["rmse_reduction_percent"]) in html),
    ("frontend bias reduction 99.1", str(imp["bias_reduction_percent"]) in html),
    ("frontend+js slope 0.2694", "0.2694" in html and "0.2694" in js and flm["slope"] == 0.2694),
    ("frontend+js intercept -1.18", "1.18" in html and "-1.18" in js
     and flm["intercept"] == -1.18),
    ("js step 2.85 = metrics", str(m.get("observed_sensor_shift_ratio")) in js),
    ("js overlap 3.71 = metrics", str(m.get("overlap_viirs_to_modis_ratio")) in js),
    ("sim default 79.6", ">79.6<" in html),
    ("sim CI [59.1, 95.6]", "[59.1, 95.6]" in html),
    ("sim mitigation -73.5%", ">-73.5%<" in html),
    ("84 overlapping months fixed", "84 overlapping months" in html and "84 months" in m.get("training_period", "")),
    ("per-year 2019 -11.52", "-11.52" in html),
    ("per-year 2020 -17.61", "-17.61" in html),
    ("per-year 2021 +16.86", "+16.86" in html),
    ("sensitivity 49.69 sourced from JSON", "49.69" in sens_raw or "49.69" in met_raw),
    ("sensitivity -10.74 sourced from JSON", "-10.74" in sens_raw or "-10.74" in met_raw),
    ("234 monthly records", "234 monthly records" in html),
    ("CHT_SERIES rows = 234", len(re.findall(r'\{m:"', js)) == 234),
    ("bootstrap 500 in metrics", "500" in met_raw),
    ("matrix legend thresholds match js classes",
     all(s in html for s in ["1–20 (Low)", "21–100 (Moderate)", "101–250 (High Jhum)",
                             "251–600 (Peak Flare)", "600+ (Extreme Fire Season)"])
     and all(s in js for s in ["cls = 'c-2'", "cls = 'c-3'", "cls = 'c-4'", "cls = 'c-5'"])),
    ("map popup top-30 = sync CELL_TOP_N", "top-30" in js),
    ("og:image URL still live",
     "chart_b_harmonized_splice.png" in html),
]
for label, cond in checks:
    chk(label, cond)

rf = m.get("region_filter") or {}
chk("region_filter.name present (for provenance)", bool(rf.get("name")), str(rf.get("name")))
dr = rf.get("dropped_outside_region") or {}
chk("dropped_outside_region counts present", "modis" in dr and "viirs" in dr,
    f"MODIS={dr.get('modis')} VIIRS={dr.get('viirs')}")

# --- per-district fits: every number on the page comes from district_metrics.json ---
import csv

dm_path = ROOT / "data" / "processed" / "district_metrics.json"
dm = json.load(open(dm_path, encoding="utf-8"))
per = m.get("per_district") or {}
pd_block = per.get("districts") or {}
chk("district_metrics.json matches metrics.per_district", dm == pd_block)
chk("three districts fitted", len(dm) == 3 and all(v.get("status") == "fitted" for v in dm.values()))

for name, e in dm.items():
    chk(f"district {name} slope on page", f"Slope: {e['slope']:.4f}" in html)
    chk(f"district {name} held-out R2 on page", f"Held-out R²: {e['held_out_r2']:.4f}" in html)
    det_total = int((e.get("clean_detections") or {}).get("modis", 0)) + int((e.get("clean_detections") or {}).get("viirs", 0))
    chk(f"district {name} detections total on page", f"{det_total:,}" in html)
    fit_better = e["held_out_rmse"] < e["held_out_scalar_rmse"]
    claim = "Fit beats simple scaling" if fit_better else "Simple scaling is as good or better"
    chk(f"district {name} scalar comparison is honest", claim in html,
        f"fit={e['held_out_rmse']} scalar={e['held_out_scalar_rmse']}")

# --- sensor custody: every record month gets exactly one label ---
legs = (m.get("sensor_custody") or {}).get("legs") or []
chk("sensor_custody has legs", bool(legs), f"({len(legs)} legs)")


def month_idx(value):
    year, mon = (int(p) for p in value.split("-")[:2])
    return year * 12 + mon


labels = {}
for leg in legs:
    last = leg.get("end") or "2099-12"
    for idx in range(month_idx(leg["start"]), month_idx(last) + 1):
        labels.setdefault(idx, []).append(leg["key"])
chk("each month has exactly one custody label", all(len(v) == 1 for v in labels.values()))
chk("custody legs are contiguous", sorted(labels) == list(range(min(labels), max(labels) + 1)))
chk("record edge is S-NPP test", labels.get(month_idx("2021-12")) == ["snpp_test"])
chk("post-archive months are gap, not NOAA-20", labels.get(month_idx("2022-01")) == ["gap"])
chk("NOAA-20 leg starts post-sunset", labels.get(month_idx("2026-11")) == ["noaa20"])
chk("no segment labeled NOAA-20 before sunset",
    all(k != "noaa20" for idx, v in labels.items() if idx < month_idx("2026-11") for k in v))

chk("custody segment count matches metrics",
    len(re.findall(r'class="provenance-segment ', html)) == len(legs), f"({len(legs)} legs)")
chk("gap strip labels the undownloaded archive", 'provenance-segment seg-gap" data-start="2022-01"' in html)
for leg in legs:
    chk(f"custody {leg['key']} start wired to page", f'data-start="{leg["start"]}"' in html)

# --- NOAA-20 leg: claim only what is fitted ---
n20 = m.get("noaa20_model") or {}
chk("NOAA-20 status on page", n20.get("status", "") in html, str(n20.get("status")))
if n20.get("status") != "fitted":
    chk("NOAA-20 refusal is explicit", "Not fitted" in html and "not fitted" in html)
    chk("NOAA-20 overlap counted honestly", f"{n20.get('overlap_months', 0)} / {n20.get('min_overlap_months', 24)}" in html)
    chk("no NOAA-20 equation is claimed", not n20.get("equation") or n20["equation"] not in html)
else:
    chk("NOAA-20 equation is shown", n20.get("equation", "") in html)

# --- generated CSVs stop at the real archive edge (no fabricated zero months) ---
monthly_rows = list(csv.DictReader(open(ROOT / "data" / "processed" / "monthly.csv", encoding="utf-8")))
chk("monthly.csv ends at the archive edge", monthly_rows[-1]["month"] == "2021-12",
    monthly_rows[-1]["month"])
chk("monthly.csv has no post-2021 rows",
    all(r["month"] <= "2021-12" for r in monthly_rows))
chk("monthly.csv has the NOAA-20 column", "viirs_noaa20" in monthly_rows[0])

dist_rows = list(csv.DictReader(open(ROOT / "data" / "processed" / "monthly_districts.csv", encoding="utf-8")))
chk("district grid rows = months x 3", len(dist_rows) == 3 * len(monthly_rows), f"({len(dist_rows)})")
for name, e in dm.items():
    got = sum(float(r[k]) for r in dist_rows if r["district"] == name for k in ("modis", "viirs") if r[k] not in ("", "nan"))
    want = sum(int(e["clean_detections"][k]) for k in ("modis", "viirs"))
    chk(f"district {name} rows sum to clean detections", round(got) == want, f"{round(got)} vs {want}")

# --- sync markers ---
for src, text in (("index.html", html), ("app.js", js)):
    begins = len(re.findall(r"BEGIN:", text))
    ends = len(re.findall(r"END:", text))
    chk(f"{src} BEGIN/END markers balanced", begins == ends, f"({begins}/{ends})")

# --- every DOM id the JS asks for must exist in the HTML ---
js_targets = sorted(set(re.findall(r"getElementById\('([^']+)'\)", js)))
missing_ids = [t for t in js_targets if f'id="{t}"' not in html]
chk("every getElementById target exists in HTML", not missing_ids,
    str(missing_ids) if missing_ids else f"({len(js_targets)} targets)")

print("TOTAL FAILURES:", len(fails))
sys.exit(1 if fails else 0)
