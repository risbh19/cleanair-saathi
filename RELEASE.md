# CleanAir Saathi demo

Start Compose in fixture mode and open the dashboard on a phone-sized viewport. In the language menu select Hindi. Create a household from the multigenerational example and review its room and commute before saving. On Today, open a plan comparison, examine its assumptions and mark the card done. In Indoor Lab, compare the purifier on and off with hourly Delhi inputs. Use the lowest outdoor forecast hour to explore timing. A DIY filter uses a measured CADR for its particular build and fan setting. The linked EPA guide covers equipment and safe use.

Open Ask Saathi after the companion assistant PR is merged. Ask “फ़िल्टर कब बदलें?” and open the source. Ask an unrelated question to exercise the insufficient-evidence path. In Community, view the private week, search the locality, then open the explicitly fictional example to try sharing even on an empty installation.

| Behavior | Reproducible verification |
|---|---|
| Household ownership, progress and weekly deletion | PostgreSQL-backed `backend.tests.test_households` |
| Locality suppression and separate impact totals | `test_weekly_privacy_threshold_and_ownership` |
| Forecast coverage, indoor dose and emissions assumptions | `backend.tests.test_forecast`, `test_indoor` and `test_commute` |
| Phone navigation, Hindi cards and shareable summary | `python frontend/smoke.py` against the running fixture stack |
| Cited reference, refusal, persona/language/band matrix | `backend.tests.test_saathi` in the companion assistant PR |

The digest counts completed items on plans dated in the last seven Delhi calendar dates and in the active data mode. It requires five distinct participating households and independently suppresses each modeled metric below five contributing households. New plans snapshot their locality. Older plans with no location snapshot remain in the private week. A household deletion cascades through both views. The fictional preview has a separate endpoint and is excluded from all real totals. Completing a comparison records participation, not proof of avoided emissions or exposure.

Run `python -m unittest discover -s backend/tests -v` with `TEST_DATABASE_URL` pointing at a disposable PostgreSQL database for the integration cases. Run `npm ci && npm run build` from `frontend/`. GitHub Actions also upgrades an existing volume, checks persistence after restart and exercises the mobile flow in Chrome. The service worker caches static release assets only. API responses, household records and chat content are excluded.

### Optional Telegram morning brief

Preview the public Delhi message with `python -m backend.app.morning_brief`. To deliver to your own opted-in chat, configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the scheduler’s environment, then schedule `python -m backend.app.morning_brief --send` at your preferred morning time in Asia/Kolkata. Keep tokens out of the command line and source control. Delivery is disabled by default. The message includes source, timestamp, data mode and freshness.

### Offline phone demo and school runs

After the production build has loaded once and its service worker is active, disconnect the browser and open the offline demo. The bundled synthetic snapshot includes a 48-hour forecast, a checkable example plan and eight indoor comparisons produced by the Python engine. Regenerate it with `python -m scripts.offline_demo`. Offline demo changes stay in memory. Shared household records and community queries require the API.

Adults can create a private school-run group code in Community and give it to known families. Each household opts in to one quarter-hour departure slot in its locality for seven days. The API returns only whether another household in that group chose the same locality and slot. Withdraw the offer to remove it immediately.
