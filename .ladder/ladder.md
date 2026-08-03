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

- [ ] **R004** — 3-season WhoScored scrape: PL + Bundesliga (2023/24 done, 2024/25 + 2025/26 needed) → *large*
  - Context: Shots/SOT calibration proven on PL 2023/24 + Bundesliga 2023/24. Goal is 3 consecutive seasons per league — rotation players accumulate enough minutes for reliable shrinkage and we can distinguish consistent shot-takers from one-season noise.
  - Why: 3 seasons per league is the minimum for stable player-level priors before Phase B live pipeline
  - [x] PL 2025/26 — 380/380 complete, 0 malformed rows, checkpointed in data/raw_whoscored/ws_scrape_export_E0_2025-2026.tsv (gitignored, local)
  - [ ] Bundesliga 2025/26 — not started (~306 matches)
  - [ ] PL 2024/25 — not started (~380 matches) — missing middle season
  - [ ] Bundesliga 2024/25 — not started (~306 matches)
  - Blocked by: ~none~
  - Note: PL 2025/26 done via iframe-based scrape harness (extractMatch reads tbody rows off the livestatistics page's two summary tables, player_id from the /players/ link, shots/ShotsOT columns by header index, sub-minute from the 3rd player-meta-data span) driven from a single foreground tab so background-tab JS throttling never triggers. Batches of 8 downloaded as a Blob to ~/Downloads then merged+deduped into the TSV by match_id. Recurring "CDP Runtime.evaluate timed out" on the await call is just the response reporting hanging — the page-side loop keeps running; poll `Object.keys(window.__results).length` and/or take a `computer` screenshot to unstick the connection, don't re-run the batch. One session saw a real interruption: an ad hijacked the foreground tab to a random whoscored.com page mid-batch, which resets all injected JS state — recovery is to recompute the remaining match_ids from the on-disk TSV (source of truth, not the in-memory index) and reinstall the whole harness fresh. Next up: same harness, swap in the Bundesliga 2025/26 match_list.
  - Status: in_progress

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
