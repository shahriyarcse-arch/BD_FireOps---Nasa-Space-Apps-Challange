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
> 500-sample bootstrap coefficient interval, BD-FireOps reduces held-out test RMSE by
> **95.1%** (from 1,130.64 to 55.67 hotspots/month) and cuts mean prediction bias by **99.1%**
> (from +468.92 to −4.09 hotspots/month) on the 2019–2021 held-out test window,
> reaching **R² = 0.9811** on unseen months.
> Deployed as a clean, light-themed web GIS and a Streamlit data-science console, it
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
- **Two extra robustness runs:** (i) keeping low-confidence detections moves the slope `0.2694 → 0.2464 (−8.54%)` and RMSE `55.67 → 58.43 (+4.96%)`; (ii) restricting **both sensors to daytime only** (`daynight = D`; MODIS 42,391 / VIIRS 64,537 rows) moves the slope to `0.2956 (+9.73%)` and RMSE to `49.69 (−10.74%)`. Night rows therefore add noise rather than signal — reported plainly, with the day-only configuration listed as future work (switching the headline config days before submission would invalidate the tested numbers).

### 2.4 Held-Out Validation Benchmark (2019–2021)
Unlike prototypes that report in-sample metrics, BD-FireOps validates on an untouched 3-year held-out window (N = 36 months; train 84 / test 36, no leakage):

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
2. **Disaster Management & Early Warning:** a harmonised baseline so local fire emergencies are judged against true historical normals rather than sensor steps.
3. **Indigenous Land Management:** preserves *Jhum* cultivation data continuity without inflating indigenous farming activity through a sensor change.

### 2.6 Scientific Integrity & Honest Limitations
- **Regional Bound:** calibrated for the CHT only; **not** a universal global converter, and it is a held-out-tested prototype, not a peer-reviewed operational product.
- **Aggregation:** monthly regional counts, not paired fire-pixel intersections; scan angle, overpass time, land cover and FRP are not modelled.
- **Detection Absences:** non-detection ≠ no fire (cloud, smoke, geometry, no observation). This tool does **not** classify fire cause.
- **Zero vs gap:** uncovered months stay blank instead of being reported as fire-free.
- **Future Transition:** because S-NPP delivery ends 1 Nov 2026, the pipeline is built to refit against NOAA-20 / NOAA-21.

---

## 3. Cue-by-Cue 240-Second (4-Minute) Video Presentation Script

Record this walkthrough using OBS Studio, Loom, or Windows Game Bar (`Win + G`):

| Time Code | Visual on Screen | Spoken Script (English Voiceover) |
|:---|:---|:---|
| **0:00 – 0:45** | Title slide + NASA Earthdata alert screenshot of the S-NPP cessation notice. | *"Hello judges, we are Team Claude Fable 7.0 presenting BD-FireOps. NASA projects end-of-science for Terra MODIS in February 2027 and Aqua in September 2027, and NOAA has announced that Suomi-NPP VIIRS data delivery stops permanently on November 1st, 2026. Simply stitching 20 years of MODIS and VIIRS records together creates an artificial +185% — a 2.85-times — step jump in recorded fires. Today we show how BD-FireOps harmonizes those records for the Chittagong Hill Tracts in Bangladesh."* |
| **0:45 – 1:30** | Web App (`index.html`). **Chart A (wrong join) vs Chart B (fixed line)**, side by side. | *"Here is the core problem. From 2002 to 2011, Aqua MODIS recorded a mean of 207 hotspots per month across the CHT districts. After VIIRS comes online in 2012 at 375-metre resolution, the raw mean jumps to 590 hotspots per month — a 2.85-times step at the splice, and 3.71-times when we compare only months where both sensors observe together. Only the sensor changed; a policy maker reading the raw chart would think fires nearly tripled overnight."* |
| **1:30 – 2:30** | **Chart B (fixed line)**, then the simplified hill-district map. | *"Now Chart B: BD-FireOps's harmonized series. We keep only Aqua MODIS afternoon overpasses, keep only detections inside the Bandarban, Rangamati and Khagrachhari district polygons (geoBoundaries BGD-ADM2 simplified geometry — border cells have ~1% tolerance), drop low-confidence detections, and fit an empirical scaling model on 2012–2018 only, converting later VIIRS counts into MODIS-equivalent activity. Coefficient uncertainty is reported separately as a 95% block-bootstrap interval — the slope sits between 0.220 and 0.297. Note the March–April seasonal peak stays continuous and comparable across two decades."* |
| **2:30 – 3:20** | **Held-out test results (2019–2021)** + validation scatter plot. | *"We did not just fit a curve. On three full years of unseen data — 2019 through 2021, never touched during training — held-out test RMSE drops from 1,131 to 56 hotspots per month, a 95.1% RMSE reduction. Mean prediction bias falls from plus 469 to minus 4, a 99.1% bias reduction on the same held-out window, with an R-squared of 0.9811 on held-out months."* |
| **3:20 – 4:00** | **Interactive Calibration box**, then limitations and the GitHub repo. | *"Our interface also includes an interactive calibration box where you can try the fitted conversion. In conclusion, BD-FireOps gives Bangladesh forest managers and climate researchers a continuous 2002–2021 record (observed Aqua MODIS 2002–2011, VIIRS converted to MODIS-equivalent after — model fitted on 2012–2018, tested on 2019–2021). The code is reproducible, open-source, and every number here is generated from metrics.json rather than typed by hand. Thank you!"* |

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
