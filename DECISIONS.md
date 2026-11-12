
# Kisan Cold Link — Engineering Decision Log

This file is append-only.

Never delete or rewrite an accepted decision.
When a decision changes, create a new ADR that supersedes it.

---

## ADR-001: Separate public website and backend

Date: 2026-11-11
Status: Accepted

Context:
The project requires a public-facing website with real agricultural
data and machine-learning functionality.

Decision:
Use React + Vite for the frontend and FastAPI for the backend.

Consequences:
Frontend and backend run as separate processes.
Frontend accesses backend through HTTP APIs.

---

## ADR-002: No database

Date: 2026-11-11
Status: Accepted

Context:
The current scope does not require user accounts or transactional
data persistence.

Decision:
Use local CSV, Parquet and model artifacts.

Consequences:
No PostgreSQL, MongoDB or Redis.
Historical data is stored as files.
Models are loaded from saved artifacts.

---

## ADR-003: Official government agricultural data only

Date: 2026-11-11
Status: Accepted

Context:
Market intelligence must be credible and reproducible.

Decision:
Use original government-published datasets and official APIs.

Primary source:
AGMARKNET / data.gov.in.

Consequences:
No synthetic market prices.
No third-party substitute datasets without a new decision.
Every source must be documented.

---

## ADR-004: Real ML training

Date: 2026-11-11
Status: Accepted

Context:
The website requires an actual price-forecasting demonstration.

Decision:
Train and evaluate models using verified historical government data.

Candidates:
Naive baseline, moving average, Random Forest and XGBoost.

Consequences:
Use chronological evaluation.
Persist model metadata.
Never fabricate metrics or predictions.

---

## ADR-005: One-command local development

Date: 2026-11-11
Status: Accepted

Decision:
Provide root-level ./dev.sh.

Consequences:
The script starts FastAPI and Vite.
Ctrl+C must stop both processes.
No database or Docker required.

---

## ADR-006: Persistent agent documentation

Date: 2026-11-11
Status: Accepted

Decision:
Maintain AGENTS.md and CLAUDE.md.

Consequences:
Coding agents must inspect project rules before making changes.

---

## ADR-007: Append-only decision history

Date: 2026-11-11
Status: Accepted

Decision:
Maintain this file as the permanent decision record.

Consequences:
New decisions use new ADR identifiers.
Superseded decisions remain available for historical context.

---

## ADR-008: Codebase knowledge graph

Date: 2026-11-11
Status: Accepted

Decision:
Maintain knowledge-graph.json and knowledge-graph.mmd.

Consequences:
Architecture dependencies must be visible and updateable.
No graph database is required.

---

## New decisions

Add new decisions below this line.

Template:

## ADR-XXX: Decision title

Date:
Status: Proposed / Accepted / Rejected / Superseded

Context:

Decision:

Alternatives:

Consequences:

Related modules:

---

## ADR-009: Immutable raw store with per-run manifests

Date: 2026-11-11
Status: Accepted

Context:
Spec sections 6.4 and 7 require raw data to be preserved, never overwritten, and fully traceable.

Decision:
Each fetch/import is a run directory `backend/data/raw/<dataset>/<run_id>/` holding the exact
response bytes of every API page (or the original imported file) plus `manifest.json`
(source, resource id, publisher, filters, request params without the key, retrieval
timestamps, total reported by the API, record count, completeness, schema fields, SHA-256 per file).
Files are written with exclusive-create and set read-only. `sources.json` is regenerated from
manifests by `scripts.preprocess_data`.

Alternatives:
Re-serialised JSON (not byte-exact); a single appended CSV (mutable, loses provenance).

Consequences:
Processed data is always rebuildable from raw. Checksum mismatches exclude a run and are reported.

Related modules:
backend/app/pipeline/raw_store.py, backend/scripts/fetch_official_data.py, backend/scripts/preprocess_data.py

---

## ADR-010: Historical mandi data source (to be verified)

Date: 2026-11-11
Status: Proposed

Context:
The current-price resource (9ef84268-...) exposes only the latest published day. Training needs history.

