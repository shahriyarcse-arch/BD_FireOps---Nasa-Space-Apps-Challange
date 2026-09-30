# BD-FireOps MVP Plan v3 (30 Sep 2026 porjonto verified, review corrections soho)

**Challenge:** Harmonization of MODIS and VIIRS Hot Spots ([official page](https://www.spaceappschallenge.org/2026/challenges/harmonization-of-modis-and-viirs-hot-spots/))
**Hackathon:** 14-15 Nov 2026. Submission 14 Nov 9:00 AM theke 15 Nov 11:59 PM local ([official](https://www.spaceappschallenge.org/2026/))
**Title:** BD-FireOps: An Uncertainty-Aware MODIS-VIIRS Fire Record for Bangladesh CHT
**Claim (eta bolbe):** "Region-specific, held-out tested harmonization prototype for Bangladesh CHT."
**Claim (eta bolbe na):** global solution, universal conversion, fire cause, "fire nai".

---

## 0. Rule (age eta)

NASA FAQ onujayi participants ra hackathon shuru holei actual kaj shuru korbe ([FAQ](https://legacy.spaceappschallenge.org/resources/faq/), [NASA organizer reply](https://github.com/nasa/spaceapps/discussions/1273)). Ei year er rulebook ami dekhte pari ni, tai 2026 Participant Guide o local lead theke confirm koro. Code share korte hobe, pre-existing library disclose korte hobe.

**Ekhon korte paro:** NASA account + Dhaka event select, team role, MAP_KEY, data dictionary pora, wireframe, pitch outline, AIUB venue confirm.
**Default dhoro rule ta ei year o lagu:** real regression output, trained model, final chart, processed NASA result hackathon shuru holei toiri hobe. Generic utility/downloader code age likhbe kina, ta 2026 Participant Guide ba local lead er lekha uttor dekhe thik koro. Guide hate na pawa porjonto shobcheye safe path hoilo kichu na likha.
README te likhe rakho: "The team followed the 2026 Participant Guide and local organizer instructions. Pre-existing libraries and AI tools are disclosed."

## 1. Verified facts

| Fact | Source |
|---|---|
| MODIS C6.1: Terra 1 Nov 2000, Aqua July 2002 | [FIRMS](https://firms.modaps.eosdis.nasa.gov/active_fire/) |
| VIIRS S-NPP 20 Jan 2012, NOAA-21 17 Jan 2024. NOAA-20 date duita page e alada, `data_availability` diye check | [Archive](https://firms.modaps.eosdis.nasa.gov/download/) |
| VIIRS choto fire beshi dhore | [Schroeder 2014](https://www.sciencedirect.com/science/article/abs/pii/S0034425713004483) |
| VIIRS FRP boro boreal fire e ~47% kom, choto fire e beshi | [Li 2018](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2017JD027823) |
| Terra end-of-science Feb 2027, Aqua Sep 2027 | [NASA](https://science.nasa.gov/science-research/earth-science/terra-the-end-of-an-era/) |
| **S-NPP delivery 1 Nov 2026, 13:00 UTC e bondho** | [NOAA](https://www.nesdis.noaa.gov/news/cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-onafter-november-01-2026) |
| S-NPP gap: [1 June](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-outage-anomaly-june-1-2026), [10 July 2026](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-outage-anomaly-july-10-2026) | Earthdata |
| BD te 2003-2021 e 54,669 MODIS hotspot, mainly CHT hill forest e | [Farukh et al.](https://www.osti.gov/pages/servlets/purl/2424866) |
| CHT range 21°25'-23°45' N, 91°54'-92°50' E | [figure](https://www.researchgate.net/figure/a-Map-of-the-forest-areas-of-Bangladesh-compiled-from-MODIS-Terra-Aqua-16-day_fig1_366752100) |

Motivation likhbe continuity o artificial jump diye. MODIS shutdown context hishebe.

## 2. Scope lock

**Korbe:** CHT, monthly hotspot count, Aqua MODIS reference, S-NPP VIIRS, overlap 2012-2021, simple linear + log1p model, time-split validation, bootstrap coefficient uncertainty, Streamlit dashboard.
**Korbe na:** FRP calibration, burned area, Punjab/California, land-cover, orbit matching, fire cause, real-time API, full 2000-2026 validated record.
**Optional display (model fit e use korbe na):** 2022-2026, S-NPP cutoff/gap marker soho.
**Stretch (somoy thakle):** district-wise view (Bandarban, Rangamati, Khagrachhari), NOAA-20 refit, Terra+Aqua sensitivity.

## 3. Data

| Ki | Link |
|---|---|
| Archive download (main route) | https://firms.modaps.eosdis.nasa.gov/download/ |
| MAP_KEY | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| Area API | https://firms.modaps.eosdis.nasa.gov/api/area/ |
| Data availability | https://firms.modaps.eosdis.nasa.gov/api/data_availability/ |
| Python example | https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html |
| Attributes | https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs |
| Backup: Earth Engine FIRMS | https://developers.google.com/earth-engine/datasets/catalog/FIRMS |
| Readme (file naming) | https://firms.modaps.eosdis.nasa.gov/download/Readme.txt |

Sources: `MODIS_SP`, `VIIRS_SNPP_SP`. API: `/api/area/csv/[MAP_KEY]/[SOURCE]/[w,s,e,n]/[DAY_RANGE]/[DATE]`, limit 5000 transaction / 10 min. Day range 1-5 din, tai loop 5-din chunk e (7 din er ekta mention o ache, ami sure na). Hackathon e prothome 1 din test, status code ar column print, tarpor 5 din chunk. Downloader e `response.raise_for_status()` ar empty-response check (`if not response.text.strip()`) rakho. **Earth Engine data ar FIRMS CSV ekoi model e mishabe na**, product characteristics alada.

**Bounding box:** `91.9,21.4,92.9,23.8` (paper er CHT range theke rounded). District boundary polygon file pele oita diye filter koro (source ami verify kori ni). Na pele README te likho: "approximate bounding box used for prototype."

**Archive request 14 Nov e hackathon shuru holei pathao.** Email e ashte somoy lage, tai parallel e API chunk loop chalao.

## 4. Process (hackathon er 48 ghonta)

| Somoy | Kaj | Output |
|---|---|---|
| 0-1h | Repo structure, `.env` (MAP_KEY), `.gitignore`, archive request | folder ready |
| 1-4h | Downloader, schema check, region filter | `data/raw/*.csv` |
| 4-8h | Cleaning, confidence, duplicate, monthly aggregation | `monthly.csv` |
| 8-14h | Regression, time split, metrics | `metrics.json` |
| 14-20h | Bootstrap, sensitivity, splice charts | PNG charts |
| 20-30h | Streamlit dashboard | working app |
| 30-38h | README, architecture diagram, screenshots | docs |
| 38-44h | Demo video, project page draft | video |
| 44-48h | Test, submit, **buffer** | submitted |

**Cutoff rule:** 24 ghontar moddhe validated result na ashle dashboard chere shudhu chart + report submit koro.

**Jodi effective somoy matro ~8 ghonta hoy:**

| Somoy | Must-have |
|---|---|
| 0-1h | API test, column check, **Aqua filter verify** |
| 1-3h | Download |
| 3-5h | Clean + monthly aggregation |
| 5-6h | Train/test model + metrics |
| 6-7h | 3 chart (+ Streamlit jodi validated chart ashe) |
| 7-8h | README, demo, backup |

Dashboard shuru korar age 6 ghontar moddhe validated chart na pele dashboard baad. Chart + README + metrics diye o submission hoy.

## 5. Method

**Structure**
```
bd-fireops/
├── data/raw/  data/processed/
├── analysis/  (download.py, clean.py, aggregate.py, model.py)
├── dashboard/app.py
├── README.md  requirements.txt  .env  .gitignore
```

**Cleaning** (actual column name CSV theke check koro)
- MODIS: `confidence >= 30`
- VIIRS: `confidence` l/n/h, `l` baad (baseline). Sensitivity run e sob rakho
- `acq_date` UTC, invalid coordinate baad, duplicate baad
- FRP rakho, model e use korbe na

**Reference sensor (gate):** `MODIS_SP` te Terra ar Aqua dutoi thakte pare. Age downloaded CSV te `satellite` / `instrument` column dekho, tarpor `df["satellite"].astype(str).str.upper().str.contains("AQUA")` diye filter koro. **Aqua filter verify na kore model fit korbe na.** Filter na hole scope bodlao ar README te likho "Terra/Aqua combined MODIS reference". Filter hole likho: "Aqua was used as reference only after filtering by satellite metadata." Terra+Aqua sensitivity run rakho.

**Aggregation:** monthly regional count. README e likho: "regional monthly counts, not paired fire-level detections."

**Model:**
```python
import numpy as np
from sklearn.linear_model import LinearRegression

train = ov[ov.month < "2019-01"]
test  = ov[ov.month >= "2019-01"]

m = LinearRegression().fit(train[["viirs"]], train["modis"])
test = test.assign(harm=m.predict(test[["viirs"]]).clip(0))

# log1p variant
ml = LinearRegression().fit(np.log1p(train[["viirs"]]), np.log1p(train["modis"]))
test["harm_log"] = np.expm1(ml.predict(np.log1p(test[["viirs"]]))).clip(0)
```
Train 2012-2018, test 2019-2021. Je variant held-out RMSE te bhalo ar jar negative prediction nai tai rakho. Duita kachakachi hole linear rakho, explain kora sohoj.
**Zero month:** fit er age `describe()` ar `isna().sum()` dekho. Zero month baad dibe na, rakho, log1p model use koro, README te zero-count handling likho.
Coefficient ke "true MODIS conversion" bolbe na. Bolbe "fitted regional empirical relationship".

**Uncertainty (coefficient):** bootstrap 500 bar train resample, slope/intercept er 2.5-97.5 percentile. Dashboard e alada label: "Bootstrap coefficient interval" ar "Held-out test error". Duita ek jinis na, prediction interval bolbe na. Sathe confidence-threshold sensitivity.

**Metrics:** bias, MAE, RMSE, R², Spearman, raw VIIRS vs harmonized, test period e. `metrics.json` e save koro.
```python
import json
json.dump({"raw_rmse": r1, "harm_rmse": r2, "raw_bias": b1, "harm_bias": b2}, open("data/processed/metrics.json","w"))
```

**Challenge er main chart (Luna er plan e chilo na):**
- Chart A: Aqua 2002-2011 + raw VIIRS 2012+. Label: "Illustrative raw sensor splice, not a continuous fire estimate."
- Chart B: Aqua 2002-2011 + harmonized VIIRS 2012+. Vertical marker 2012 e. Label: "2002-2011 observed Aqua MODIS; 2012-2021 VIIRS converted to MODIS-equivalent." Model 2012-2018 theke fit, pre-2012 e apply hoy na.
- Seasonality, missing observation ar overpass difference thakay chart ta proman na, illustration.
Jump thakbe kina data bolbe. Na thakle ba kom hole seta likho, ja ashe tai.

## 6. Dashboard (Streamlit)

Tab: Raw / Naive vs Harmonized splice / Validation.
Metric `metrics.json` theke load. `df.attrs` use korbe na (CSV te save hoy na).
Footer note: "Non-detection does not prove absence of fire. Model is region- and period-specific."
Local browser demo ok, deploy dorkar nai.

## 7. AI use

File-by-file: downloader, cleaner, aggregator, model, charts, dashboard. Prottek step e first 5 row, column name, actual error dao. MAP_KEY kokhono paste korbe na. AI er output number nijer chokhe verify koro. Pre-existing library gulo README e disclose koro.

## 8. README te ja thakbe

Problem, study area, data (NASA FIRMS MODIS + VIIRS S-NPP, citation), method, validation, limitation, future work (grid matching, overpass timing, FRP, NOAA-20/21 refit, burned-area validation), code sharing, AI tool disclosure.
**Limitation e likhbe:** S-NPP delivery 1 Nov 2026 e shesh, tai model refit lagbe NOAA-20/21 diye. Sathe S-NPP er 2026 gap.

**Claim wording:** "BD-FireOps is a region-specific, held-out-tested harmonization prototype for estimating MODIS-equivalent monthly fire activity from VIIRS observations in an approximate Bangladesh CHT study area."
**Not a claim:** "Not a universal MODIS-VIIRS conversion, a fire-cause classifier, or proof of fire absence."
**Method limitation:** "Regional monthly counts, not paired fire-level detections. No overpass-time, scan-angle, exact administrative boundary, land-cover or FRP modeling."
**Data limitation:** "FIRMS reports positive detections. A missing detection may reflect cloud, viewing geometry, algorithm sensitivity or no observation."
Metric panel label: "Raw VIIRS vs MODIS reference" ar "Harmonized VIIRS vs MODIS reference" (RMSE, MAE, bias, correlation).

## 9. Demo (3 min)

- 0:00-0:25 Problem: MODIS 1 km vs VIIRS 375 m, raw jog korle false trend hote pare.
- 0:25-0:55 Raw CHT chart.
- 0:55-1:30 Naive vs harmonized splice.
- 1:30-2:00 Held-out result (tomar real number).
- 2:00-2:35 Uncertainty ar limitation.
- 2:35-3:00 Future work, reproducible code.

## 10. Fallback

Archive dari hole: API chunk. API atke gele: Earth Engine (NRT/rasterized, science-quality na, UI te note dao). Data kom hole: 2018-2021 subset, method o validation dekhao.

## 11. Ja verify hoy ni

2026 rulebook o participant guide, AIUB venue, district boundary file, NOAA-20 start date, Aqua vs S-NPP overpass timing, API day range (5 na 7).
