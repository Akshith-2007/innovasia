# Kisan Cold Link

**Preserving Produce. Powering Possibilities.**

A public AgriTech website plus a FastAPI backend that retrieves official AGMARKNET mandi prices and
district crop statistics from data.gov.in. It validates and stores them as files, trains a real
price-forecasting model and serves transparent predictions. It uses no database, no synthetic
data and no hardcoded predictions.

## Architecture

```
React + Vite website (127.0.0.1:5173)
        │  HTTP /api/v1
FastAPI backend (127.0.0.1:8000)
        ├─ providers/   data.gov.in client (only module that calls the government API)
        ├─ pipeline/    immutable raw store → validation → Parquet
        ├─ services/    market queries, crop statistics
        └─ ml/          features, training, model loading, prediction
Files:  backend/data/{raw,processed,metadata}   backend/models/
```

See `docs/knowledge-graph.mmd` for the full module graph and `DECISIONS.md` for design decisions.

## Requirements

- Python 3.11+ (tested on 3.13)
- Node.js 20+ (tested on 22)
- Bash (Git Bash on Windows) for `./dev.sh`
- Optional: a personal data.gov.in API key (only for live daily prices and API downloads; CSV import needs none)

## Environment setup

```bash
cp backend/.env.example backend/.env       # then set DATA_GOV_API_KEY
cp frontend/.env.example frontend/.env.local   # optional: contact emails, social links, site URL
```

### Government API key (optional)

1. Sign in at https://www.data.gov.in/ and open **My Account → API key**.
2. Put it in `backend/.env` as `DATA_GOV_API_KEY=...`.
3. The key is read only by the backend. Never put it in `frontend/`.

Without a key, the site still runs. Pages that need data explain what is missing rather than
showing numbers.

## Start the app

```bash
./dev.sh
```

- Website: http://127.0.0.1:5173
- API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

If port 8000 is taken by another program, use `API_PORT=8010 ./dev.sh`; the website follows automatically.

The launcher creates `backend/.venv`, installs missing Python and npm dependencies, starts both
servers and stops both on Ctrl+C. It never downloads datasets, trains models or starts a database.

Manual alternative:

```bash
cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload   # Windows
cd backend && .venv/bin/python -m uvicorn app.main:app --reload       # macOS/Linux
cd frontend && npm run dev
```

## Data acquisition (explicit)

### Option A: no API key (default, ADR-019)

1. In a browser, open the official dataset page, for example
   https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi
   (or the variety-wise daily market prices catalogue for history), and download the **CSV**.
   Do the same for https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0.
2. Import each file from `backend/`, passing the page you downloaded it from:

```bash
python -m scripts.fetch_official_data market-import ~/Downloads/mandi_prices.csv \
    --url "https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi"
python -m scripts.fetch_official_data crop-import ~/Downloads/crop_production.csv
python -m scripts.validate_data
python -m scripts.preprocess_data
```

The importer keeps the original file untouched. It refuses files with prices that are not in
Rs./quintal, or that lack the state, market, commodity, date or modal-price columns. Without a
key, live daily prices are off and the site shows your imported official data, labelled "Stored".
Each new day's prices need a new download and import.

### Option C: Kaggle mirror of AGMARKNET history (used for the current model, ADR-022)

A public Kaggle copy of the data.gov.in AGMARKNET daily prices (2001–2026, GODL licence) provides
multi-year history without a key or login:

```bash
python -m scripts.import_kaggle_mirror --years 2022-2026   # ~230 MB download, preserved read-only
python -m scripts.preprocess_data                          # keeps MARKET_STATES (default Telangana, Andhra Pradesh)
```

Mirror rows are labelled "Kaggle mirror" everywhere on the site and in API responses. Official
downloads (Options A/B) automatically take precedence wherever both cover the same record.
Processing all of India needs roughly 9 GB of RAM; widen `MARKET_STATES` with care.

### Option B: with an API key

Run these from `backend/` with the venv's Python (`.venv/Scripts/python` on Windows, `.venv/bin/python` elsewhere):

```bash
# 1. Inspect the resources first: fields, totals, date format (ADR-010)
python -m scripts.fetch_official_data probe --resource current
python -m scripts.fetch_official_data probe --resource history

# 2. Today's prices (snapshot) and history for a state/commodity
python -m scripts.fetch_official_data current --state Telangana
python -m scripts.fetch_official_data history --state Telangana --commodity Tomato
python -m scripts.fetch_official_data history --state Telangana --from 2026-04-21 --to 2026-11-12   # one query per day

# 3. District crop production: via API, or import the CSV downloaded from the catalogue page
python -m scripts.fetch_official_data crop-api --state Telangana
python -m scripts.fetch_official_data crop-import ~/Downloads/crop_production.csv
```

Each run is stored read-only under `data/raw/<dataset>/<run_id>/` with a `manifest.json`
(source, resource id, filters, retrieval time, record count, SHA-256 checksums).

> The historical-price resource id and the crop-production resource id in `.env.example` are
> **unverified**. Run `probe` and confirm them on data.gov.in before bulk downloads.

## Storage planner (sell now or store?)

