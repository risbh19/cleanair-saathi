# CleanAir Saathi

CleanAir Saathi is a household air-quality planner for Delhi-NCR. The FastAPI service serves Delhi PM2.5 estimates and forecasts from a synthetic fixture or the CAMS regional model.

## Run locally

Use Python 3.11 or newer from the repository root.

```sh
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` on Linux and macOS, then run the API.

```sh
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open [the API documentation](http://localhost:8000/docs), or request `GET /air/now?lat=28.61&lon=77.21`. The API loads the fixture once at startup. `GET /health` provides liveness.

## Run with Docker

Copy `.env.example` to `.env`, set `POSTGRES_PASSWORD`, then start the services.

```sh
docker compose up --build --wait
```

The API listens on localhost port 8000. PostgreSQL stores its data in a named volume and enables pgvector when a new volume is initialized. The backend applies pending household migrations on startup, including on existing volumes. The fixture API reads its bundled CSV directly.

## Household dashboard

Open http://localhost:5173 after `docker compose up --build --wait`. Today shows the Delhi regional PM2.5 component, its source and timestamp, and the 48-hour forecast in India Standard Time. Switch between English and Hindi in the header. Household setup saves location, home details, members and commutes using the anonymous profile API. The Indoor Lab uses room settings from the saved profile and an editable outdoor concentration.

For frontend development, start the backend on port 8000, then run `npm ci` and `npm run dev` from `frontend/` using Node 22.12 or newer. Vite proxies requests under `/api` to the local backend. Compose serves the production build through nginx. Each browser origin keeps its own anonymous token and language preference.

## Verify

```sh
python -m unittest discover -s backend/tests -v
python -m backend.app.brief backend/data/fixtures/synthetic_day.csv
```

The CLI and engine tests run with the Python standard library alone. API tests require the development dependencies. GitHub Actions runs the suite and starts both Compose services for an HTTP smoke check.

## Data and calculation

The bundled 24-hour series is synthetic and represents an illustrative Delhi cell covering latitudes 28.5–28.8 and longitudes 77.0–77.4. Requests outside that cell receive a validation error. The response includes the observation timestamp, age, stale flag and source. Fixture dates remain fixed so the example is reproducible.

Its last hour has PM2.5 of 150 µg/m³, yielding a component estimate of 323 (Very poor). The 24-hour mean is 107.375 µg/m³ and yields a separate estimate of 257 (Poor).

The engine interpolates between the published PM2.5 breakpoints and truncates to a whole number for display, preserving the band for values fractionally above a cutoff. Above 250 µg/m³ it reports Severe and returns a null numerical value because the published concentration band has an open upper end. For these concentrations the API supplies `value_range: [401, 500]` from the [CPCB breakpoint table](https://airquality.cpcb.gov.in/ccr_docs/About_AQI.pdf). The dashboard labels this as a band range. Other bands retain their numeric estimate with a null range. Insufficient coverage still yields a null sub-index.

A 24-hour estimate requires at least 16 distinct valid hourly slots. The official overall AQI also requires multiple pollutants. All figures here represent the PM2.5 component.

[National AQI methodology and worked examples](https://ies.gov.in/arthapedia/concept/national-air-quality-index)

To supply your own single-location series to the CLI, create a CSV with columns `timestamp,pm25_ug_m3`. Each timestamp must have an explicit UTC offset and lie on a UTC hour boundary. Omit missing hours. Duplicate hours, negative concentrations and non-finite values cause an error. Pass `--as-of` with an offset-aware hour to choose the reporting window. The default uses the latest hour in the file.

## Delhi forecast and live data

`GET /air/forecast?hours=48` returns the next 1–48 hourly slots in UTC. It includes the earliest lowest and highest available PM2.5 hours. Missing slots have null values and are excluded from the ranking. These hours compare pollution within the requested window.

Set `DATA_MODE=live` in the Compose .env and run `docker compose up -d` to use CAMS via Open-Meteo. For a native run, set the environment variable before starting Uvicorn. The worker fetches the Delhi cell at startup and hourly thereafter. Data requests read the latest in-process snapshot. A failed refresh retains the prior snapshot and retries after five minutes. An empty cache or exhausted forecast window returns HTTP 503. Restarting clears the live cache. After three hours the API flags the cached download as stale. The model estimates regional concentrations, including for the current hour. Station observations can supply the current reading when OpenAQ is configured.

Fixture mode uses a fixed reference hour and a separate synthetic 48-hour forecast for offline demos. Both modes use the same Delhi coverage and response fields.

[Air-quality data and attribution: CAMS and Open-Meteo](https://open-meteo.com/en/docs/air-quality-api)


## Indoor Air Lab API

Open `POST /simulate/indoor` in [/docs](http://localhost:8000/docs) and try an eight-hour bedroom scenario.

```json
{
  "floor_area_m2": 12,
  "ceiling_height_m": 2.7,
  "windows": "closed",
  "purifier_cadr_m3_h": 300,
  "outdoor_pm25_ug_m3": [220, 220, 220, 220, 220, 220, 220, 220]
}
```

Each entry supplies the outdoor concentration for one hour. The selected scenario and the closed-window, purifier-off baseline use the same room and outdoor series. In this example the estimated inhaled mass is about 39 µg with the purifier and 438 µg at baseline. A negative avoided dose means the selected scenario increased exposure. A zero baseline yields a null percentage.

The model assumes a well-mixed room at equilibrium in each hour and excludes indoor sources such as cooking. Penetration, deposition, air exchange, breathing rate and the sizing target are editable scenario assumptions. The response includes them so a client can show how each estimate was calculated. The sizing output multiplies room volume by the selected clean-air changes per hour. This endpoint works offline in both data modes.

[US EPA APEX model documentation, section 8.2.2](https://www.epa.gov/system/files/documents/2023-08/APEX52_UsersGuide_Vol2_June2023.pdf)

## Anonymous household profiles

Generate a random UUIDv4 once per browser profile (for example, `crypto.randomUUID()`), save it before the first request, and send it as `Authorization: Bearer <token>` on each household request. Treat it as a password and use HTTPS outside localhost. Anyone with the token can access that profile. Clearing the token removes access. PostgreSQL stores its SHA-256 digest.

| Request | Result |
| --- | --- |
| `POST /households` | Save the complete profile. Reusing the token replaces the home, members and commutes together and keeps the household ID. |
| `GET /households/me` | Reload the profile for the current token. An empty session returns 404. |
| `DELETE /households/{id}` | Delete the owned profile, members and commutes. Success returns 204. An unknown or unowned ID returns 404. |

Open `/docs`, select **Authorize**, enter the UUID, then try the following request body. Enter a neighbourhood for locality. Coordinates are rounded to two decimal places before storage.

```json
{
  "lat": 28.6139, "lon": 77.2091, "locality": "Central Delhi",
  "home_type": "flat", "room_area_m2": 12, "ceiling_m": 2.7,
  "windows_leaky": false, "purifier_cadr_m3h": 0, "cooking_fuel": "lpg", "budget_band": "low",
  "members": [{"age_band": "adult", "sensitive": false, "commutes": [
    {"mode": "metro", "distance_km": 7, "depart_time": "08:30", "return_time": "18:00"}
  ]}]
}
```

For a native API run, set `DATABASE_URL` to your PostgreSQL connection string and run `python -m backend.db.migrate` before starting Uvicorn. Compose supplies the database settings and runs migrations automatically. To run the database integration tests, point `TEST_DATABASE_URL` at a disposable database and run `python -m unittest backend.tests.test_households -v`. Fixture air routes can run without a database.

## Delhi weather forecast

`GET /weather/forecast?hours=48` returns the next 1–48 UTC hours for the Delhi cell. Today displays the selected forecast hour in IST, with temperature (°C), relative humidity (%), 10-metre wind speed (m/s) and boundary-layer height (m). A missing field stays null. An hour counts as available when it contains at least one value.

Fixture mode uses a synthetic hourly series aligned with the air forecast. Live mode refreshes the [Open-Meteo Weather Forecast](https://open-meteo.com/en/docs) independently of CAMS, retries failed downloads after five minutes and marks a retained snapshot stale after three hours. When no usable weather hours remain the weather route returns 503. Responses include the source, mode, reference hour and live fetch timestamp. Weather data attribution and usage terms are available from [Open-Meteo](https://open-meteo.com/en/terms).

## Nearby station observations

In live mode, set `OPENAQ_API_KEY` in the backend environment or local Compose `.env` to enable [OpenAQ v3](https://docs.openaq.org/using-the-api/api-key). Keep the key on the server. The worker discovers fixed PM2.5 stations in the supported Delhi cell and loads their latest observations approximately every 15 minutes. It checks the pollutant, concentration unit, measurement time and station identity. Without a key the app uses the CAMS model.

`GET /air/now?lat=28.61&lon=77.21` selects up to three nearest reporting stations with readings less than three hours old. It uses one reading per station and returns their median in µg/m³. The current timestamp and age describe the oldest contributor. The response lists each station, original provider, timestamp, concentration, distance and OpenAQ location link. The PM2.5 sub-index is an estimate from this median. The dashboard uses the saved household coordinates when available.

When station readings expire, current conditions fall back to CAMS with its timestamp and stale flag. The 24-hour component and forecast use the regional model independently. A fresh station result can still be served while the model is unavailable, in which case the 24-hour fields are empty. Fixture mode remains synthetic. See the [OpenAQ terms of use](https://docs.openaq.org/about/terms) and original providers’ licensing information when reusing observations.

## Delhi-NCR GRAP orders

Today reads `GET /grap/status`. It shows the most recent recorded CAQM order whose effective time has arrived, in both fixture and live air modes. An empty database returns `{"order": null}`. Stage 0 means an entered order explicitly leaves no stage active. GRAP records are maintained by an operator independently of the pollution readings.

To record an order, configure a strong random `GRAP_ADMIN_TOKEN` in the backend environment and recreate the backend service. In the local API docs, authorize the admin request with that bearer token and call `PUT /admin/grap-status`. Supply the highest stage still in effect after the order (integer 0–4), `effective_from` with its UTC offset, and `source_url` pointing to the official HTTPS order PDF on caqm.nic.in. Verify the document and effective time before entering them. Use HTTPS for remote administration. The dashboard only uses the public read route.

A future order takes effect at its specified time. Repeating the same entry preserves its recorded timestamp. Submitting corrected details for the same effective time replaces that entry. Older orders remain stored. The admin route is disabled until its token is configured.

## Offline Delhi winter replay

Set `DATA_MODE=replay` in the local `.env` and run `docker compose up -d --build`. Open http://localhost:5173. To return to the synthetic demo, set `DATA_MODE=fixture` and rerun Compose.

The replay bundles 168 hourly model values for 6–12 January 2025 UTC at the requested Delhi coordinates (28.61, 77.21). Its reference time is 10 January at 23:00 UTC (11 January at 04:30 IST). The usual air and weather endpoints return the next 48 archived hours. The 24-hour PM2.5 average uses only values up to the reference time. These are retrospectively retrieved model series. No historical forecast issuance or station measurement is implied. The GRAP panel still reads the latest effective order in the local database.

The [capture manifest](backend/data/fixtures/delhi-winter-2025/manifest.json) records the exact retrieval URLs, UTC capture date and SHA-256 digests of the two original JSON responses. Air data are from Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo. Weather data are from the Open-Meteo Historical Forecast API. The API returns these source links and the capture date in replay mode. [Air data attribution](https://open-meteo.com/en/docs/air-quality-api) · [Weather archive](https://open-meteo.com/en/docs/historical-forecast-api) · [Open-Meteo terms](https://open-meteo.com/en/terms)

## Household action plan

Save a household and open Today to see its English or Hindi action cards. `GET /plan/today` takes the household’s bearer token and returns up to seven actions in stable priority order. The catalogue includes 15 actions with steps in both languages. Rules use member age groups and sensitivity flags, existing purifier capacity, fuel, commute modes and the PM2.5 component band at the household coordinates. Current conditions from the selected fixture or replay drive the demo. In live mode, a stale or missing reading leaves only household-based actions eligible.

This first plan is regenerated on request. It does not record completion or calculate individual exposure or emission savings. General pollution precautions draw on the [Ministry of Health advisory](https://ncdc.mohfw.gov.in/wp-content/uploads/2025/11/Ministrys-DO-dated-01.11.2025-1.pdf).