Decision:
Use the AGMARKNET "Variety-wise Daily Market Prices Data of Commodity" resource on data.gov.in
(configured id 35985678-0d79-46b4-9ed6-6f13308a1d24, UNVERIFIED) for history, fetched per
state/commodity with offset pagination. `fetch_official_data probe` reports fields, totals and
dates so coverage, date format and filter keys can be confirmed before bulk download. Filter
names are resolved against the resource's declared fields, trying plain then `.keyword` keys.
Daily snapshots of the current resource can also accumulate history over time.

Alternatives:
Scraping agmarknet.gov.in report pages (not an official API; rejected). Third-party datasets (forbidden by ADR-003).

Consequences:
Must be confirmed by a new ADR once the resource id, coverage and rate limits are verified with a real key.
The crop production resource id (35be999b-...) is likewise unverified; CSV import from the catalogue page is supported.

Related modules:
backend/app/providers/agmarknet.py, backend/scripts/fetch_official_data.py, backend/.env.example

---

## ADR-011: Pipeline package and extra provenance endpoints

Date: 2026-11-11
Status: Accepted

Context:
The spec's backend tree has no home for shared fetch/validate/process logic used by scripts and tests.

Decision:
Add `backend/app/pipeline/` (raw_store, market_processing, crop_processing). Add
`GET /api/v1/data/sources` (provenance and quality summary for the Research page) and
`GET /api/v1/agriculture/options` (selector values).

Alternatives:
Logic inside scripts (untestable); inside services (mixes serving with ingestion).

Consequences:
Scripts are thin CLIs; the pipeline is unit-tested.

Related modules:
backend/app/pipeline/, backend/app/api/sources.py, backend/app/api/agriculture.py

---

## ADR-012: Market data validation rules

Date: 2026-11-11
Status: Accepted

Decision:
- Excluded and counted: unparseable or missing arrival date, future date, missing state/market/commodity,
  missing or non-numeric modal price, modal price <= 0.
- Kept but flagged in `quality_flags` (and excluded from training): missing min/max, negative
  min/max, min > max, modal outside [min, max], modal more than 8x or less than 1/8 of the series
  median (possible unit error).
- Exact duplicates collapse to one row. Conflicting duplicates (same series and date, different prices)
  keep the most recently retrieved publication; the count is reported.
- No filling or forward-filling of any price or date, anywhere.
- Prices stay in INR/quintal as published; the unit is stored per row.

Alternatives:
Dropping all suspicious rows (loses information); imputing gaps (forbidden).

Consequences:
`quality_report.json` documents every exclusion and flag.

Related modules:
backend/app/pipeline/market_processing.py, backend/scripts/validate_data.py

---

## ADR-013: Forecast target and features

Date: 2026-11-11
Status: Accepted

Context:
Mandi series are irregular (holidays, days without arrivals). Calendar-day lags would require
filling gaps, which ADR-012 forbids.

Decision:
- Series key = state, district, market, commodity, variety, grade.
- Horizon = next reported observation, only when it falls within 7 days of the origin.
- Target = log(p[t+1] / p[t]); predictions are converted back to INR/quintal.
- Features: observation lags 1/3/7/14/30 as ratios to the current price, rolling means (7, 14),
  rolling std (7), 7-observation change, min-max spread, days since previous observation, day span
  of the last 7 observations, month sin/cos, day of week, log price, and label-encoded
  commodity/market/variety ids.
