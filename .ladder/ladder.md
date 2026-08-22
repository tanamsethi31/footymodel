---
project: footymodel
version: 1
---

## foundation

- [~] **R001** — Project scaffold & folder structure → *small*
  - Context: Setting up the repo
  - Why: Everything builds on this
  - Note: Abandoned: init placeholder, not real work - project already at Phase I
  - Status: abandoned

## core

- [~] **R002** — Your first real feature → *medium*
  - Context: What you are building right now
  - Why: The meat of the project
  - Note: Abandoned: init placeholder, not real work - project already at Phase I
  - Status: abandoned

## expansion

- [ ] **R003** — Corners/cards betting market → *large*
  - Why: HC/AC/HY/AY/HR/AR already scraped into every match row, unused by any model - softer/less efficient market than 1X2/O-U/AH, genuinely untested

- [x] **R004** — 3-season WhoScored scrape: PL + Bundesliga (2023/24, 2024/25, 2025/26 all done) → *large*
  - Context: Shots/SOT calibration proven on PL 2023/24 + Bundesliga 2023/24. Goal is 3 consecutive seasons per league — rotation players accumulate enough minutes for reliable shrinkage and we can distinguish consistent shot-takers from one-season noise.
  - Why: 3 seasons per league is the minimum for stable player-level priors before Phase B live pipeline
  - [x] PL 2025/26 — 380/380 complete, 0 malformed rows, checkpointed in data/raw_whoscored/ws_scrape_export_E0_2025-2026.tsv (gitignored, local)
  - [x] Bundesliga 2025/26 — 306/306 complete, 0 malformed rows, checkpointed in data/raw_whoscored/ws_scrape_export_D1_2025-2026.tsv (gitignored, local)
  - [x] PL 2024/25 — 380/380 complete, 0 malformed rows, checkpointed in data/raw_whoscored/ws_scrape_export_E0_2024-2025.tsv (gitignored, local)
  - [x] Bundesliga 2024/25 — 306/306 complete, 0 malformed rows, checkpointed in data/raw_whoscored/ws_scrape_export_D1_2024-2025.tsv (gitignored, local)
  - Blocked by: ~none~
  - Note: All four legs done via the same iframe-based scrape harness (extractMatch reads tbody rows off the livestatistics page's two summary tables, player_id from the /players/ link, shots/ShotsOT columns by header index, sub-minute from the 3rd player-meta-data span) driven from a single foreground tab so background-tab JS throttling never triggers. Match list built via WhoScored's JSON fixtures API (`https://www.whoscored.com/tournaments/{stageId}/data/?d=YYYYMM&isAggregate=false`, one call per month) — far faster than DOM-scraping the fixtures page, and confirmed the URL slug is cosmetic-only (any placeholder works, only the match ID routes). To find a season's stageId: open the league's region/tournament page, use the season dropdown to get the seasonId, navigate to that season, then read the "Fixtures" link's href for the stageId. Batches of 8-10 downloaded as a Blob to ~/Downloads then merged+deduped into the TSV by match_id via the reusable scratchpad/merge.py helper. Recurring "CDP Runtime.evaluate timed out" is cosmetic — the page-side loop keeps running; poll `Object.keys(window.__results).length` and/or take a `computer` screenshot to unstick the connection, don't re-run the batch. Interruptions handled across this work: an ad hijacking the foreground tab (recover by recomputing remaining match_ids from the on-disk TSV, the source of truth, and reinstalling the harness fresh) and Chrome extension disconnects (harness state survives in `window`, just re-poll). All four raw TSVs + match_list CSVs sit under data/raw_whoscored/ (gitignored). Wired up: `_raw_path`/`load_players` now resolve by (league, season) via a season-suffix convention, with 2023/24 kept as a legacy special case for backward compat - verified 2023/24 and 2024/25 both load full match counts (380/306) for E0/D1, whoscored_calibration_test.py runs clean on 2024/25. Resolved: ran `python -m footymodel.data` and `python -m footymodel.understat` with 2025 added to `--seasons`, refreshing matches.parquet/matches_xg.parquet through 2025/26 (2025/26 has fully completed by now - not still in progress). `load_players('E0'/'D1', '2025/26')` now returns full 380/306 match counts.

Bug found + fixed while verifying: 145 of the 380 PL 2025/26 rows (exactly the ones checkpointed by the *prior* session, before this session's harness rebuild) had home_team == away_team in the raw TSV - a scrape-time bug where the old harness's `a[href*="/teams/"]` document-wide link scan occasionally picked up an async-injected sidebar/widget link (e.g. a related-content or video-recommendation link mentioning the home team again) instead of the real away-team link, silently mislabeling the away side while the away player-table content itself stayed correct. Confirmed isolated to that one file/session - the 1227 matches scraped later in this session (Bundesliga both seasons, PL/Bundesliga 2024/25, and the other 235 of PL 2025/26) were all clean. Fixed by rewriting `__extractMatch` to (a) select the home/away tables by their stable container IDs (`#statistics-table-home-summary`/`#statistics-table-away-summary`) instead of raw document order, and (b) parse team names from `document.title` (server-rendered as "{Home} {h}-{a} {Away} - League Season - Live Statistics", immune to async widget races) instead of scanning team-link text - then re-scraped just the 145 affected match_ids and merged the fix in. Verified: 0 rows with home==away across all six (league, season) files; all six load full match counts via `load_players`; `whoscored_calibration_test.py` runs clean on E0 2025/26. If any future scrape session reuses the old link-scanning approach, re-run the `n_bad = sum(home==away)` check from this note against the output before trusting it.
  - Status: done

- [ ] **R005** — Referee-tendency data for cards markets → *medium*
  - Why: Card counts correlate with individual refs; not pulled at all currently, would pair with a cards model

- [ ] **R006** — Per-league xi and blend-weight sweep → *small*
  - Why: xi=0.0018 and BEST_BLEND_W=0.25 are global constants tuned once on big-5; backtest.py already accepts --xi so a sweep is cheap
  - Context: PL season kicks off in 3 days, live pipeline already running via cron; question is whether to re-tune before or after the season starts feeding Phase J live-validation data
  - [ ] Sweep now, before kickoff — cheap, could improve live numbers from day one
  - [ ] Leave on current global constants, sweep later with a season of fresh data — avoids confounding the Phase J live-validation read (recommended: re-tuning right before the exact window being validated muddies whether results reflect the model or the retune)
  - Blocked by: ~none~

- [ ] **R007** — Ensemble goals+lineup+SOT models → *large*
  - Why: Three models run as independent tracks with no combined signal; real upside but real risk of adding noise if blended carelessly

- [ ] **R008** — Dynamic Elo-style ratings vs batch Dixon-Coles refit → *large*
  - Why: Reacts faster to current form than per-matchday batch refit; bigger rewrite, higher overfitting risk

- [ ] **R009** — Extend WhoScored-only shots/SOT to non-big-5 leagues → *medium*
  - Why: Phase C ruled out lineup-xG extension to Championship/Eredivisie due to no Understat xG there, but WhoScored raw shots/SOT doesn't need xG at all - that constraint may not actually block this

- [ ] **R010** — Where to push coverage next: league tier vs. new markets → *medium*
  - Context: Brainstormed after R004 status review: more scraping, other leagues, which tier (mid vs top-5), and whether to hunt more betting markets
  - Why: Big-5 O/U/1X2/AH are proven efficient (no edge) - more top-5 coverage of the same markets won't surface edge; mid-tier leagues and softer markets are the two levers that could
  - [ ] More top-5 leagues (La Liga, Serie A, Ligue 1) on the existing goals/O-U/1X2 model — low new-code cost but tests an already-efficient market, unlikely to surface edge
  - [ ] Drop down a tier (Championship, Eredivisie, etc.) and re-test the already-rejected 1X2/O-U/AH markets there — thinner books, less sharp money, real shot at reopening a "no edge" verdict
  - [ ] New softer markets on existing big-5 data (BTTS, correct score, team totals) — same league tier, different market efficiency profile; corners/cards is already scoped separately as R003
  - Related: R003 (corners/cards market), R009 (extend shots/SOT to non-big-5) — both are specific instances of the levers above, not blockers
  - Blocked by: ~none~

- [x] **R011** — AI/ML integration order → *medium*
  - Context: Drafting VISION.md — user wants to eventually bring AI/ML into the project, on top of the existing Dixon-Coles/statistical core
  - Why: every confirmed edge so far (lineups, venue) came from a better feature on a simple model, not a fancier model — jumping straight to ML risks re-learning that lesson the expensive way
  - [x] AI-as-reporting-layer first (LLM-written weekly performance/calibration summaries) — zero risk to the prediction path, automates what RESULTS.md already does by hand
  - [ ] NLP feature extraction next (team news/injury reports → structured signal into the existing lineup model) — extends a market that's already proven, doesn't replace it
  - [ ] Predictive ML last (XGBoost/LightGBM on a consolidated feature store, Phase M/N) — held to the same walk-forward + CLV bar that already killed the O/U and AH "edges"; only worth it once a feature store (Phase L) makes it cheap to test honestly
  - Blocked by: ~none~
  - Note: full writeup in VISION.md §5

- [ ] **R012** — Track CLAUDE.md, VISION.md, .claude/ in git → *small*
  - Context: "open our footymodel project to get working" session — found these three untracked in `git status` despite being established project files referenced elsewhere (VISION.md linked from roadmap discussion, CLAUDE.md is the ladder-tracking contract itself)
  - Why: untracked project files mean a fresh clone or collaborator loses the vision doc and ladder-tracking setup silently
  - [ ] `git add` + commit all three now
  - [ ] Leave untracked intentionally (e.g. CLAUDE.md/.claude/ meant to stay local-only tooling, not shipped)
  - Blocked by: ~none~

- [x] **R013** — Live poller barely running: laptop sleep is killing cron coverage → *medium*
  - Context: PL season already ~2 weeks in (user asked for a status update); investigated why `live_seen_fixtures.json` had only 1 fixture ID and no CSVs existed after 349 logged cron runs
  - Why: Verified the code live against the real API — league IDs (39/140/78/135/61) resolve correctly, no pagination bug (paging 1/1, PL fixtures present in date-only queries), quota healthy (16/100 used). The pipeline logic works. `pmset -g log` shows the machine cycling into real `Sleep` every ~10-15min all day (not just brief DarkWake) — plain crontab doesn't run/complete jobs while asleep, so nearly every 20-min poll window across 11+ days of live PL/La Liga/Bundesliga/Serie A/Ligue 1 fixtures was silently skipped. Phase J (live validation — the one thing that actually matters right now) has collected almost no data as a result, not because the edge doesn't exist but because the poller isn't actually running when it needs to.
  - [x] Move the poller to a GitHub Actions scheduled workflow — repo already has Actions/CI wired up (`.github/workflows/ci.yml`), zero cost, always-on, removes the laptop-sleep dependency entirely (recommended)
  - [ ] Keep it local, use `caffeinate`/`pmset repeat wake` scheduled around known kickoff windows — fragile, still tied to the laptop being physically available at the right times
  - [ ] Cheap always-on VPS or Raspberry Pi cron — more control, more to maintain for a research project
  - Blocked by: ~none~
  - Note: Also found a second bug while building this — local cron's 10am-10pm window was in IST (04:30-16:30 UTC), which misses most actual kickoff times (11:00-20:30 UTC across the 5 leagues). New workflow (`.github/workflows/live_poll.yml`) polls 09:00-21:40 UTC every 20min instead. Tracks matches/matches_xg/player_match parquet + live CSVs/seen-fixtures JSON via .gitignore exceptions so the Actions runner has the model inputs and commits results back. Committed locally (9e22c27); not yet pushed, and the `API_FOOTBALL_KEY` repo secret still needs to be set by the user (can't be done on their behalf).
  - Status: done — verified green end-to-end (run 32498185226). Manually triggering + watching the first three Actions runs caught two CI-only gaps a local test never would: `pyarrow` was installed in the local venv but missing from requirements.txt (parquet reads failed), and `data/raw_fbref/player_match.jsonl` (fbref.py's SOTModel input) was fully gitignored, same dir/* traversal issue as the parquet files. Both fixed and pushed (4d8699e, 4e00de2). Poller now runs clean, correctly logs "no new confirmed-lineup fixtures" when nothing's in the pre-kickoff window.

- [x] **R014** — Local crontab: remove now, or leave running alongside Actions? → *small*
  - Context: R013 moved the live poller to GitHub Actions; the local crontab entry (`*/20 10-22 * * *` -> `footymodel.live.run_all`) is still installed
  - Why: if both run, they build divergent local vs. Actions-checkout `live_seen_fixtures.json` state and can race pushing to the same file — local writes aren't synced with Actions' commits, so a local run could push a conflicting version or silently diverge with no push at all
  - [x] Remove the local crontab entry now — Actions is the sole poller, no race risk
  - [ ] Leave it running as a redundant local fallback — accepts the divergence/race risk in exchange for a second data source if Actions has an outage
  - Blocked by: ~none~
  - Note: R013's push landed on origin/main (9e22c27) and `API_FOOTBALL_KEY` repo secret confirmed set (`gh secret list`). Local crontab removed. Live poller is now Actions-only.
  - Status: done

- [x] **R015** — Goals engine 0/7, props engine working: player_match.parquet is a season stale → *small*
  - Context: First real status check on Actions-run data (2026-08-22) — `live_player_props.csv` has 111 real rows across 5+ fixtures (Phase J finally collecting props data), but `live_recommendations.csv` (the goals/O-U engine — the one edge with actual statistical confirmation, t=3.04) still doesn't exist despite 7 fixtures reaching confirmed-lineups
  - Why: root-caused via the Actions run logs + a direct data check. `data/processed/player_match.parquet` (Understat player roster, powers the goals engine's LineupModel) tops out at 2025-05-25 and was last touched Jul 29 — a full extra season stale vs. `matches.parquet`/`matches_xg.parquet` (current to 2026-05-24, refreshed Aug 4). The Aug 4 data refresh only touched the football-data.co.uk pipeline, not the Understat one, and they've silently drifted a year apart. Two failure modes result: newly-promoted teams (Hull City, Sunderland) missing from the roster entirely -> outright team-match failures; established teams (Everton, Palace, Forest, Leeds, Athletic Club, Sevilla) missing two transfer windows' worth of signings -> too few starters matched (6/9, 8/3, 8/2, all below the 8-of-11 confidence floor). The props engine (fbref-sourced) doesn't have this problem, which is why it's the only one logging real data so far.
  - [x] Fix now: rebuilt `player_match.parquet` via `build_player_dataset` for all 5 leagues, 2019-2026 — unblocks the goals engine today, matches the existing manual-refresh workflow already used for matches.parquet
  - [ ] Fix now AND automate: same refresh, plus a weekly scheduled Actions job so this can't silently drift again as the season progresses (more moving parts, but no recurring manual toil) — still open, deliberately deferred (see note)
  - [ ] Leave it — accept the goals engine stays blind until someone happens to refresh manually; the props engine alone is still collecting real Phase J data in the meantime
  - Blocked by: ~none~
  - Note: decoupled as planned. Refresh done and pushed (840e422): 377,678 rows (was 322,832), max date now 2026-08-22, Hull/Sunderland/Coventry all confirmed present. Per-match data for 2019-2025 was already cached locally (from the original Jul 29 build plus a killed earlier attempt this session) so only ~16 fresh 2026/27 matches needed real network fetches - fast. Could NOT do a live end-to-end confirmation against a real fixture: triggering a manual Actions run (32597493534) hit `You have reached the request limit for the day` on API-Football's free 100-req/day tier - partly the normal 20-min cadence, partly my own repeated manual workflow_dispatch test triggers today. Self-resolving at UTC midnight reset; not a bug, nothing to fix. The "automate the refresh" sub-decision is still genuinely open.
  - Pending: scheduled a one-time cloud routine (trig_01WYsi7AwZcBJHALg7FZ3cmJ) for 2026-08-23T00:30Z, 30min after the expected quota reset, to (1) confirm the goals engine actually logs real rows now with no more team-match-failure errors, and (2) return a concrete recommendation on the "fix now AND automate" vs. "leave manual" choice above based on that evidence. Resolve those two checkboxes once it reports back — don't decide blind before then.
