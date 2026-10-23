# BD-FireOps PRD & Competitive Audit — Space Apps 2026

Oct 20, 2026 · @Sarder Mahmud

The project is viable and should be kept, but three things must change before the hackathon on Nov 14, 2026: the headline claim is measured against a baseline no analyst would use, the record stops in 2021, and Suomi-NPP stops delivering data on Nov 1, 2026, thirteen days before you compete.

## 1. Executive verdict

**Keep the project. Change how it argues for itself, extend the record, and make the sensor transition the live story rather than a footnote.** The topic fits the challenge, the pipeline is real, the data is genuine NASA FIRMS, and the engineering discipline is above average for a hackathon. The weakness is not the code. It is that the headline claim rests on a comparison that a knowledgeable judge will take apart in a minute, and that the project's own urgency argument points at a date the project does not reach.

### The five risks that matter

1. **The error-reduction headline is measured against a straw man.** The 95.1% figure compares the fitted model with splicing raw unscaled VIIRS counts onto MODIS, which no analyst would do. A single scalar ratio of 0.2673 reaches RMSE 56.63 against the fitted model's 55.67, so the model gains 1.7%. This is the highest-severity issue, because it is a credibility risk rather than a technical one.
2. **Suomi-NPP stops delivering on 1 November 2026, thirteen days before the hackathon.** By the time you present, the sensor your record is built on will be dead. This is either the project's biggest weakness or its sharpest hook, depending entirely on whether you add a NOAA-20 leg before the event.
3. **The record ends in 2021 while the pitch is about 2026.** Five years of available data are missing, and a judge will ask why.
4. **Other teams are already building the same thing, several of them in Bangladesh.** Public repositories for this challenge show global burning-activity calendars with per-cell calibration and near-real-time early warning. A region-level monthly-count prototype is narrower than what several competitors will show.
5. **Accuracy is carried by six months of the year.** Thirty of the thirty-six held-out months average 2.7 detections, with a median error of 1.3. R² of 0.9811 reports that the burning season is large, not that the model is excellent.

### What this means in practice

None of these require a new project or a new architecture. Four of the five are repairs to framing, scope and data freshness that the existing codebase already supports. The fifth, the NOAA-20 leg, is genuine new work and is the single feature most likely to separate you from the other teams on this challenge.

## 2. Existing-project audit

I read the repository in `D:\Downloads\Nasa`, re-ran `analysis/model.py` against your own `data/processed/monthly.csv`, refitted the model under several variations, and loaded `index.html` in a headless browser with and without network access. Everything below was executed, not assumed. I did not run `analysis/download.py`, because it needs your FIRMS key, so the data acquisition path is reviewed by reading the code rather than by running it.

### Verified working

| Component | Evidence |
| --- | --- |
| FIRMS provenance | `data_source.json` records `nasa_firms_api`, MODIS\_SP and VIIRS\_SNPP\_SP, 42,716 and 70,857 clean detections |
| District clipping | geoBoundaries ADM2 polygons drop 54,300 MODIS and 85,857 VIIRS rows outside the three districts |
| Zero-month handling | 57 of 120 overlap months contain a zero; kept, not dropped, with NaN reserved for no-coverage months |
| Time-split validation | Train 2012–18, test 2019–21, no overlap, genuinely untouched during fitting |
| Coefficient stability | Refitting after removing the 1, 2 and 3 largest training months moves the slope only between 0.264 and 0.289 |
| Bootstrap | Moving-block resampling over 12-month blocks, correct choice for seasonal data, correctly labelled a coefficient interval |
| Reproducibility | `model.py` reproduces every published number exactly; 28 pipeline tests and a 48-check end-to-end audit pass |
| Number discipline | `sync_web.py` and `sync_readme.py` generate every displayed figure from `metrics.json`, so the UI cannot drift |

This is the part worth defending. Very few hackathon projects can regenerate their own claims from their own data.

### Incorrect or misleading

**The improvement claim.** Reported against the raw splice only. The honest competing baseline, one scalar of total train MODIS over total train VIIRS, scores RMSE 56.63 and R² 0.9804 on the held-out set against the fitted model's 55.67 and 0.9811. The equation is, in effect, a ratio estimator with an intercept near zero.

**The accuracy claim.** Held-out error splits as RMSE 136.14 across the six March–April months, against 3.43 across the other thirty. Median absolute error across the whole test set is 1.3 detections. One month, March 2019, supplies 45% of the total squared error.

**The offline claim.** The documents described the dashboard as fully offline, but the map pulled basemap tiles from Esri and the page pulled Google Fonts. On a weak venue connection the map would have rendered as an empty grey panel during judging.

**The product naming in your own brief.** Your prompt describes the datasets as MCD14DL and VNP14IMGTDL, which are the near-real-time products. The code requests `MODIS_SP` and `VIIRS_SNPP_SP`, which are the standard-processing archive. These are different access routes with different latency. The submission must say which one it uses.

### Missing or unverified

The record stops at 2021 by a hardcoded date rather than by data availability. There is no NOAA-20 leg, so the project cannot continue past the Suomi-NPP shutdown. There is no comparison against any existing tool. There is no spatial validation: the fit is region-wide monthly counts, so nothing tests whether the correction holds in one district and fails in another. The Streamlit console in `dashboard/app.py` exists but I did not run it, so I cannot confirm it works.

### Already repaired

In the previous session I implemented the honest baseline, the seasonal split, the MODIS-only control test, the offline map fallback, the dynamic study window and the forward mapping, and wrote them back to your folder. The audit and the test suite pass on those changes. The roadmap below starts from that repaired state, not from the original.

## 3. Official 2026 requirements

**Important limitation.** The official challenge page at `spaceappschallenge.org` blocks automated fetching, so I could not read the Challenge 9 statement verbatim. Everything below marked unverified must be confirmed by a team member opening the page directly. I have not substituted previous-year text as current rules, and where I cite 2025 material it is labelled as historical.

### Verified from official sources