- All features use rows <= t of the same series only (covered by a leakage test).
- Arrival quantities are not used (not among the resources' canonical fields).

Alternatives:
Calendar-day lags with resampling (requires imputation); one model per series (too little data each).

Consequences:
"7-day lag" in the spec is implemented as a 7-observation lag plus explicit gap features.

Related modules:
backend/app/ml/features.py

---

## ADR-014: Training, selection and interval policy

Date: 2026-11-11
Status: Accepted

Decision:
- Eligibility: a series needs >= 120 clean observations; others receive an `insufficient_data` response.
- Chronological split by target date: 70% train, 15% validation, 15% test; each split needs >= 50 rows.
- Compete: last-observation baseline, 7-observation moving average, Random Forest, XGBoost.
- Select by lowest validation MAE (a baseline may win and is then served). Refit learned models on
  train+validation, then score every model once on test.
- 80% interval from validation-residual quantiles; published only if test coverage is within 5 points.
- Artifacts: `models/price_model/<version>/{model.joblib, metadata.json, test_predictions.parquet}`
  with pointer `models/current.json`. `scripts.evaluate_model` recomputes test metrics from saved predictions.
- Directional accuracy is computed on rows where the price moved; flat forecasts count as wrong.

Alternatives:
Random K-fold (leaks future data; forbidden). Selecting on test metrics (optimistic bias).

Consequences:
Reported test metrics are produced exactly once by the training pipeline and are reproducible.

Related modules:
backend/app/ml/training.py, backend/app/ml/predictor.py, backend/scripts/train_price_model.py, backend/scripts/evaluate_model.py

---

## ADR-015: Live prices with honest fallback

Date: 2026-11-11
Status: Accepted

Decision:
`/market/prices` tries data.gov.in first (in-memory cache, default 900 s, to respect rate limits).
On any failure, or with no key configured, it serves the latest stored official observation per
series with `source.live=false, source.cached=true` and the live error in `meta.live_error`.
The UI shows a "Stored" badge and a notice. History, trends, comparisons and forecasts always use stored data.

Alternatives:
Fail hard when live is unavailable (worse UX); silently show stored data (forbidden by AGENTS.md).

Consequences:
Cached data is never presented as live.

Related modules:
backend/app/services/market_service.py, frontend/src/components/market/PriceCards.tsx

---

## ADR-016: Frontend design system

Date: 2026-11-11
Status: Accepted

Decision:
- Typography: Fraunces (display serif) and Public Sans (body), self-hosted via @fontsource.
- Tokens in `src/styles/globals.css` (@theme): forest, forest-deep, charcoal, paper, sage, amber.
- shadcn/ui-style primitives (Button with cva and Radix Slot, Card/Badge, form fields) are written in
  `src/components/ui/` rather than generated by the CLI; selects are native for accessibility.
- Magic UI / Aceternity UI are not adopted yet; no section has needed them.
- Hero and diagrams are original SVG (no stock photography). Real photography can go in `public/images/`.
- All routes except Home are lazy-loaded; vendor chunks are split (react, motion, data).
- Recharts pinned to v2.

Alternatives:
Full shadcn CLI scaffold (more files than needed); stock hero photography (licensing, generic look).

Consequences:
New UI must use the tokens and primitives above.

Related modules:
frontend/src/styles/, frontend/src/components/ui/, frontend/vite.config.ts

---

## ADR-017: Test inputs and fixtures

Date: 2026-11-11
Status: Accepted

Decision:
Provider tests use an envelope-shape fixture whose values are labelled placeholders
(`backend/tests/fixtures/ogd_envelope_shape.json`) until a genuine recorded response replaces it.
ML and API tests build deterministic, labelled test series in pytest temp dirs; they are never
written to `backend/data` or `backend/models`, never displayed and never shipped as a model.

Alternatives:
No fixtures until a key exists (leaves error handling untested).

Consequences:
Replace the envelope fixture with a recorded genuine page once data has been fetched.

Related modules:
backend/tests/, frontend/src/test/

---

## ADR-018: Cooling hardware labelled as concept

Date: 2026-11-11
Status: Accepted

Decision:
PCM storage, water loop, chamber and re-cooling source are labelled "Concept"; sensors/ESP32 are
"Planned". Only the software platform is labelled "Working on this site". Impact items are
labelled objectives, not results.

Alternatives:
"Prototype" labels (unverified claim).

Consequences:
Change labels only when hardware exists, via a new ADR.

Related modules:
frontend/src/pages/HomePage.tsx, frontend/src/pages/TechnologyPage.tsx

---

## ADR-019: Keyless operation via official CSV downloads

Date: 2026-11-11
Status: Accepted

Context:
The project owner chose not to depend on a personal data.gov.in API key. The data itself is
published openly under the Government Open Data License - India; only the API requires a key.

Decision:
Primary acquisition path is manual download of official CSV files from data.gov.in catalogue
pages / AGMARKNET, imported with `python -m scripts.fetch_official_data market-import <file.csv> --url <download page>`
(and `crop-import` for crop statistics). The importer:
- preserves the original file byte-for-byte as a read-only raw run with checksum and provenance (ADR-009);
- maps AGMARKNET export headers (e.g. "Market Name", "Modal Price (Rs./Quintal)", "Price Date");
- refuses files whose price columns are not in Rs./quintal, or that lack state, market, commodity,
  date or modal price, instead of guessing.
The API key stays optional: without it, live daily prices are off and the site serves imported
official observations labelled "Stored" (ADR-015).

Alternatives:
Shared public sample API key (about 10 records per call, impractical for history); community
mirrors such as Kaggle (not government-published, would violate ADR-003).

Consequences:
Data freshness depends on how often files are downloaded and imported. The download page URL is
mandatory provenance for every import. This decision does not supersede ADR-010; the API path remains available.

Related modules:
backend/scripts/fetch_official_data.py, backend/app/pipeline/raw_store.py, backend/app/providers/agmarknet.py, backend/tests/test_csv_import.py

---

## ADR-020: Browser testing, accessibility gate and hardening

Date: 2026-11-12
Status: Accepted

Context:
Phase 6 requires browser tests, accessibility checks and a security review. jsdom unit tests
missed a crash that only occurred in a real browser (effects returning non-function values),
which every page hit.

Decision:
- Add Playwright (`@playwright/test`) and `@axe-core/playwright` as frontend dev dependencies.
  `npm run test:e2e` runs the real backend and Vite dev server at desktop (1440), tablet (820)
  and mobile (Pixel 7) sizes. Each page must render its h1, have no horizontal overflow, raise
  no page errors and have zero serious/critical axe violations (WCAG 2.1 AA tags). Market and
  Research pages must show explanations, never prices, when data or the model is missing.
- Add a route-level error page so a render failure never shows the framework's developer screen.
- Accessibility fixes: list items rendered by `Reveal as="li"`; new `amber-ink` text token;
  `muted` darkened to #565c55 for AA contrast on sage backgrounds.
- Security: httpx/httpcore logging raised to WARNING (they log full URLs, which contain the
  data.gov.in key); all AppError messages pass through `redact()`; API responses carry
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and a referrer policy. An e2e test
  checks that the API key name or an `api-key=` parameter never appears in browser-loaded scripts.
- `dev.sh`: refuses to start if a port is busy; the API port is overridable (`API_PORT=8010 ./dev.sh`)
  and the website follows it via `VITE_API_BASE_URL`; on Windows the cleanup records each server's
  Windows PID at launch and kills the whole process tree (uvicorn reloader + worker, npm + cmd + vite)
  before signalling the shell wrappers.

Alternatives:
Cypress (heavier, slower on Windows); manual accessibility review only (not repeatable).

Consequences:
Port 8000 is used by another service on the current development machine, so local runs there use
`API_PORT=8010`. The spec default remains 8000. The backend API has no request rate limiting of
its own; add it before any public deployment.

Related modules:
frontend/e2e/, frontend/playwright.config.ts, frontend/src/pages/RouteErrorPage.tsx,
frontend/src/styles/globals.css, backend/app/core/logging.py, backend/app/core/exceptions.py,
backend/app/main.py, dev.sh

---

## ADR-021: In-process API rate limiting and dev-server stability

Date: 2026-11-12
Status: Accepted

Context:
ADR-020 noted the API had no request limiting of its own. Bursts could also exhaust the
data.gov.in quota through `/market/prices`.

Decision:
- `RateLimitMiddleware`: sliding one-minute window per client IP, in memory, default 120
  requests/minute (`RATE_LIMIT_PER_MINUTE`, 0 disables). Over the limit it returns 429 with
  `Retry-After` and the standard error envelope (`code: rate_limited`). Health and docs are exempt.
- The website shows a "wait a minute" hint for `rate_limited`.
- Playwright's backend runs with the limit disabled (many parallel page loads from one IP); the
  limiter is covered by a backend unit test. Playwright allows one retry, reported as "flaky".
- Vite pre-bundles the lazy routes' dependencies (`optimizeDeps.include`) so the dev server does
  not reload pages mid-session when it discovers them.

Alternatives:
slowapi/Redis-backed limiter (new dependency; Redis forbidden by ADR-002); reverse-proxy limiting
(no proxy in this architecture yet).

Consequences:
Limits are per process and reset on restart; behind a proxy all clients may share one IP, so
configure the proxy to limit instead, or raise the value.

Related modules:
backend/app/core/rate_limit.py, backend/app/main.py, backend/app/core/config.py,
frontend/src/components/layout/States.tsx, frontend/playwright.config.ts, frontend/vite.config.ts

---

## ADR-022: Kaggle mirror of AGMARKNET permitted for history and training (partly supersedes ADR-003)

Date: 2026-11-12
Status: Accepted

Context:
The project owner instructed that a Kaggle dataset be used for model training. data.gov.in blocks
automated downloads (HTTP 403), and the official API needs a personal key the owner has not
supplied, so no official history was available. ADR-003 allowed third-party datasets only via a new decision.

Decision:
- Permit `khandelwalmanas/daily-commodity-prices-india` on Kaggle
  (https://www.kaggle.com/datasets/khandelwalmanas/daily-commodity-prices-india) as a source of
  historical mandi prices for display and model training. It states it is a cleaned copy of the
  data.gov.in AGMARKNET variety-wise daily prices, licensed under the Government Open Data
  License - India (GODL). Schema matches AGMARKNET; prices are INR/quintal; dates are ISO.
- Import with `python -m scripts.import_kaggle_mirror --years 2022-2026`. Each yearly Parquet file is
  preserved unmodified as an immutable raw run with `source_kind = "third_party_mirror"`, licence,
  Kaggle URL, upstream URL and checksum.
- Official rows always win over mirror rows on conflicting duplicates.
- Every API response and page that shows mirror data says so (`source.third_party`, per-row
  `source_kind`, "Kaggle mirror" badges, Research page source table and limitations).
- Model metadata records the source kinds and states of its training data.
- Scope: `MARKET_STATES` (default Telangana, Andhra Pradesh). All India for 2022-2026 is 20.9M rows
  and about 8.8 GB in memory, too large for this single-process file-based design.
- Rejected Kaggle listings: synthetic mandi data (skm1234556/mandi-data) is never allowed;
  tiny extracts (e.g. ishankat, 225 KB) are insufficient for training.

Alternatives:
Wait for official CSVs/API key (blocks the ML demo); use the shared public sample key (refused
earlier as not user-authorised, and limited to 10 records per call).

Consequences:
ADR-003's "official data only" now reads "official data, or this specific GODL-licensed mirror of
official data, always disclosed". The mirror is not verified record-by-record against data.gov.in;
once official downloads exist, they override overlapping mirror rows automatically. No synthetic
data is introduced. Raw mirror files occupy about 200 MB under backend/data/raw (git-ignored,
synced by OneDrive on the current machine).

Related modules:
backend/scripts/import_kaggle_mirror.py, backend/app/pipeline/market_processing.py,
backend/app/services/market_service.py, backend/app/schemas/common.py, backend/app/ml/training.py,
frontend/src/components/layout/States.tsx, frontend/src/components/market/PriceCards.tsx,
frontend/src/pages/ResearchPage.tsx

---

## ADR-023: South-India scope, official gap fill, multi-horizon forecasts and storage planner

Date: 2026-11-12
Status: Accepted

Context:
The owner supplied a data.gov.in key and asked for current market prices, a cost/storage
estimate for farmers, and a south-India-first rollout. ADR-010's historical resource was unverified.

Decision:
- ADR-010 confirmed with a real key: resource 35985678-0d79-46b4-9ed6-6f13308a1d24 ("Variety-wise
  Daily Market Prices Data of Commodity", 83M records) filters by plain field ids `State` and
  `Arrival_Date` (dd/mm/yyyy); the current-price resource needs `state.keyword`.
- `fetch_official_data history --from --to` fetches one query per day into one immutable run;
  completeness is the sum of each day's reported total. Official rows (Apr 2026 onward) override
  Kaggle mirror rows (ADR-022).
- Scope `MARKET_STATES` = Telangana, Andhra Pradesh, Karnataka (owner's choice). Tamil Nadu and Kerala
  (~5.6M more rows) follow after memory work.
- Horizon models for 7, 14 and 30 calendar days: target = first observation in [t+h, t+h+3];
  same features, chronological split and interval policy as ADR-014; candidates are the baselines
  plus XGBoost only (Random Forest was within 1% of XGBoost at one step and ~10x slower). Each
  horizon records `beats_naive_on_test`; the site labels horizons that do not as "weak forecast".
- Predictor filters to one series before cleaning (was 1.4-4.7 s per request on all rows).
- Storage planner: `GET /decision/storage-options`, `POST /decision/plan`. Six options (sell now,
  home/shed, Zero Energy Cool Chamber, ventilated onion structure, rented cold storage, warehouse),
  suggested by commodity category. Defaults only from cited sources (CWC 2019-20 warehouse rate via
  FCI; Guntur chilli cold-storage rent 2018-19; ICAR onion storage losses; ICAR ZECC shelf-life
  studies). Where no source exists the value is empty and the API returns `input_required` instead
  of assuming. Loss is prorated linearly (stated). Results show net receipts, interval-based range,
  difference vs selling now, profit and break-even price when total cost is given.
- Market page adds "Today's prices across the state" from the live API.

Alternatives:
Seasonal history instead of forecasts (owner chose models); uncited "typical" storage defaults (rejected).

Consequences:
Cited rates are several years old and labelled with their year; farmers should use local quotes.
Horizon accuracy is reported, not assumed; long horizons may not beat "price stays the same".

Related modules:
backend/scripts/fetch_official_data.py, backend/app/pipeline/raw_store.py, backend/app/ml/features.py,
backend/app/ml/training.py, backend/app/ml/predictor.py, backend/app/ml/model_loader.py,
backend/app/services/storage_planner.py, backend/app/api/decision.py,
frontend/src/components/market/StoragePlanner.tsx, frontend/src/components/market/StateLivePrices.tsx

---

## ADR-024: Cold-storage admin portal and ESP32 device link (partly supersedes the "no authentication" rule)

Date: 2026-11-12
Status: Accepted

Context:
The owner asked for an admin portal to monitor the chamber (DHT11 air temperature/humidity, DS18B20
coil/heat-sink water temperature) and control the pump of an ESP32 node over Wi-Fi. A public pump
switch is a safety and security risk. AGENTS.md said "no authentication"; the owner chose an admin password.

Decision:
- ESP32 firmware (`firmware/kisan_cold_link_esp32/`) POSTs readings every 5 s to
  `/api/v1/device/telemetry` and polls `/api/v1/device/command`; the backend holds the desired pump
  state. If Wi-Fi or the backend is unreachable the pump keeps its last state (owner's choice).
- Device requests carry `X-Device-Key`; admin requests carry `X-Admin-Password`. Both are single
  shared secrets in backend/.env compared in constant time. No user accounts, sessions or database.
  Empty secret = feature disabled (503).
- Modes: Manual (portal buttons) and Auto (pump ON above an upper limit, OFF below a lower limit;
  limits must be set by the admin, no defaults). A manual press switches to Manual.
- PCM backup is a labelled design estimate: default 5 h full charge, drains while the pump is off
  (faster by a configurable 10%/°C above a target), refills while on (default 5 h full recharge).
  Gaps over 5 minutes are not counted.
- Usage tips are temperature rules: coil not colder than chamber while pumping, chamber outside the
  admin's limits, PCM estimate under 1 h, device offline or sensor failure.
- Storage: `data/device/state.json` (atomic replace) and daily CSV telemetry under `data/device/telemetry/`.
- `dev.sh` accepts `API_HOST=0.0.0.0` so the ESP32 can reach the API on the LAN.

Alternatives:
USB serial bridge (owner chose Wi-Fi); localhost-only portal (not reachable from phones); per-user accounts (needs a database).

Consequences:
Traffic is plain HTTP on the local network: the password and device key can be read by anyone on
that Wi-Fi. Use only on a trusted network, or put the API behind HTTPS before exposing it. Single
device only (shortcut noted in code). The 5-hour PCM figure is not measured; replace with test data.

Related modules:
backend/app/api/device.py, backend/app/services/device_service.py, backend/app/core/config.py,
frontend/src/pages/AdminPage.tsx, firmware/kisan_cold_link_esp32/kisan_cold_link_esp32.ino, dev.sh

---

## ADR-025: Physics-based PCM backup estimate (supersedes the PCM countdown in ADR-024)

Date: 2026-11-12
Status: Accepted

Context:
ADR-024 estimated PCM backup with a fixed 5-hour countdown. The owner asked for a calculation
from the actual PCM mass and chamber, not a hardcoded figure.

Decision:
- The admin enters PCM mass (kg), latent heat (kJ/kg), melting point (°C), outside temperature (°C),
  insulated surface area (m²), insulation thickness (mm) and conductivity k (W/m·K); optionally the
  coil-to-PCM heat transfer (W/K). Nothing is assumed: until these are entered the portal shows no estimate.
- Energy balance on every reading:
  stored capacity E = m · L; heat leak Q = UA · (T_outside − T_chamber) with UA = area · k / thickness
  and T_chamber from the DHT11; recharge P = coil_UA · (T_melt − T_coil) while the pump runs and the
  DS18B20 coil is colder than the melt point. State of charge += (P − Q) · Δt / E, clamped to 0–1.
  Backup hours = remaining E / Q.
- Presets are limited to a physical constant (water/ice: 334 kJ/kg at 0 °C) and typical insulation
  conductivities (PUF ≈ 0.023, XPS ≈ 0.032, EPS ≈ 0.036 W/m·K) labelled "typical; use the datasheet".
- Without a coil transfer value, recharge is not modelled; the admin uses "Mark fully charged".
- Telemetry logs state of charge, backup hours and heat load per reading.

Alternatives:
Keep the countdown (rejected by owner); full transient model with sensible heat, product respiration and
door openings (more inputs than the owner has; can extend later).

Consequences:
Latent heat only (sensible heat of PCM and contents ignored, so slightly conservative); steady-state heat
leak; outside temperature is a typed value because the node has no ambient sensor. Still an estimate,
labelled "not a measurement"; validate against a real discharge test.

Related modules:
backend/app/services/device_service.py, backend/app/api/device.py, frontend/src/pages/AdminPage.tsx

---

## ADR-026: Farmer lots and best-mandi comparison with transport fare

Date: 2026-11-12
Status: Accepted

Context:
The owner asked for the admin to record a farmer's lot with its location and details, forecast
prices at nearby mandis, and say which gives the most profit after transporting the lot to the mandi.
The repository has no mandi coordinates, and the owner asked for the most feasible approach.

Decision:
- Admin-only endpoints (`X-Admin-Password`, ADR-024): `GET/POST /admin/lots`, `DELETE /admin/lots/{id}`,
  `GET /admin/lots/{id}/compare`. Lots are stored in `data/lots/lots.json` (atomic replace), no database.
- A lot records farmer name, phone (required), village, state, optional latitude/longitude (typed or from the
  browser's geolocation), commodity, quantity, optional production cost, fee %, storage choice, and a
  list of candidate mandis, each with the road distance in km entered by the admin.
- Transport fare = distance_km x rate (INR per quintal per km, owner's choice) x quantity, one way.
  The rate has no default; the admin enters it.
- For each mandi the storage planner (ADR-023) runs on that mandi's own series with that mandi's transport
  cost. The best option per mandi and overall is the highest net receipts. Mandis without a supported series
  or model report the reason and get no figure; nothing is borrowed from another mandi.

Alternatives:
Automatic distances via OpenStreetMap Nominatim/OSRM (new third-party source, unreliable mandi geocoding,
outbound calls; not done now). Per-vehicle-trip fares (owner chose per quintal per km).

Consequences:
Distances are only as good as the admin's entry. Lot data includes farmer names and phone numbers stored
in plain JSON on the server; it is reachable only with the admin password, over the same plain-HTTP caveat as ADR-024.

Related modules:
backend/app/services/lot_service.py, backend/app/api/lots.py, backend/tests/test_lots.py,
frontend/src/components/admin/FarmerLots.tsx, frontend/src/pages/AdminPage.tsx, frontend/src/services/api.ts

---

## ADR-027: Farmer lot register with automatic distances and 7/14/30-day sale plans (coexists with ADR-026)

Date: 2026-11-12
Status: Superseded by ADR-028

Context:
Developed in parallel with ADR-026 and merged on 2026-11-12; both features are kept. ADR-026 uses
admin-typed distances per lot at /admin/lots; this one uses district-HQ distances at /admin/farmer/lots.
The owner asked for a farmer portal inside the admin portal: log storage lots, then use the forecasts to
decide when and where to sell, counting distance, transport and storage costs. The original spec excluded
a farmer application, inventory management and financial records; the owner's request overrides that for
this admin-only, file-based feature.

Decision:
- Admin-only (ADR-024 password). Lots hold farmer name, village, commodity, optional variety/grade,
  quantity (quintals) and entry date. No phone numbers, IDs or payments. Stored in data/farmer/lots.json (git-ignored).
- Facility settings (data/farmer/settings.json): cold-storage district, transport ₹ per quintal per km,
  storage rent ₹/quintal/month, expected loss %/30 days (all required), optional commission %, optional
  maximum km, and per-mandi km overrides. Nothing is assumed: a plan without them returns input_required.
- Distance: offline table of district-headquarters coordinates (TG, AP, Karnataka; hand-entered,
  ±5-10 km), straight line x 1.3 road factor, labelled "approx."; admin overrides win (owner's choice;
  no external geocoding).
- Transport = quantity x km x ₹/q/km (owner's choice).
- Plan: every mandi with a current series (price in the last 30 days) for the lot's commodity (lot's
  variety if given, else each mandi's most-recorded one) and an evaluated model; options sell now
  (latest recorded price) and after 7/14/30 days (horizon models, ADR-023). Net = sale value after loss
  - commission - transport - storage rent from the entry date; ranked by net. Reuses the planner's
  tested scenario() maths. Mandis without enough history are counted and reported, not guessed.
- Batch forecasting filters prices to the commodity once (about 1-9 s per plan on 1.5M rows).

Alternatives:
Typed distances only; OpenStreetMap routing (external service); per-trip vehicle costing (owner chose per q/km).

Consequences:
Personal data is limited to names and villages in a local file; protect the machine and the admin password.
Distances are approximate. Coverage is limited by AGMARKNET's Dec 2025 market renaming (fewer mandis
with long enough history) until names are harmonised.

Related modules:
backend/app/services/farmer_service.py, backend/app/services/geo.py, backend/app/api/farmer.py,
backend/app/ml/predictor.py, frontend/src/components/admin/FarmerPortal.tsx, frontend/src/pages/AdminPage.tsx

---

## ADR-028: Keep only the ADR-026 lots feature (supersedes ADR-027)

Date: 2026-11-12
Status: Accepted

Context:
ADR-026 (enftaurus: lots with admin-typed mandi distances, /admin/lots) and ADR-027 (lots with
district-HQ distance estimates and sale plans, /admin/farmer/lots) were built in parallel and both kept
at merge. The owner chose the ADR-026 implementation.

Decision:
Remove the ADR-027 feature: backend/app/api/farmer.py, backend/app/services/farmer_service.py,
backend/app/services/geo.py, backend/tests/test_farmer.py, frontend/src/components/admin/FarmerPortal.tsx,
the predictor's batch forecast helper used only by it, and its admin tab and git-ignore entry.
ADR-026 is unchanged.

Alternatives:
Keep both (duplicated features, two lot registers to maintain).

Consequences:
One lot register (data/lots/). Distances are admin-entered per mandi as ADR-026 describes; the
district-distance estimate and automatic multi-mandi ranking are gone. Recoverable from git history (013c89d).

Related modules:
backend/app/main.py, backend/app/ml/predictor.py, frontend/src/pages/AdminPage.tsx, .gitignore

---

## ADR-029: Commit processed data and trained models so a fresh clone works

Date: 2026-11-12
Status: Accepted

Context:
A fresh clone could load the committed models but not forecast: the processed price table and its
provenance files were git-ignored, and rebuilding them needs ~420 MB of raw downloads.

Decision:
Commit backend/data/processed/market_prices.parquet (~8 MB) and backend/data/metadata/{sources,quality_report}.json
alongside backend/models/. Raw downloads (backend/data/raw/) stay git-ignored; private files (.env,
data/lots/) stay ignored. Rebuilding with scripts.preprocess_data and retraining still work as before.

Alternatives:
Keep data out of git and document the rebuild (slow, needs keys/downloads); Git LFS (extra tooling).

Consequences:
Repository grows by ~8 MB per committed data refresh; commit refreshed data deliberately. The processed
table carries per-row source_kind, so Kaggle-mirror labelling (ADR-022) survives in clones.

Related modules:
.gitignore, backend/data/processed/, backend/data/metadata/, backend/models/
