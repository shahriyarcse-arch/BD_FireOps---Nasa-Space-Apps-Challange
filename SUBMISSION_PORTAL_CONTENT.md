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
3. **Answer-first tools.** Where to look first (per district), Was this season unusual? (rank, typical range and uncertainty, in plain words), When do the Hills burn?, and a CSV download.
4. **The 2012 jump.** A drag-to-compare chart shows the raw join against the corrected record on the same axis; monthly charts and the formula sit one click away.
5. **Evidence.** The Aqua-only control test, the held-out 2019–2021 test (with the honest 1.7% gain over simple scaling), and all detailed numbers inside *All the numbers, for reviewers*.
6. **Map.** 2002–2021 detections on 5 km cells inside the district polygons, with year controls, autoplay and a satellite-by-year strip.
7. **Built to be checked.** Every number is written into the page by `tools/sync_web.py` from our results files; `tools/e2e_audit.py` (104 checks) fails if any number drifts. Static site, vendored Leaflet 1.9.4 and Chart.js 4.4.1, WCAG checks with axe-core (0 violations), phone-first layout from 320 px.

---

## 3. Cue-by-Cue 240-Second (4-Minute) Video Presentation Script

Record this walkthrough using OBS Studio, Loom, or Windows Game Bar (`Win + G`).
**On-screen route:** Hero → The 2012 jump → Control test → Unseen-year test → Forest ranger path → Converter and After Suomi-NPP → Limits and Team.s & Method.

| Time Code | Visual on Screen | Spoken Script (English Voiceover) |
|:---|:---|:---|
| **0:00 – 0:30** | Hero: headline and the one-line answer. | *"We are Team Claude Fable 7.0 — Shamim Shahriyar, Tanjum Raisa, Rashedul Anik and Nusrat Alam Lamim — answering the 2026 challenge Harmonization of MODIS and VIIRS Hot Spots. NASA's MODIS and VIIRS cameras both count fires in Bangladesh's Chittagong Hill Tracts. Join their records and fires seem to triple in 2012. They did not. The camera changed."* |
| **0:30 – 1:10** | *The 2012 jump*: drag the compare handle. Then *Did fires really rise in 2012?* | *"MODIS averaged about 207 hotspots a month before 2012. VIIRS, with 375-metre pixels, reports about 590. Joined raw, that is a false 2.85-times jump. The proof: Aqua MODIS flew through the whole period with the same camera, and it saw 23 per cent less burning after 2012. The step belongs to the sensor, not the forest."* |
| **1:10 – 1:50** | *Tested on years it never saw*: the three cards and the "Worth knowing" note. | *"We fitted the conversion on 2012 to 2018 and tested it on 2019 to 2021, data it never saw. The monthly error is 55.67 hotspots, against 1,130 for the raw join. To be straight with you: one simple scaling factor already gets 56.63, so our fitted line adds 1.7 per cent. Our contribution is the regional calibration, the uncertainty range, the sensitivity runs and the honest test."* |
| **1:50 – 2:40** | *I am a… → Forest ranger*. Next through: Right now → Where to look first (April 2014) → Was this season unusual? → Map. | *"A forest officer opens the site. Right now shows this week's NOAA-20 and NOAA-21 detections, refreshed every six hours and compared only with the same kind of camera. Where to look first ranks each district against its own normal: in April 2014, Rangamati at about twice its usual April. Was this season unusual answers in plain words, with uncertainty, and the map steps to that year."* |
| **2:40 – 3:20** | *Try the conversion* (300 → 79.6, range 59.1–95.6), then *After Suomi-NPP* (0 / 24). | *"Any monthly VIIRS count converts to the MODIS scale with an honest range. Suomi-NPP stopped on 1 November 2026. We will not fake a NOAA-20 formula: the code refuses to fit one until 24 months of overlap exist, and the page says so."* |
| **3:20 – 4:00** | *What this tool can and can't do*, then *Who built this* and the GitHub link. | *"Our data: NASA FIRMS MODIS_SP from Aqua, VIIRS_SNPP_SP, the NOAA-20 and NOAA-21 near-real-time feeds, and geoBoundaries district polygons. It covers three districts, it is not a fire alarm, and no dot does not mean no fire. Everything is open source and re-runs from NASA data. Thank you."* |
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

**Gemini prompts:** *(team: add the prompts you actually used with Gemini/Antigravity here)*

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
| Shamim Shahriyar | Data & pipeline |
| Tanjum Raisa | Web dashboard |
| Rashedul Anik | Science validation & documentation |
| Nusrat Alam Lamim | Story, video & presentation |

Also replace the dashed placeholders in the **Team** section of `index.html`. Under-18 members: no recognisable name, voice or face in any video or submission (Guide §10).

---

## 7. Video 2 — changes to the 4-minute script above

The Guide requires, in **every** video: team name, **every member by name**, the problem and challenge statement; Video 2 also needs a **working demo** and **NASA datasets said out loud**, with **English subtitles**, under 240 s.

1. **0:00 opening line, replace with:** *"We are Team Claude Fable 7.0 — Shamim Shahriyar, Tanjum Raisa, Rashedul Anik, and Nusrat Alam Lamim — answering the 2026 challenge Harmonization of MODIS and VIIRS Hot Spots."*
2. **Follow one path (about 25 s):** under *I am a…* click **Forest ranger**; the page jumps to stop 1 and a small dock at the bottom gives *Next* / *Back* through its 5 stops. At *Where should rangers look first?* set **April 2014**: *"An officer asks where to look first. Each district is compared with its own normal."* The season check below shows the same month, and the map can be stepped to 2014. *"One question, followed from district to month to map."*
3. **Add at about 1:55 (swap for part of the simulator segment):** open **Check a season**, choose *March 2019*: *"A forest officer asks: was this March unusual? BD-FireOps answers in plain words — within the normal range, ranked 6 of 19 years — and gives the uncertainty."* Then click **Download CSV**.
4. **Say the data aloud:** *"We use NASA FIRMS MODIS_SP from Aqua and VIIRS_SNPP_SP, plus geoBoundaries district polygons."*
5. Time it with a stopwatch. Over 240 s gets cut off.

---

## 8. Video 3 — 30-second global judging video (due 14 Nov, 12:00 PM)

| Time | On screen | Voiceover |
| :--- | :--- | :--- |
| 0–5 s | Title card: BD-FireOps · Team Claude Fable 7.0 · Shamim, Tanjum, Rashedul, Nusrat | *"Team Claude Fable 7.0: Shamim Shahriyar, Tanjum Raisa, Rashedul Anik, and Nusrat Alam Lamim."* |
| 5–12 s | Chart A jump at 2012 | *"Join NASA's MODIS and VIIRS fire records and Bangladesh's hill fires seem to triple overnight."* |
| 12–18 s | Control panel: MODIS −23.1% | *"But the camera that never changed saw burning fall. It's the sensor, not the forest."* |
| 18–26 s | Chart B, then the Check-a-season answer | *"BD-FireOps puts both on one scale from NASA FIRMS data, so anyone can ask: was this season unusual?"* |
| 26–30 s | Repo URL + "Built to outlive Suomi-NPP" | *"Open source, tested on unseen years."* |

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