| Item | Detail | Source |
| --- | --- | --- |
| Hackathon dates | 14–15 November 2026 | [spaceappschallenge.org/2026](https://www.spaceappschallenge.org/2026/), accessed 20 Oct 2026 |
| Theme | "The Next Frontier" | same |
| Submission window | Opens Sat 14 Nov 09:00, closes Sun 15 Nov 23:59 local time | same |
| Registration | Open until the hackathon closes on 15 November | same |
| Participant survey | Due 30 November 2026 | same |
| Eligibility for global judging | Submitting a project earns a certificate and makes the team eligible for Global Judging | same |

You therefore have roughly three and a half weeks, and the event is a two-day build with a hard local-time deadline.

### Historical context, 2025, not confirmed for 2026

The 2025 awards page lists ten global award categories, each with a one-line definition: Best Use of Science, Best Use of Data, Best Use of Technology, Galactic Impact, Best Mission Concept, Most Inspirational, Best Use of Storytelling, Global Connection, Art & Technology, and Local Impact. It describes judges at local and universal events selecting Global Nominees, NASA and partner subject-matter experts choosing Global Finalists and Honorable Mentions, and an executive committee selecting ten Global Winners. **There is no published numerical rubric, and I will not invent one.** Treat these categories as a guide to what NASA values, not as a 2026 scoring sheet.

For your project, three of those categories are plausibly reachable: Best Use of Science, Best Use of Data, and Local Impact.

### Unverified, confirm yourselves

- The verbatim Challenge 9 statement, its stated objectives, its "potential considerations" list and its recommended NASA resources. Read it at the challenge page and check that your framing answers the question it actually asks.
- Whether the challenge expects a global or an any-area solution rather than one fixed region. Public repositories from other teams suggest a global or user-selectable area framing, which would make a Bangladesh-only tool a partial answer. This matters enough that it should be checked first, before any further building.
- Dhaka local event specifics: venue, local judging arrangement, presentation length, whether slides or a live demo are expected, and any local submission steps. Ask the Dhaka organisers directly; none of this is published in a form I could verify.
- Any 2026 rules on AI-generated work, external datasets and third-party APIs. Read the Participant Guide and FAQ on the official site, and record what they say, because your project uses AI assistance and vendored third-party libraries.

### The one date that changes your strategy

NOAA and NASA have both announced that Suomi-NPP data product delivery ceases permanently on 1 November 2026, thirteen days before the hackathon. Your project is built on `VIIRS_SNPP_SP`. By the time you present, that sensor is no longer delivering. Either you treat this as the reason the project exists and show the record continuing on NOAA-20, or a judge points out that your pipeline stops working the fortnight before you demonstrate it.

## 4. Dataset and study-area assessment

### What the FIRMS API actually offers

The FIRMS Area API exposes eight sources: `LANDSAT_NRT`, `MODIS_NRT`, `MODIS_SP`, `VIIRS_SNPP_NRT`, `VIIRS_SNPP_SP`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA20_SP` and `VIIRS_NOAA21_NRT`. Each request accepts a day range of 1 to 5, and a map key allows 5,000 transactions per 10-minute interval, with increases available on request. Omitting the date returns the most recent data ([FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/), accessed 20 Oct 2026).

Two consequences follow. First, **`VIIRS_NOAA20_SP` already exists**, so the NOAA-20 leg is a data pull you can make today rather than a research proposal. Second, the 5-day chunk limit means a 24-year pull is roughly 1,750 requests per sensor, which fits inside the rate limit but takes time. Run it before the event, not during it.

### Products and their characteristics

| Property | MODIS | VIIRS |
| --- | --- | --- |
| Nominal resolution | \~1 km | \~375 m at nadir, growing off-nadir (bow-tie) |
| Platforms in FIRMS | Terra, Aqua | Suomi-NPP, NOAA-20, NOAA-21 |
| Overpass, daytime | Terra \~10:30, Aqua \~13:30 | \~13:30 ascending, all three within about an hour |
| Strengths | Long record from 1999/2002 | Small fires, large-fire perimeters, night performance |
| Known artefacts | — | Low-confidence night pixels in the South Atlantic Anomaly, removed from FIRMS NRT |

Source: [VIIRS I-Band 375 m Active Fire Data](https://www.earthdata.nasa.gov/data/instruments/viirs/viirs-i-band-375-m-active-fire-data), accessed 20 Oct 2026.

Your Aqua-only filter is well founded and should be kept and defended out loud. Aqua crosses at about 13:30 and so does Suomi-NPP, while Terra crosses at about 10:30. Mixing Terra into the reference would confound the sensor difference with a three-hour diurnal difference in burning activity, which matters enormously for agricultural fires lit in the afternoon.

### Suitability for your claims

The datasets support a claim about **detection counts**, and nothing more. An active-fire detection is a satellite observation of a thermal anomaly, not a confirmed wildfire, not a fire event, not burned area, and not severity. Three distinctions must appear in your submission text and in your presentation, because a remote-sensing judge will listen for them.

1. A rise in hotspot counts does not establish that fires increased. Your own control test demonstrates exactly this.
2. A detection is not an event. Several detections in adjacent pixels on one day may be one fire.
3. Absence of detection is not absence of fire. Cloud, overpass timing and algorithm sensitivity all suppress detections.

### Standard processing versus near-real-time

Your pipeline uses standard processing, which is the right choice for a historical record because it is the quality-controlled archive. The trade-off is latency: standard processing lags the present, and I could not verify by how much without a map key. **Check this first when you extend the window**, because it decides whether your record reaches mid-2026 or only 2025. The dynamic window now in `analysis/window.py` handles a short archive gracefully, since the monthly grid is built from the chunks actually downloaded, but you should know the real end date before you claim one.

If you add a live element, that element must use an NRT source and must be labelled near-real-time and provisional on screen. Do not mix NRT into the fitted record.

### Study area

**Keep the Chittagong Hill Tracts, but make the area selectable.** The three districts are defensible: jhum burning gives a strong, well-understood March–April signal, the district polygons are a real spatial gate rather than a bounding box, and local relevance supports a Local Impact argument at a Dhaka event. The weakness is that a fixed region answers a narrower question than the challenge appears to ask, and competing teams are offering any-area selection.

The practical resolution is to keep the CHT as the worked, validated example and add the ability to refit for another area on demand, with an honest label when the fit is weak. That gives you both the local story and the general tool without rebuilding anything.

### Data-quality checklist

- Confidence thresholds applied per sensor and published, with the alternative run as a sensitivity case. **Already done.**
- Duplicate collapse on coordinates, date, time and satellite. **Already done**, and the audit records that zero duplicate groups disagreed on confidence.
- Zero months kept inside coverage, NaN outside it. **Already done.**
- Coverage windows derived from the chunks actually downloaded, not assumed. **Already done.**
- Spatial gate by district polygon rather than bounding box. **Already done.**
- Day and night mix reported, with a day-only sensitivity run. **Already done.**
- Per-district counts, to test whether one district drives the whole fit. **Not done.** This is the main gap in the data work.
- Sensor-outage detection, so a delivery gap is not read as a quiet month. **Not done**, and it becomes important the moment you extend into the Suomi-NPP anomaly period of June 2026.

## 5. Competitive positioning

### What other teams are already building

Public repositories tagged to this challenge show a clear convergence, and several of the teams are Bangladeshi. This is verifiable competitive intelligence, not speculation, though I cannot know which teams will attend Dhaka or how finished their work is.

| Project | Approach | What it has that you do not |
| --- | --- | --- |
| [FireCal](https://github.com/samuelakosaonyejekwe/firecal) | Global 24-year calendar, 0.1° daily cells, local MODIS/VIIRS ratios shrunk toward a global prior, outage detection, NRT early warning | Any-area selection, per-cell calibration, out-of-sample error by country, "indicative only" labelling |
| [IGNIS](https://github.com/Hisernberg/ignis-public) | 26-year harmonised record, in-browser segmentation, five-model family, key-free on NASA GIBS | No API key needed, so no demo-day key risk |
| [Chronofire](https://github.com/shahedrayhan23/Chronofire) | Harmonisation engine plus burning-activity calendar, framed on removing the step change | The same core idea as yours, stated the same way |
| [kiln-watch](https://github.com/Aalvee-Aarham/kiln-watch) | Harmonised Bangladesh calendar with kiln and crop source separation | Bangladesh focus plus a source-attribution angle |

The lesson is uncomfortable but useful: **the harmonisation equation is not your differentiator, because everyone has one.** Several teams are also using the phrase "burning activity calendar", which suggests the official challenge text asks for something calendar-shaped. Confirm that against the official statement, because if it does, a dashboard that shows two charts and a map only partly answers it.

### Where you are genuinely ahead

Three things in your repository are rare and hard to copy in a weekend.

**Honest uncertainty.** A moving-block bootstrap, a published coefficient interval, a confidence-threshold sensitivity run and a day-only sensitivity run. Most teams will show a single number.

**A control test.** The MODIS-only continuity check is the cleanest proof in this whole problem space, and I have not seen another team present one. The instrument that never changed reads −23.1% across the boundary while the spliced series claims +185%. That is a complete argument in two numbers.

**Numbers that cannot drift.** Every figure on the page is generated from `metrics.json` and checked by an audit. If a judge asks where a number comes from, you can show the file and the test that enforces it.

### The positioning I recommend

> **BD-FireOps turns two incompatible NASA fire sensors into one continuous record for the Chittagong Hill Tracts, and is honest about how much of that repair is arithmetic and how much is science. It is built to survive the Suomi-NPP shutdown on 1 November 2026.**

This positioning works because it does not claim novelty you do not have. The equation is ordinary and you say so. The uncertainty work, the control test and the sensor-transition continuity are the contribution. A judge who has heard four teams claim a 95% improvement will remember the team that explained why that number is the wrong one to quote.

### What to add, and what to refuse

**Add, in this order:** the NOAA-20 leg, because it is the only feature that answers the 1 November shutdown and most competitors will still be fitting S-NPP only; per-district breakdown, because it tests your own fit spatially; and user-selectable area with an honest fit-quality label, because it closes the scope gap against the global tools.

**Refuse:** fire prediction or forecasting, risk scoring, cause classification, live alerting, and any machine-learning model family added for appearance. Each would need validation you cannot do in the time available, and each invites a question you cannot answer. A five-model comparison on a problem whose honest answer is a scalar is exactly the kind of thing a scientific judge punishes.

## 6. Compliance matrix

Status values are verified, partially verified, unverified or not satisfied. "Unverified" means I could not reach an official source, not that you are failing it.

| Requirement | Official source | Status | Evidence | Gap | Action | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Team registered and project submitted in the window | [spaceappschallenge.org/2026](https://www.spaceappschallenge.org/2026/) | Partially verified | Dates confirmed; your registration state unknown to me | Submission not yet drafted in portal | Draft the portal text now, paste on the day | Must |
| Project answers Challenge 9 as officially written | Challenge page, not machine-readable | **Unverified** | Could not fetch the statement | Framing may not match the official objectives | One member opens the page and checks every objective against your features | **Must, do first** |
| Uses NASA open data | FIRMS Area API | Verified | `data_source.json` records MODIS\_SP and VIIRS\_SNPP\_SP with row counts | None | Keep provenance visible on the page | Must |
| Data use correctly attributed | FIRMS, geoBoundaries | Verified | Footer credits FIRMS and geoBoundaries; geoBoundaries CC BY 3.0 recorded | None | Keep | Must |
| Open-source licence | Repository | Verified | `LICENSE` present | None | Confirm it is the licence you intend | Should |
| Rules on AI-generated work | Participant Guide / FAQ | **Unverified** | Not fetched | Your work is AI-assisted; disclosure expectations unknown | Read the guide and write an AI-use disclosure either way | Must |
| Rules on third-party APIs and libraries | Participant Guide / FAQ | **Unverified** | Not fetched | You vendor Leaflet and Chart.js and call Esri tiles | Confirm, and keep the offline fallback regardless | Should |
| Local judging format at Dhaka | Local event organisers | **Unverified** | Not published in reachable form | Demo length and format unknown | Ask organisers this week | Must |
| Demonstration works without reliable internet | Not a published rule | Verified by test | Offline fallback triggers; page renders with network blocked | None | Rehearse with wifi off | Must |
| Claims supported by evidence | Scientific expectation | Verified after repair | Both baselines, seasonal split and control test now published | Was not satisfied before this week | Keep both baselines in every surface | Must |
| Record continues past Suomi-NPP shutdown | [NASA Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026) | **Not satisfied** | Forward mapping is an algebraic inversion only | No NOAA-20 fit | Fit a NOAA-20 leg from `VIIRS_NOAA20_SP` | **Must** |
| Record is current | Scientific expectation | Not satisfied | Data ends 2021 | Five years missing | Re-run the pipeline with the dynamic window | Must |
| Spatial validity of the fit | Scientific expectation | Not satisfied | Region-wide monthly counts only | One district may drive the fit | Add per-district breakdown | Should |
| Any-area applicability | Possibly required by the challenge | Not satisfied | Fixed to three districts | Competitors offer any-area | Add area selection with fit-quality labelling | Should, Must if the challenge says so |

## 7. PRD, part one: what we are building and why

### 7.1 Executive summary

BD-FireOps reconstructs a single continuous active-fire detection record for the Chittagong Hill Tracts across the MODIS and VIIRS era, quantifies the uncertainty in that reconstruction, and carries the record forward across the Suomi-NPP shutdown. The hackathon release adds three things to the existing prototype: a current record, a NOAA-20 calibration leg, and a per-district view. It removes one thing: the claim that the correction is a large accuracy win.

### 7.2 Challenge alignment

The project addresses the harmonisation of MODIS and VIIRS hot spots by fitting an empirical relationship on the overlap period, validating it on unseen months, and publishing the corrected series with its uncertainty. **Alignment with the official objectives is unverified until a team member reads the challenge page.** If the statement asks for a burning-activity calendar or an any-area tool, add the area selector and a seasonality calendar view; both are achievable and the groundwork exists.

### 7.3 Title and value proposition

**BD-FireOps — a continuous, uncertainty-aware fire record for the Chittagong Hill Tracts, built to outlive its sensors.**

One sentence: BD-FireOps removes the false 2012 jump created by the switch from 1 km MODIS to 375 m VIIRS, says honestly how much of that repair is simple scaling, and keeps the record running after Suomi-NPP stops delivering on 1 November 2026.

### 7.4 Problem statement

The Chittagong Hill Tracts burn every March and April, driven by jhum shifting cultivation and forest clearing. Anyone asking whether burning is rising or falling over two decades must cross the 2012 sensor boundary, and crossing it naively produces a 185% step that is an artefact of pixel size. A forestry officer comparing this year with the 2000s, or a researcher fitting a climate trend, will reach a wrong conclusion unless the step is removed and the residual uncertainty is stated. The problem becomes acute in November 2026, when the sensor that half the record depends on stops transmitting and every ongoing analysis must switch platforms again.

### 7.5 Users and use cases

| User | Need | What they do with the output |
| --- | --- | --- |
| Bangladesh Forest Department, CHT divisions | Compare this season with a true long-run normal | Judge whether a season is unusual, not whether the satellite changed |
| Climate and land-use researchers | A consistent series to fit trends on | Use the harmonised series with its confidence interval, cite the limitations |
| District administration and disaster planners | Seasonal timing of burning by district | Plan awareness and patrol effort for the March–April window |
| Other harmonisation teams | A worked method with published uncertainty | Reuse the approach; the repository is open |

These are plausible users based on the data and the region. I have not interviewed any of them, and the PRD should not claim validated user demand.

### 7.6 Goals, success criteria and non-goals

**Goals.** A continuous record from 2002 to the most recent complete month. A published calibration with an uncertainty interval and an honest baseline comparison. Continuity across the S-NPP to NOAA-20 transition. A demonstration that works with no internet.

**Success criteria, each measurable.** The record's last month is within the archive's latency of today. A NOAA-20 leg is fitted and held-out tested, with its own error figures published. Per-district fits are published with their own error figures. Every number on the page is regenerated from `metrics.json` and the audit passes. The dashboard renders fully with the network disabled.

**Non-goals, stated so nobody asks.** Not a fire forecast. Not a risk model. Not a live alerting system. Not a cause classifier distinguishing jhum from kiln or forest fire. Not a burned-area or emissions product. Not a universal MODIS-to-VIIRS conversion valid outside this region.

### 7.7 Current state worth preserving

Keep the cleaning and aggregation pipeline, the district polygon gate, the Aqua-only reference filter, the zero and gap handling, the time-split validation, the moving-block bootstrap, the sensitivity runs, the generate-from-metrics discipline in `sync_web.py` and `sync_readme.py`, the end-to-end audit, and the dashboard shell. That is the majority of the repository, and it is sound.

## 8. PRD, part two: requirements

### 8.1 Priority classification

**Must have.** Current record to the archive edge. NOAA-20 calibration leg, fitted and held-out tested. Honest dual-baseline reporting everywhere. Seasonal split and control test on the page. Offline-safe demonstration. Regenerated, audited numbers.

**Should have.** Per-district fits with their own errors. A seasonality calendar view. User-selectable area with a fit-quality label. Sensor-outage detection in the monthly grid.

**Could have.** A near-real-time panel clearly labelled provisional. An export of the harmonised series as CSV. A short methods PDF.

**Won't have, this cycle.** Forecasting, risk scoring, alerting, cause classification, burned-area estimation, grid-cell matching, FRP-based calibration, overpass-angle modelling. Each is listed in the README as future work, which is the correct place for it.

### 8.2 Functional requirements

| ID | Requirement | Input | Processing | Output | Acceptance test | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Extend the record to the archive edge | FIRMS key, dynamic window | Download, clean, aggregate, refit | `monthly.csv` reaching the latest complete archived month | `data_source.json` end month is within archive latency of today; audit passes | Must |
| F2 | Fit a NOAA-20 leg | `VIIRS_NOAA20_SP` over the S-NPP overlap | Same fit procedure, own train/test split | `noaa20_model` in `metrics.json` with slope, interval and held-out error | Held-out RMSE and Spearman published; refuses to fit with under 24 overlap months | Must |
| F3 | Report both baselines everywhere | `metrics.json` | Scalar ratio scored beside the fitted model | Dual figures on page, README, portal text | Audit check fails if the scalar baseline is absent from the page | Must (**done**) |
| F4 | Publish the seasonal split | Held-out predictions | Score peak and quiet months separately | Two-row table plus median error | Audit check for both RMSE values on the page | Must (**done**) |
| F5 | Publish the MODIS-only control | Pre and post 2012 MODIS means | Compare against the spliced step | Control panel with three figures | Audit check that the control change is under 50% | Must (**done**) |
| F6 | Per-district fits | Clean detections with district label | Group by district, fit and test each | Per-district slope, interval, held-out error, fit quality | Three districts published; a district with too few months is labelled indicative | Should |
| F7 | Seasonality calendar | Harmonised monthly series | Bin by year and month into tiers | Year-by-month matrix | Matrix renders for every year in the record | Should (**partly exists**) |
| F8 | Area selection | User-drawn box or district choice | Refit on demand from cached detections | Series plus fit quality for that area | Returns a labelled result or an explicit "insufficient data" | Should |
| F9 | Outage detection | Monthly coverage and counts | Flag months where delivery gaps explain a low count | Flag in series, marked on chart | June 2026 S-NPP anomaly is flagged once data covers it | Should |
| F10 | Offline-safe map | Vendored polygons and cells | Fall back when tiles fail | Flat-background map with boundaries and detections | Page renders with network disabled | Must (**done**) |
| F11 | NRT panel | `VIIRS_NOAA20_NRT` | Fetch recent days, display only | Recent detections, labelled provisional | Panel shows a stale-data notice when the fetch fails | Could |
| F12 | Series export | Harmonised series | Serialise | CSV download | File opens with expected columns | Could |

### 8.3 Non-functional requirements

**Reliability.** The dashboard must render completely with no network. Every external call must have a disclosed fallback. No demonstration path may depend on a live API.

**Reproducibility.** One documented command sequence regenerates every published number. Dependencies pinned. A frozen window via `BDFIREOPS_STUDY_END` for citable runs. This is already satisfied.

**Usability.** Every metric on the page carries a plain-language label. Every uncertainty is shown as a range, not a point. Nothing is stated as a fire count without the word "detections" nearby.

**Performance.** Page interactive within three seconds from local files. Full pipeline re-run must complete overnight, not during judging.

**Accessibility.** Keyboard reachable controls, text alternatives on charts, contrast sufficient in both themes. Partly satisfied; worth a pass before the event.

**Security.** The FIRMS key stays in `.env`, never committed, never in the client bundle. Already satisfied.

**Deployment.** Static site, no server, no build step, deployable to Vercel and runnable from a local file. Already satisfied.

## 9. PRD, part three: method, interface and conduct

### 9.1 Data strategy

Acquisition uses the FIRMS Area API in 5-day chunks against the CHT bounding box, for four sources: `MODIS_SP` as the reference, `VIIRS_SNPP_SP` as the main calibration target, `VIIRS_NOAA20_SP` for the forward leg, and optionally `VIIRS_NOAA20_NRT` for a labelled live panel. Raw chunks are kept on disk so coverage is derived from what was actually fetched.

Cleaning applies the existing gates in order: confidence threshold per sensor, Aqua-only for MODIS, coordinate validity, district polygon containment, duplicate collapse, and the study-window clamp. Each gate writes its dropped-row count to the audit, which is what makes the pipeline defensible.

Aggregation produces regional monthly counts, and now also per-district monthly counts for F6. Zeros inside coverage are real zeros; months outside coverage stay empty.

Update strategy is a full re-run, because the archive is small and reproducibility matters more than speed. Run it twice before the event: once now, once in the final week.

### 9.2 Analytical method

The method is ordinary least squares on monthly counts over the overlap, fitted on the earlier years and tested on the later ones, with a moving-block bootstrap for the coefficient interval and a log1p variant as a zero-robustness check. Keep it. The sophistication belongs in the validation, not in the estimator.

Three additions. First, the scalar-ratio baseline is scored on every run, so the marginal gain is always visible. Second, the NOAA-20 leg repeats the whole procedure on the S-NPP and NOAA-20 overlap, producing a second published equation with its own interval and held-out error. Third, each district is fitted separately, and any district whose overlap is too short or whose fit is poor is labelled indicative rather than published as a result.

The chain of custody for the final series should be stated plainly on the page: observed Aqua MODIS before 2012, S-NPP VIIRS converted to MODIS-equivalent from 2012, and NOAA-20 VIIRS converted through the second leg once S-NPP ends. A reader must be able to see which sensor produced any given month.

### 9.3 Interface requirements

The existing sections stay: the dual chart, the control test, the validation panel, the map, the simulator, the seasonality matrix and the limits card. Four changes.

The hero must lead with the control test rather than the error reduction, because the control test is the stronger and more honest claim. The validation panel must show the scalar baseline beside the fitted model, which it now does. A sensor-provenance strip should run along the time axis, coloured by which instrument produced each month, so the two transitions are visible rather than described. The per-district view should be a small-multiples panel, three charts side by side, since that shows at a glance whether the correction behaves consistently.

Every chart needs a one-line reading underneath it in plain words. A judge walking past the screen should understand the point without the presenter.

### 9.4 Error handling and fallbacks

| Failure | Behaviour |
| --- | --- |
| Basemap tiles unreachable | Offline map mode with local polygons and detections, visible notice. **Implemented and tested.** |
| FIRMS API down or key rejected | Pipeline exits with a clear message; dashboard is unaffected because it reads committed files |
| NRT panel fetch fails | Panel shows last-successful timestamp and a stale notice, never silently blank |
| Partial download | Coverage derived from chunks; missing months stay empty rather than becoming zeros |
| Rate limit reached | Backoff and retry already implemented; chunking stays within 5 days |
| Venue has no internet at all | Entire demonstration runs from local files; this is the default, not a fallback |

### 9.5 Responsible use and uncertainty

Four statements belong in the submission and in the talk. A detection is an observation, not a confirmed fire. A count is not an area and not a severity. No detection does not mean no fire. The calibration is regional and does not transfer without refitting.

There is a fifth, specific to your region. Jhum cultivation is a livelihood practice of indigenous communities in the Chittagong Hill Tracts. The project reports detections, and must not be framed in a way that reads as attributing blame or as supporting enforcement against those communities. Say what the data shows and stop there.

Privacy is not a significant concern, since all data is satellite-derived and public, and no personal data is collected. The site sets no cookies and loads no third-party analytics, which is worth stating in one line.

### 9.6 Deployment

Static files served from Vercel, with the same files runnable by opening `index.html` directly or through a local Python server. No backend, no database, no API key in the client. The entire deployment story is a strength for a hackathon: there is nothing to break on stage.

## 10. Prioritised features with acceptance criteria

Each feature below names the user problem, the processing, the dependency and the test that proves it works. Drop from the bottom if time runs short.

**P1 — Current record (F1).** The problem is that a record ending in 2021 cannot speak about 2026. Input is the FIRMS key and the dynamic window; processing is the existing four-stage pipeline; output is a record reaching the archive edge. Depends on nothing but the key. **Accepted when** `data_source.json` reports an end month consistent with archive latency, the audit passes, and the page's coverage tile updates itself. Failure point: archive latency may be longer than expected, so check `data_availability` first.

**P2 — NOAA-20 leg (F2).** The problem is that S-NPP stops delivering thirteen days before the hackathon. Input is `VIIRS_NOAA20_SP` across the S-NPP overlap; processing repeats the fit with its own split and bootstrap; output is a second equation with its own held-out error. Depends on P1's download machinery. **Accepted when** the second equation, its interval and its held-out RMSE and Spearman appear in `metrics.json` and on the page, and the code refuses to fit on fewer than 24 overlap months. This is the highest-value new feature in the whole plan.

**P3 — Sensor-provenance strip.** The problem is that a reader cannot tell which instrument produced a given month. Input is the harmonised series; processing is a per-month sensor label; output is a coloured band along the time axis with a legend. Depends on P2 for the third colour. **Accepted when** every month carries exactly one sensor label and the two transition points are visible without explanation.

**P4 — Per-district fits (F6).** The problem is that a region-wide fit hides whether the correction works everywhere. Input is detections labelled by district; processing is three separate fits with their own tests; output is three small charts with their own error figures. **Accepted when** each district publishes a slope, an interval and a held-out error, and any district with insufficient overlap is labelled indicative rather than reported.

**P5 — Area selection (F8).** The problem is that the tool answers one area while the challenge may ask for any. Input is a drawn box or a district choice; processing refits from cached detections; output is a series with a fit-quality label. **Accepted when** an area with adequate data returns a labelled fit and an area without returns an explicit refusal rather than a bad number.

**P6 — Outage detection (F9).** The problem is that a delivery gap looks like a quiet month. Input is coverage and counts; processing flags months where a gap explains a low count; output is a marker on the chart. **Accepted when** the June 2026 S-NPP anomaly is flagged automatically once the data covers it.

**P7 — NRT panel (F11).** The problem is that judges respond to live data. Input is `VIIRS_NOAA20_NRT` for the last few days; processing is display only, never fitting; output is a panel labelled provisional with a timestamp. **Accepted when** a failed fetch shows a stale notice rather than an empty panel, and the label never claims the data is harmonised. Drop this first if time is short.

**P8 — CSV export (F12).** Smallest and least important. **Accepted when** the file opens with the expected columns.

### Drop order under time pressure

P8, then P7, then P6, then P5. Never drop P1 or P2. If you reach the final week with only P1 and P2 done plus the repairs already made, you still have a coherent, honest and defensible submission.

## 11. Architecture and data pipeline

&#91;embedded content: BD-FireOps pipeline · 6 stages, one audit gate\]

Nothing on the dashboard is hand-written: the sync tools regenerate it from `metrics.json`, and the audit refuses to pass if the two disagree. Keep that property while adding features, because it is what lets you answer "where does that number come from?" in one move.

### Component responsibilities

`analysis/window.py` owns the study window and nothing else, so the end date is defined once rather than in four files. `analysis/download.py` talks to FIRMS in 5-day chunks with backoff, and writes raw chunks whose filenames define coverage. `analysis/clean.py` applies every quality gate and writes an audit of what each gate dropped. `analysis/aggregate.py` turns detections into the monthly grid, keeping the distinction between a real zero and no data. `analysis/model.py` fits, bootstraps, tests and writes `metrics.json`. The `tools/` scripts regenerate the web and README surfaces and then verify them.

The frontend is deliberately plain: one static page, vendored Leaflet and Chart.js, no build step, no framework, no backend. For a hackathon this is an advantage, because there is nothing to install on the judging machine and nothing to fail on stage.

### Where the new work lands

The NOAA-20 leg is a second source in `download.py`, a second series through `clean.py` and `aggregate.py`, and a second fit block in `model.py` writing a `noaa20_model` key. The per-district work is a grouping change in `aggregate.py` and a loop in `model.py`. Both extend the existing shape rather than replacing it. No new service, no database, no architectural change is needed for anything in this PRD.

## 12. Live demonstration and fallbacks

### What is live and what is not

Be precise about this on screen, because claiming a replay is live is the fastest way to lose a scientific judge's trust.

| Element | Status | Label on screen |
| --- | --- | --- |
| Harmonised 2002–present record | Precomputed from the standard-processing archive | "NASA FIRMS archive, standard processing, as of \<date>" |
| Fitted models and intervals | Precomputed, reproducible from the repository | "Fitted on 2012–2018, tested on unseen months" |
| Map detections | Precomputed aggregate cells | "Aggregated detections, 0.05° cells" |
| Simulator | Computed live in the browser from the published coefficients | "Computed now from the fitted model" |
| NRT panel, if built | Genuinely live fetch | "Near-real-time, provisional, not harmonised" |

The simulator is your honest live element: it really does compute, in front of the judge, from the published coefficients and their bootstrap interval. That is enough. Do not dress up a replay as a live feed.

### Four-minute demonstration script

| Time | Screen | What you say |
| --- | --- | --- |
| 0:00–0:35 | Hero and control-test panel | "Two NASA sensors watched these hills for twenty-four years. Join them raw and fires appear to triple in 2012. Here is how we know they did not: Aqua MODIS flew across the whole period unchanged, and its own record falls 23 per cent. The camera that did not change saw no jump." |
| 0:35–1:15 | Chart A to Chart B toggle, sensor-provenance strip | "The step is the pixel size, 1 km against 375 m. We fit the relationship on the overlap years and rebuild the record on one footing. The strip shows which instrument produced each month." |
| 1:15–2:00 | Validation panel with both baselines | "We will be straight about the size of this. Against an unscaled splice the error falls 95 per cent, but nobody splices raw counts. Against simple scaling, our fitted line gains 1.7 per cent. The value is not the number. It is that the calibration is regional, carries a bootstrap interval, survives two sensitivity tests, and was validated on months the model never saw." |
| 2:00–2:40 | Seasonal split and per-district panel | "Accuracy is seasonal, and we show it. Six burning months carry an RMSE of 136; the other thirty carry 3.4 against a median error of 1.3 detections. Here is the same fit in each district separately." |
| 2:40–3:20 | NOAA-20 section | "Suomi-NPP stopped delivering on the first of November, thirteen days ago. Every analysis built on it breaks now. We fitted a second leg against NOAA-20 on their overlap, so the record continues. This is the part that matters after today." |
| 3:20–4:00 | Simulator and limits card | "Enter any VIIRS count and the model answers with a range, not a magic number. And here is what we do not claim: these are detections, not confirmed fires, not burned area. A detection missing does not mean no fire. The calibration is for these three districts." |

If you are given less time, cut the simulator and the district panel, and keep the control test, the honest baseline and the NOAA-20 leg. Those three carry the submission.

### Fallback plan

Run the whole demonstration from local files on your own laptop, with the wifi switched off deliberately, and say so. "We turned the network off, because a fire record should not depend on a venue's wifi" is a stronger line than apologising for a grey map. Keep a second laptop with the same folder, a USB copy of the repository, a PDF of the key screens, and a short screen recording of the full flow. If the projector fails, the PDF carries the argument.

If you build the NRT panel and the fetch fails on stage, the panel must show its last-successful timestamp and a stale notice. Point at it and move on. A visible, honest failure costs you nothing; a blank panel you cannot explain costs you the demonstration.

## 13. Execution roadmap

Ordered by dependency, not by date. Group A is already complete. Work down the list and stop wherever the time runs out; everything below group B is optional.

### Group A — corrections to the existing project (**done**)

| ID | Task | Files | Status |
| --- | --- | --- | --- |
| A1 | Scalar-ratio baseline scored and published | `model.py`, `sync_web.py`, `sync_readme.py` | Done, audited |
| A2 | Seasonal split and median error | `model.py`, `index.html` | Done, audited |
| A3 | MODIS-only control test section | `model.py`, `sync_web.py`, `index.html` | Done, audited |
| A4 | Offline map fallback and webfont removal | `app.js`, `style.css`, `index.html` | Done, tested headless |
| A5 | Dynamic study window | `analysis/window.py` and three callers | Done, tests updated |
| A6 | Forward mapping published with caveat | `model.py`, `index.html`, README | Done |

### Group B — minimum viable submission

**B1. Read the official challenge statement.** No dependency. Output: a written note confirming your features answer each stated objective, or a list of what is missing. **Do this before anything else.** Failure point: the statement may ask for an any-area tool, which promotes P5 from Should to Must.

**B2. Check archive latency.** Depends on your map key. Query the FIRMS data-availability endpoint for `MODIS_SP`, `VIIRS_SNPP_SP` and `VIIRS_NOAA20_SP`, and record the real end dates. Output: three dates. Failure point: the standard-processing archive may end earlier than you hope, which is fine but must be stated rather than discovered on stage.

**B3. Re-run the full pipeline.** Depends on B2. Files: no code change needed. Output: record extended to the archive edge, all artefacts regenerated, audit passing. Test: `python tools/e2e_audit.py` and `python tests/test_pipeline.py` both clean, and the page's coverage tile updates itself. Failure point: a long download; start it overnight. Fallback: keep the 2021 artefacts committed on a branch so you always have a working build.

**B4. Fit the NOAA-20 leg.** Depends on B3. Files: `download.py`, `clean.py`, `aggregate.py`, `model.py`, `sync_web.py`, `index.html`, plus new audit checks. Output: a second equation with its own interval and held-out error. Test: the leg refuses to fit with fewer than 24 overlap months, and its figures appear on the page. Failure point: the S-NPP and NOAA-20 overlap may be short or noisy in this small region. Fallback: publish the attempt with its honest error figures and say the overlap is too short for a confident fit. **A negative result, clearly reported, is still a strong answer to the shutdown.**

**B5. Sensor-provenance strip.** Depends on B4. Files: `app.js`, `sync_web.py`. Output: a coloured band showing which instrument produced each month. Test: every month has exactly one label.

**B6. Rewrite the submission text and video script.** Depends on B4. Output: portal text, a four-minute script, and the limits card, all consistent with the dual-baseline framing. Test: read it aloud and check no sentence claims a 95% improvement without naming the baseline.

### Group C — differentiating features

**C1. Per-district fits.** Files: `aggregate.py`, `model.py`, `sync_web.py`. Test: three districts each publish slope, interval and held-out error; insufficient districts are labelled indicative. This is the best value-per-hour item in group C.

**C2. Area selection with fit-quality labelling.** Files: `app.js`, plus a precomputed per-cell aggregate. Test: adequate areas return a labelled fit, inadequate areas return a refusal. Promote to group B if B1 shows the challenge asks for any-area.

**C3. Outage detection.** Files: `aggregate.py`, `model.py`. Test: the June 2026 S-NPP anomaly is flagged automatically.

### Group D — demonstration and deployment

**D1. Offline rehearsal.** Switch the wifi off and run the whole four minutes. Fix whatever breaks. Do this at least twice, and once on the second laptop.

**D2. Demo kit.** Second laptop with the repository, USB copy, PDF of key screens, screen recording of the full flow, printed one-page summary with the three headline numbers.

**D3. Deploy and verify.** Push to Vercel, open the public URL on a phone, confirm the layout holds at phone width and the offline fallback still works on a throttled connection.

### Group E — validation and submission

**E1. Full test pass.** `test_pipeline.py`, `e2e_audit.py`, `sync_web.py --check`, `sync_readme.py --check`, all clean on the final artefacts.

**E2. Claim sweep.** Read every sentence in the README, the portal text, the summary and the dashboard, and check each number against `metrics.json`. The audit does most of this, but prose claims it cannot see are where overstatement hides.

**E3. Submit early.** The window opens on 14 November at 09:00 and closes on 15 November at 23:59 local time. Submit a complete version on the Saturday evening and improve it on Sunday. Teams lose on deadline mechanics more often than on quality.

**E4. Participant survey** by 30 November 2026.

## 14. Evaluation and testing

### Baselines you must report

Three, always together. The unscaled splice, which is the error being illustrated. The scalar ratio, which is the honest competitor. The fitted model. Reporting the first and third alone is what made the original claim indefensible, and the audit now fails if the scalar baseline is missing from the page.

For the NOAA-20 leg, the same discipline applies: report its scalar baseline too. If the leg does not beat simple scaling there either, say so.

### Metrics and how to read them

| Metric | Why it is reported | Known weakness |
| --- | --- | --- |
| RMSE | Comparable with the baselines | Dominated by the burning peak |
| Bias | Shows systematic over- or under-correction | Can look good while monthly errors are large |
| MAE and median error | Median shows the typical month | Median is near zero because most months are quiet |
| R² | Conventional, expected by judges | Flattered by seasonal variance; never report alone |
| Spearman | Robust to the skew, tests ordering | Says nothing about magnitude |
| Seasonal split | Shows where the error actually lives | Only six peak months in the current test set |

### Test layers

**Functional.** `tests/test_pipeline.py`, 28 checks on synthetic fixtures covering the confidence gate, the Aqua filter, the region gate, the duplicate rule, the window clamp, the coverage logic and the zero-versus-NaN distinction. Extend it when the NOAA-20 leg lands.

**Data quality.** The clean audits record every dropped row by reason. Add two checks: that per-district counts sum to the regional count, and that no month inside coverage is silently missing.

**Analytical.** The held-out test, the two sensitivity runs, the bootstrap, and a leave-one-year-out refit, which is worth adding because it shows the coefficient's stability across years in one table rather than one interval.

**Consistency.** `e2e_audit.py`, now 48 checks, plus `--check` on both sync tools in CI. This is the layer that stops the dashboard drifting from the data.

**Usability.** Give the page to someone who has not seen it and ask three questions: what is the problem, what did this team do, and what do they not claim. If any answer takes more than a few seconds to find, the page is wrong, not the reader.

**Demonstration.** The offline rehearsal is a test, not a formality. Run it headless as well, which I have done once already, and run it on the actual laptop you will present from.

### Reproducible experiment record

Freeze a citable run with `BDFIREOPS_STUDY_END` and record, for that run, the window, the row counts, the fitted coefficients with intervals, every baseline, the seasonal split and the sensitivity deltas. That record is what lets a judge or a reviewer repeat your work, and it already exists in `metrics.json`. Keep it that way.

## 15. Presentation, submission and three-reviewer assessment

### The narrative that should win you attention

Lead with the control test, not the error reduction. "The camera that never changed saw no jump" is a complete scientific argument in nine words, and no other team on this challenge appears to be making it. Follow with the honest baseline, because volunteering your own weakness before a judge finds it converts a liability into evidence of rigour. Close with the NOAA-20 leg, because it is the only part that is about the future rather than the past, and because the shutdown happened two weeks before you speak.

Three numbers should be the only ones a judge needs to remember: −23.1% for the unchanged sensor, +185% for the wrong join, and 1.7% for what your equation actually adds.

### Submission text

Write it before the event and paste it on the day. State the challenge, the region, the method in two sentences, the validation, and the limitations. Name the data sources with their exact FIRMS identifiers. Include the repository link, the deployed link, and an explicit note on AI assistance. Do not put a 95% figure in the first paragraph.

### Reviewer A — challenge alignment

**Strongest.** The topic is squarely within the challenge, the NASA data is genuine and properly attributed, the work is open source and reproducible, and the deployment needs nothing from the organisers.

**Unresolved.** Nobody on the team has verified the project against the official challenge statement, which I could not fetch. The Dhaka local judging format is unknown. The 2026 rules on AI-generated work have not been read, and this project is heavily AI-assisted.

**Mandatory.** Read the challenge page and the participant guide this week. Write an AI-use disclosure regardless of what the rules require. Ask the Dhaka organisers about demo length and format.

### Reviewer B — remote sensing and scientific validity

**Strongest.** The Aqua-only filter is correctly motivated by overpass timing. Zero and gap handling is careful. The held-out split is genuine. The bootstrap is the right kind for seasonal data and is correctly labelled. The control test is excellent and is the strongest piece of evidence in the project.

**Unresolved.** The fit is region-wide, so it is untested spatially; one district could be driving everything. There is no outage detection, which will matter once the record crosses the June 2026 anomaly. The forward mapping is an algebraic inversion presented alongside fitted models, and although it is labelled, a careless reader may take it as validated. The record is still monthly counts, which is the correct scope but a coarse one.

**Mandatory.** Add per-district fits. Keep the detection-is-not-a-fire language prominent. Either fit the NOAA-20 leg properly or state clearly that the forward direction is unvalidated. Never present R² without the seasonal split beside it.

### Reviewer C — hackathon judge and product engineer

**Strongest.** It runs, it is fast, it needs no backend, it survives a dead network, and every number is traceable to a file. The dashboard is more finished than most hackathon output.

**Unresolved.** The user value is still implicit. Nobody has talked to a forest officer, and the page does not show a decision anyone would make differently because of this tool. Several competing teams offer any-area selection and a calendar framing, which may match the challenge better. The live element is thin: one in-browser calculator.

**Mandatory.** Add one concrete decision example to the page, worked end to end: a specific season compared against the corrected normal instead of the raw one, with the two conclusions side by side. That single addition converts a method demonstration into a tool. Decide on area selection once B1 is answered.

### Resolving the disagreement

Reviewer B wants more scientific depth, Reviewer C wants more user value, and they compete for the same hours. The resolution is that B's per-district work also serves C, because a district-level answer is what a district officer would act on. Build C1 and present it as both. Reviewer A's items cost almost no build time and gate everything else, so they come first. The order stands as written in the roadmap: verify the challenge, extend the data, fit NOAA-20, then per-district, then the worked decision example.

## 16. Go or no-go checklist

### Definition of done

The submission is ready when every line below is true. Tick them in order; the first five are non-negotiable.

- [ ] A team member has read the official Challenge 9 statement and confirmed in writing that the features answer its objectives
- [ ] The record reaches the archive edge, and the end date on the page matches `data_source.json`
- [ ] The NOAA-20 leg is either fitted and tested, or its failure is stated with its error figures
- [ ] Every surface reports both baselines, and no sentence claims a 95% improvement without naming the baseline
- [ ] The dashboard renders completely with the network switched off, rehearsed on the presenting laptop
- [ ] `test_pipeline.py`, `e2e_audit.py` and both `--check` runs pass on the final artefacts
- [ ] The control test, the seasonal split and the limits card are all visible without scrolling past three screens
- [ ] Per-district fits are published, or their absence is listed as a limitation
- [ ] The AI-use disclosure is written and matches whatever the participant guide requires
- [ ] Portal text, video script and repository README tell the same story with the same numbers
- [ ] Demo kit assembled: second laptop, USB copy, PDF of key screens, screen recording
- [ ] A complete version submitted on Saturday evening, before any Sunday improvements
- [ ] Participant survey completed by 30 November 2026

### Stop conditions

Stop and reconsider the plan if any of these is true at the start of the hackathon weekend. The challenge statement asks for something structurally different, such as a global calendar, in which case promote area selection and seasonality to Must and cut the district work. The NOAA-20 overlap proves too short for a usable fit, in which case present the attempt honestly and lean harder on the control test. The archive latency turns out to be long, in which case say so plainly and show the archive edge on the page rather than implying currency you do not have.

### What I could not verify

The official Challenge 9 statement, the 2026 judging criteria, the Dhaka local event arrangements, the 2026 rules on AI-assisted work, and the current latency of FIRMS standard processing. Each is marked unverified in the compliance matrix, and each is answerable by your team in under an hour. Do those first.

## Sources

- [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/2026/) — dates, theme, submission window, survey deadline. Accessed 20 October 2026.
- [NASA Space Apps 2025 Awards](https://www.spaceappschallenge.org/2025/awards/) — global award categories and the nomination path. Historical, 2025.
- [FIRMS Area API documentation](https://firms.modaps.eosdis.nasa.gov/api/area/) — source identifiers, day-range limit, rate limits. Accessed 20 October 2026.
- [VIIRS I-Band 375 m Active Fire Data](https://www.earthdata.nasa.gov/data/instruments/viirs/viirs-i-band-375-m-active-fire-data) — product names, resolution, overpass times, detection characteristics. Accessed 20 October 2026.
- [Suomi NPP Data Product Delivery to Cease on November 1, 2026](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026) — NASA Earthdata notice.
- [Cessation of S-NPP data to users on or after November 2, 2026](https://www.nesdis.noaa.gov/news/cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-onafter-november-2-2026) — NOAA NESDIS notice.
- [Suomi NPP VIIRS Data Outage / Anomaly on June 1, 2026](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-outage-anomaly-june-1-2026) — relevant once the record extends into 2026.
- Competing public repositories for this challenge: [FireCal](https://github.com/samuelakosaonyejekwe/firecal), [IGNIS](https://github.com/Hisernberg/ignis-public), [Chronofire](https://github.com/shahedrayhan23/Chronofire), [kiln-watch](https://github.com/Aalvee-Aarham/kiln-watch), [firelens](https://github.com/shahmirkhan106/firelens). Accessed 20 October 2026; their descriptions are their authors' claims, not verified results.
- The project audit figures come from executing your own repository at `D:\Downloads\Nasa` on 20 October 2026, not from any external source.
