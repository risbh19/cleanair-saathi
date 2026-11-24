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
