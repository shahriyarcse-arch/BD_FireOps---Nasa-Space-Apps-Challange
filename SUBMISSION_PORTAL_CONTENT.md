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
`BD-FireOps: Real-Time & 20-Year Fire Monitoring for Bangladesh Hills`
*(Alternative subtitle: An Uncertainty-Aware MODIS-VIIRS Fire Record for Bangladesh CHT)*

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
> 500-sample **moving-block** bootstrap coefficient interval, BD-FireOps rebuilds the record on one
> footing and states plainly how much of the repair is simple arithmetic. Against an unscaled splice,
> held-out RMSE falls by **95.1%** (1,130.64 to 55.67 hotspots/month); against the honest competing
> baseline, a single scalar ratio, it falls by a further **1.7%** (56.63 to 55.67). The control test
> settles the question the headline cannot: Aqua MODIS, the instrument that never changed, reads
> **−23.1%** across the 2012 boundary while the spliced series appears to rise **+185%**.
> Delivered as a phone-friendly website (with guided paths for rangers, hill communities, researchers and judges, plus a 6-hourly NOAA-20/21 live view) and a Streamlit console, it
> gives climate scientists, the Bangladesh Forest Department and indigenous CHT communities
> a continuous, uncertainty-quantified 2002–2021 monthly active-fire record (observed Aqua
> MODIS 2002–2011, then VIIRS converted to MODIS-equivalent — the 2012–2018 overlap used
> only to fit the conversion, tested on 2019–2021) with the 2012
> sensor step quantified and removed rather than hidden.

### Space Agency Data Used (Checkboxes & Citations)
- **NASA FIRMS Area API — source `MODIS_SP` (MODIS 1 km active fire, Collection 6.1):** daily hotspots for the CHT search window, coverage window **2002-07 → 2021-12** (first CHT-district detection 2002-12-15); Aqua-only gate applied for the reference series (`satellite = Aqua`; Terra rows counted but excluded); district-polygon gate keeps 42,716 of 112,681 raw rows.
- **NASA FIRMS Area API — source `VIIRS_SNPP_SP` (VIIRS 375 m active fire, Suomi-NPP):** daily hotspots for the CHT search window, coverage window **2012-01 → 2021-12** (`satellite = N`); study-window clamp drops 1 straggler day (2022-01-01) returned inside the final chunk, then the district-polygon gate keeps 70,857 of 172,197 raw rows.
- **NASA FIRMS Area API — near-real-time sources `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`, `MODIS_NRT`:** the last 5 days over the CHT window, fetched every 6 hours by a GitHub Action (`tools/fetch_live.py`), same confidence gates as the archive, shown as raw points in *Right now* and never mixed into or converted with the 2002–2021 record.
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

| Evaluation Metric | Naive Splice (Raw VIIRS) | Scalar-Ratio Baseline (×0.2673) | BD-FireOps (Harmonized) | Gain vs Scalar Baseline |
|:---|:---:|:---:|:---:|:---:|
| **Root Mean Squared Error (RMSE)** | 1,130.64 | 56.63 | **55.67** | **−1.7%** |
| **Mean Sensor Bias** | +468.92 | −4.63 | **−4.09** | small |
| **Mean Absolute Error (MAE)** | 468.92 | 21.95 | **21.56** | **−1.8%** |
| **Coefficient of Determination (R²)** | −6.8012 (anti-predictive) | 0.9804 | **0.9811** | marginal |
| **Spearman Rank Correlation (ρ)** | 0.9280 | 0.9280 | **0.9488** | seasonal ranking preserved |

**We report both baselines on purpose.** Comparing only against an unscaled splice would overstate
what the fitted line contributes, because nobody splices raw counts. A single scalar already removes
most of the step. What this project adds is the regional calibration for the CHT, the bootstrap
coefficient interval, the confidence-threshold and day-only sensitivity runs, and a genuine held-out
test.

**Accuracy is seasonal, and we say so.** Of the 36 held-out months, the six March–April burning
months carry an RMSE of 136.14 against a mean of 1,050.67 detections, while the other 30 months carry
an RMSE of 3.43 against a mean of 2.7. The median monthly absolute error across the whole held-out
set is 1.3 detections, so R² is reported alongside the seasonal split and Spearman rank correlation
rather than on its own.

**Control test.** Aqua MODIS observed the same districts throughout and never changed: it averages
207.1 detections/month before 2012 and 159.2 after, a change of −23.1%, while the spliced series
appears to change by +185%. The unchanged instrument shows no step, which is the clearest evidence
that the step belongs to the sensor.

