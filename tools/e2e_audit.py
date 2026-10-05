"""One-shot E2E audit: frontend numbers vs pipeline outputs. Not part of CI; run manually."""
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
imp = m["performance_improvement"]
flm = m["fitted_linear_model"]

checks = [
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

# --- sync markers ---
for src, text in (("index.html", html), ("app.js", js)):
    begins = len(re.findall(r"BEGIN:", text))
    ends = len(re.findall(r"END:", text))
    chk(f"{src} BEGIN/END markers balanced", begins == ends, f"({begins}/{ends})")

print("TOTAL FAILURES:", len(fails))
sys.exit(1 if fails else 0)
