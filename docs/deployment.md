# Public deployment

The root `Dockerfile` builds the React dashboard and serves it with FastAPI in
one web service. The dashboard uses `/api` on the same HTTPS origin. PostgreSQL
is external and persists household profiles, plans and progress across service
restarts. The existing three-service `compose.yaml` remains the local workflow.

## Required configuration

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | A private connection string for a dedicated PostgreSQL database; include the provider's required TLS settings, such as `sslmode=require` |
| `PORT` | The platform's HTTP port; defaults to `8000` outside the platform |
| `DATA_MODE` | `fixture` for clearly labelled synthetic data, `replay` for archived data, or `live` for current external feeds |
| `LLM_MODE` | `reference` without provider calls, `replay` for deterministic fixtures, or `live` for Gemini selection |
| `GEMINI_API_KEY` | Required when `LLM_MODE=live`; keep on the server |
| `GEMINI_MODEL` | Required when `LLM_MODE=live`; use a model ID available to your key and quota |
| `GEMINI_EMBEDDING_MODEL` | Optional; requires the pgvector index preparation below |
| `OPENAQ_API_KEY` | Optional nearby station observations in live data mode |
| `GRAP_ADMIN_TOKEN` | A strong random secret if an operator will record GRAP orders |

Do not commit credentials. The application does not automatically load `.env`
for native Python runs; export variables in the shell or use your host's secret
settings. Docker accepts `--env-file .env`.

Use a dedicated database with permission to create tables. The production
entrypoint validates configuration and the built dashboard, applies pending
migrations under a PostgreSQL advisory lock, then starts one Uvicorn process on
`0.0.0.0:$PORT`. Failed migrations stop startup. Existing rows are retained.
Back up valuable data before deploying schema changes. Migration errors are
sanitized in startup logs to avoid exposing credentials.

## Render configuration

The root `render.yaml` defines **one Free Docker web service**. It does not
create a database, paid disk, worker or second web service. Provide an existing
persistent PostgreSQL database through the secret `DATABASE_URL` prompt.

After the changes are pushed to the branch you intend to deploy:

1. Create a Blueprint from that repository and branch. Inspect its proposed
   resources and confirm that the web service's plan is **Free**.
2. Supply `DATABASE_URL` privately. Do not put the URL in the YAML or GitHub.
3. The Blueprint uses `/health/ready` as its health check, enables current air
   feeds (`DATA_MODE=live`), and starts with reference answers (`LLM_MODE=reference`).
4. For the GenAI submission, add `GEMINI_API_KEY` and `GEMINI_MODEL` in the service
   environment, change `LLM_MODE` to `live`, and redeploy. Update the Blueprint's
   non-secret `LLM_MODE` value too before future Blueprint syncs.
5. Verify the hosted application using the checks below. Automatic later deploys
   wait for checks to pass on the linked branch.

Render Free web services can sleep after 15 minutes without traffic and take
about a minute to start again. Monthly usage limits are shared with other
services in the workspace. Open the submitted URL before recording or presenting
the demo. Do not put PostgreSQL or uploaded files on the web service's ephemeral
filesystem. Free Render Postgres databases currently expire after 30 days; an
existing external database keeps this Blueprint independent of that lifecycle.
Confirm the database provider's free quota and lifecycle before using it.

Platform references: [Free services](https://render.com/docs/free),
[Blueprint YAML](https://render.com/docs/blueprint-spec), and
[web service ports](https://render.com/docs/web-services#port-binding).

## Run the deployment image locally

Set the required variables in an untracked `.env` (copy `.env.example` and supply
`DATABASE_URL`). Use a database address reachable **from inside the container**;
`localhost` refers to the container itself. Then run from the repository root:

```sh
docker build -t cleanair-saathi .
docker run --rm --env-file .env -p 127.0.0.1:8080:8000 cleanair-saathi
```

This mapping assumes `PORT=8000` in `.env`. Open `http://localhost:8080`.
Database storage is external, so stopping this container does not remove rows.

For a native run, build the frontend and export the required environment first:

```sh
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
python -m backend.serve
```

The native and container entrypoints perform the same configuration validation
and migrations. Keep API access logging disabled to avoid retaining locality
queries. A trusted gateway should enforce public request limits before scaling
to multiple instances; the application limit is in memory per process.

## Verify the public URL

| Path or action | Expected result |
| --- | --- |
| `/` | Dashboard loads with JavaScript and styles |
| `/sw.js` | JavaScript worker, with revalidation enabled |
| `/health` | HTTP 200, process and data-mode information |
| `/health/ready` | HTTP 200 only when the database is reachable and all bundled migrations are recorded; otherwise HTTP 503 |
| `/api/air/now` and `/api/air/forecast` | Labelled fixture/replay data or a current live feed; live startup can return 503 while the initial download is pending |
| `/api/docs` | Interactive API documentation with `/api` URLs |
| Household → save → reload | Saved profile remains available in the same browser |
| Daily plan → update progress → reload | Progress is retained |
| Indoor Lab and Commute | Comparisons show calculated outputs and assumptions |
| Ask Saathi | Supported question shows reviewed text and citations |

`/health/ready` checks storage and migration history, not Google or air-provider
availability. Live data and AI calls can fall back or become unavailable while
the server is healthy. A startup configuration check cannot verify provider
credentials or quotas: before claiming Gemini use, confirm a successful provider
response rather than only seeing the reference fallback. Gemini orders eligible
actions and selects reviewed passage IDs; calculations and final passage text
remain controlled by the application.

Semantic retrieval is optional. Only if you enable it, use PostgreSQL with the
`vector` extension and prepare the index from a trusted environment with the
same database and Gemini variables:

```sh
python -m backend.app.retrieval
```

Basic household storage, action plans and reference answers do not require the
vector extension. Never use a production database for `TEST_DATABASE_URL`.