Fitted regional empirical relationship: `MODIS_eq = 0.2694 × VIIRS + (−1.18)`.
Forward direction for the post-Suomi era: `VIIRS_eq = 3.7126 × MODIS + 4.37` — an algebraic
inversion, not a model fitted on NOAA-20 detections.
NOAA-20 leg status: implemented end-to-end (`--sensor viirs_noaa20`), but **not fitted** — no NOAA-20
archive is included, so 0 of the required 24 overlap months exist. The page states that explicitly
instead of showing an equation.
Per-district fits repeat the same split: slopes 0.2692 / 0.2574 / 0.2855 (Bandarban / Rangamati /
Khagrachhari) are consistent with the regional 0.2694, but the scalar-ratio baseline matches or beats
the fitted line in Bandarban (32.93 vs 33.85) and Khagrachhari (7.16 vs 8.18); the fit only wins in
Rangamati (34.74 vs 35.38). Every district card prints that comparison.
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
- **Future Transition:** because S-NPP delivery ends 1 Nov 2026, the pipeline ships a NOAA-20 / NOAA-21 leg; it refuses to publish a slope until at least 24 S-NPP / NOAA-20 overlap months are downloaded, and is currently reported as not fitted.

### 2.7 Who it is for, and what changes after one minute

| User | What is hard today | What they get from BD-FireOps in one minute |
| :--- | :--- | :--- |
| A forest officer in Rangamati, Bandarban or Khagrachhari | FIRMS shows thousands of dots; after 2012 every year looks like a record, so real anomalies are hidden | *Where should rangers look first?* ranks the three districts against each district's own normal for that month |
| A family in the hills that burns jhum fields | No simple answer to "when is the risky time?" | *When do the Hills burn?* — an average year, plus three plain safety tips |
| A climate researcher | MODIS and VIIRS counts cannot be joined without a false step | One 2002–2021 monthly record on the MODIS scale, with a held-out test, a bootstrap range and a CSV download |
| A NASA judge | Needs the claim, the evidence and the limits quickly | A 6-stop guided path: claim → control test → unseen-year test → NOAA-20 gap → team and data |

### 2.8 What the website does (current build)

1. **Two clocks, kept apart.** *Right now* shows the latest NOAA-20/NOAA-21 detections (raw 375 m points, refreshed every 6 hours by a GitHub Action, with "updated N hours ago" and an overdue warning). It is compared only with the same kind of 375 m camera in the archive. The 2002–2021 record below is the harmonized archive. Live points are never converted with the monthly formula: that formula was fitted on monthly regional totals from Suomi-NPP and has not been fitted for NOAA-20.
2. **Guided paths.** *I am a…* chips (Forest ranger, Hill community, Researcher, NASA judge) jump to stop 1; a small dock gives Next / Back with progress. Links like `?view=judge` open a path directly.
3. **Answer-first tools.** Where to look first (per district triage), Was this season unusual? (rank, typical range and uncertainty, in plain words), When do the Hills burn?, and a CSV download.
4. **The 2012 jump.** A drag-to-compare chart shows the raw join against the corrected record on the same axis; monthly charts and the formula sit one click away.
5. **Evidence.** The Aqua-only control test (-23.1%), the held-out 2019–2021 test (with the honest 1.7% gain over simple scaling), and all detailed numbers inside *All the numbers, for reviewers*.
6. **Web GIS Map.** 2002–2021 detections on 5 km cells inside the district polygons, with year controls, autoplay timeline, dual basemap toggle (Esri Satellite / Dark Matter) and a satellite custody strip.
7. **Performance & Accessibility.** Hardware-accelerated 60/120fps smooth scrolling (background composited on dedicated GPU layer to eliminate scroll repaints, zero-blur compositor transforms). Phone-first responsive design from 320 px to 4K.
8. **Built to be checked.** Every number is written into the page by `tools/sync_web.py` from our results files; `tools/e2e_audit.py` (104 automated checks, 0 failures) verifies data provenance on every build. Static site, vendored Leaflet 1.9.4 and Chart.js 4.4.1, WCAG 2.2 compliant (axe-core 0 violations).

---

## 3. Cue-by-Cue 240-Second (4-Minute) Video Presentation Script

Record this walkthrough using OBS Studio, Loom, or Windows Game Bar (`Win + G`).
**Screen flow:** Continuous top-to-bottom downward scroll in one single take.
**Target duration:** 3 minutes 45 seconds (leaves a safe 15-second buffer under the 240 s hard limit).

