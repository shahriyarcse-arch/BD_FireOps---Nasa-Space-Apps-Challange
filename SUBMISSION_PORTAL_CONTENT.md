# BD-FireOps — NASA Space Apps Challenge 2026 Official Submission Package

> **Challenge:** Harmonization of MODIS and VIIRS Hot Spots  
> **Category:** Earth Science / Active Fire Earth Observation  
> **Team:** Claude Fable 7.0 (Dhaka Local Chapter / BASIS)  
> **Target Region:** Chittagong Hill Tracts (CHT), Bangladesh (search window `91.9°–92.9°E, 21.4°–23.8°N`,
> detections kept only inside the Bandarban / Rangamati / Khagrachhari district polygons)  

> **NUMBER RULE:** every metric below is copied from `data/processed/metrics.json`
> (real NASA FIRMS observations, `kind: nasa_firms_api`). If that file changes,
> update this document — never type a number from memory.

---

## 1. Portal Basic Information (Copy-Paste Ready)

### Project Title
`BD-FireOps: An Uncertainty-Aware MODIS-VIIRS Fire Record for Bangladesh CHT`

### Short Project Description (Elevator Pitch / Tagline)
> NASA projects end-of-science activities for Terra MODIS (February 2027) and Aqua MODIS
> (September 2027), while NOAA/NESDIS has announced that Suomi-NPP VIIRS data delivery stops
> permanently on 1 November 2026. Earth-observation scientists therefore face an operational
> dilemma: merging 1 km MODIS and 375 m VIIRS active-fire records produces an artificial
> step at the 2012 hand-off in fire counts over Bangladesh's Chittagong Hill Tracts
> (CHT): **+185% (2.85×)** comparing Chart-A era means (mean raw VIIRS 2012–2021 ÷
> mean MODIS 2002–2011, zero months counted on both sides — the jump Chart A draws),
> and **3.71×** comparing the same 2012–2021 months where both sensors observe together
> (the sensor sensitivity difference the model is fitted on). BD-FireOps bridges this sensor gap. Using a rigorously filtered Aqua MODIS reference
> baseline, time-split empirical modelling (2012–2018 train, 2019–2021 held-out test) and a
> 500-sample **moving-block** bootstrap coefficient interval, BD-FireOps reduces held-out test RMSE by
> **95.1%** (from 1,130.64 to 55.67 hotspots/month) and cuts mean prediction bias by **99.1%**
> (from +468.92 to −4.09 hotspots/month) on the 2019–2021 held-out test window,
> reaching **R² = 0.9811** on unseen months.
> Deployed as an interactive, dark/light NASA Earth Observation Telemetry Web GIS HUD and a Streamlit data-science console, it
> gives climate scientists, the Bangladesh Forest Department and indigenous CHT communities
> a continuous, uncertainty-quantified 2002–2021 monthly active-fire record (observed Aqua
> MODIS 2002–2011, then VIIRS converted to MODIS-equivalent — the 2012–2018 overlap used
> only to fit the conversion, tested on 2019–2021) with the 2012
> sensor step quantified and removed rather than hidden.

