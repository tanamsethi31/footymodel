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
  - Note: All four legs done via the same iframe-based scrape harness (extractMatch reads tbody rows off the livestatistics page's two summary tables, player_id from the /players/ link, shots/ShotsOT columns by header index, sub-minute from the 3rd player-meta-data span) driven from a single foreground tab so background-tab JS throttling never triggers. Match list built via WhoScored's JSON fixtures API (`https://www.whoscored.com/tournaments/{stageId}/data/?d=YYYYMM&isAggregate=false`, one call per month) — far faster than DOM-scraping the fixtures page, and confirmed the URL slug is cosmetic-only (any placeholder works, only the match ID routes). To find a season's stageId: open the league's region/tournament page, use the season dropdown to get the seasonId, navigate to that season, then read the "Fixtures" link's href for the stageId. Batches of 8-10 downloaded as a Blob to ~/Downloads then merged+deduped into the TSV by match_id via the reusable scratchpad/merge.py helper. Recurring "CDP Runtime.evaluate timed out" is cosmetic — the page-side loop keeps running; poll `Object.keys(window.__results).length` and/or take a `computer` screenshot to unstick the connection, don't re-run the batch. Interruptions handled across this work: an ad hijacking the foreground tab (recover by recomputing remaining match_ids from the on-disk TSV, the source of truth, and reinstalling the harness fresh) and Chrome extension disconnects (harness state survives in `window`, just re-poll). All four raw TSVs + match_list CSVs sit under data/raw_whoscored/ (gitignored). Wired up: `_raw_path`/`load_players` now resolve by (league, season) via a season-suffix convention, with 2023/24 kept as a legacy special case for backward compat - verified 2023/24 and 2024/25 both load full match counts (380/306) for E0/D1, whoscored_calibration_test.py runs clean on 2024/25. Known gap, not a bug in the wiring: `load_players('E0'/'D1', '2025/26')` returns 0 rows because matches.parquet/matches_xg.parquet (football-data.co.uk results, a separate pipeline from this WhoScored scrape) only go up to 2024/25 - the current season needs a normal data-refresh run before its SOT rows are usable.
  - Status: done

- [ ] **R005** — Referee-tendency data for cards markets → *medium*
  - Why: Card counts correlate with individual refs; not pulled at all currently, would pair with a cards model

- [ ] **R006** — Per-league xi and blend-weight sweep → *small*
  - Why: xi=0.0018 and BEST_BLEND_W=0.25 are global constants tuned once on big-5; backtest.py already accepts --xi so a sweep is cheap

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