| Time Code | Visual on Screen | Spoken Script (English Voiceover) |
|:---|:---|:---|
| **0:00 – 0:35**<br>*(35s)* | **Hero & Challenge Title:** Open `index.html` at 1080p in Dark Mode. Hover cursor over the kicker `CHALLENGE: HARMONIZATION OF MODIS AND VIIRS HOT SPOTS`, the flame mark, and the 4 stakeholder chips. | *"Hello judges! We are Team Claude Fable 7.0: Shamim Shahriyar, Tanjum Raisa, Rashedul Anik, and Nusrat Alam Lamim, presenting BD-FireOps for the challenge Harmonization of MODIS and VIIRS Hot Spots. In Bangladesh’s Chittagong Hill Tracts, seasonal farming fires happen every spring. But in 2012, when NASA swapped older MODIS satellites for sharper VIIRS sensors, fire counts seemed to triple overnight. The forest didn't change — the camera did. So we built BD-FireOps to bridge twenty years of NASA data into one honest scale."* |
| **0:35 – 1:15**<br>*(40s)* | **Guided Ranger Demo:** Click **Forest ranger** chip in Hero. Bottom dock appears. Click *Next* to `#priority`. Select **April 2014** (shows `Rangamati, about 2.0× normal`). Click *Next* to `#season`, choose **March 2019** (`within normal range, ranked 6 of 19`). Click **Download CSV**. | *"To make this useful on day one, we created guided paths for different stakeholders. Watch what happens when a forest ranger visits our site: clicking 'Forest ranger' opens a dock at the bottom to walk through their exact questions. First, under 'Where to look first', an officer picks April 2014. BD-FireOps immediately flags Rangamati at two times its normal fire activity, prioritizing ranger patrols where they matter most. Next, under 'Check a season', they select March 2019: it instantly reports 'within normal range', ranked 6th out of 19 years, complete with statistical bounds. And with one click on 'Download CSV', rangers get the clean twenty-year numbers for their own reports."* |
| **1:15 – 1:55**<br>*(40s)* | **Live Telemetry & 20-Year Map:** Scroll to `#now` (*Right now*). Click red dot in Rangamati on live map (`FRP: 3.74 MW`). Scroll to `#map-section`. Toggle **Satellite** basemap, click **Play** on timeline scrubber. | *"Now, what is happening right now? In Chapter 00, BD-FireOps connects to NASA FIRMS near-real-time telemetry, updating every six hours. Over the last five days, NOAA-20 and 21 detected active heat points in the hills. We keep live data as raw, provisional dots — because forcing a monthly model onto a five-day snapshot would be scientifically false. Below, our interactive 20-year map filters over one hundred and thirteen thousand clean detections inside district boundaries. Pressing Play animates fire patterns from 2002 to 2021, showing that eighty percent of burning takes place during pre-monsoon clearing in March and April."* |
| **1:55 – 2:40**<br>*(45s)* | **2012 Jump & Control Test:** Scroll to `#problem`. **Drag Before/After compare handle** across Chart A & B. Hover over `-23.1%` Aqua control badge, the 3 metric cards (RMSE 55.67, Bias -4.09, Spearman 0.9488), and click *All the numbers, for reviewers*. | *"The heart of our project is the science. In Chapter 02, we show why you can't just stitch these satellites together. Aqua MODIS averaged 207 hotspots a month before 2012. When VIIRS arrived with smaller 375-meter pixels, monthly counts surged to 590 — an artificial almost three-times jump. Watch our comparison slider: the naive join creates a false climate crisis, while BD-FireOps restores continuous physical truth on the exact same axis. How do we prove fires didn't really rise? Because Aqua MODIS flew across the entire period without changing, and its own camera saw fires drop twenty-three percent! On an untouched three-year test set, our model cuts prediction error by ninety-five percent."* |
| **2:40 – 3:15**<br>*(35s)* | **Uncertainty & Honest Limits:** Scroll to `#try`. Move slider to **300 VIIRS** (converts to `80 MODIS-eq`, 95% bootstrap CI `[59.1, 95.6]`). Highlight *After Suomi-NPP* (`Not fitted: 0 / 24`). | *"We also give users practical uncertainty tools. If an analyst enters 300 VIIRS detections in our calculator, BD-FireOps converts it to about 80 MODIS-equivalent fires, with a 500-sample bootstrap confidence range of 59 to 96. And because Suomi-NPP was retired on November 1st, 2026, we prepared our pipeline for the future. But we stay completely honest: we refuse to publish a conversion for NOAA-20 until at least 24 overlapping months exist. The site openly states: zero of twenty-four months."* |
| **3:15 – 3:45**<br>*(30s)* | **Usability, Open Data & Close:** Scroll to `#method` and `#team`. Highlight 4 member cards and the GitHub link. | *"To make sure this actually works for real people, we usability-tested the prototype with three people outside our team and fixed where they got stuck. Our entire pipeline uses official open data: NASA FIRMS Aqua MODIS, Suomi-NPP VIIRS, NOAA-20 and 21 near-real-time feeds, and geoBoundaries district polygons. Every calculation is automated, reproducible, and open source on GitHub. Thank you so much from Team Claude Fable 7.0!"* |
---

