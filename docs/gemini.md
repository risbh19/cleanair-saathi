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
priority. Invalid output preserves the deterministic plan. The first plan for a date
is persisted, so changing Gemini settings affects newly generated plans only.

The SDK uses five-second timeouts, one attempt, 1,200 output tokens per generation,
and a shared per-process ceiling of 12 provider requests per minute. Each chat can
use two requests; plans use one. Multiple workers multiply that process ceiling.
No live key is needed for unit tests: provider responses are mocked at the SDK boundary.

References: [Google GenAI SDK](https://github.com/googleapis/python-genai),
[structured outputs](https://ai.google.dev/gemini-api/docs/structured-output),
[function calling](https://ai.google.dev/gemini-api/docs/function-calling),
[current model availability](https://firebase.google.com/docs/ai-logic/models).