### Space Agency Data Used (Checkboxes & Citations)
- **NASA FIRMS Area API — source `MODIS_SP` (MODIS 1 km active fire, Collection 6.1):** daily hotspots for the CHT search window, coverage window **2002-07 → 2021-12** (first CHT-district detection 2002-12-15); Aqua-only gate applied for the reference series (`satellite = Aqua`; Terra rows counted but excluded); district-polygon gate keeps 42,716 of 112,681 raw rows.
- **NASA FIRMS Area API — source `VIIRS_SNPP_SP` (VIIRS 375 m active fire, Suomi-NPP):** daily hotspots for the CHT search window, coverage window **2012-01 → 2021-12** (`satellite = N`); study-window clamp drops 1 straggler day (2022-01-01) returned inside the final chunk, then the district-polygon gate keeps 70,857 of 172,197 raw rows.
- **Boundary reference:** geoBoundaries BGD-ADM2 (BBS / OCHA ROAP), CC BY 3.0 — 54,300 MODIS / 85,857 VIIRS bbox rows outside Bandarban, Rangamati and Khagrachhari dropped.
- **NASA Earthdata / NOAA NESDIS alerts:** *Suomi NPP Data Product Delivery to Cease on November 1, 2026* (NESDIS notice issued 2026-08-03 at 16:00 UTC; impact 13:00 UTC on 2026-11-01) and *Suomi NPP VIIRS Data Outage / Anomaly on June 1, 2026*.
- **Academic Grounding:** Schroeder et al. (2014) *Remote Sensing of Environment*; Li et al. (2018) *JGR Atmospheres*; Farukh et al. (2023) *Atmosphere*.

---

## 2. Detailed Project Description (Markdown for NASA Portal)

### 2.1 The Operational Crisis: The Impending Sensor Sunset
Long-term climate impact assessment requires uninterrupted environmental time series spanning multiple decades. For active wildfire monitoring, the global scientific community has relied on NASA's flagship EOS satellites: Terra MODIS (operational since 2000) and Aqua MODIS (operational since May 2002).

NASA states that **Terra end-of-science activities are projected for February 2027 and Aqua's for September 2027** (NASA Earth Observatory, Dec 2025 — mission-status updates shift these dates). Separately, NOAA/NESDIS officially announced the **permanent cessation of Suomi-NPP science data delivery at 13:00 UTC on 1 November 2026**, and advises users to transition to NOAA-21 (primary) and NOAA-20 (secondary).

To preserve climate records, researchers must move to VIIRS (S-NPP until Nov 2026, then NOAA-20/21). Yet naive concatenation of MODIS and VIIRS records creates artificial distortions that corrupt historical trend analyses.

### 2.2 The Physics of Discontinuity in Bangladesh CHT
In the Chittagong Hill Tracts (CHT) of southeastern Bangladesh (`91.9°–92.9°E, 21.4°–23.8°N`), fire activity is dominated by pre-monsoon agricultural slash-and-burn farming (*Jhum* cultivation) concentrated in the dry months, peaking in March–April (Farukh et al., 2023).

These fires are spatially small and fragmented along steep, forested slopes:
1. **Pixel Footprint Mismatch:** MODIS has a nominal nadir footprint of ~1 km, while S-NPP VIIRS I-Band is 375 m, giving far greater response to small/cool burns.
2. **Sub-Pixel Detection Sensitivity:** VIIRS's finer I-band channels detect small, sub-pixel burns that never cross MODIS detection thresholds.
3. **The Artificial Step Jump:** In the unadjusted splice (Chart A), 2012 onward shows an instantaneous **+185% step (2.85× mean raw VIIRS 2012–2021 ÷ mean MODIS 2002–2011)**. Comparing only the months where both sensors observe each other, raw VIIRS averages **3.71×** the MODIS count. A casual observer would conclude fires nearly tripled overnight, when in reality only the sensor changed.