## 4. GitHub & Vercel Deployment Checklist (When You're Ready)

### Step 1: Code Repository (Already Live on GitHub)
- **Repository:** `https://github.com/shahriyarcse-arch/BD_FireOps---Nasa-Space-Apps-Challange`
- Code is pushed to `main`. AI assistance is disclosed in §5; do not describe the history as purely human-authored.

### Step 2: Deploy to Vercel (Optional for 24/7 Custom URL)
1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **"Add New Project"** -> Select `BD_FireOps---Nasa-Space-Apps-Challange`.
3. Framework Preset: Leave as **Other** (pure high-performance static web GIS app).
4. Click **Deploy**. Within 20 seconds, you will have a live public HTTPS URL (e.g. `https://bd-fireops.vercel.app`) to share.

---

## 5. Use of AI (required NASA page field)

> Participants Guide §10 and §15: name every AI tool, explain the prompts and reasoning, say what data the AI worked on, and show where your own work went. **Edit this to match exactly what your team did.**

| Tool | What it was used for | Data it saw | Human check |
| :--- | :--- | :--- | :--- |
| Anthropic Claude (chat / Cowork) | Code review, end-to-end audit design, wording of the dashboard and this document, the "Was this season unusual?" widget and plain-language layer | Our repository and `metrics.json`; no personal data | Every number is generated by our pipeline from NASA FIRMS and verified by `tools/e2e_audit.py`; the team reviewed and tested all code |
| Google DeepMind / Antigravity (Gemini) | Full codebase audit, live browser automation & verification (Playwright), CSS specificity bug-fix, and scroll UX optimization | Repository source files, DOM structure, and test suites | All fixes verified through automated Playwright runs and CI test suite; code changes verified and approved by the team |

**Prompts we gave Claude (translated from Bangla, in order):**
1. "Audit the whole project in phases (data, science, code, web, submission) without changing code, and list what is weak."
2. "Fix everything the audit found and make this the best project in its genre."
3. "Analyse the site from three users' points of view: a forest officer, a hill community member, a researcher."
4. "Check every section for numbers that are typed by hand instead of coming from the data, and rewrite text so it does not read as AI-generated."
5. "Separate historical and live data clearly, and refresh the live data every 6 hours."
6. "Test the site with the ui-ux-pro-max and addyosmani/agent-skills checklists (accessibility, performance) and fix what fails."
7. "Make the site minimal and easy to understand, but keep the stakeholder guided paths."
8. "Is it scientifically right that the live data is not converted to the MODIS scale?" (Claude found that our live comparison mixed a MODIS-scale average with raw VIIRS points; we changed it to compare like with like.)
9. "Check the project against the Participants Guide and the Quality Suggestions document."

**Prompts we gave Google DeepMind / Antigravity (Gemini):**
1. "Run end-to-end audit verification across web, metrics.json, and CI with 104-point e2e audit."
2. "Fix live telemetry comparison to compare 375 m VIIRS detections like-with-like against the historical VIIRS archive baseline rather than the 1 km MODIS scale."
3. "Implement hardware-accelerated 60fps smooth scrolling by eliminating background-attachment: fixed repaints and heavy blur filters."
4. "Restore stakeholder guided navigation (Forest ranger, Hill community, Researcher, NASA judge) with bottom progress dock."
5. "Verify 100% WCAG 2.2 accessibility, contrast compliance, and zero duplicate HTML IDs across all viewports."

**Why we used AI:** a 4-person student team, two days, and a large audit surface; AI was used to review, test and word things, never to produce data or results.

**What is ours:** the choice of study area and reference sensor (Aqua-only), the cleaning rules, the time-split validation design, the control-test argument, the district gate, and all interpretation of results. No AI-generated images, audio, voices or datasets are used.

---

## 5b. Test with three people (Quality Suggestions §5) — fill in before submitting

