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

The API listens on localhost port 8000. PostgreSQL stores its data in a named volume and enables pgvector when a new volume is initialized. The database is prepared for the next persistence milestone. The fixture API reads its bundled CSV directly.

## Verify

```sh
python -m unittest discover -s backend/tests -v
python -m backend.app.brief backend/data/fixtures/synthetic_day.csv
```

The CLI and engine tests run with the Python standard library alone. API tests require the development dependencies. GitHub Actions runs the suite and starts both Compose services for an HTTP smoke check.

## Data and calculation

The bundled 24-hour series is synthetic and represents an illustrative Delhi cell covering latitudes 28.5–28.8 and longitudes 77.0–77.4. Requests outside that cell receive a validation error. The response includes the observation timestamp, age, stale flag and source. Fixture dates remain fixed so the example is reproducible.

Its last hour has PM2.5 of 150 µg/m³, yielding a component estimate of 323 (Very poor). The 24-hour mean is 107.375 µg/m³ and yields a separate estimate of 257 (Poor).

The engine interpolates between the published PM2.5 breakpoints and truncates to a whole number for display, preserving the band for values fractionally above a cutoff. Above 250 µg/m³ it reports Severe and returns a null numerical value because the published concentration band has an open upper end. That numerical mapping needs a verified extension before it can cover the full 0–500 scale.

A 24-hour estimate requires at least 16 distinct valid hourly slots. The official overall AQI also requires multiple pollutants. All figures here represent the PM2.5 component.

[National AQI methodology and worked examples](https://ies.gov.in/arthapedia/concept/national-air-quality-index)

To supply your own single-location series to the CLI, create a CSV with columns `timestamp,pm25_ug_m3`. Each timestamp must have an explicit UTC offset and lie on a UTC hour boundary. Omit missing hours. Duplicate hours, negative concentrations and non-finite values cause an error. Pass `--as-of` with an offset-aware hour to choose the reporting window. The default uses the latest hour in the file.

## Delhi forecast and live data

`GET /air/forecast?hours=48` returns the next 1–48 hourly slots in UTC. It includes the earliest lowest and highest available PM2.5 hours. Missing slots have null values and are excluded from the ranking. These hours compare pollution within the requested window.

Set `DATA_MODE=live` in the Compose .env and run `docker compose up -d` to use CAMS via Open-Meteo. For a native run, set the environment variable before starting Uvicorn. The worker fetches the Delhi cell at startup and hourly thereafter. Data requests read the latest in-process snapshot. A failed refresh retains the prior snapshot and retries after five minutes. An empty cache or exhausted forecast window returns HTTP 503. Restarting clears the live cache. After three hours the API flags the cached download as stale. The model estimates regional concentrations, including for the current hour. Station observations and weather are pending.

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
