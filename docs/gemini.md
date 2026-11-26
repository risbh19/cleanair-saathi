# Gemini copilot

The default `LLM_MODE=reference` uses reviewed bilingual passages and the existing
calculation engines without provider calls. `LLM_MODE=replay` retains the checked-in
selection fixtures. To enable Gemini, set these server environment values in `.env`:

```dotenv
LLM_MODE=live
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart with `docker compose up --build --wait`. Keep the key on the server; the
browser sends only the household bearer token. Use an AI Studio key without billing
to stay within the provider's available free quota. Availability and quotas depend
on the account and model; quota failures use reference answers, with no paid fallback.

Ask Saathi uses native function declarations to read reviewed guidance, current air,
the requesting household's room context, its indoor simulation and commute comparison.
The server executes at most four allowlisted tools with no model-controlled arguments.
A separate structured request selects evidence; the server renders reviewed prose and
engine results, preventing invented URLs, instructions or readings. There is no
unbounded agent loop. Invalid responses, timeouts and missing keys use the reference
path. Medical diagnosis and prescription questions retain the existing refusal.

Household context excludes identifiers, coordinates, locality names and commute times.
Live chat can send the question and reduced household details to Google. Chat responses
are `no-store`; prompts and provider errors are not logged. Household context is loaded
from the requesting token; models cannot request another household. No history is sent.

Daily plans use Pydantic structured output to schedule and order all eligible action
IDs for the household and air band. Catalogue text and engine calculations stay on the
server. IDs, uniqueness and time slots are validated. Severe-air indoor advice retains
priority and an anytime slot. Invalid output preserves the deterministic plan. The first plan for a date
is persisted, so changing Gemini settings affects newly generated plans only.

The SDK uses five-second timeouts, one attempt, 1,200 output tokens per generation,
and a shared per-process ceiling of 12 provider requests per minute. Each chat can
use two requests; plans use one. Multiple workers multiply that process ceiling.
No live key is needed for unit tests: provider responses are mocked at the SDK boundary.

References: [Google GenAI SDK](https://github.com/googleapis/python-genai),
[structured outputs](https://ai.google.dev/gemini-api/docs/structured-output),
[function calling](https://ai.google.dev/gemini-api/docs/function-calling),
[current model availability](https://firebase.google.com/docs/ai-logic/models).

## Optional reviewed-source retrieval

Set `GEMINI_EMBEDDING_MODEL=gemini-embedding-001` and leave
`RAG_SIMILARITY_MIN=0.75` unless you have evaluated another threshold. Prepare the
six reviewed bilingual passages explicitly:

```sh
docker compose up --build --wait
docker compose exec backend python -m backend.app.retrieval
```

The SDK requests 768-dimensional `RETRIEVAL_DOCUMENT` embeddings during indexing and
`RETRIEVAL_QUERY` embeddings for questions, including Hindi and Hinglish. Reduced
embeddings are normalized. Index keys include the embedding model and a content hash
of the full reviewed library. Source/model changes require running preparation again;
an outdated or missing index is ignored without spending query quota.

Search returns at most five reviewed IDs above the cosine similarity floor. The
copilot receives only those passages plus lexical matches, and may abstain. Returned
citations resolve IDs against the current reviewed library, never model-authored URLs.
Missing pgvector, low similarity, timeouts and quota failures retain keyword lookup
and insufficient-evidence responses. The database remains optional for public chat.
The shared 12-request process budget also counts embeddings. Index preparation is
an operator action and sends public guidance only. Questions are sent for query
embeddings in live mode. See [embedding documentation](https://ai.google.dev/gemini-api/docs/embeddings).

## Purifier photo analysis

Indoor Lab offers an optional photo form. The user explicitly permits submission to
Google, then chooses a JPEG, PNG or WebP under 1 MiB and 8 megapixels. The backend
limits the complete request to 1,500,000 bytes, verifies the decoded image, rejects
animated images, strips metadata and resizes to at most 1,024 pixels on either side.
Images are processed in memory and are not written to app storage or logs. Google's
handling is subject to the API account's data terms.

`POST /purifier/analyze` takes `image_base64`, `mime_type`, and `language` (`en` or `hi`).
Structured observations cover visible dust, possible obstructions and a legible CADR
label in m³/h. Unreadable labels produce null CADR. The app does not infer electrical
safety, indoor PM2.5, filter lifetime or performance from a photo. Responses include
reviewed EPA guidance and `Cache-Control: no-store`; unavailable/invalid provider
responses offer manual checks.

A possible CADR value requires a separate **I checked the label — use this CADR**
action before it fills the Indoor Lab scenario. It never saves or changes the household
profile automatically. The existing indoor engine performs the comparison after the
user submits the scenario. Photo observations can be wrong; verify the device label
and manufacturer's instructions. Never treat a photo as an air-quality measurement.

## Review and validation

PR 2 (`gemini-grounding-vision`) is stacked on PR 1 (`gemini-copilot`). Review and merge
PR 1 first, then retarget PR 2 to `main` before merging it. Neither is auto-merged.
Provider tests use mocked SDK outputs, including malformed responses, timeout/quota
fallbacks, invented source IDs, invalid images and inconsistent CADR labels. CI also
runs the existing PostgreSQL/pgvector integration check with fixture embeddings.