### 2.3 The BD-FireOps Solution
BD-FireOps is an uncertainty-aware, region-specific empirical harmonisation engine:
- **Strict Aqua Filtering Gate:** Terra and Aqua overpasses occur at different times of day (~10:30 vs ~13:30 local). S-NPP VIIRS has an afternoon overpass (~13:30), so the reference series is restricted to `satellite = Aqua` detections (Terra rows are counted in the audit and excluded from the fit) to avoid diurnal confounding.
- **Quality-Assurance Cleaning:** bbox filter to the CHT window, **district-polygon gate (Bandarban / Rangamati / Khagrachhari)**, de-duplication (highest-confidence row wins inside a duplicate group), UTC `acq_date` parsing, study-window clamp, and per-sensor confidence thresholds (`confidence ≥ 30` for MODIS; VIIRS low-confidence `l` rows dropped).
- **Time-Split Modelling:** trained strictly on the 2012–2018 overlap (84 months) with ordinary least squares on raw counts, plus a `log(1+x)` variant as a zero-robust check (it did not beat the linear model: 243.95 vs 55.67 RMSE).
- **Uncertainty Quantification:** a 500-sample **moving-block bootstrap** (12-month blocks, because monthly fire counts are seasonal/autocorrelated) gives a 95% **coefficient** interval (not a prediction interval) of **[0.2198, 0.2970]** for the slope (±14.3% of the point estimate) and **[−6.79, 6.52]** for the intercept.
- **Two extra robustness runs:** (i) keeping low-confidence detections moves the slope `0.2694 → 0.2464 (−8.54%)` and RMSE `55.67 → 58.43 (+4.96%)`; (ii) restricting **both sensors to daytime only** (`daynight = D`; MODIS 42,391 / VIIRS 64,537 rows) moves the slope to `0.2956 (+9.73%)` and RMSE to `49.69 (−10.74%)`. Both alternative cleaning choices measurably change the fit; they are published as-is instead of being folded into the headline. The baseline retains day+night observations for cross-sensor consistency; the day-only variant is listed as future work because promoting it days before submission would invalidate the tested headline numbers.

### 2.4 Held-Out Validation Benchmark (2019–2021)
Unlike prototypes that report in-sample metrics, BD-FireOps validates on an untouched 3-year held-out window (N = 36 months; train 84 / test 36, strict chronological split with no train/test month overlap):

| Evaluation Metric | Naive Splice (Raw VIIRS) | BD-FireOps (Harmonized) | Performance Delta |
|:---|:---:|:---:|:---:|
| **Root Mean Squared Error (RMSE)** | **1,130.64** | **55.67** | **−95.1% Error Reduction** |
| **Mean Sensor Bias** | **+468.92** | **−4.09** | **−99.1% Bias Reduction (held-out 2019–2021)** |
| **Mean Absolute Error (MAE)** | 468.92 | 21.56 | **−95.4% Error Reduction** |
| **Coefficient of Determination (R²)** | −6.8012 (invalid/anti-predictive) | **0.9811** | Strong held-out fit |
| **Spearman Rank Correlation (ρ)** | 0.9280 | 0.9488 | Seasonal ranking preserved |

Fitted regional empirical relationship: `MODIS_eq = 0.2694 × VIIRS + (−1.18)`.
57 of the 120 overlap months contain a zero (57 MODIS / 31 VIIRS); zero months are retained, not dropped.

### 2.5 Practical Applications & Local Impact
1. **Bangladesh Forest Department:** consistent 2002–2021 monthly fire record without sensor-induced bias, for seasonal hill-burning (Jhum) monitoring — not a live alert, and not a wildfire-crisis claim.
2. **Disaster Management & Planning:** a harmonised baseline so historical fire anomalies are compared against true multi-year normals rather than sensor steps (this is a historical analysis product, not an early-warning or alerting system).
3. **Indigenous Land Management:** preserves *Jhum* cultivation data continuity without inflating indigenous farming activity through a sensor change.

### 2.6 Scientific Integrity & Honest Limitations
- **Regional Bound:** calibrated for the CHT only; **not** a universal global converter, and it is a held-out-tested prototype, not a peer-reviewed operational product.
- **Aggregation:** monthly regional counts, not paired fire-pixel intersections; scan angle, overpass time, land cover and FRP are not modelled.
- **Detection Absences:** non-detection ≠ no fire (cloud, smoke, geometry, no observation). This tool does **not** classify fire cause.
- **Zero vs gap:** uncovered months stay blank instead of being reported as fire-free.
- **Future Transition:** because S-NPP delivery ends 1 Nov 2026, the pipeline is built to refit against NOAA-20 / NOAA-21.

