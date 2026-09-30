"""
BD-FireOps: Streamlit Interactive Dashboard
Challenge: Harmonization of MODIS and VIIRS Hot Spots (NASA Space Apps 2026)
Team: Claude Fable 7.0
Study Area: Bangladesh Chittagong Hill Tracts (CHT)
"""

import os
import json
import numpy as np
import pandas as pd
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="BD-FireOps | NASA Space Apps 2026",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark space-grade aesthetic)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #8b949e;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: bold;
        color: #3fb950;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .alert-box {
        background-color: #1f1d18;
        border-left: 4px solid #d29922;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 20px;
        color: #e3b341;
        font-size: 0.95rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 6px;
        padding: 8px 18px;
        color: #c9d1d9;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Load processed data and metrics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def _data_freshness() -> str:
    """Cache key: after a pipeline re-run the dashboard must not serve stale data."""
    parts = []
    for name in ("metrics.json", "monthly_harmonized.csv", "monthly.csv"):
        p = PROCESSED / name
        parts.append(f"{p.stat().st_mtime_ns}:{p.stat().st_size}" if p.exists() else "missing")
    return "|".join(parts)


@st.cache_data
def load_data(freshness: str = ""):
    df_path = str(PROCESSED / "monthly_harmonized.csv")
    metrics_path = str(PROCESSED / "metrics.json")
    monthly_path = str(PROCESSED / "monthly.csv")

    if not os.path.exists(df_path) or not os.path.exists(metrics_path):
        if not os.path.exists(monthly_path):
            st.error(
                "**No processed data yet.**\n\n"
                "Run `python probe_firms.py --run-all` (needs `FIRMS_MAP_KEY` in `.env`) "
                "or `python probe_firms.py --demo` (simulated data) first, then reload."
            )
            st.stop()
        from analysis.model import run_harmonization_pipeline, generate_publication_charts
        df, metrics = run_harmonization_pipeline(monthly_path)
        generate_publication_charts(df, metrics)
        return df, metrics

    df = pd.read_csv(df_path)
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)
    return df, metrics

df, metrics = load_data(_data_freshness())

SRC = metrics.get("data_source", {}) or {}
IS_REAL = bool(SRC.get("is_nasa_firms"))
IMP = metrics.get("performance_improvement", {})
LIN = metrics["held_out_test_comparison"]["harmonized_linear_vs_modis"]
NAIVE = metrics["held_out_test_comparison"]["naive_raw_viirs_vs_modis"]
SHIFT = metrics.get("observed_sensor_shift_ratio")
SHIFT_S = "n/a" if SHIFT is None or SHIFT != SHIFT else f"{SHIFT}x"
OVL = metrics.get("overlap_viirs_to_modis_ratio")
OVL_S = "n/a" if OVL is None or OVL != OVL else f"{OVL}x"

try:
    with open(str(PROCESSED / "sensitivity.json"), encoding="utf-8") as _f:
        SENS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError, OSError):
    SENS = None



def pct_text(v):
    return "n/a" if v is None else f"{-v:+}%"


def metric_card(value: str, label: str) -> str:
    return (f'<div class="metric-card"><div class="metric-val">{value}</div>'
            f'<div class="metric-lbl">{label}</div></div>')


# ----------------- SIDEBAR -----------------
st.sidebar.image("https://www.nasa.gov/wp-content/themes/nasa/assets/images/nasa-logo.svg", width=120)
st.sidebar.markdown("### **NASA Space Apps 2026**")
st.sidebar.markdown("**Challenge:** *Harmonization of MODIS & VIIRS Hot Spots*")
st.sidebar.markdown("**Team:** `Claude Fable 7.0` (Bangladesh)")
st.sidebar.markdown("---")

st.sidebar.markdown("#### **Study Domain**")
st.sidebar.markdown("""
- **Region:** Chittagong Hill Tracts (CHT)
- **Bounding Box:** `91.9° - 92.9°E, 21.4° - 23.8°N`
- **Districts:** Bandarban, Rangamati, Khagrachhari
- **Boundary gate:** district polygons (geoBoundaries BGD-ADM2); bbox rows outside the CHT dropped
- **Fire Dynamics:** Seasonal Jhum shifting cultivation
""")

st.sidebar.markdown("---")
st.sidebar.markdown("#### **Sensor Operational Timeline**")
st.sidebar.markdown("""
- **Terra MODIS (1km):** 2000 – Feb 2027 (end-of-science projected)
- **Aqua MODIS (1km):** 2002 – Sep 2027 (end-of-science projected)

- **Suomi-NPP VIIRS (375m):** 2012 – **1 Nov 2026 (Permanent Cutoff)**
- **NOAA-20 / 21 VIIRS:** 2018 / 2023 – Operational
""")

