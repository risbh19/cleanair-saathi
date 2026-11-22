# CleanAir Saathi

CleanAir Saathi is a household air-quality planner for Delhi-NCR. This first milestone provides a tested PM2.5 engine and a FastAPI air brief backed by a clearly labelled synthetic Delhi series.

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

## Build status

The air brief, health endpoint, source metadata, input validation, CORS allow-list and database startup setup are implemented. Live ingestion, forecast endpoints, household persistence, daily plans, Indoor Lab, Ask Saathi, community digest and the React interface remain in the build plan. `DATA_MODE` currently accepts `fixture`. Enabling another mode fails startup with a clear error.