### 2.7 Interactive Telemetry Web GIS & Mission Control HUD Architecture
To bridge the gap between rigorous scientific calibration and operational decision-making, BD-FireOps ships a zero-dependency, client-side Web GIS interface engineered with modern telemetry aesthetics:
1. **Dual-View Time-Series Analytics (Split vs. Continuous):** Users can seamlessly toggle between the split view (directly contrasting Naive Splice against BD-FireOps Harmonized Splice) and a single continuous 2002–2021 combined chart plotting all three series on one graph (raw naive join, Aqua MODIS ground truth, and the BD-FireOps harmonized line).
2. **Multi-Layer Web GIS Mapping Engine:** Leaflet-powered geospatial engine supporting on-the-fly toggling between **Esri World Imagery** (high-resolution satellite basemap) and **CartoDB Dark Matter**, rendered with official geoBoundaries district polygons (Bandarban, Rangamati, Khagrachhari) and spatial cell clusters.
3. **20-Year Burning Seasonality Heatmap Matrix:** A comprehensive matrix across all 12 calendar months from 2002 to 2021, classifying fire intensity into operational risk tiers (Low, Moderate, High Jhum, Peak Flare, Extreme Fire Season) to expose multi-decadal pre-monsoon burning dynamics.
4. **Animated Temporal Scrubber:** A full-range year slider (2002–2021) with an Auto play / Pause loop, six quick-jump milestone pills, and a live era badge (MODIS Years / Training Years / Test Years), letting stakeholders visualize the geographical progression of fire detections across the full 20-year archive.
5. **Interactive Calibration Playground with Moving-Block Bootstrap Uncertainty:** One live slider (0–3000 raw VIIRS detections) plus scenario presets (Low Season 25 / Typical 300 / Peak Season 940 / Severe Outbreak 2500), instantly rendering the MODIS-equivalent estimate (79.6 at the default 300), its honest 95% bootstrap range (`[59.1, 95.6]`, derived from the `[0.2198, 0.2970]` slope interval), and the avoided false-inflation percentage — all computed client-side.
6. **Zero-Dependency & Offline Vendored Architecture:** Pure HTML5, CSS3 design tokens, and vanilla JavaScript. Leaflet 1.9.4, Chart.js 4.4.1, and the official NASA Meatball vector insignia are 100% vendored locally for uninterrupted offline operation without third-party CDN vulnerability.

---

## 3. Cue-by-Cue 240-Second (4-Minute) Video Presentation Script

Record this walkthrough using OBS Studio, Loom, or Windows Game Bar (`Win + G`).
**On-screen route follows the live Web GIS HUD:** Topbar Telemetry → Problem & Dual-View Chart → Proof Cards & Per-Year Table → Live Scenario Simulator → GIS Map (Satellite / Dark) & Timeline Scrubber → Seasonality Heatmap Matrix → Scientific Limits & Method.