# ----------------- MAIN HEADER -----------------
st.markdown('<div class="main-header">🔥 BD-FireOps: MODIS-VIIRS Harmonization Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">An Uncertainty-Aware, Held-Out Validated Continuous Fire Record for Bangladesh Chittagong Hill Tracts (2002–2021)</div>', unsafe_allow_html=True)

st.markdown("""
<div class="alert-box">
⚠️ <b>Operational Transition Notice:</b> NASA projects end-of-science for Terra (Feb 2027) and Aqua (Sep 2027), and Suomi-NPP data delivery permanently ceases on November 1, 2026. Without cross-sensor harmonization, naive splicing between MODIS (1km) and VIIRS (375m) generates false multi-fold burning trends.

</div>
""", unsafe_allow_html=True)

if IS_REAL:
    st.caption(f"Data source: **NASA FIRMS Area API** ({', '.join(SRC.get('sources', []))}) — "
               "recorded in `data/processed/data_source.json`.")
else:
    st.markdown(
        """
        <div class="alert-box" style="background:#2d1618; border-left-color:#f85149; color:#ff7b72;">
        🧪 <b>DEMO DATA — NOT NASA FIRMS.</b> Every figure below comes from a simulated
        monthly series used to exercise the pipeline. Run
        <code>python probe_firms.py --run-all</code> with a FIRMS <code>MAP_KEY</code>
        before submission.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- TABS -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Splice Comparison (Chart A vs B)", 
    "🧪 Held-Out Model Validation", 
    "🗺️ Geospatial & Seasonal Profile", 
    "⚠️ Uncertainty & Honest Limitations"
])

with tab1:
    st.subheader("1. Naive Sensor Splice vs. BD-FireOps Continuous Record")
    st.markdown(
        f"""
    Compare the raw data concatenation against our empirical harmonization. Notice how the naive
    splice exhibits an abrupt **{SHIFT_S} step at the 2012 sensor transition** (mean raw VIIRS
    2012–2021 ÷ mean MODIS 2002–2011 for this CHT window; where both sensors observe together the
    same-month ratio is **{OVL_S}**). The step is a sensor/footprint artefact, not a fire-regime
    change, and our model removes it.
    """
    )

    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### **Chart A: Naive Sensor Splice (Unadjusted)**")
        st.image(str(PROCESSED / "chart_a_naive_splice.png"), width='stretch')
        st.caption("🔴 **Failure Mode:** Abrupt spike at 2012 sensor transition. Reflects VIIRS 375m sub-pixel sensitivity, NOT real-world fire growth.")
        
    with col_b:
        st.markdown("#### **Chart B: BD-FireOps Harmonized Splice**")
        st.image(str(PROCESSED / "chart_b_harmonized_splice.png"), width='stretch')
        st.caption("🟢 **Success Mode:** Multi-decadal continuous baseline. Converts 2012–2021 VIIRS observations into calibrated MODIS-equivalent counts.")

    st.markdown("---")
    st.subheader("Interactive Temporal Inspector")
    
    years = sorted(int(y) for y in df["year"].unique())
    default_year = 2015 if 2015 in years else years[len(years) // 2]
    selected_year = st.slider("Select Year to inspect monthly observations:",
                              min_value=years[0], max_value=years[-1], value=default_year)

    
    year_data = df[df["year"] == selected_year][["month", "modis", "viirs", "pred_linear", "harmonized_splice"]]
    year_data = year_data.rename(columns={
        "month": "Month",
        "modis": "Observed MODIS (1km)",
        "viirs": "Raw S-NPP VIIRS (375m)",
        "pred_linear": "BD-FireOps MODIS-Equiv",
        "harmonized_splice": "Continuous Record"
    })
    st.dataframe(year_data.style.format({
        "Observed MODIS (1km)": "{:.0f}",
        "Raw S-NPP VIIRS (375m)": "{:.0f}",
        "BD-FireOps MODIS-Equiv": "{:.1f}",
        "Continuous Record": "{:.1f}"
    }), width='stretch')

with tab2:
    st.subheader(f"2. Rigorous Held-Out Validation (Test Set: {metrics.get('held_out_test_period', '2019-01 to 2021-12')})")
    st.markdown(
        f"""
    To avoid over-fitting and prevent data leakage, the harmonization models were trained strictly on
    **{metrics.get('training_period', '2012-01 to 2018-12')}** and evaluated on an independent,
    **held-out test set from {metrics.get('held_out_test_period', '2019-01 to 2021-12')}**.
    """
    )

    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card(pct_text(IMP.get("rmse_reduction_percent")), "RMSE Reduction"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card(pct_text(IMP.get("bias_reduction_percent")), "Bias Reduction"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card(str(LIN.get("r2", "n/a")), "Test Set R² Score"), unsafe_allow_html=True)
    with col4:
        rho = LIN.get("spearman_corr")
        st.markdown(metric_card("n/a" if rho is None else str(rho), "Spearman Rank Corr"), unsafe_allow_html=True)


    st.markdown("<br>", unsafe_allow_html=True)
    
    col_scat, col_details = st.columns([3, 2])
    with col_scat:
        st.image(str(PROCESSED / "chart_validation_scatter.png"), width='stretch')
        st.caption(f"Left: raw VIIRS overestimates MODIS by about {OVL_S} in the overlapping 2012–2021 months. "
                   "Right: BD-FireOps aligns tightly along the 1:1 parity line.")

        
    with col_details:
        st.markdown("#### **Fitted Calibration Functions**")
        st.code(metrics["fitted_linear_model"]["equation"], language="text")
        
        st.markdown("#### **Bootstrap coefficient interval (500 resamples):**")
        st.write(f"- **Slope 95% CI:** `{metrics['fitted_linear_model']['bootstrap_slope_95_ci']}`")
        st.write(f"- **Intercept 95% CI:** `{metrics['fitted_linear_model']['bootstrap_intercept_95_ci']}`")
        st.caption("Coefficient interval, not a prediction interval.")

        if SENS and (SENS.get("delta") or {}).get("slope_percent") is not None:
            _d = SENS["delta"]
            _b = SENS["baseline"]
            _l = SENS["low_confidence_kept"]

            def _f(v):
                return "n/a" if v is None else f"{float(v):+.2f}%"

            st.markdown("#### **Confidence-threshold sensitivity:**")
            st.write(f"- Slope: `{_b.get('slope')}` → `{_l.get('slope')}` ({_f(_d.get('slope_percent'))})")
            st.write(f"- Held-out RMSE: `{_b.get('test_rmse')}` → `{_l.get('test_rmse')}` "
                     f"({_f(_d.get('test_rmse_percent'))} — positive = worse with looser thresholds)")

            st.caption("Baseline MODIS conf ≥ 30 / VIIRS drops `l` is the reported configuration; "
                       "low-confidence rows are kept in `data/processed/sensitivity.json`.")


        st.markdown("#### **Held-out test error (2019–2021):**")

        comp = metrics["held_out_test_comparison"]
        comp_df = pd.DataFrame({
            "Metric": ["RMSE (Hotspots)", "Bias (Mean Error)", "MAE", "R² Score", "Spearman ρ"],
            "Raw VIIRS vs MODIS reference": [
                comp["naive_raw_viirs_vs_modis"]["rmse"], comp["naive_raw_viirs_vs_modis"]["bias"],
                comp["naive_raw_viirs_vs_modis"]["mae"], comp["naive_raw_viirs_vs_modis"]["r2"],
                comp["naive_raw_viirs_vs_modis"]["spearman_corr"]],
            "Harmonized VIIRS vs MODIS reference (linear)": [
                comp["harmonized_linear_vs_modis"]["rmse"], comp["harmonized_linear_vs_modis"]["bias"],
                comp["harmonized_linear_vs_modis"]["mae"], comp["harmonized_linear_vs_modis"]["r2"],
                comp["harmonized_linear_vs_modis"]["spearman_corr"]],
            "Harmonized VIIRS vs MODIS reference (log1p)": [
                comp["harmonized_log1p_vs_modis"]["rmse"], comp["harmonized_log1p_vs_modis"]["bias"],
                comp["harmonized_log1p_vs_modis"]["mae"], comp["harmonized_log1p_vs_modis"]["r2"],
                comp["harmonized_log1p_vs_modis"]["spearman_corr"]],
        })
        st.table(comp_df)


with tab3:
    st.subheader("3. Bangladesh Chittagong Hill Tracts (CHT) Fire Profile")
    st.markdown("""
    In Bangladesh, the subtropical hill forests of the **Chittagong Hill Tracts (CHT)** account for the
    largest share of detected wildland fires, driven by indigenous **Jhum (shifting cultivation)**,
    grazing and settlement — the causes attributed to ~88% of fires in a 2003–2021 hotspot study
    (Farukh et al., 2023). Our window is CHT-only, so this regional share comes from that literature,
    not from our own sample.
    """)
    
    # Calculate seasonal monthly averages
    seasonal = df.groupby("month_num").agg({
        "modis": "mean",
        "pred_linear": "mean"
    }).reset_index()
    seasonal["month_name"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    st.markdown("#### **Monthly Climatological Fire Cycle (CHT)**")
    st.bar_chart(seasonal.set_index("month_name")[["modis", "pred_linear"]])
    st.caption("Active fires surge during the dry pre-monsoon window (February to May, peaking in March-April) and drop to near-zero during the monsoon season (June to October).")

with tab4:
    st.subheader("4. Uncertainty, Assumptions & Honest Scientific Limitations")
    st.markdown("""
    BD-FireOps explicitly documents all operational boundaries and known caveats:
    """)

    zh = metrics.get("zero_month_handling", {})

    _ci = metrics.get("fitted_linear_model", {}).get("bootstrap_slope_95_ci")
    _slope = metrics.get("fitted_linear_model", {}).get("slope")
    _ci_w = "n/a"
    if isinstance(_ci, (list, tuple)) and len(_ci) == 2 and _slope:
        _ci_w = f"±{round(100 * abs((float(_ci[1]) - float(_ci[0])) / 2) / abs(float(_slope)), 1)}% of the point slope"

    if SENS and (SENS.get("delta") or {}).get("slope_percent") is not None:
        _sd = SENS["delta"]
        _sb = SENS["baseline"]
        _sl = SENS["low_confidence_kept"]
        _sens_item = (f"Keeping low-confidence detections moves the fitted slope `{_sb.get('slope')}` → "
                      f"`{_sl.get('slope')}` ({float(_sd['slope_percent']):+.2f}%) and held-out RMSE "
                      f"`{_sb.get('test_rmse')}` → `{_sl.get('test_rmse')}` "
                      f"({float(_sd['test_rmse_percent']):+.2f}%). The baseline thresholds "
                      f"(MODIS conf ≥ 30, VIIRS drops `l`) are the reported configuration.")
    else:
        _sens_item = ("No sensitivity run recorded — reproduce with "
                      "`python analysis/clean.py --sensitivity` then `python tools/sensitivity.py`.")

    st.markdown(f"""
    1. **Regional Scope (Not a Global Model):**
       *BD-FireOps is fitted specifically to the Chittagong Hill Tracts (CHT).* It is NOT a universal global conversion function, and it is a held-out-tested prototype rather than a peer-reviewed operational product. Transferring these coefficients to Boreal forests or African savannas without local refitting would introduce bias.

    2. **Spatial Aggregation Caveat:**
       This prototype operates on *monthly regional counts*, not individual paired fire-pixel geometric intersections. Sub-pixel spatial overlap, scan-angle distortion, and satellite overpass time drift were not explicitly modeled in this MVP.

    3. **Zero Months & Coverage Gaps:**
       {zh.get('months_with_any_zero', 'n/a')} of {zh.get('overlap_months', 'n/a')} overlap months contain a zero and were **retained**, not dropped
       ({zh.get('zero_modis_months', 'n/a')} MODIS / {zh.get('zero_viirs_months', 'n/a')} VIIRS). Months outside a sensor's
       coverage window stay blank instead of being reported as fire-free.

    4. **Positive Detections Only:**
       NASA FIRMS registers *positive active fire detections*. A non-detection does NOT definitively prove absence of fire; it may result from heavy monsoon cloud occlusion, thick smoke plumes, or timing between satellite overpasses. This tool does **not** classify fire cause — it is not a fire-cause classifier.

    5. **Critical Suomi-NPP Sunset (Nov 1, 2026):**
       As officially announced by NOAA/NASA, Suomi-NPP VIIRS data delivery permanently terminates on **November 1, 2026**. Future operational deployments of BD-FireOps must transition to NOAA-20 (VJ114) and NOAA-21 records.

    6. **Confidence-threshold sensitivity:**
       {_sens_item}

    7. **Coefficients are fitted estimates:**
       The slope's bootstrap 95% coefficient interval is `{_ci}` — {_ci_w}. This is uncertainty on the
       *fit*, not a prediction interval for individual months.
    """)


    
    st.markdown("---")
    st.markdown("#### **Academic Citation & Reference Standards**")
    st.markdown("""
    - **Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. (2014):** *The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment.* Remote Sensing of Environment, 143, 85–96. doi:10.1016/j.rse.2013.12.008
    - **Li, F., et al. (2018):** *Comparison of Fire Radiative Power Estimates From VIIRS and MODIS Observations.* Journal of Geophysical Research: Atmospheres. doi:10.1029/2017JD027823
    - **Farukh, M. A., Islam, M. A., & Hayasaka, H. (2023):** *Wildland Fires in the Subtropical Hill Forests of Southeastern Bangladesh.* Atmosphere, 14(1), 97. doi:10.3390/atmos14010097 (OSTI ID 2424866)
    """)

# ----------------- FOOTER -----------------
st.markdown("---")
st.markdown("<div style='text-align: center; color: #8b949e; font-size: 0.85rem;'>Developed with passion by <b>Team Claude Fable 7.0</b> for the <b>NASA Space Apps Challenge 2026</b>.<br>Non-detection does not prove absence of fire. Model is region- and period-specific. Open Source & Reproducible.</div>", unsafe_allow_html=True)
