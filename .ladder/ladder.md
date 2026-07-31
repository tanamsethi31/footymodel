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

- [▶] **R004** — Second full season of player-level scraping → *medium*
  - Context: WhoScored shots/SOT calibration (Phase E-G) is well-calibrated but only proven on one season each (PL 2023/24, Bundesliga 2023/24) - the thinnest evidence base in the project. (Corrected: the t=3.04 lineup-edge stat belongs to the separate Understat/big-5 goals-lineup model, which already has 3 seasons - not this one.)
  - Why: Tests whether the venue effect and calibration hold across TIME, not just across leagues, before trusting them into a live season
  - [x] WhoScored shots/SOT, PL only, 2025/26 season (most recently completed - closer roster continuity to the upcoming live season than reaching back further)
  - [ ] WhoScored shots/SOT, PL + Bundesliga, 2025/26 season
  - [ ] Lineup model (Understat), one more big-5 season (pushed back on - that edge is bottlenecked by "closing odds already price lineups," not backtest sample size)
  - Blocked by: ~none~
  - Status: in_progress
  - Note: Match list (380/380) built and committed. Scraping in progress via
    browser DOM-extraction (same technique as Phase E/G) - 33/380 matches
    checkpointed to data/raw_whoscored/ws_scrape_export_E0_2025-2026.tsv.
    Progress slowed sharply mid-scrape (WhoScored rate-limiting, same pattern
    documented in Phase E) - each match now taking near the full per-request
    timeout instead of ~1s. Checkpointing to disk incrementally now (an
    earlier browser-session interruption lost ~144 unsaved matches before
    this pattern was adopted).

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