| Time Code | Visual on Screen | Spoken Script (English Voiceover) |
|:---|:---|:---|
| **0:00 – 0:35** | Topbar & Hero section of `index.html` (NASA Meatball insignia, dark/light mode toggle, the hero KPI ribbon — 20 Yrs coverage, −95.1% RMSE reduction, −99.1% bias cut, 0.9811 test-set R² — plus the HISTORICAL DATA · CHECKED status pill). | *"Hello judges, we are Team Claude Fable 7.0 presenting BD-FireOps. With NASA projecting end-of-science for Terra and Aqua MODIS in 2027 and NOAA ceasing Suomi-NPP VIIRS delivery on November 1, 2026, Earth observation faces an imminent data cliff. For Bangladesh's Chittagong Hill Tracts, we engineered an uncertainty-quantified, held-out-tested harmonization system that turns two incompatible sensors into one continuous, 20-year fire record — without hiding the sensor transition."* |
| **0:35 – 1:15** | **Problem Section**: Show Chart A and hover the red step warning badge. Then click the **Chart View Switcher** to toggle between **Split Comparison** and **Continuous Harmonized (2002–2021)**. | *"Here is the crisis: Aqua MODIS averaged 207 hotspots a month from 2002 to 2011. When VIIRS arrives in 2012 with 375-meter pixels, raw counts surge to a monthly mean of 590 — an artificial 2.85-times jump at the splice, and 3.71-times during overlapping months. The climate didn't change overnight — only the sensor's optical sensitivity did. Toggling our continuous view shows how BD-FireOps repairs this transition into an uninterrupted multi-decadal baseline."* |
| **1:15 – 1:55** | **Proof Section**: Focus on the 3 prominent KPI cards (**RMSE: 55.67**, **Bias: −4.09**, **R²: 0.9811**), the fitted linear formula, and the per-year held-out test table (2019, 2020, 2021). | *"We trained strictly on 2012–2018 and validated on an untouched 36-month held-out test set from 2019–2021. Uncalibrated RMSE plunged by 95.1% from 1,130.64 down to 55.67 hotspots per month. Mean sensor bias was slashed by 99.1% from +468.92 to just −4.09, achieving an R² of 0.9811 on unseen months. Our 500-resample moving-block bootstrap yields a strict 95% coefficient confidence interval of 0.2198 to 0.2970."* |
| **1:55 – 2:35** | **Live Scenario Simulator**: Drag the VIIRS monthly slider (e.g. 300 → 79.6 MODIS-eq), click a preset chip (Low Season / Typical / Peak Season / Severe Outbreak), and highlight the honest uncertainty box `[59.1, 95.6]`. | *"Operational planners can test custom scenarios live. If VIIRS reports 300 active detections in a month, our calibrated engine estimates MODIS would have observed approximately 80. The estimate comes with an honest bootstrap range — 59 to 96 — not a single magic number, giving decision-makers statistical confidence rather than blind guesses."* |
| **2:35 – 3:20** | **Web GIS Map & Seasonality Matrix**: Toggle basemaps between **CartoDB Dark Matter** and **Esri World Imagery (Satellite)**. Hit **Play** on the temporal scrubber to animate fire detections from 2002 to 2021 across CHT districts. Scroll to the **20-Year Seasonality Matrix**. | *"Our Web GIS maps real detection cells strictly inside Bandarban, Rangamati, and Khagrachhari — filtering out over 140,000 fringe detections outside CHT borders. Users can switch between high-resolution satellite imagery and high-contrast dark basemaps, or hit 'Play' to watch two decades of fire dynamics unfold. Below, our 20-year seasonality matrix clearly reveals the recurring March–April pre-monsoon Jhum agricultural burning cycles."* |
| **3:20 – 4:00** | **Scientific Limits & Method Card**: Point to the 5-step methodology, honest scientific boundaries, and conclusion on the open-source GitHub repository. | *"We remain completely transparent about scientific boundaries: this is a regional empirical calibration for CHT monthly trends, not a global converter or live wildfire alarm. All code, data schemas, sync utilities, and 35-check end-to-end audits are fully open-source and reproducible from our GitHub repository. Thank you."* |

---

## 4. GitHub & Vercel Deployment Checklist (When You're Ready)

### Step 1: Code Repository (Already Live on GitHub)
- **Repository:** `https://github.com/shahriyarcse-arch/BD_FireOps---Nasa-Space-Apps-Challange`
- Code is pushed to `main` branch with clean, human-authored commit history.

### Step 2: Deploy to Vercel (Optional for 24/7 Custom URL)
1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **"Add New Project"** -> Select `BD_FireOps---Nasa-Space-Apps-Challange`.
3. Framework Preset: Leave as **Other** (pure high-performance static web GIS app).
4. Click **Deploy**. Within 20 seconds, you will have a live public HTTPS URL (e.g. `https://bd-fireops.vercel.app`) to share.