On the Market Intelligence page, after choosing a mandi and commodity, enter quantity, total cost,
transport and commission, pick a storage option, and compare selling now with selling after 7, 14
or 30 days. Defaults for storage rent, losses and shelf life come only from cited sources (shown
next to each value, with their year); where none exists you must enter your own. Each horizon's
forecast shows whether it beat "price stays the same" in testing (ADR-023).

## Cold storage admin portal and ESP32 (ADR-024)

1. `backend/.env` holds `ADMIN_PASSWORD` (portal sign-in) and `DEVICE_KEY` (sent by the ESP32).
   Both were generated randomly; change them if you like, then restart.
2. Start the API so the ESP32 can reach it on Wi-Fi:
   `API_HOST=0.0.0.0 API_PORT=8000 ./dev.sh` (on a machine where 8000 is busy, use 8010 and put
   that port in the firmware). Allow Python through Windows Firewall when asked.
3. Find the laptop's Wi-Fi IP (`ipconfig` → IPv4 Address).
4. Open `firmware/kisan_cold_link_esp32/kisan_cold_link_esp32.ino` in Arduino IDE (ESP32 board
   package; libraries "DHT sensor library", "OneWire", "DallasTemperature"). Set `WIFI_SSID`,
   `WIFI_PASSWORD`, `BACKEND_URL` (e.g. `http://192.168.1.100:8000/api/v1`) and `DEVICE_KEY`, then upload.
5. Open http://127.0.0.1:5173/admin and sign in with `ADMIN_PASSWORD`.

The ESP32 sends readings every 5 s and applies the pump state set in the portal (Manual buttons
or Auto thermostat with your upper/lower chamber limits). If Wi-Fi drops, the pump keeps its last
state. PCM backup time is calculated from the PCM mass, latent heat and the heat leaking through
the insulation (enter these in the portal, ADR-025); it is an estimate, not a measurement. Traffic is
plain HTTP: use only on a trusted Wi-Fi network.

## Farmer lots: best mandi after transport (ADR-026)

In the admin portal, **Farmer lots & best mandi** tab → **Add lot** records the farmer, village and location (typed or
"Use this device's location"), commodity, quantity, costs, the transport fare in ₹ per quintal per km,
and the nearby mandis with their road distance in km (enter from a map; distances are never guessed).
Optionally pick a storage option to also compare the 7/14/30-day forecasts. **Best mandi** then shows,
for every mandi, net receipts after transport (km × rate × quantity), fees and storage, and highlights
the mandi and selling time that pays the most. Mandis without enough history show the reason, not a number.

## Validation and processing

```bash
python -m scripts.validate_data     # checksums, schema drift, quality counts (no writes)
python -m scripts.preprocess_data   # rebuild processed Parquet + sources.json + quality_report.json
```

Rules: rows without a valid date or a positive modal price are excluded and counted. Suspicious
rows are flagged and kept out of training. Missing prices are never filled (ADR-012).

## Model training

```bash
python -m scripts.train_price_model --assess   # which series have enough history (>= 120 obs)
python -m scripts.train_price_model            # train baselines + Random Forest + XGBoost
python -m scripts.evaluate_model               # recompute test metrics from saved predictions
```

The model predicts the next reported modal price. Splits are chronological (70/15/15). The
winner is chosen by validation MAE and scored once on the held-out test period. If no series
has enough history, training stops with `INSUFFICIENT DATA` and creates no model.

## Testing

```bash
cd backend && .venv/Scripts/python -m pytest    # 59 tests: provider errors, pagination, CSV import, validation, leakage, splits, API
cd frontend && npm test                          # 18 tests: states, source labels, no fake values, all pages render
cd frontend && npm run typecheck && npm run build
cd frontend && npm run test:e2e                  # Playwright + axe at desktop/tablet/mobile (first time: npx playwright install chromium)
python docs/generate_graph.py --check            # knowledge graph matches the code
```

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Site says "API is not reachable" | Backend not running; use `./dev.sh`. |
| `data_unavailable` errors | Run the fetch commands, then `scripts.preprocess_data`. |
| `model_unavailable` | Run `scripts.train_price_model`. |
| `insufficient_data` on a forecast | That series has < 120 clean observations; fetch more history. |
| Prices show "Stored" not "Live" | No key, or data.gov.in failed; see the notice for the reason. |
| `auth` upstream error | API key wrong or missing in `backend/.env`. |
| `rate_limited` | Either data.gov.in or this API's own limit (`RATE_LIMIT_PER_MINUTE`, default 120/min per IP). Wait a minute; live responses are cached for `LIVE_CACHE_TTL_SECONDS`. |
| `Port 8000 is already in use` | Another program uses 8000. Run `API_PORT=8010 ./dev.sh` (and `API_PORT=8010 npm run test:e2e`). |
| Page shows "This page could not be displayed" | A page crashed; the message under it is the error to report. |
| `PermissionError` on raw files | Expected: raw files are read-only by design. |
| Admin portal says `not_configured` | Set `ADMIN_PASSWORD` (and `DEVICE_KEY`) in `backend/.env` and restart. |
| ESP32 prints `Telemetry failed (HTTP -1)` | Wrong IP/port, backend started without `API_HOST=0.0.0.0`, or firewall blocking. |
| ESP32 prints `HTTP 401` | `DEVICE_KEY` in the sketch differs from `backend/.env`. |
| Planner says `input_required` | No published loss figure for that storage and crop; enter your own estimate. |