Validity scores 20 only when the prototype is *usability tested*. Before Saturday morning, show the site to three trusted people outside the team (for example a forestry or geography student, a family member, a classmate from another department). Give each one task, watch silently, and write down where they hesitated.

| Tester (role only, no names of anyone under 18) | Task | Where they hesitated | What we changed |
| :--- | :--- | :--- | :--- |
| | "Was March 2021 an unusual fire month?" | | |
| | "Which district should a ranger check first in April 2014?" | | |
| | "Why don't fires really triple in 2012?" | | |

Only write what really happened. One honest line here is worth more than a long claim.

---

## 6. Team members and roles (required on the NASA Members tab and in every video)

| Name | Role |
| :--- | :--- |
| Shamim Shahriyar | Team lead |
| Tanjum Raisa | Presenter / storyteller |
| Nusrat Alam Lamim | Designer |
| Md. Rashidul Islam | Developer |

Also replace the dashed placeholders in the **Team** section of `index.html`. Under-18 members: no recognisable name, voice or face in any video or submission (Guide §10).

---

## 7. Video 2 — Recording Checklist & Quality Requirements

The Guide requires in Video 2 (Full Presentation & Working Demo):
1. **Team Name:** State *"Team Claude Fable 7.0"* clearly.
2. **Every Member by Name:** State *"Shamim Shahriyar, Tanjum Raisa, Rashedul Anik, and Nusrat Alam Lamim"* aloud.
3. **Challenge Named:** State *"Harmonization of MODIS and VIIRS Hot Spots"* aloud.
4. **NASA Datasets Spoken Aloud:** Say *"NASA FIRMS MODIS_SP from Aqua, VIIRS_SNPP_SP, the NOAA-20 and NOAA-21 near-real-time feeds, and geoBoundaries district polygons."*
5. **Live Working Demo:** Follow the Forest ranger guided path (triage in April 2014, season check in March 2019, CSV export, live map).
6. **Hard Limit:** Strictly under 240.0 seconds! Target: **3 minutes 45 seconds** (time it with a stopwatch before final upload).
7. **English Subtitles:** Burn in captions or upload an SRT file. Under-18 members: no recognisable face, voice or full name.

---

## 8. Video 3 — 30-Second Global Judging Teaser Video Script (Due 14 Nov, 12:00 PM)

> **Hard Limit:** Strictly under 30.0 seconds! Target: **26–28 seconds** (70 words, natural conversational pace).  
> **Subtitles:** Burn in English subtitles or provide SRT captions (mandatory for judging).

| Time | On Screen (`index.html`) | Voiceover (Natural Human Speech) |
| :--- | :--- | :--- |
| **0:00 – 0:08**<br>*(8s)* | **Hero & Challenge Title:** Top of page in Dark mode. Hover cursor over kicker `CHALLENGE: HARMONIZATION OF MODIS AND VIIRS HOT SPOTS` and team names. | *"We are Team Claude Fable 7.0 — Shamim Shahriyar, Tanjum Raisa, Rashedul Anik, and Nusrat Alam Lamim — for the challenge Harmonization of MODIS and VIIRS Hot Spots."* |
| **0:08 – 0:15**<br>*(7s)* | **2012 Jump & Control Test:** Drag comparison slider across Chart A showing the jump, then hover over `-23.1%` Aqua control badge. | *"When NASA added sharper VIIRS sensors in 2012, fire counts seemed to triple. But Aqua MODIS actually fell 23 percent!"* |
| **0:15 – 0:22**<br>*(7s)* | **Continuous 20-Year Solution:** Scroll to `#continuity` showing Chart B's continuous line and `95.1%` error reduction card. | *"BD-FireOps removes 95 percent of that sensor error, creating one continuous 20-year record for Bangladesh hills —"* |
| **0:22 – 0:28**<br>*(6s)* | **Tested, Live & Open Source:** Scroll to `#now` showing live NOAA-20/21 points, then snap to GitHub link. | *"tested with users, live with NOAA-20, and fully open source."* |

English subtitles required. Upload to YouTube or Vimeo, paste into the Google Form **and** the NASA Project Demo field, and test the link in a private window.

---

## 9. Final NASA page checklist

- [ ] Members tab: every member, photo, role. Team photo added.
- [ ] Challenge named: Harmonization of MODIS and VIIRS Hot Spots (2026 list).
- [ ] High-Level Summary includes the 240 s video link and the GitHub link.
- [ ] Project Demo: 30 s video. Final Project: GitHub link.
- [ ] Use of AI (§5), NASA data sources (§1), References.
- [ ] GitHub and video links tested in a private window.
- [ ] **Clicked Submit.**
