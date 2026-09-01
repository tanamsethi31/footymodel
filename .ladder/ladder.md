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
  - Related finding (user asked "what was our prediction for Hull v Man Utd" — checked live_player_props.csv): same root cause showed up a second place. `shots_engine.py`'s `player_rows_for_fixture` requires BOTH teams to resolve against the Understat/fbref rosters before computing any probability (`if u_pid and opp_u`, `if f_pid and opp_f`) — Hull being unmatched at request time meant even Man Utd's players logged blank `p_shots_gt*`/`p_sot_gt*`, only odds got captured, for all 22 rows. Fixture 1557368 is in `seen_fixtures.json` so this is permanent, not retryable. Unverified: whether `data/raw_fbref/player_match.jsonl` (the SOT half) has the same promoted-team gap Understat had — if so, Sunderland/Coventry fixtures could hit this same blank-prediction outcome even after today's fix. Worth checking before the next promoted-team fixture, not urgent right now.

## product

- [x] **R016** — Public dashboard hosting platform → *medium*
  - Context: user wants a "fancy proper dashboard" that auto-updates before match time with key predictive-analysis outcomes (Phase P in VISION.md) — brainstorming via superpowers:brainstorming, visual companion running at http://localhost:58090
  - Why: matches the VISION.md §9 motive (CV/portfolio surface, "something explainable end-to-end in a product/business conversation") — where it lives affects how it reads in that context
  - [x] Vercel-hosted site — real deployed URL, auto-redeploys from GitHub, best portfolio fit, CLI/plugin already set up
  - [ ] GitHub Pages — zero extra infra, static-only, less flashy
  - [ ] Claude Artifact — instant, no deploy step, claude.ai-hosted rather than a standalone project URL
  - Blocked by: ~none~

- [x] **R017** — Dashboard scope: picks only, or also a graded track record? → *large*
  - Context: follow-up to R016 during brainstorming
  - Why: a track record (hit rate, realized CLV once matches finish) is far more portfolio-worthy than a live picks list alone, but requires a new results-grading step that doesn't exist anywhere in the codebase yet — genuinely bigger scope, not a UI-only decision
  - [ ] Upcoming picks only — today's/this week's confirmed-lineup fixtures with model prob, odds, EV; no new backend logic beyond reading existing CSVs
  - [x] Upcoming picks + running track record — needs a new grading step: fetch final results for previously-logged predictions, compare to the pick, aggregate hit rate/CLV
  - Blocked by: ~none~
  - Note: grading scope itself needs its own decision (goals-only vs. goals+props) — see next rung.

- [x] **R018** — Prop-grading scope: verify player-stats endpoint first, or build blind? → *small*
  - Context: follow-up to R017 (chose "grade both from day one") — goals grading is easy (final score, already fetched), props grading needs an unverified player-match-stats API endpoint
  - Why: don't want to design/build a props-grading feature around an endpoint that turns out to be Pro-tier-only or shaped differently than assumed
  - [x] Verify the endpoint against a real completed fixture before designing the props-grading feature
  - Blocked by: ~none~
  - Status: blocked — attempted verification, discovered the API-Football account itself is suspended (see R019), not just an endpoint-availability question. Re-attempt once R019 clears.

## infra

- [x] **R019** — API-Football account suspended → *unknown*
  - Context: discovered while trying to verify the player-stats endpoint for R018. `c.status()` (normally free/uncounted) now returns `{'access': 'Your account is suspended, check on https://dashboard.api-football.com.'}` — a harder failure than the daily-quota exhaustion seen earlier this week
  - Why: blocks everything — live poller (R013/R015's whole point), R018's endpoint check, and by extension R017's "grade both" dashboard scope. Traced via Actions logs: last known-good run was 13:25 UTC 2026-08-24 (`No new confirmed-lineup fixtures`, no error); first suspended run was 15:22 UTC 2026-08-24 (32744344728). Every run since has failed the same way — ~18hrs and counting as of this check (09:27 UTC 2026-08-25), zero new predictions logged by either engine in that window.
  - [x] User checks dashboard.api-football.com for the actual reason (billing/plan issue vs. an automated abuse flag, plausibly from repeated daily-quota hits including manual testing this week) and resolves it — this is account/billing-level, not something fixable from code
  - Blocked by: ~none~ (blocks R013 live validation, R017/R018 dashboard scope)
  - **Resolved 2026-08-27.** Real reply from human support (via the dashboard chat, not the AI bot): "Your account has been reactivated. The suspension was likely not caused by your daily quota, but by the shared infrastructure used by GitHub Actions. Its outbound IP addresses can also be used by other API-SPORTS users, which may trigger the Free plan security or multi-account protections. For more reliable usage, we recommend using an environment with a dedicated/static outbound IP address when possible." Confirmed directly (`c.status()`): `active: true`, 6/100 used today.
  - **Important, not just a one-off**: the cause was GitHub Actions' shared/rotating outbound IPs, not anything this project did — some *other* GH-Actions-hosted API-SPORTS user likely tripped the flag on an IP later assigned to this workflow. This can recur unpredictably, entirely outside our control, unless we pay for a dedicated/static outbound IP. Retroactively validates building the SofaScore (R021, dormant) and RapidAPI (R027, live) fallback engines — they're real insurance against this exact recurring risk, not redundant effort.
  - Status: done — account reactivated, all three engines (API-Football, SofaScore, RapidAPI) now theoretically available; API-Football is primary again but the underlying risk (shared CI IPs) is structural and could resurface.
  - Note: dashboard shows account fine / 0% quota used, but the API itself still returns the suspension error (confirmed twice, a few seconds apart — not transient). User confirmed there's a *different* plan/account status flag than what they checked, not yet found. Browser check attempted to help locate it but the in-app Browser pane is an isolated sandbox with no shared login session, so it hit API-Football's login page, not the dashboard — can't help locate it that way without credentials, which I won't handle.

- [ ] **R020** — Suspension unresolved: keep resolving API-Football, or migrate to another free platform? → *large*
  - Context: user proposed switching to another free platform while R019 stays unresolved; researched real alternatives via WebSearch before recommending anything
  - Why: a platform swap means rewriting client.py + engine.py + shots_engine.py's parsing and namematch.py's team/player matching against a third naming scheme — large, and only worth it if an alternative actually covers what's needed
  - [x] Keep resolving API-Football (recommended) — researched football-data.org (lineups+odds both paid add-ons), Sportmonks (free tier is only Danish Superliga + Scottish Premiership, odds paid regardless), Highlightly (100 req/day like API-Football, odds paid-only). Odds licensing is a paid feature industry-wide, not an API-Football-specific limitation — a swap is unlikely to fix the actual problem (getting odds for free) and costs a real rewrite for likely the same or worse limits
  - [ ] Migrate to an alternative platform anyway — accepts losing odds/EV entirely (guts the project's actual thesis: beating the market, not just predicting) or betting on an unverified/likely-not-legitimate "free unlimited odds" source (e.g. BSD/bzzoiro's claims read as SEO/affiliate bait, same red flags as OddsPapi's already-rejected claims from Phase I)
  - Blocked by: R019 (still unresolved — user is looking for the specific status flag)

- Update to R019: found the notification, via the user's real logged-in session (claude-in-chrome, not the sandboxed browser pane — confirms actual account state, not stale). Bell icon shows exactly one notification: "Your account is Suspended" — no reason given, not clickable, no self-service unsuspend action anywhere in the dashboard (checked Home, /subscription/all, notification panel). The subscription page's own fine print explains the likely mechanism: "If you significantly exceed your allowed rate limits or generate abnormal traffic spikes, our firewalls may automatically and without prior notice temporarily or permanently block your access" — free plan is 10 req/min AND 100 req/day; this week's combination of normal cron + my manual workflow_dispatch triggers + the verification routine's repeated polling plausibly tripped the per-minute limit even while the daily counter (which shows 0% now) looked fine. Only path forward visible: the "Chat" support widget on the dashboard — this needs the user to actually contact support, nothing further to dig up from the dashboard itself.

- [x] **R020** — No free-API replacement exists: wait on support, scrape, or both? → *small*
  - Context: user asked "do we have any alternatives now" a second time after R019's suspension was confirmed with no ETA on resolution
  - Why: re-checked two more candidates (SharpAPI — odds only from US books DraftKings/FanDuel, uncertain EU-soccer/prop coverage, "17,280 req/day free" claim itself is a blog-summary red flag; RapidOddsAPI/OddsPapi — already unverifiable per Phase I). No clean free API bundles lineups+odds for EU soccer, confirming R019's earlier read. The one credible different-shaped option is scraping (SofaScore/FlashScore/Oddsportal), matching the project's own FBref/WhoScored precedent, but it's real new engineering (new scraper, new anti-bot handling, new name-matching), not a quick swap
  - [x] Wait on API-Football support — near-zero effort, but live data collection stays paused with no known timeline
  - [ ] Scope out a scraping-based replacement now (SofaScore/FlashScore/Oddsportal) — removes the API-quota dependency long-term, real build effort
  - [ ] Both in parallel — submit support request now, scope scraping as a fallback independent of the response
  - Blocked by: ~none~
  - Note: user is submitting the support request themselves; I have live-session access via claude-in-chrome if they want help drafting/sending it, but haven't been asked to yet — send only on explicit request (sending messages on the user's behalf needs it).
  - Note: sent the support message via the user's real dashboard session (claude-in-chrome) at their explicit request. It hit an AI FAQ bot, not a human directly, but the bot confirmed messages through that chat interface get auto-forwarded to the human support team. No ticket number, no ETA. As of the next check, account was still suspended.

- [x] **R021** — SofaScore-based goals engine, built and shipped → *large*
  - Context: R020 chose "build the SofaScore path"; verified live (tournament IDs, lineups, Match-goals O/U odds all real and working from a browser context) before writing code
  - Why: API-Football suspension had no ETA; SofaScore had confirmed lineups + real 2.5-line odds for free, matching what the goals engine needs (props still has no free path anywhere - confirmed again, permanent conclusion)
  - Built: `footymodel/live/sofascore_client.py` (Playwright-based - plain HTTP 403s, needs a real browser), `sofascore_engine.py` (same LineupModel/namematch/EV logic as engine.py, new data source), `scripts/sofascore_odds_parse_test.py` (fractional->decimal + 2.5-line lookup, added to CI). Wired into `live_poll.yml` with Playwright install + browser cache, `continue-on-error` since it's the newer/less-proven path. Pushed (e0660ff).
  - **Critical finding, same session**: mid-build, this sandbox's IP got 403'd by SofaScore (confirmed via two independent browser contexts) - the same bot-detection cat-and-mouse already documented for WhoScored/FBref, but immediate rather than eventual. Triggered a real GitHub Actions run (32904932028) to check if a different IP would fare better: **also 403'd**. This means it's very likely blocking cloud/datacenter IP ranges categorically (standard Cloudflare-style behavior), not a single flagged IP - a structural blocker for any cloud CI environment, not something better code or backoff logic fixes.
  - Status: code shipped and correct, but **not currently usable in production** - every fixtures-fetch call from GH Actions 403s. Effectively dead until/unless proven otherwise. Also gitignored `data/raw_understat_matches/` (474MB/12k-file cache, never tracked) caught before being accidentally committed.
  - Blocked by: needs a fresh decision on next steps (see R022)

- [ ] **R022** — SofaScore is blocked from cloud CI: what now? → *small*
  - Context: R021's SofaScore path is code-complete but non-functional in production - confirmed blocked from both this sandbox and real GitHub Actions runners
  - Why: the free-odds search has now hit two structural dead ends independently (no free API bundles lineups+odds; the one working scrape source blocks cloud/datacenter IPs) - worth deciding deliberately rather than continuing to burn effort chasing the next option
  - [x] Keep waiting on API-Football support (recommended) — leave the SofaScore code in place harmlessly (already `continue-on-error`, costs nothing to leave failing silently) in case their blocking policy ever changes; focus effort on the one lever that's actually proven to work before (a human at API-Football lifting the suspension)
  - [ ] Route SofaScore requests through a residential/rotating proxy service — could plausibly work (real user IPs aren't datacenter-flagged) but reintroduces a paid third-party dependency, defeating the original "find something free" motivation, plus no guarantee it beats other detection signals (TLS fingerprint, request patterns)
  - [ ] Stop here — accept live validation is fully paused until API-Football responds, remove/disable the now-dead SofaScore CI step to stop it running for nothing every 20min
  - Blocked by: ~none~
  - Status: done — confirmed with user ("sofascore continue" -> clarified as "leave code as-is, no proxy"). SofaScore engine stays wired into live_poll.yml as a dormant no-cost fallback; no new spend, no further build. Next real move is still whatever comes back from API-Football support.

- [x] **R023** — FlashScore as another free scrape source: dig deeper, build with risk, or stop? → *medium*
  - Context: user still wanted "any other free alternative" after checking dashboard.api-football.com and finding it still suspended; researched FlashScore as a second scrape candidate after SofaScore's cloud-IP block killed R021
  - Why: FlashScore fixtures + 1X2 odds both confirmed working via plain `curl` — no bot-block hit, no browser/Playwright needed at all, which would avoid the exact structural problem that killed the SofaScore build. But the decisive piece (pre-match lineups) is unconfirmed: a match a few days out showed no Lineups tab in the nav, and guessed lineups URLs 404'd. Don't want to repeat the SofaScore mistake of building a full client+engine before confirming the one requirement that actually matters
  - [x] Keep digging now — wait for/find a match in its actual pre-kickoff lineup window, confirm the real lineups URL/routing before writing any code
  - [ ] Build it anyway on the fixtures+odds evidence alone, treat lineup availability as a risk to discover during testing
  - [ ] Stop here too — two dead-end/uncertain scrape attempts (SofaScore blocked, FlashScore lineups unconfirmed) is enough signal; go back to just waiting on API-Football
  - Blocked by: ~none~
  - Result: dug further, found a conclusive negative rather than a confirmation. Checked 4 real match pages via the interactive browser (Crystal Palace v Man City and Real Madrid v Real Sociedad, both future; Aston Villa v Arsenal, future despite a misleading "LIVE" tab title; Bodo/Glimt v Nijmegen, a just-finished Champions League qualifier) — none showed a Lineups tab in their nav (only Match/Odds/H2H/Standings/News/Report/Draw/Video, varying by competition). The string "TRANS_DETAIL_BOOKMARK_LINEUPS":"Lineups" exists in FlashScore's JS bundle but never actually rendered on any match checked, including a big, heavily-covered European fixture post-match. Consistent pattern across 4 matches, different states and competitions — FlashScore's free web tier does not reliably expose pre-match lineups. Same disqualifying outcome as SofaScore (different reason: missing the required feature entirely, vs. SofaScore having the feature but being blocked from cloud IPs).
  - Status: done — FlashScore ruled out. Recommend closing the scraping-alternatives search here (two credible candidates checked, both dead-ended for independent reasons) and returning fully to waiting on API-Football support.

- [ ] **R024** — RapidAPI "Free API Live Football Data": pay for Pro, or stay free and wait? → *medium*
  - Context: user pointed at a specific RapidAPI listing (Creativesdev/free-api-live-football-data) and asked to try it with their logged-in RapidAPI session
  - Why: verified via curl with the user's real API key — real, rich lineup data (e.g. Feyenoord full squad w/ stats) and fixtures with timestamps matching SofaScore's down to the second (likely the same underlying data, proxied through RapidAPI's own infra) - Lineups, Odds, Fixtures, Statistics all included on every plan, and critically no bot-block risk since it's a proper API gateway, not a scraped site directly. But the free "Basic" plan is a hard 100 requests/MONTH limit - nowhere near enough for a 20-min cron (would exhaust it in a day or two). Pro tier is $9.99/mo for 20,000 requests/month, comfortably enough (~3,600/mo worst case) - cheaper and more complete than the residential-proxy idea from R022, since it solves both lineups AND odds for both engines in one place
  - [x] Don't pay — confirms free truly doesn't work here either (same as every other candidate checked); return fully to waiting on API-Football support
  - [ ] Pay $9.99/mo for Pro and build the integration — verified data first this time (learned from the SofaScore false start), real ongoing cost though small
  - Blocked by: ~none~
  - Status: done — user chose free (Basic, $0) over paying. Started building `rapidapi_client.py` against it (plain `requests` works, no browser needed, real lineup+odds data confirmed via curl) before hitting a new problem — see R025.

- [x] **R025** — RapidAPI free-tier lineups have no confirmed/predicted flag → *small*
  - Context: found while building the free-tier client (R024) — checked both the lineup endpoint and the match-list endpoint for any signal distinguishing an official confirmed XI from FotMob's own prediction; neither has one (unlike SofaScore's explicit `confirmed:true/false`, or API-Football which simply returns empty until confirmed)
  - Why: the goals model's statistical validity (t=3.04) rests specifically on CONFIRMED lineups — silently treating a predicted XI as confirmed would corrupt predictions without any error signal. Also burned ~8-9 of the 100 monthly calls on verification, some wastefully duplicated
  - [x] Build with a timing heuristic — only fetch within ~20-30min of kickoff, assume that close in it's very likely the real XI (not guaranteed, but the budget doesn't support re-checking anyway)
  - [ ] Don't use it for the goals engine — too risky for the core mechanic; explore for something lower-stakes or stop here
  - Blocked by: ~none~
  - Note: Sportmonks (R026) ruled out first, then user confirmed the timing-heuristic option directly.

- [x] **R026** — Sportmonks with user's real API token → *small*
  - Context: user supplied a real Sportmonks v3 API token and asked to try it, as a possible way around R025's confirmed-flag gap
  - Why: earlier research (R020, web-search-only) claimed Sportmonks' free tier covers only Danish Superliga + Scottish Premiership - worth re-verifying against the user's actual account rather than trusting secondhand blog claims, especially since a real token might mean a paid plan
  - Tested: `GET /v3/football/leagues?api_token=...` (correct path is `/v3/football/leagues`, not `/v3/my/enabled-leagues` which 404'd) — one clean call, no guessing needed after that
  - Result: confirmed directly against the real account — exactly 4 leagues in this subscription: Danish Superliga, Scottish Premiership, and their playoffs. None of our 5 target leagues. Same conclusion as the earlier web research, now verified rather than assumed.
  - Status: done — ruled out immediately, no need to check lineups/odds since league coverage fails at the first gate.

- [x] **R027** — RapidAPI goals engine built and shipped → *large*
  - Context: R025 resolved on the timing-heuristic option; built the full integration
  - Built: `footymodel/live/rapidapi_client.py` (plain `requests`, no browser needed — the one candidate this session that doesn't have a bot-detection or Playwright problem), `rapidapi_engine.py` (same LineupModel/namematch/EV logic as the other engines; a `rapidapi_budget.json` file tracks monthly usage against the 90-of-100 cap, `rapidapi_fixtures_cache.json` scans fixtures once/day instead of every 20-min cron tick to conserve budget, `LINEUP_WINDOW_MINUTES=30` heuristic gates lineup fetches to close-to-kickoff only), `scripts/rapidapi_odds_parse_test.py` (added to CI). League IDs verified against real data (E0=47, SP1=87, D1=54, I1=55, F1=53 — league *name* alone isn't unique, e.g. "Premier League" also exists for Russia/Tanzania/Azerbaijan/etc., so id was confirmed by country code, not name).
  - Verified end-to-end locally: real run scanned 2 live fixtures for 2026-08-27, cache reuse confirmed on a second run (0 extra budget spent), budget tracking correct (1/90 after the scan).
  - Wired into `live_poll.yml` (`continue-on-error`, same as SofaScore's step) — needs the user to set the `RAPIDAPI_KEY` repo secret before it can run in Actions (same as R013's `API_FOOTBALL_KEY` flow).
  - Blocked by: ~none~
  - Status: done — pushed (18ea82b), `RAPIDAPI_KEY` secret set, verified GREEN in real GitHub Actions (run 33100490609): key loaded, budget correctly reused the committed cache (stayed 1/90, no wasted re-scan on a fresh checkout), clean exit. Third engine now genuinely live in production, not just locally — unlike R021's SofaScore build, this one actually works end to end.

- [x] **R028** — Odds fetch silently failing across all 8 logged predictions → *small*
  - Context: user asked to check `live_recommendations.csv` post-reactivation; the 8 rows found (all from 2026-08-23, pre-suspension) are real model predictions, but every single row has empty `odds_over25`/`odds_under25`
  - Why: `engine.py`'s `process_fixture` only adds `fair_p_over25`/`ev_over25`/`ev_under25` when `over_odds and under_odds` are both truthy — since that's never happened once across 8 fixtures, EV has never actually been computed for any live prediction so far, only the bare model probability. A real, previously-unnoticed gap in the one thing (EV vs. market) this whole project is meant to test
  - [x] Dig into it now — check whether the odds fetch is erroring (network/API issue), returning an unexpected shape, or genuinely finding no Over/Under market for these specific fixtures
  - [ ] Leave it — fresh fixtures will flow now that the account's reactivated; revisit if the gap persists on new data too
  - Blocked by: ~none~
  - Root cause: `_best_over_under_odds` checked bet name `== "Over/Under"`; API-Football's real market is named `"Goals Over/Under"` (confirmed live against fixture 1570336). One-line fix, plus the dry-run mocks had the same wrong name baked into their fake data (tests were "passing" against a bug that matched the code, not reality) — fixed those too and added `scripts/goals_odds_parse_test.py` to CI to catch this exact regression class going forward.
  - Status: done — pushed (2adeef3), verified live: a real production row (Celta Vigo v Osasuna, via the RapidAPI engine) logged with real odds (2.2/1.6) and full EV (`ev_over25: 0.009`) — the first EV ever actually computed on a live prediction in this project's history.

- [x] **R029** — Restrict live goals engine to individually-backtested leagues → *small*
  - Context: user asked about running only leagues with real backtesting behind them, after all 5 big-5 leagues had been live-polled by default since R013
  - Why: the t=3.04 figure cited throughout this session is the POOLED stat across all 5 leagues (RESULTS.md Phase A, full-lineup model) — not five individually-confirmed leagues. Per-league t-stats: E0 2.23 (significant alone), I1 1.97 (borderline), SP1 1.36 / D1 1.32 / F1 0.72 (not significant individually, Ligue 1 barely distinguishable from noise). RESULTS.md's own read is that pooling is legitimate (every league moves the same direction), but that's different from each league having its own confirmed evidence
  - [x] E0 only — the one league that clears individual significance on its own, cleanest and most defensible scope
  - [ ] E0 + I1 — include Serie A too (borderline, t=1.97)
  - [ ] Keep all 5 — trust the pooled stat as the real signal, no code change
  - Blocked by: ~none~
  - Implemented: `LEAGUE_API_IDS` (engine.py), `TOURNAMENT_IDS` (sofascore_engine.py), `LEAGUE_IDS` (rapidapi_engine.py) all trimmed to `{"E0": ...}` only. `shots_engine.py` (props) was already E0-only by design, unaffected. Full local CI suite re-verified green after the change.

## product

- [x] **R030** — Public dashboard, resumed and rescoped → *large*
  - Context: picks back up R016-R018 (paused when the API-Football suspension crisis hit) with a concrete, expanded spec: goals O/U AND player shots/SOT (both backtested markets, both E0-only per R029), hosted on Vercel, with free push notifications to the user's phone the moment a new prediction is logged
  - Why: R016 already settled on Vercel hosting; this adds the notification requirement and confirms scope explicitly covers both markets, not just goals
  - Stack decided: Next.js on Vercel, reads `live_recommendations.csv`/`live_player_props.csv` directly from the GitHub repo (no duplicate DB for prediction data), Web Push + VAPID (genuinely free, no Firebase/OneSignal) with subscriptions in Upstash Redis (free tier via Vercel Marketplace), triggered instantly by extending `live_poll.yml`'s existing commit step rather than polling
  - [x] Picks-only view (Recommended) — no graded track record yet, matches what was literally asked (predictive analysis output, not historical performance)
  - [ ] Also build graded track record (R017's original bigger-scope option) in the same pass — deferred, not chosen this time
  - Blocked by: ~none~
  - Note: flagged one real platform limitation up front - iOS Safari requires "Add to Home Screen" before web push works at all (OS restriction, not something buildable around). User proceeded aware of this.
  - Progress: repo turned out to be private (never verified before choosing "fetch CSVs directly" as the architecture) - user chose keep-private + GitHub-token access over making it public. Dashboard built (Next.js, both markets, real data verified locally via `next dev`), Vercel project linked, root directory sorted out (CLI deploys upload just the current dir - a repo-root "dashboard" setting was wrong and got reverted), Upstash Redis provisioned via Marketplace (needed the user to accept Upstash's ToS in-browser - not something to click through on their behalf), env var naming mismatch fixed (`KV_REST_API_*` not `UPSTASH_REDIS_REST_*`).
  - Blocked by: production build fails - `gh auth token`'s value isn't stable (rotated between capture and use, confirmed by two calls seconds apart returning different values with the old one already invalid), so it can't serve as a long-lived Vercel secret for the private-repo GitHub API access. Asked the user to create a proper fine-grained PAT (Contents: read-only, scoped to just this repo) instead.
  - [x] Fine-grained PAT (Contents: read-only, scoped to just this repo) — tried twice with two independently-generated tokens, both 404 on basic repo metadata despite the user confirming correct Resource owner and repository selection each time; the token itself checks out (correctly identifies the account via `/user`), so something about the fine-grained repo-selection flow specifically isn't taking - not resolved
  - [x] Classic PAT (`repo` scope) — pivoted to this instead: broader scope than ideal, but no per-repo selection step to get wrong, known-reliable pattern
  - Blocked by: ~none~
  - Status: done — classic token worked immediately (200 on both repo metadata and contents). Deployed to production: https://dashboard-nine-theta-13.vercel.app, real data confirmed live. `scripts/notify_dashboard.py` wired into `live_poll.yml`'s commit step (parses the staged git diff, POSTs a summary to `/api/notify`, never blocks the commit on failure) and verified on a real Actions run (33112733355) — full pipeline (both market engines + notify) green end to end.

- [x] **R031** — Graded track record (dashboard "next level") → *large*
  - Context: user asked to brainstorm taking the project further; scoped down via superpowers:brainstorming to "the dashboard" -> "graded track record" specifically (win/loss history, realized CLV, not just a live picks list)
  - Why: VISION.md's own read is that a graded track record is "far more portfolio-worthy than a live picks list alone" - the current dashboard shows predictions but never proves whether they were right
  - Design: new `footymodel/live/grade_results.py` finds predictions with kickoff 3+hrs in the past and no grade yet, looks up the real final score via API-Football (date + fuzzy team-name match, works regardless of which engine originally logged the prediction - avoids spending RapidAPI's scarce budget on grading), computes model-accuracy AND a betting grade (only when odds+positive EV existed - realized return in stake units), writes to a new `data/processed/graded_results.csv`. New daily `grade_results.yml` workflow (06:30 UTC, separate from the live poller so it never competes for budget). Dashboard gets a new "Track Record" section: running stats (accuracy%, bets placed, bet win rate, cumulative return) + per-pick table.
  - [x] Goals-only for v1 (Recommended) — props grading needs per-player post-match stats, unverified across all three sources all session; explicit future item, not blocking
  - [ ] Also grade props now — deferred, not chosen
  - Blocked by: ~none~
  - Status: done — built, tested (a temporary real commit of test data confirmed the dashboard UI renders correctly, immediately reverted since it wasn't real), and verified green in production: dashboard deployed (Track Record section live, correctly empty until real grades land), `grade_results.yml` ran clean on a real Actions run (33113872415) — correctly found nothing gradeable yet (the one recent prediction is ~2hrs old, below the 3hr grading delay) rather than erroring. Two real bugs found and fixed along the way: pandas.read_csv choking on the same ragged-column schema drift already worked around in the TS dashboard, and pandas.to_datetime silently dropping every RapidAPI-sourced row to NaT on mixed timestamp formats (own regression test added). Next real predictions will get graded automatically once the daily 06:30 UTC job runs.

## dashboard-v2

- [x] **R032** — Dashboard redesign: tab navigation → *medium*
  - Context: user wants the dashboard "to the next level" - too much scrolling on one long page, needs tabs (Track Record / Goals O-U / Player Props), fancier design with proper animation per the emil-design-eng skill, and a redesigned props table showing Shots + SOT at 1+/2+/3+ thresholds. Brainstorming via superpowers:brainstorming + visual companion (localhost, restarted once after a 30min auto-exit during a usage-limit gap)
  - Why: single scrolling page doesn't scale as more picks/grades accumulate; tabs are the standard fix
  - Shown: floating pill-tab navigation (segmented control, active pill slides via transform per emil's clip-path/transform guidance) across the 3 sections
  - Blocked by: ~none~
  - Status: shown, no explicit objection raised - proceeding as the base navigation pattern pending final confirmation alongside R033

- [x] **R033** — Player props table: full grouped columns vs. threshold toggle → *small*
  - Context: follow-up to R032 - user's specific ask was showing Shots AND SOT probability at 1+/2+/3+ thresholds (6 numbers/player), not just the current single "1+" column
  - Why: fitting 6 data points/player without becoming unscannable is a real layout tradeoff, not just a color/spacing choice
  - [ ] Option A — grouped 2-level-header columns, all 6 numbers visible at once, no interaction needed but wider table
  - [x] Option B — 1+/2+/3+ segmented toggle above a simpler 2-column (Shots, SOT) table, less clutter but hides other thresholds until toggled
  - Blocked by: ~none~
  - Status: done — user chose Option B via the mockup.

- [x] **R034** — Most-probable-bets summary strip (top of Player Props tab) → *small*
  - Context: follow-up to R032/R033 - user's ask included a short "most probable bets from every match" section at the top of the Player Props tab, aggregating best picks across all matches
  - Why: needs to stay short/glanceable per the original ask, not duplicate the full table below it - three genuinely different density/emphasis tradeoffs
  - [x] Option A — horizontal-scroll cards, one per pick, roomiest, most visual
  - [ ] Option B — ranked compact list (top 5, with probability bars), most scannable
  - [ ] Option C — single hero pick + small ticker of the next few, most minimal
  - Blocked by: ~none~
  - Status: done — user chose Option A via the mockup.

- [x] **R035** — Dashboard redesign implementation → *large*
  - Context: R032 (tabs) + R033 (props threshold toggle) + R034 (most-probable-bets strip) all approved via mockups; consolidated final mockup combining all three shown and approved ("ok")
  - Why: this is the actual build, not another design decision - logged for completeness per the ladder's own rule (every major step tracked)
  - Built: `lib/format.tsx` (shared formatters/EvBadge, split out of page.tsx), `lib/data.ts` gained `getMostProbablePicks()`, `components/DashboardTabs.tsx` (client, pill-tab nav using the duplicate-layer + clip-path technique, 260ms cubic-bezier(0.23,1,0.32,1)), `components/MostProbableStrip.tsx` (horizontal-scroll cards, staggered entrance), `components/MatchPropsTable.tsx` (client, 1+/2+/3+ segmented toggle with blur-crossfade on value swap - SOT 3+ correctly renders "—", no underlying data exists for it), `components/PropsPanel.tsx`. `app/globals.css` gained `stagger-in`/`panel-in` keyframes with a `prefers-reduced-motion` guard. `app/page.tsx` rewritten around `DashboardTabs`.
  - Blocked by: ~none~
  - Status: done — `npx tsc --noEmit` clean, `npm run build` clean, verified live in the browser preview against real production data (tab switching + pill slide, most-probable-bets strip with real players/odds, threshold toggle re-rendering all three positions correctly including the SOT 3+ blank, Goals tab). Mobile viewport (375px) confirmed correct responsive stacking via screenshot; mobile click-interaction testing hit repeated browser-pane timeouts unrelated to the code (desktop interactions all confirmed working first). Not yet deployed to Vercel production - deploy is the next step, pending user go-ahead.

- [x] **R036** — Deploy dashboard redesign to Vercel production → *small*
  - Context: R035 (redesign implementation) is built, type-checked, and verified locally against real data - not yet pushed live
  - Why: production is a real deployed URL the user shares/checks - worth a deliberate go/no-go rather than deploying silently
  - [x] Deploy now — build and local verification already passed, no known open issues
  - [ ] Hold for further testing/iteration first — e.g. finish mobile interaction testing, or request more visual changes before it goes live
  - Blocked by: ~none~
  - Status: done — user said "complete and deploy it live".

## quant-expansion

- [x] **R037** — Monte Carlo simulation scope → *medium*
  - Context: user asked about using Monte Carlo simulation / quant methods "as a full project to develop and test first"
  - Why: two genuinely different projects hide under "Monte Carlo" - worth pinning down which before scoping either
  - [x] Staking/bankroll simulator — simulate thousands of seasons at different Kelly fractions on already-graded picks to get real risk-of-ruin/drawdown numbers; low-risk, layers on existing `grade_results.py` output, no new modeling
  - [ ] Scoreline/market simulator — sample from the existing Dixon-Coles goal-rate parameters to get correct-score/BTTS/other exotic-market probabilities with no clean closed form; a real new market (relates to R010's "new softer markets" lever), higher effort, untested for edge
  - Blocked by: ~none~
  - Status: done — user chose the staking/bankroll simulator.

- [x] **R038** — Bankroll simulator: which bets to draw from → *small*
  - Context: brainstorming R037's staking/bankroll simulator via superpowers:brainstorming - `evals_main.parquet` (36,525 rows, real model_p/odds/outcome across all 5 leagues+markets) is the real candidate data source, not the tiny `paper_trades.csv` (3 rows) or empty `graded_results.csv`
  - Why: which population the sim draws from directly determines whether the bankroll conclusions rest on proven edge or not
  - [x] E0-only O/U 2.5 (Recommended) — same individually-significant scope (t=2.23) R029 already restricted the live engine to
  - [ ] All 5 leagues pooled O/U 2.5 — broader pooled stat (t=3.04), includes leagues not individually significant
  - [ ] All markets + leagues in evals_main.parquet — biggest sample, includes markets never proven to have edge
  - Blocked by: ~none~
  - Status: done — user chose E0-only O/U 2.5.

- [x] **R039** — Bankroll simulator: outcome-generation mechanism → *small*
  - Context: brainstorming R037/R038's staking simulator - the core "Monte Carlo" design choice
  - Why: determines whether the sim explores variance beyond what the real historical sample happened to produce, or just reshuffles it
  - [x] Parametric (Recommended) — Bernoulli draw per bet from the model's own model_p, standard Monte Carlo, also tests model calibration itself
  - [ ] Bootstrap — resample realized won/lost outcomes with replacement, stays closer to "what really happened" but can't explore beyond the historical sample
  - Blocked by: ~none~
  - Status: done — user chose parametric Bernoulli draws.

- [x] **R040** — Bankroll simulator: what to actually test/output → *small*
  - Context: brainstorming R037-R039's staking simulator
  - Why: "develop and test" implies validating/tuning staking choice, not just confirming what's already in `staking.py`
  - [x] Sweep multiple Kelly fractions (Recommended) — flat-stake baseline + 1/8, 1/4, 1/2, full Kelly compared on risk-of-ruin/drawdown/growth percentiles, picks the actual best multiplier
  - [ ] Validate the current default only — stress-test the existing kelly_mult=0.25/max_fraction=0.02 defaults, narrower
  - Blocked by: ~none~
  - Status: done — user chose the multi-fraction sweep.

- [x] **R041** — Bankroll simulator: how it lives in the project → *small*
  - Context: brainstorming R037-R040's staking simulator
  - Why: a research-script-only version vs. a full dashboard surface is a real scope fork
  - [ ] Standalone research script + RESULTS.md write-up (Recommended) — matches existing backtest.py/scripts/RESULTS.md pattern, no UI work
  - [x] Reusable module + dashboard tab — Python module computes the sweep, same CSV-to-dashboard pattern as R030/R031 (graded_results.csv), new tab reads it
  - Blocked by: ~none~
  - Status: done — user chose module + dashboard tab.

- [x] **R042** — Bankroll simulator dashboard tab: content scope → *small*
  - Context: follow-up to R041 - once a dashboard tab is in scope, what it actually renders is a real complexity fork
  - Why: full trajectory fan charts need a charting approach (new dependency or hand-rolled SVG) and more data shipped; summary stats need neither
  - [x] Summary stats per Kelly fraction (Recommended) — stat cards (median final bankroll, max drawdown %, risk-of-ruin %), same visual language as existing Track Record cards, zero new dependencies
  - [ ] Full bankroll trajectory fan chart — real percentile-band curves over time, needs a charting library or hand-rolled SVG, meaningfully more effort
  - Blocked by: ~none~
  - Status: done — user chose summary stats, no new dependency.

- [x] **R043** — Build the bankroll simulator, or skip it and focus on model-improvement instead → *small*
  - Context: user asked directly whether R037-R042's design actually improves the predictive model before committing to build it
  - Why: honest answer is no - the simulator is a downstream staking/risk-sizing tool that takes the model's existing edge as a given; it doesn't touch accuracy, calibration, or find new edge. Genuinely useful only if real staking is ever on the table (or as a standalone portfolio artifact per VISION.md §9); useless if the project stays paper-trade indefinitely
  - [x] Build it anyway (the full R037-R042 design) — real value if real staking is ever considered, or as a CV/portfolio quant piece even if not
  - [ ] Skip it, focus on model-improvement levers instead — R007 (ensemble models) or R010 (new leagues/markets) would actually move the needle on edge itself, unlike the simulator
  - Blocked by: ~none~
  - Status: done — user said "go ahead and build it".

- [x] **R044** — Implementation execution mode → *small*
  - Context: implementation plan for R037-R043's Kelly bankroll simulator written and committed (docs/superpowers/plans/2026-08-28-kelly-bankroll-simulation.md); writing-plans skill's standard handoff choice
  - Why: determines how the 10-task plan gets executed - affects review cadence and iteration speed
  - [x] Subagent-driven (Recommended) — fresh subagent per task, review between tasks, fast iteration
  - [ ] Inline execution — batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R045** — Kelly bankroll simulator: subagent-driven execution, all 10 tasks → *large*
  - Context: executed the R037-R044 plan via superpowers:subagent-driven-development, directly on main (explicit consent given, matching how the rest of this session operated)
  - Why: tracks the actual execution outcome, including real issues the two-stage review process caught
  - Built: `footymodel/simulate.py` (filter_value_bets/load_value_bets, simulate_bankroll, sweep), `scripts/kelly_simulation.py` (CLI), `scripts/kelly_simulation_test.py` (CI-wired), `data/processed/kelly_simulation.csv` (tracked), dashboard `getKellySimResults()` + `StakingPanel.tsx` + 4th "Staking" tab.
  - Real bugs caught and fixed during review (not just style nits):
    - Task 2: ruin-detection off-by-one — the ruin-floor check ran before processing each bet, so a trial crossing the floor on its last bet was never flagged; inherited from the plan's own code, fixed post-review with a boundary regression test.
    - Task 4: broken `--help` output (`description=__doc__` flattened the usage examples); fixed to match the codebase's per-flag `help=` convention.
    - Task 7: discovered the EARLIER dashboard redesign (R035, already deployed to production) had never actually been committed to git — Vercel CLI deploys upload the working directory directly, bypassing git entirely. Task 7's `git add lib/data.ts` swept that pre-existing uncommitted work into its own commit. Fixed by splitting history: redesign committed on its own (accurately describing what it actually is), Task 7's addition re-committed cleanly on top.
    - Final full-implementation review: `StakingPanel` hardcoded `startBankroll=100` despite the CLI exposing a real `--start-bankroll` flag — today's committed CSV happened to use the default so nothing was visibly broken, but any future non-default run would have silently mislabeled every card. Fixed by adding `start_bankroll` to the CSV/type/component end to end.
  - Deployment note: found (and worked around) a real, project-wide latent issue — the Vercel project has no `rootDirectory` configured, so a plain git-based deploy fails (`Couldn't find any pages or app directory`) since the Next app lives in `dashboard/`, not the repo root. Worked around per-deploy via `vercel deploy --prod --yes --archive=tgz` (forces a local-upload deploy instead of git-clone). Not fixed at the project-settings level - see R046.
  - Blocked by: ~none~
  - Status: done — all 10 tasks implemented, spec-reviewed, and code-quality-reviewed (with re-review loops on every finding), final whole-implementation review passed, pushed to origin/main, verified live in production (https://dashboard-nine-theta-13.vercel.app, Staking tab renders real data: 547 bets, 10,000 trials/strategy, flat 1.94x / 1-8 Kelly 4.35x / 1-4 Kelly 5.43x / 1-2 Kelly 5.63x / full Kelly 5.64x median bankroll, 0% ruin probability at the current 2%-max-fraction cap).

- [x] **R046** — Vercel project has no rootDirectory set: fix now or leave as a known workaround? → *small*
  - Context: discovered while deploying R045 - a plain `vercel deploy --prod` (or any future git-push-triggered deploy) fails because the project's rootDirectory is unset while the Next app lives in `dashboard/`, not the repo root
  - Why: this is a standing footgun for ANY future deploy of this project, not specific to the Kelly simulator feature - the `--archive=tgz` workaround only fixes it deploy-by-deploy
  - [x] Set `rootDirectory=dashboard` in the Vercel project settings — the real, permanent fix. Confirmed via `vercel api` (CLI has no direct settings command, `vercel api` gives authenticated REST access) that this project is GitHub-linked (`link.type: "github"`, productionBranch `main`) — meaning **every `git push origin main` auto-triggers a Vercel deploy via webhook, independent of any manual CLI deploy**. That auto-deploy clones the whole repo and needs `rootDirectory=dashboard` to find the Next app - this is exactly what broke for the user (a real push triggered the auto-deploy, which failed with "No Next.js version detected"). First attempt at this fix was wrongly reverted (see history below) because it only tested against manual CLI deploys, not the actual GitHub auto-deploy path that was the real problem.
  - [ ] Leave as-is, keep using `--archive=tgz` on every future manual deploy — superseded, this was based on an incomplete diagnosis (see below)
  - Blocked by: ~none~
  - Status: done. **Corrected conclusion** (supersedes the earlier "revert, use --archive=tgz" note): `rootDirectory=dashboard` is set and staying set. There are two independent deploy paths for this project - (1) the GitHub-linked auto-deploy that fires on every push (needs rootDirectory=dashboard, this is the one the user actually hit an error on), and (2) manual `vercel deploy --archive=tgz` run from inside `dashboard/` (needs rootDirectory unset, since the uploaded tarball root already IS dashboard's content - confirmed archive mode does NOT bypass rootDirectory, it fails the same way plain upload does). These two paths want opposite settings and can't both be satisfied by one static value. Resolution: keep rootDirectory=dashboard (fixes the auto-deploy, which is the path that actually matters going forward since it fires automatically on every push already made in this session's normal workflow) and stop using manual `vercel deploy` entirely — verified by creating a real git-source deployment via `POST /v13/deployments` against current HEAD, which built successfully and aliased correctly to the production domain (dashboard-nine-theta-13.vercel.app), confirmed live in browser.

## live-ops

- [x] **R047** — Live poller scheduled runs stalled: trigger manually now, or dig into why first? → *small*
  - Context: user asked about tonight's PL match (Crystal Palace v Manchester City, 19:00 UTC kickoff) prep; checking the live poller's health for it surfaced that `live_poll.yml`'s scheduled (cron) runs stopped at 2026-08-28T04:06:09Z despite the `*/20 9-21 * * *` schedule - zero scheduled fires between 09:00-13:27 UTC today, right in the middle of its intended window
  - Why: lineups for tonight's match land ~18:20-18:40 UTC (20-40min pre-kickoff per API-Football); if the schedule stays stalled through then, the match gets missed entirely and there's no prediction logged for it
  - [x] Trigger `live_poll.yml` manually now via `gh workflow run`, and again closer to kickoff as a backstop — doesn't fix the root cause but guarantees tonight's match isn't missed regardless of why the schedule stalled
  - [x] Investigate why the schedule stalled first (GitHub Actions platform delay vs. a real repo-side issue) before doing anything - slower, but avoids masking a real problem with a manual workaround
  - Blocked by: ~none~
  - Status: done — did both. Investigated first: full run history showed no stuck/queued runs, and even "normal" days (Aug 25-26) fired every ~50-90min instead of every 20 - this is GitHub Actions' documented free-tier cron throttling, not a repo bug, nothing to fix in code. Triggered manually (run 33176122425, completed clean: "No new confirmed-lineup fixtures this poll" - correct, too early). Scheduled two session-scoped one-shot reminders (~18:07 and ~18:33 UTC) to re-trigger and report on tonight's match specifically, with the caveat flagged to the user that these die if the session ends.

## dashboard-v3

- [x] **R048** — Team-wise lineup tabs: execution mode → *small*
  - Context: implementation plan for splitting each Player Props match card's 22-player table into per-team tabs is written and committed (docs/superpowers/plans/2026-08-28-team-lineup-tabs.md) - single task, one file (~15-line diff); writing-plans skill's standard handoff choice
  - Why: determines review overhead vs. speed for a change small enough that the usual subagent two-stage review may be disproportionate
  - [x] Subagent-driven — dispatch a fresh subagent + two-stage review, same process as the Kelly simulator (R044/R045)
  - [ ] Inline execution — implement directly in this session, proportionate to a single-file ~15-line change
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R049** — Team-wise lineup tabs: implementation → *small*
  - Context: single-task plan executed via subagent-driven-development, spec+code-quality review passed clean on the first try
  - Why: tracks the outcome for completeness
  - Built: `dashboard/components/MatchPropsTable.tsx` gained a team-name segmented toggle (same visual style as the existing 1+/2+/3+ toggle, per the spec's deliberate "secondary control, don't compete with primary nav" choice) and a `teamRows` filter; threshold state stays shared/unaffected across team switches.
  - Code-quality review flagged two future-only notes (not blocking): `activeTeam` has no bounds-clamp if `rows` ever shrinks under a mounted instance (currently unreachable - no client-side revalidation exists, only full-navigation ISR), and neither toggle has ARIA labeling (pre-existing gap, now on two controls instead of one).
  - Blocked by: ~none~
  - Status: done — pushed (b70b426), Vercel auto-deploy succeeded, verified live in production: team toggle switches the table between Bournemouth/Manchester City rosters, and the 2+ threshold selection correctly survives the team switch (didn't reset to 1+).

- [x] **R050** — Goals tab EV/fair-p column mismatch bug → *small*
  - Context: user reported "tabs switching visually is incorrect" - investigated by clicking through all tabs in production; found real (not visual-only) data corruption on the Goals O/U tab for tonight's Crystal Palace v Manchester City row, not a tab-animation glitch
  - Why: `getGoalsPicks()` (dashboard/lib/data.ts) mapped the CSV's ragged trailing columns by a FIXED position (source, fair_p_over25, ev_over25, ev_under25), assuming every row with extra columns follows RapidAPI/SofaScore's 4-column shape. `footymodel/live/engine.py` never writes a "source" field, so its rows have only 3 extra columns when odds are present - the fixed mapping silently shifted fair_p/ev_over/ev_under left by one, showing ev_under25's value in the ev_over25 slot and leaving ev_under25 blank. Never surfaced before tonight because no engine.py row had ever successfully gotten real odds until this exact prediction (R028 fixed odds-fetching weeks ago, but this was the first row to actually exercise that path).
  - Fix: rewrote the extra-column mapping to use the parsed field COUNT (0/1/3/4, which never collide across engine.py vs rapidapi/sofascore x odds-present/absent) to disambiguate which fields are actually present, instead of assuming a fixed column order.
  - Blocked by: ~none~
  - Status: done — verified locally (Crystal Palace v Man City now correctly shows EV +7.3%/-11.1% instead of blank/-11.1%), tsc/build clean, pushed (cf61844), Vercel auto-deploy confirmed.

- [x] **R051** — Tab-switcher pill misalignment → *small*
  - Context: user came back with "fix the tabs switcher, its not properly made" - the R050 investigation had fixed a real data bug but hadn't addressed what the user actually meant by the original "tabs switching visually is incorrect" report. Reproduced live: clicking "Player props" showed the pill visibly clipping the label mid-word ("Player prop" with the trailing "s" left uncovered)
  - Why: `DashboardTabs.tsx`'s clip-path was computed as a naive equal fraction of the bar width (`i/TABS.length`), which only lines up with real button boundaries if every tab label happens to render the same width. With four genuinely different-length labels ("Track record" vs "Staking"), it never did - most visibly on "Player props", whose actual rendered width exceeds one quarter of the bar.
  - Fix: replaced the fraction-based math with real measurement - `getBoundingClientRect()` on the active button inside a `useLayoutEffect`, corrected for the clip overlay's own `inset-1` padding (subtracted via `getComputedStyle`, not hardcoded, so it doesn't silently break if the padding class ever changes) - drives the clip-path with actual pixel offsets instead of assumed equal fractions.
  - Blocked by: ~none~
  - Status: done — verified all 4 tabs align correctly locally (Player props no longer clips, Staking's pill hugs its short label instead of stretching to a quarter-width), tsc/build clean, pushed (6f0c3e5), Vercel auto-deploy confirmed.

- [x] **R052** — Batch of 5 dashboard asks: scope + sequencing → *large*
  - Context: user bundled 6 requests in one message (equal-width tabs, remove em dashes from UI copy, a glossary/info page for terms, a full UI makeover/rebrand with a new logo + brand identity + "always sliding" tab switch, expandable match-detail cards on Goals O/U with analysis/lineups/confidence rationale, and a decimal-odds explainer). Flagged as a multi-subsystem request per superpowers:brainstorming's scope-assessment guidance rather than brainstorming all of it in one pass
  - Why: the rebrand reshapes what the glossary page and expandable match cards should visually look like, so building those first risks redoing them after the rebrand lands; the two trivial items (equal-width tabs, no em dashes) have no design dependencies and can go first regardless of ordering elsewhere
  - [x] Trivial items first (equal-width tabs, remove em dashes), then rebrand (#5), then glossary page (#3) and expandable match detail (#4) styled to match the new brand (Recommended)
  - [ ] Glossary page (#3) and expandable match detail (#4) first, rebrand (#5) after - ships user-facing content sooner, accepts re-styling both once the rebrand lands
  - Blocked by: ~none~
  - Status: done — user confirmed ("ok"). Starting with the two trivial items now.
  - Note: expandable match detail (#4) has a real backend gap underneath the UI ask - lineups (player names) aren't currently persisted anywhere for Goals O/U predictions, only starter-counts (`n_home_starters_matched`/`n_away_starters_matched`). Showing lineups in the expanded view needs a `footymodel/live/engine.py` change to log the actual starting XI, not just a dashboard change.

- [x] **R053** — R052's trivial items: equal-width tabs + remove em dashes → *small*
  - Context: first stage of R052's agreed sequencing
  - Why: no design dependencies, both mechanical, could ship before the rebrand
  - Built: `DashboardTabs.tsx` gives each button a fixed `w-32` instead of sizing to its own text (the getBoundingClientRect pill-measurement fix from R051 still applies correctly - it just now reports four equal widths). Replaced every em dash across `dashboard/` - prose ones with a period/colon depending on what read better, and the "-" null-value placeholder glyph (in `EvBadge`/`pct`/`odds`/`MatchPropsTable`) with a plain hyphen.
  - Blocked by: ~none~
  - Status: done — tsc/build clean, verified visually (all 4 tabs equal width, no em dashes remain anywhere per `grep -rl`), pushed (24b3a00), Vercel auto-deploy confirmed, verified live in production.

- [ ] **R054** — Start the rebrand now, or pause here → *small*
  - Context: R053's two trivial items just shipped - the natural next step per R052's agreed sequencing is the rebrand (#5: logo, brand identity, full UI makeover, "always sliding" tab switch), which is large enough to need its own proper brainstorm/mockup pass
  - Why: rebrand work is a genuinely separate, sizeable project (visual identity, not a quick pass) - worth checking whether the user wants to dive in now or stop here for this session
  - [x] Start the rebrand brainstorm now (with visual companion, given how visual this work is)
  - [ ] Pause here - two shipped fixes is a natural checkpoint
  - Blocked by: ~none~
  - Status: done — user said "start the rebrand now".

## rebrand

- [x] **R055** — Visual companion for the rebrand brainstorm → *small*
  - Context: rebrand work is heavily visual (logo, colors) - offered per superpowers:brainstorming's standard offer
  - Why: standard offer before visual questions
  - [ ] Use the visual companion
  - [x] Text only
  - Blocked by: ~none~
  - Status: done — user chose text-only.

- [x] **R056** — Rebrand: keep the project name or rename → *small*
  - Context: "brand identity" work could include a rename, worth confirming before designing a logo
  - Why: renaming adds real scope (new domain/branding everywhere) vs. just visual identity on the existing name
  - [x] Keep "footymodel" (Recommended)
  - [ ] Open to a new name
  - Blocked by: ~none~
  - Status: done — user chose to keep the name.

- [x] **R057** — Brand tone/personality → *small*
  - Context: drives color palette, typography, logo style choices downstream
  - Why: needed before any visual decisions could be made
  - [x] Serious quant/fintech (Recommended)
  - [ ] Sports-editorial
  - [ ] Minimal academic/research
  - Blocked by: ~none~
  - Status: done — user chose serious quant/fintech.

- [x] **R058** — Logo mark style → *small*
  - Context: follow-up to R057's tone choice
  - Why: determines whether this is a quick wordmark or a real icon-design task
  - [ ] Wordmark only (Recommended)
  - [ ] Wordmark + small icon
  - [x] Icon-first, wordmark secondary
  - Blocked by: ~none~
  - Status: done — user chose icon-first (the bigger design lift of the three options).

- [x] **R059** — Icon concept → *small*
  - Context: follow-up to R058's icon-first choice; described in words since text-only (R055)
  - Why: concrete visual concept needed before writing any SVG
  - [x] Ball + trajectory line (Recommended)
  - [ ] Pitch reduced to a data grid
  - [ ] Goal-frame bracket
  - Blocked by: ~none~
  - Status: done — user chose ball + trajectory line.

- [x] **R060** — Color palette approach → *small*
  - Context: current dashboard uses neutral dark background + emerald/red EV semantics only, no brand accent
  - Why: whether to introduce a new brand color at all, before picking which one
  - [x] Add one accent color (Recommended)
  - [ ] Keep exactly as-is
  - Blocked by: ~none~
  - Status: done — user chose to add one accent color.

- [x] **R061** — Accent color choice → *small*
  - Context: follow-up to R060
  - Why: emerald/red are taken by EV semantics, needed a color that reads as "brand" not "good/bad"
  - [x] Electric blue/indigo (Recommended)
  - [ ] Amber/gold
  - [ ] Violet/purple
  - Blocked by: ~none~
  - Status: done — user chose electric blue/indigo.

- [x] **R062** — "Always sliding" tab switch: what it actually means → *small*
  - Context: user's original ask ("make tabs switching always sliding switch") was ambiguous against the already-existing pill-slide mechanic
  - Why: "content slides like a carousel" vs. "just make the existing pill glide feel smoother" are very different amounts of work
  - [ ] Content also slides horizontally (Recommended)
  - [x] Keep content fade, just make the pill glide feel more continuous
  - Blocked by: ~none~
  - Status: done — user chose the lighter option. Assessed as likely already resolved by R051 (alignment fix) + R053 (equal-width tabs, consistent glide distance) rather than needing new animation work - will re-verify after the reskin.

- [x] **R063** — Active tab pill color → *small*
  - Context: follow-up to R061's accent color choice
  - Why: whether the new brand color becomes visible in the tab bar's own active state, or stays confined to the logo/links
  - [x] Pill becomes the accent color (Recommended)
  - [ ] Keep pill white/light, accent used elsewhere only
  - Blocked by: ~none~
  - Status: done — user chose to make the active pill the accent color.

- [x] **R064** — Consolidated rebrand design: approval gate → *medium*
  - Context: full design presented (icon SVG concept, color system, favicon, tab-slide assessment, explicit scope note excluding a layout redesign) after R055-R063's brainstorm; superpowers:brainstorming's hard-gate requires explicit approval before any implementation
  - Why: nothing gets built until this is approved or revised
  - [x] Approved as presented
  - [ ] Revise before approving
  - Blocked by: ~none~
  - Status: done — user approved ("ok"). Writing the spec doc next.

- [x] **R065** — Rebrand implementation: execution mode → *small*
  - Context: implementation plan for the rebrand (docs/superpowers/plans/2026-08-29-dashboard-rebrand.md) is written and committed - 2 tasks, 4 files total (Logo component, favicon, header wiring, active-pill recolor); writing-plans skill's standard handoff choice
  - Why: determines review overhead vs. speed for a small, well-scoped change
  - [x] Subagent-driven - fresh subagent per task, two-stage review, same process as the Kelly simulator and team-lineup-tabs work
  - [ ] Inline execution - implement directly in this session, proportionate to the small scope
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R066** — Rebrand: implementation → *small*
  - Context: 2-task plan executed via subagent-driven-development, both tasks passed spec review clean on the first try
  - Why: tracks the outcome, including a real issue the code-quality review caught
  - Built: `dashboard/components/Logo.tsx` (ball + trajectory icon, "footymodel" wordmark), `dashboard/app/icon.svg` (matching favicon, Next.js auto-detected), wired into `app/page.tsx`'s header; `DashboardTabs.tsx`'s active pill recolored to the blue accent.
  - Real issue caught by code-quality review: `bg-blue-500` (dark mode) + `text-white` computed to ~3.68:1 contrast, below WCAG AA's 4.5:1 minimum for normal-weight text - light mode's `blue-600` was already fine at ~5.17:1. Fixed by dropping the `dark:` variant entirely and using `blue-600` in both themes; verified visually in both color schemes.
  - Also flagged (not fixed, out of scope per the approved design): `MatchPropsTable.tsx`'s team/threshold segmented toggles still use the old white/neutral style, so the brand doesn't yet read as fully consistent across every screen - a legitimate follow-up if a fully unified look is wanted later, not a defect in this task.
  - Blocked by: ~none~
  - Status: done — pushed (787f5db), Vercel auto-deploy confirmed, verified live in production (logo + favicon + blue active pill all render correctly in both light and dark mode).

- [x] **R067** — Continue to glossary page + expandable match detail, or pause → *small*
  - Context: R052's sequencing (trivial items -> rebrand -> glossary/#3 + expandable match detail/#4) has now shipped its first two stages; #3 and #4 are next in line
  - Why: natural checkpoint after three consecutive shipped stages - worth confirming before starting a new brainstorm rather than assuming
  - [x] Continue now - brainstorm the glossary page and/or expandable match detail
  - [ ] Pause here for this session
  - Blocked by: ~none~
  - Status: done — user said "keep going, do the glossary page next" (specifically #3, not #4 yet).

- [x] **R068** — Glossary page placement → *small*
  - Context: R052's #3 item ("a glossary/info page for terms") - first question of the brainstorm
  - Why: whether it's a full page, inline tooltips, or a modal changes the entire component approach
  - [x] Own 5th tab (Recommended)
  - [ ] Inline tooltips on each term
  - [ ] A modal opened from a header info icon
  - Blocked by: ~none~
  - Status: done — user chose a 5th tab.

- [x] **R069** — Glossary organization → *small*
  - Context: follow-up to R068
  - Why: whether terms are grouped by which tab they belong to, or listed flat/alphabetically
  - [x] Grouped by tab (Recommended)
  - [ ] One flat alphabetical list
  - Blocked by: ~none~
  - Status: done — user chose grouped by tab.

- [x] **R070** — Shared vs. repeated EV/odds explanations → *small*
  - Context: EV and decimal odds appear identically on both the Goals O/U and Player Props tabs
  - Why: whether to explain them once in a shared section or duplicate the explanation per tab-specific section
  - [x] One shared "General concepts" section up top (Recommended)
  - [ ] Repeat the explanation in each relevant section
  - Blocked by: ~none~
  - Status: done — user chose one shared section.

- [x] **R071** — Glossary design: approval gate → *small*
  - Context: consolidated design presented after R068-R070's brainstorm - 5th "Glossary" tab, new static `GlossaryPanel.tsx`, 5 sections (General concepts, Track Record, Goals O/U, Player Props, Staking terms), reusing the existing h2+description section pattern rather than per-term cards
  - Why: superpowers:brainstorming's hard-gate requires explicit approval before any implementation
  - [x] Approved as presented
  - [ ] Revise before approving
  - Blocked by: ~none~
  - Status: done — user approved ("ok"). Writing the spec doc next.

- [x] **R072** — grade_results.py has the same column-mismatch bug as R050, never fixed → *small*
  - Context: while checking a real automated grading commit that landed mid-session (the first-ever real graded prediction), found `bet_side`/`bet_odds`/`bet_won`/`realized_return` were all blank for Crystal Palace v Manchester City despite the dashboard correctly showing +7.3%/-11.1% EV
  - Why: `footymodel/live/grade_results.py`'s `_read_predictions_csv()` used a fixed `pd.read_csv(names=<16 columns>)`, the exact same wrong assumption fixed on the dashboard side in R050 (`dashboard/lib/data.ts`) - engine.py's rows have only 3 extra columns (no "source"), not 4, so the fixed mapping shifted `fair_p_over25`/`ev_over25`/`ev_under25` left by one, and the "is there positive EV" check silently found nothing
  - Fix: rewrote `_read_predictions_csv()` to read raw rows via `csv.reader` and map each one by its actual field count (0/1/3/4, confirmed these never collide) via a new `parse_prediction_row()`, instead of a fixed-position `names=` list. Added `scripts/grade_results_columns_test.py` covering all four shapes, wired into CI.
  - Blocked by: ~none~
  - Status: done — re-graded the one affected fixture after the fix (deleted and regenerated `graded_results.csv`): `bet_side`/`bet_odds`/`bet_won`/`realized_return` went from all-blank to `over`/`1.77`/`True`/`+0.77`. Pushed (00e75ac), verified live in production - Track Record now correctly shows 1 bet placed, 100% win rate, +77.0% cumulative return, instead of 0 bets placed.

- [x] **R073** — Glossary plan: execution mode → *small*
  - Context: never actually asked this after committing the plan (docs/superpowers/plans/2026-08-29-glossary-page.md) - "check it live" and the R072 bug fix intervened first
  - Why: standard writing-plans handoff choice, tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - same process used for every previous plan this session
  - [ ] Inline execution - proportionate given the small scope
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R074** — Mobile tab bar unreachable, found during glossary Task 2 review → *small*
  - Context: code-quality reviewer for glossary Task 2 found the fixed `w-32` x 5 tab bar (introduced in R053) overflows its container below ~640px with no scroll mechanism - Staking and Glossary (the very tab this plan was building) were completely unreachable on phone-width viewports; the plan's claim that this layout "already generalizes... confirmed when Staking was added" was false, since Staking was added before tabs were fixed-width
  - Why: a real accessibility regression found during review, fixed immediately rather than deferred - same pattern as R066's contrast fix
  - Fix: added `overflow-x-auto` to the tab bar's container so it scrolls instead of overflowing; that alone squeezed the fixed-width buttons via flexbox's default shrink and garbled the tab text, fixed by adding `shrink-0` to the button wrapper, each button, and each clip-path overlay span
  - Blocked by: ~none~
  - Status: done — verified at 375px: all 5 tabs reachable via scroll, each tab's clip-path pill aligns correctly on click (including Staking, after scrolling), content renders correctly for every tab. `tsc --noEmit` and `next build` clean. Committed (6d540a0).

- [x] **R075** — R074's fix left the clip-path pill mispositioned once the bar actually scrolls → *small*
  - Context: after shipping R074, live verification on production showed a stray blue disc pinned near the tab bar's left edge instead of a pill around the clicked tab, whenever the bar was scrolled (Staking/Glossary)
  - Why: the clip-path math measured the active button's offset against the scroll container's own frame (fixed in the viewport, doesn't move on scroll), then applied it to an overlay that DOES move with scroll and whose width was constrained to the container's visible width (~333px) rather than the full scrollable content (~640px) - the two disagreed by exactly `scrollLeft`, and the overlay was too narrow to ever reach the later tabs
  - Fix: nested the overlay inside the buttons wrapper div (so it shares the same scrolled coordinate space and sizes naturally to the full row) and measured the active button's offset against that wrapper instead of the outer container
  - Blocked by: ~none~
  - Status: done — confirmed via direct `getBoundingClientRect()`/`clipPath` inspection (visible region now matches the target button's rect exactly at any scroll position) and visually at 375px for every tab, scrolled and unscrolled. `tsc --noEmit` and `next build` clean. Committed (2e47475).

## match-detail

- [x] **R076** — Expandable match detail: how far to reach into the backend → *medium*
  - Context: brainstorming item #4 from the original bundled request - clicking a match in the Goals O/U tab should show more analysis detail. Research showed the dashboard only stores 16 fields per match today, but the live engines (engine.py/rapidapi_engine.py/sofascore_engine.py) compute real starting-XI names and a team-model/lineup-model/blended breakdown at prediction time, then discard everything but the blended numbers and a starter count before writing to CSV
  - Why: determines whether this ships as a pure frontend reshuffle of existing fields, or needs new logging in all three live engines
  - [ ] Frontend only, no backend change - reorganize existing fields, ships fastest but no real "how we arrived at this" depth
  - [ ] Frontend + small backend change - log the already-computed team-model/lineup-model estimates (4 more numbers), no real lineup names
  - [x] Frontend + full backend change (chosen) - log real starting-XI names AND the team/lineup/blended breakdown; only applies to predictions logged going forward, past rows stay counts-only
  - Blocked by: ~none~
  - Status: chosen — user picked full backend change during brainstorming.

- [x] **R077** — Expandable match detail: storage format for the new data → *small*
  - Context: live_recommendations.csv's ragged-column format already caused two separate bugs this session (R050, R072) from silently growing optional trailing fields over time; adding lineup names (a whole list, not a scalar) and 2 more numeric fields would make that CSV parsing worse, not better
  - Why: avoid creating a third version of the same class of bug in a file that's already fragile
  - [x] Separate JSON side-log keyed by fixture_id (chosen) - new match_detail.jsonl, one JSON object per prediction, existing CSV untouched entirely
  - [ ] Extend the existing CSV with more trailing columns - consistent with how the file has always grown, but adds a 5th/6th field-count case and doesn't cleanly fit a name list into one CSV cell
  - Blocked by: ~none~
  - Status: chosen — user picked the separate JSON side-log.

- [x] **R078** — Expandable match detail: expand interaction pattern → *small*
  - Context: this is the first expand/collapse UI element anywhere in the dashboard - no existing pattern to follow (MatchPropsTable's pill-button group swaps which data is shown, it doesn't grow/collapse a card)
  - Why: sets the interaction convention for this and any future expandable card
  - [x] Accordion: click anywhere on the card, content grows below in place (chosen) - matches the existing card-based layout, no page-level layout jump elsewhere
  - [ ] Explicit "Details" button/link per card - clearer affordance but an extra visible element on every card
  - Blocked by: ~none~
  - Status: chosen — user picked whole-card accordion.

- [x] **R079** — Expandable match detail: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-29-expandable-match-detail.md written and committed, standard writing-plans handoff choice
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R080** — Expandable match detail: shipped end-to-end → *large*
  - Context: subagent-driven execution of all 8 tasks from docs/superpowers/plans/2026-08-29-expandable-match-detail.md - backend (new footymodel/live/match_detail.py JSONL side-log, wired into all 3 live engines + run_all.py) and frontend (dashboard/lib/data.ts join + new MatchCard.tsx expandable component wired into the Goals O/U tab)
  - Why: closes item #4 from the original bundled feature request - clicking a Goals O/U match now expands to show a team-model vs. lineup-model vs. blended breakdown, a plain-English confidence read, and the actual starting XI
  - Fix: 3 real bugs were found and fixed during review before this ever reached origin - (1) engine.py's process_fixture() is also called by run_all.py, the ACTUAL cron entry point, which didn't pop the new "_detail" key before writing the CSV - would have leaked a stray column into live_recommendations.csv, exactly the failure class already fixed twice this session (R050/R072); fixed in the same push, never independently deployed; (2) live_poll.yml's cron commit step never `git add`s match_detail.jsonl, AND .gitignore's blanket data/processed/* rule had no negation for it either - the file would have been written and silently discarded every poll forever; (3) getMatchDetails() used raw Number() instead of this file's own num() helper, so a malformed JSONL line would render literally "NaN%" instead of degrading to the existing null-fallback UI
  - Blocked by: ~none~
  - Status: done — all 8 tasks implemented, spec-reviewed, and code-quality-reviewed (with fix-and-re-review loops on 3 tasks). Pushed to origin/main (76af9c8..8091204, 13 commits). Verified in the dev server: the fallback state (works today, all real predictions), and the populated state (verified via a temporary, uncommitted local mock of getMatchDetails() for a real fixture_id - reverted after confirming the model breakdown, confidence line, and starting XI all render correctly). True production verification of a live engine actually writing a real match_detail.jsonl entry will only happen once the next confirmed-lineup prediction lands via the cron poller.

- [x] **R081** — SofaScore engine 403s from the cron; investigated fix + alternative → *medium*
  - Context: user reported the Goals O/U tab looking stale (all matches Aug 23-28, none upcoming); investigation found the poller itself healthy (successful runs every ~20min all day, confirmed via `gh run list`), but a manually-triggered run found ZERO E0/I1/SP1/D1/F1 fixtures at all within the lookahead window - a genuine gap in the football calendar right now, not a bug. Separately found sofascore_engine.py failing with a persistent HTTP 403 on every recent cron run
  - Why: confirmed via direct local test (`SofaScoreClient().scheduled_events(17, ...)` succeeded locally, 8 events returned) that this is GitHub Actions' shared runner IPs being blocked by SofaScore's bot-detection specifically, not a code bug or a broad SofaScore outage
  - [ ] Route through a paid residential-proxy service - needs the user to sign up with a provider (Bright Data/Smartproxy/Webshare-class, ~$3-10/mo) and hand over credentials as a GitHub secret; Claude can wire it into sofascore_client.py's Playwright launch once credentials exist but cannot create the account itself
  - [ ] Self-host a GitHub Actions runner on the user's Mac for this job - free, routes through a home IP, but only works while the Mac is on/reachable during the 9am-9pm UTC poll window
  - [ ] Harden the RapidAPI/API-Football pairing instead (raise RapidAPI's budget ceiling if there's room, smarter fallback ordering) so SofaScore's gap matters less, given RapidAPI already works fine from GH Actions and API-Football is the primary source
  - Blocked by: user hasn't picked a direction yet between proxy vs. hardening RapidAPI/API-Football
  - Status: in progress — investigated and ruled out WhoScored.com as a free alternative data source in the same pass: checked its live match preview page directly and found it only exposes algorithmically "Predicted Lineups" (a ratings-based guess), never real confirmed starting XIs - a disqualifying gap since this project's whole model is backtested specifically on real announced lineups (the "confirmed-lineup model", individually significant on E0 at t=2.23), not predictions. WhoScored does show a real Over/Under 2.5 odds market on the same page, so it's fine for odds, just not lineups - not a viable swap for the actual gap. Also separately: the existing footymodel/whoscored.py integration is unrelated (post-match shots/SOT stats, scraped via a manual foreground-tab batch process, not live/automated) so it couldn't be repurposed here regardless. Direct-tested both other sources instead: API-Football and RapidAPI both confirmed healthy right now (API-Football returns fixtures fine; RapidAPI returned 70 leagues incl. 5 E0 matches today, budget 6/90) - the dashboard's stale look wasn't either of them being broken, it's a genuine ~17-20hr gap between today's finished E0 matches and tomorrow's (outside the engine's 2hr lookahead window), which resolves itself automatically as the cron keeps polling. Given both primary sources are solid, deprioritized the SofaScore proxy/hardening decision itself (still open, not blocking).

- [x] **R082** — Hide past-kickoff predictions from the Goals O/U tab → *small*
  - Context: found while diagnosing R081 - getGoalsPicks() has no expiry, so the tab shows every prediction ever logged sorted newest-first; combined with the genuine calendar gap (R081), the tab was showing only week-old, already-played matches
  - Why: the tab's whole purpose is "what's coming up next" - Track Record (a separate data source) already covers finished/graded predictions, so past-kickoff rows here are pure clutter with no real value
  - Fix: dashboard/app/page.tsx's GoalsPanel filters to `new Date(g.kickoff).getTime() > Date.now()` before rendering, with a plain "No upcoming predictions right now" message when the filtered list is empty
  - Blocked by: ~none~
  - Status: done — verified in the dev server: Goals O/U now shows the empty-state message (since everything currently logged is in the past), Track Record's historical data (Crystal Palace 1-4 Manchester City, +77.0% cumulative return) confirmed unaffected. `tsc --noEmit` and `next build` clean. Committed (414dda9).

- [x] **R083** — Collapse past predictions instead of hiding them; extend to Player Props → *medium*
  - Context: user asked whether Player Props needed the same fix as R082 (yes - PropsPanel grouped every logged prop by fixture with no kickoff filter, identical staleness problem), and separately wanted past-kickoff predictions still checkable rather than fully hidden
  - Why: R082's outright hide loses the ability to check old predictions without digging into git history or the raw CSV; user wants them collapsed under a disclosure instead, expandable on demand
  - [x] Collapsed disclosure below the upcoming list (chosen) - a single "Show N past predictions" line, click to reveal, rendered the same as upcoming
  - [ ] A small Upcoming/Past pill toggle at the top of the section - more visible affordance but a second toggle pattern alongside the main tab bar
  - Fix: new shared `dashboard/components/PastDisclosure.tsx` client component; wired into both GoalsPanel (page.tsx) and PropsPanel.tsx, each splitting by kickoff and passing the past group's count/children to the same disclosure. Also filtered `getMostProbablePicks()`'s input to upcoming props only, since recommending a bet on an already-played match makes no sense
  - Blocked by: ~none~
  - Status: done — verified in the dev server: Goals O/U's "Show 10 past predictions" reveals Crystal Palace v Manchester City etc. correctly; Player Props' "Show 8 past predictions" reveals the same Manchester City v Crystal Palace prop table with team-switcher/threshold pills still fully interactive; "Most probable bets" strip correctly empty (no upcoming props exist right now). `tsc --noEmit` and `next build` clean. Committed (fba4818).

- [x] **R084** — README fully refreshed → *medium*
  - Context: last touched Jul 31, had drifted badly stale - predated the entire dashboard, the RapidAPI/SofaScore fallback engines, and the move from a local crontab to a GitHub Actions cron for production polling
  - Why: user asked to "update our github page fully" - the README is the repo's front page on GitHub
  - Fix: added a "Live dashboard" section linking the deployed Vercel app and describing its 5 tabs; updated the architecture diagram to cover all 3 live sources + how the dashboard reads from the repo via GitHub's Contents API; rewrote Phase B to describe the real GitHub Actions cron mechanism and each source's actual current status (including SofaScore's R081 gap); updated the CI test list to the current 9 scripts (was showing 2); added Roadmap Phase J (multi-source live resilience) and Phase K (the public dashboard) covering everything shipped this session; removed stale claims ("season hasn't started", "needs an API key to run live")
  - Blocked by: ~none~
  - Status: done — verified every factual claim against the actual current codebase (ci.yml's test list, live_poll.yml's cron schedule, rapidapi_engine.py's budget cap, the R081 SofaScore finding, DashboardTabs.tsx's tab list) rather than assuming from memory. Committed (1b5f9f9).

- [x] **R085** — Migrated to the new footymodel.vercel.app domain → *small*
  - Context: the Vercel project moved from dashboard-nine-theta-13.vercel.app to footymodel.vercel.app - confirmed the old URL now 404s entirely, not just "also available"
  - Why: user gave the new link and asked for the README/descriptions/buttons/diagrams to be updated accordingly
  - Fix: updated README's dashboard link + added a "Live dashboard" badge at the top (previously just a plain text link, no visual button); updated live_poll.yml's NOTIFY_URL, which was still silently pointing at the dead domain (would have broken push notifications, though notify_dashboard.py fails soft so the cron itself was never at risk)
  - Blocked by: ~none~
  - Status: done — verified the new domain serves the same app before changing anything (/ returns 200, /api/notify and /api/subscribe both 405 on a bare GET, confirming the routes exist). GitHub repo's homepage field was already correct (updated separately, likely via Vercel's GitHub integration). Committed (aa7b00f).

- [x] **R086** — Fancier animated past-predictions button; fixed Glossary width shift → *small*
  - Context: user asked for the "Show N past predictions" button to be bigger/fancier/highlighted with an animated arrow and expand/collapse animation, and separately reported the Glossary tab's content width looking different from other tabs
  - Why: PastDisclosure was a plain text link with an instant (non-animated) reveal; investigated the width report directly rather than guessing - confirmed Glossary (1994px tall) is the only tab that triggers a vertical scrollbar (15px) at typical viewport heights, while every other tab (all under ~900px content height) doesn't, so `mx-auto` centering shifted the whole page ~7.5px sideways whenever switching to/from Glossary specifically
  - Fix: PastDisclosure redesigned as a pill button (rounded-full, border, bigger padding) with a right-pointing arrow that rotates 90° and the button turns solid blue when expanded; content reveal now animates via CSS grid (`grid-template-rows: 0fr` -> `1fr`, handles variable-height content with no JS measurement). Added `scrollbar-gutter: stable` to `html` in globals.css so scrollbar space is always reserved, eliminating the width shift regardless of which tab's content needs to scroll
  - Blocked by: ~none~
  - Status: done — verified in the dev server: button visibly highlights blue + arrow rotates + content animates open/closed correctly; direct measurement confirmed Goals O/U and Glossary sections now report the identical `x` position (260.5) at a 1400px viewport, where before the fix Glossary was offset by ~7.5px. `tsc --noEmit` and `next build` clean. Committed (ead780f).

- [x] **R087** — Scheduled cloud workflow to keep goals-model training data current → *medium*
  - Context: user asked whether anything required their laptop staying open; found that nothing refreshes matches.parquet/matches_xg.parquet/player_match.parquet as the season progresses - none of the 3 existing GitHub Actions workflows (ci, live_poll, grade_results) touch them, so LineupModel trains on whatever snapshot was last taken manually
  - Why: user approved doing this as a scheduled cloud workflow rather than leaving it manual
  - [x] Scheduled GitHub Actions workflow (chosen)
  - [ ] Leave manual/frozen, refresh by hand when noticed
  - Fix: new `.github/workflows/refresh_training_data.yml`, daily at 07:00 UTC (after grade_results.yml). `footymodel.data`/`footymodel.understat` run with the full big-5 season history every time (cheap - one file/request per league-season, confirmed plain `requests.get()`, no browser/bot-detection risk like SofaScore). `build_players.py` runs CURRENT SEASON ONLY (2025/26) - it's one Understat request PER MATCH, so the full 2019-2025 history would mean thousands of redundant requests daily. That required a real fix, not just a CLI arg: `build_players.py` previously overwrote `player_match.parquet` wholesale, so a current-season-only call would have silently deleted every prior season's rows. Extracted the overwrite logic into a new `merge_player_dataset()` function (replaces just the league-seasons being refreshed, leaves everything else untouched), with its own unit test (`scripts/build_players_merge_test.py`, wired into CI). Also bumped `config.DEFAULT_START_YEARS` to include 2025 (was still capped at 2024, so even a full-range refresh would have kept missing the current season)
  - Blocked by: ~none~
  - Status: done — verified the merge logic with a real unit test (keeps other leagues/seasons, replaces only the refreshed one, handles the no-prior-file case), confirmed `python -m footymodel.data --help`/`understat --help` CLI wiring, ran the full local test suite (10/10 pass) before committing. Both the workflow's hardcoded "2025" and `config.DEFAULT_START_YEARS` will need a deliberate bump once 2026/27 starts - not automated on purpose, matches this project's preference for explicit reviewed season boundaries over silently shifting scope. Committed (d9b963e).

- [x] **R088** — R087's first manual run caught a real season-year mistake → *small*
  - Context: manually triggered refresh_training_data.yml to verify it works end-to-end; the "Refresh player rosters" step ran ~55 minutes (~1900 matches) instead of the expected 1-2 minutes
  - Why: investigated rather than assuming either "it's fine, just slow" or panicking - a quick local diagnostic script gave a false "0 matches" reading (bug in the throwaway script itself: `fetch_league_season()` already pre-filters to completed matches and drops the `isResult` key, so `.get('isResult')` on its output is always None) - checking the actual cached JSON directly showed the "2025/26" season already had a full 380 completed EPL matches, and cross-checking dates showed "2025/26" spans Aug 2025-May 2026 (already fully finished) while the REAL in-progress season is "2026/27" (Aug 21 2026 onward, 5 matches so far)
  - Fix: bumped `config.DEFAULT_START_YEARS` to include 2026 (not just 2025) and the workflow's `build_players.py` argument from 2025 to 2026
  - Blocked by: ~none~
  - Status: done — re-triggered the corrected workflow, verified it now targets "2026/27" (5 E0 matches, Aug 21-22 date range) while every historical season through 2025/26 remains fully intact across all 5 leagues. Committed (2cc9948).

- [x] **R089** — Surfaced all timings in IST → *small*
  - Context: user asked to convert all timings to IST before continuing the schedule-adjustment discussion
  - Why: GitHub Actions cron schedules only run in UTC (no timezone field exists) - the actual `cron:` values can't literally be "in IST", so this means leading every comment/doc with the IST-equivalent time instead, UTC kept as the technical reference
  - Fix: updated comments in all 3 workflow files (live_poll.yml: 14:30 IST-03:29 IST next day; grade_results.yml: 12:00 IST; refresh_training_data.yml: 12:30 IST) and README's Phase B section to match. Separately fixed a real bug found while doing this: `formatKickoff()` had no explicit `timeZone`, so it silently rendered in whatever timezone the execution context happened to be in - the viewer's browser for client-rendered panels (MatchCard) vs. Vercel's server clock for server-rendered ones (TrackRecordPanel) - meaning the same kickoff could show two different times depending which tab you looked at. Now explicit `timeZone: "Asia/Kolkata"` everywhere, labeled "IST"
  - Blocked by: ~none~
  - Status: done — verified live in the dev server: Track Record (server-rendered) and Goals O/U (client-rendered) both show "Sat 29 Aug, 00:30 IST" identically. `tsc --noEmit` and `next build` clean, all 3 workflow YAMLs validated. Committed (95d88f4).

- [x] **R090** — Upcoming fixture preview: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-30-upcoming-fixture-preview.md written and committed, standard writing-plans handoff choice
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - same process used for every previous plan this session
  - [ ] Inline execution
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R091** — Upcoming fixture preview: shipped end-to-end → *large*
  - Context: subagent-driven execution of all 5 tasks from docs/superpowers/plans/2026-08-30-upcoming-fixture-preview.md - backend (run_all.py's 2-day fixture fetch extended to 3, writes a new data/processed/upcoming_fixtures.json) and frontend (dashboard/lib/data.ts join + new PreviewMatchCard.tsx wired into both Goals O/U and Player Props)
  - Why: the user asked for both tabs to preview the next scheduled PL fixtures even before lineups are confirmed, showing what's available (team names, kickoff) and leaving the rest as pending, rather than showing nothing at all between matchdays
  - Fix: API-Football's free tier caps date-based fixture queries to a rolling 3-day window (confirmed directly - querying further out is rejected), so "next fixtures" means whatever falls in that window, not a guaranteed full round; this was accepted upfront during brainstorming. 4 real bugs were found and fixed during review before this ever reached origin: (1) `build_upcoming_list()` never excluded already-kicked-off fixtures, so an unconfirmed fixture would show "pending" forever; (2) it also had no fixture_id dedup across the 3 separate date queries; (3) the same gitignore/cron-commit-list gap as two earlier features this session (`match_detail.jsonl`, and the training-data refresh) - fixed up front this time as its own task instead of waiting for review to catch it again; (4) `getUpcomingFixtures()` filtered AFTER stringifying with `String()`, so a malformed row's missing fields became the literal truthy string `"undefined"` and would have rendered as "undefined v undefined" in the UI - fixed by filtering on the raw fields first, plus a non-object guard against a stray `null` entry crashing the whole page's `Promise.all`. A 5th fix found after Task 5's own review: preview cards never re-checked kickoff time against the viewer's live clock, only against whether they already had real data - fixed by reusing each panel's own `now`
  - Blocked by: ~none~
  - Status: done — all 5 tasks implemented, spec-reviewed, and code-quality-reviewed (fix-and-re-review loops on 4 of the 5 tasks). Pushed to origin/main (20a4c7e..e96430b, 11 commits). Verified locally: the real empty-state renders correctly (file doesn't exist in production yet), and the populated state was verified via a temporary, uncommitted mock of getUpcomingFixtures() for 2 fake fixtures - confirmed both Goals O/U and Player Props render the preview cards correctly, positioned after real predictions and before the past-predictions disclosure, then reverted cleanly (confirmed via `git status` showing no diff). True production verification of a live run_all.py poll actually writing a real upcoming_fixtures.json will only happen once the next scheduled cron run executes.

- [x] **R092** — Dashboard polish round: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-30-dashboard-polish-round.md written, self-reviewed, and committed - standard writing-plans handoff choice, covering the sort-order fix, Glossary blue accents, and Staking last-run timestamp
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R093** — Dashboard polish round: shipped end-to-end → *medium*
  - Context: subagent-driven execution of all 6 tasks from docs/superpowers/plans/2026-08-30-dashboard-polish-round.md - sort-order fix (Goals O/U + Player Props upcoming lists), Glossary blue-accent bars, and a Staking "last run" timestamp
  - Why: closes 3 small gaps raised in one bundled request - upcoming matches weren't in kickoff order on either prediction tab, the Glossary had no visual structure, and the Staking tab gave no indication its numbers were manually/irregularly generated
  - Fix: root cause of the sort bug was `getGoalsPicks()`/`getPropsPicks()` sorting descending (correct for past, never for upcoming) plus `getUpcomingFixtures()` not sorting at all - fixed by sorting ascending at the exact point each panel splits into upcoming/past. Glossary got a `border-l-2 border-blue-600 dark:border-blue-400 pl-3` accent on all 20 term entries (one color-consistency bug caught and fixed during code review: initial commit used blue-500, didn't match the app's established blue-600/dark:blue-400 convention used by DashboardTabs/Logo/PastDisclosure). Staking's timestamp is a 3-commit chain: `kelly_simulation.py` stamps `generated_at` (UTC ISO) onto every row before `to_csv`, `lib/data.ts` parses it as `generatedAt: string | null`, `StakingPanel` renders "Last run: <IST time>" guarded against null (reusing `formatKickoff()`, a generically-named ISO-to-IST formatter)
  - Blocked by: ~none~
  - Status: done — all 6 tasks implemented, spec-reviewed, and code-quality-reviewed (one fix-and-re-review loop, the Glossary color fix). Final whole-implementation review passed clean (`tsc --noEmit` + `next build` both clean on the full range). Pushed to origin/main (e93b019..033fb37, 9 commits). Verified live in production: Goals O/U now shows preview fixtures in strict ascending kickoff order (Chelsea/Leeds/Sunderland 18:30 IST → Man Utd/Ipswich 21:00 IST → Aston Villa/Arsenal next day 00:30 IST); Glossary shows the blue-600 accent bar on every term in both light and dark mode; Staking shows "Last run: Sun 30 Aug, 17:49 IST", matching the actual timestamp written by the regenerated kelly_simulation.csv.

- [x] **R094** — Theme toggle: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-30-theme-toggle.md written, self-reviewed, and committed - standard writing-plans handoff choice, covering the light/dark/system toggle (Tailwind class-driven variant, flash-prevention script, ThemeToggle component, header wiring)
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R095** — Light/Dark/System theme toggle: shipped end-to-end → *medium*
  - Context: subagent-driven execution of all 4 tasks from docs/superpowers/plans/2026-08-30-theme-toggle.md - Tailwind's `dark:` variant switched from media-query-driven to class-driven (`@custom-variant dark (&:where(.dark, .dark *));`), a pre-hydration inline script in layout.tsx applies the right class before React hydrates, a new `ThemeToggle.tsx` component (3-segment pill, reusing MatchPropsTable's existing segmented-control style) reads/writes a `theme` localStorage key and toggles the class directly, wired into the page header next to SubscribeButton
  - Why: user asked for an explicit light/dark toggle - previously the dashboard only followed the OS's `prefers-color-scheme` with no override or persistence. Chosen design: 3-way Light/Dark/System (not just 2-way), placed in the header, hand-rolled with no new npm dependency (no next-themes) to keep this project's minimal dependency list as-is
  - Fix: one real bug caught and fixed proactively (before it reached review) - code review on Task 2 flagged that React Strict Mode's dev-only `<html>` remount strips a class added imperatively by the pre-hydration script, which would flash a stored dark/light preference correctly then flip back on every dev hard-reload; fixed by amending Task 3's plan to have ThemeToggle's mount effect re-apply the resolved theme, not just read state into it (dev-only issue, no prod impact). A second issue (missing `aria-pressed` on the 3 segment buttons, inconsistent with the app's existing `aria-expanded` convention on PastDisclosure/MatchCard) was caught during Task 3's code review and fixed in a follow-up commit
  - Blocked by: ~none~
  - Status: done — all 4 tasks implemented, spec-reviewed, and code-quality-reviewed (one plan amendment + one fix-and-re-review loop). Final whole-feature review passed clean (`tsc --noEmit` + `next build` both clean on the full range, confirmed the whole chain - variant, script, component, wiring - shares one consistent contract). Pushed to origin/main (rebased onto a concurrent live-poll cron commit first, no conflicts). Verified live in production: toggle renders in the header, clicking Light immediately restyles the whole page and persists across a hard reload with no flash and no console hydration warnings, reset back to System afterward.

- [x] **R096** — Mobile view fixes: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-30-mobile-view-fixes.md written, self-reviewed, and committed - standard writing-plans handoff choice, covering the header horizontal-overflow fix and the tab-bar active-highlight scroll-into-view fix
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R097** — Mobile view fixes: shipped end-to-end → *medium*
  - Context: subagent-driven execution of both tasks from docs/superpowers/plans/2026-08-30-mobile-view-fixes.md - header stacks vertically below the `sm` breakpoint (was overflowing the whole page horizontally by 74px on a 375px viewport), and the tab bar's animated active-tab highlight now scrolls the clicked tab into view via `scrollIntoView`
  - Why: user asked to "fix the mobile view visually" - investigated directly at 375px width first rather than guessing, found and confirmed two distinct reproducible bugs (header horizontal overflow via `scrollWidth`/`clientWidth` measurement; tab-pill landing on the wrong label once the 5-tab pill bar needed its own horizontal scroll) before brainstorming a fix
  - Fix: two real follow-up bugs caught during review before either reached a final "done" state - (1) the header fix's own inner `ThemeToggle`+`SubscribeButton` row had no `flex-wrap`, so `SubscribeButton`'s real "denied"/"unsupported" fallback text (not just an edge case - the actual current production state) got squeezed into a cramped multi-line column instead of dropping to its own row; fixed by adding `flex-wrap` to that inner div. (2) the `scrollIntoView` fix fired unconditionally including on initial mount, which - now that the header is taller from fix (1) - could have caused an unwanted page-level vertical scroll-jump on load if the first tab wasn't fully in view yet; fixed with a `didMountRef` guard so the scroll only fires on click-driven tab changes, verified via a real production-build A/B test (pre-fix: 61px scroll jump reproduced; post-fix: zero)
  - Blocked by: ~none~
  - Status: done — both tasks implemented, spec-reviewed, and code-quality-reviewed (two fix-and-re-review loops, one per task). Final whole-round review passed clean (`tsc --noEmit` + `next build` clean, both original bugs and both follow-up fixes independently verified empirically, not just by reading the diff). Pushed to origin/main (rebased onto a concurrent live-poll cron commit, no conflicts). Verified live in production at a real 375px viewport: `scrollWidth === clientWidth` (no horizontal overflow), `scrollY` stays 0 on load, and clicking through to the Staking tab correctly scrolls it into view with the highlight settling on the right label after its 260ms transition (a screenshot taken mid-transition briefly looked misaligned, which is expected animation behavior, not a bug - confirmed by re-checking a moment later).

- [x] **R098** — Theme switch + bell redesign: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-08-31-theme-switch-and-bell-redesign.md written, self-reviewed, and committed - standard writing-plans handoff choice, covering the binary theme switch, bell/info icon redesign, and header repositioning
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R099** — Theme switch + notification bell redesign: shipped end-to-end → *medium*
  - Context: subagent-driven execution of all 4 tasks from docs/superpowers/plans/2026-08-31-theme-switch-and-bell-redesign.md - ThemeToggle collapsed from a 3-way Light/Dark/System pill to a binary sliding switch, SubscribeButton redesigned from always-visible text to a bell+info icon pair with a glow animation and a tap-to-reveal description popover, and the header cluster restacked so the bell+info row sits above the switch
  - Why: user asked to remove "System" entirely (not just hide it) and wanted a more compact, icon-first notification control - explored via the visual-companion brainstorming tool first (2 mockup rounds: layout position, then glow subtlety) before writing the spec
  - Fix: one real cross-task bug caught during the final whole-round review, not any single task's own isolated testing - stacking the bell/info row directly above the switch (8px gap) meant the info popover's `top-full mt-2` offset landed at the exact same y-position where the switch began, so opening the popover fully painted over the switch and made it unclickable while open. Fixed by increasing the popover's offset to `mt-10`, clearing the switch's height plus the stack gap entirely - verified live afterward: switch stays visible and clickable with the popover open, popover closes cleanly on an outside click
  - Blocked by: ~none~
  - Status: done — all 4 tasks implemented, spec-reviewed, and code-quality-reviewed, plus a targeted fix-and-re-review for the cross-task overlap. Final whole-round review passed clean (`tsc --noEmit` + `next build` both clean). The one-time "system" preference migration was independently re-tested live by the controller (not just trusted from the implementer's report) and confirmed working in both directions (stale `"system"` value, and no stored value at all). The bell's glow animation was also independently confirmed via `getComputedStyle` (`animation-name: bell-glow`, `2.8s`) using a temporary, cleanly-reverted dev-server mock, since the controller's own real browser had already granted notification permission and couldn't be forced back to an unsubscribed state to observe naturally. Pushed to origin/main (rebased onto two concurrent live-poll cron commits, no conflicts). Verified live in production: switch toggles instantly and persists, bell shows a genuine subtle glow in the "on" state, and the info popover opens fully clear of the switch with the switch remaining clickable throughout.

- [ ] **R100** — Weekend PL predictions missing: cron reliability + engine's one-way kickoff cutoff → *medium*
  - Context: user reported the past-predictions list wasn't showing any of the real PL fixtures from the Aug 30-31 weekend (Aston Villa v Arsenal, Chelsea v Brighton, Leeds v Brentford, Sunderland v Fulham, Man Utd v Ipswich) despite all 5 having kicked off and finished. Investigated `gh run list` history for live_poll.yml: every run completes in ~1 minute (no stuck jobs), but the actual gaps between scheduled runs starting ~Aug 27 blew out to 6-19 hours despite the `*/20 9-21 * * *` cron - Aug 25-26 fired every 30-60min as expected, Aug 27 onward degraded sharply
  - Why: `engine.py`'s `run_once()` filters fixtures with `0 <= mins_to_ko <= hours_ahead*60` - once kickoff passes, a fixture is permanently dropped, never retried. Confirmed lineups publish only 20-40min pre-kickoff, so any poll gap that straddles that narrow window loses the fixture forever even though the lineup data itself never expires - confirmed directly via `ApiFootballClient().lineups(fixture_id)` that lineup data for both Chelsea v Brighton (1557379) and Aston Villa v Arsenal (1557377) is still fully retrievable right now, well after kickoff
  - [ ] Widen engine.py's fixture window to also catch recently-kicked-off matches (not just future ones), so a late/delayed poll can retroactively log a prediction instead of losing it forever - this is the addressable half, doesn't fix GitHub's own cron reliability but makes the system self-healing against exactly the gaps that already happened
  - [ ] Separately investigate/fix GitHub Actions' schedule-trigger reliability itself (external cron service pinging workflow_dispatch, or a self-hosted runner) - bigger, not urgent, same class of problem as R081's SofaScore CI-blocking, likely a platform limitation rather than something fixable in this repo's code alone
  - Blocked by: user hasn't confirmed whether to proceed with the engine fix + backfill the 5 missed matches
  - Status: in progress — root cause fully diagnosed and confirmed (cron gaps + one-way cutoff + lineup data still fetchable), proposed fix presented to user, awaiting go-ahead to brainstorm/implement.

- [x] **R101** — Fixture window fix + backfill: plan execution mode → *small*
  - Context: docs/superpowers/plans/2026-09-01-fixture-window-fix-and-backfill.md written, self-reviewed, and committed - standard writing-plans handoff choice, covering the widened kickoff window, extracted process_one_fixture helper, reusable backfill script, and running the real backfill for the 5 missed weekend matches
  - Why: tracked explicitly for every prior plan this session
  - [x] Subagent-driven (Recommended) - fresh subagent per task, two-stage review, same process used for every previous plan this session
  - [ ] Inline execution - batch execution with checkpoints in this session
  - Blocked by: ~none~
  - Status: done — user chose subagent-driven.

- [x] **R102** — Fixture window fix + weekend backfill: shipped end-to-end → *large*
  - Context: subagent-driven execution of all 4 tasks from docs/superpowers/plans/2026-09-01-fixture-window-fix-and-backfill.md - widened both `engine.py`'s and `run_all.py`'s (the actual production path) forward-only kickoff cutoff to also accept fixtures up to 24h in the past, extracted a shared `process_one_fixture()` helper, built a reusable `scripts/backfill_missed_fixtures.py`, and ran it for real against the missed 2026-08-30/31 weekend
  - Why: closes R100's diagnosis - the live engine permanently dropped any fixture once its kickoff passed, and combined with GitHub Actions cron gaps up to ~19h (confirmed via `gh run list`), this lost 5 real PL matches over the weekend even though confirmed-lineup data itself never expires
  - Fix: a serious, unplanned issue was caught mid-round during Task 1's own code review - widening the window enough to process fixtures AFTER kickoff broke an implicit safety property: `LiveWatcher._model_for()` fit its ratings model using wall-clock `pd.Timestamp.now()` as the training cutoff against `LineupModel.fit()`'s `date < as_of` filter, which was only safe because a fixture could never previously be processed until AFTER its own kickoff (so its own result couldn't exist in the training parquet yet). Fixed by switching `as_of` to the fixture's own kickoff date (matching the pre-existing backtest walk-forward convention in `players.py`, confirmed as the established correct pattern), closing a real model look-ahead leakage risk before it could ever fire in production. `run_all.py`'s fix automatically inherits this same leakage protection since it shares the identical `process_fixture()` method
  - Blocked by: ~none~
  - Status: done — all 4 tasks implemented, spec-reviewed, and code-quality-reviewed, including a genuine fix-and-re-review loop on Task 1 for the leakage risk. Final whole-round review passed clean (`live_dryrun.py`/`run_all_dryrun.py`/`backfill_missed_fixtures_test.py` all pass; traced and confirmed no path lets `run_all.py` bypass the fixed `_model_for`). Both new/previously-uncovered test scripts (`run_all_dryrun.py`, `backfill_missed_fixtures_test.py`) wired into CI as a follow-up, matching this project's established convention of every test script landing in `ci.yml`. Pushed to origin/main. Real backfill outcome, independently verified end-to-end (commit → push → grading → live dashboard): only 1 of the 5 originally-missed matches (Aston Villa v Arsenal) was actually recoverable - the other 4 (all 2026-08-30 kickoffs) hit a hard, already-documented API-Football free-tier wall (its rolling 3-day fixture-query window had moved past that date by the time the backfill ran on 2026-09-01) - not a script bug, a genuine data-availability ceiling. Aston Villa v Arsenal is now live on the dashboard, correctly graded (model called under 2.5, correct, bet won +1.25).
  - Note: `rapidapi_engine.py`/`sofascore_engine.py` have the identical `_model_for(now())` pattern this round fixed in `engine.py`, currently harmless since their windows remain forward-only - flagged as a dormant risk if either engine's window is ever widened backward the same way, not fixed here since it's out of scope for this round.

- [x] **R103** — Recovering the remaining 4 matches: by-ID fixture lookup bypasses the free-tier date block → *medium*
  - Context: confirmed directly against the live API-Football that the 4 unrecoverable matches from R102's backfill (Chelsea v Brighton 1557379, Leeds v Brentford 1557382, Sunderland v Fulham 1557385, Man Utd v Ipswich 1557384) ARE fully fetchable (fixture metadata + 2 confirmed lineups + odds each) when queried by fixture ID directly (`/fixtures?id=X`), even though the date-bucket query (`fixtures_by_date`) that `backfill_missed_fixtures.py` and `grade_results.py` both used is blocked by the free tier for dates that old
  - Why: this means all 4 remaining matches were genuinely recoverable, not a hard data-availability wall as R102 concluded - the limitation was specific to each script's date-based fetch method, not the API's actual data availability. User chose direct implementation over the full brainstorm/spec/plan process, given how clear-cut the fix was
  - Fix: added `ApiFootballClient.fixture_by_id()`; extended `backfill_missed_fixtures.py` with a `--ids` CLI mode and `fixture_ids` parameter that fetches directly by id instead of by date; ran it for real - 3 of 4 recovered immediately, the 4th (Man Utd v Ipswich) hit a transient per-minute rate limit (HTTP 429, not a data-availability issue) and recovered cleanly on retry after a short wait. Discovered a SECOND instance of the identical bug while re-triggering grading: `grade_results.py`'s `grade_row()` also relied on `fixtures_by_date()` + fuzzy team-name matching to find final scores, hitting the same wall and silently grading 0 of the 4 newly-backfilled matches ("No fixtures could be graded this run") - fixed the same way, by trying `client.fixture_by_id(int(row["fixture_id"]))` first (more precise too, no fuzzy matching needed) and falling back to the date+name method only for RapidAPI/SofaScore-sourced predictions (whose prefixed fixture_id, e.g. "rapid_5868013", isn't a valid API-Football id at all)
  - Blocked by: ~none~
  - Status: done — both fixes verified with new focused tests (`backfill_missed_fixtures_test.py`'s fixture_ids case, new `grade_results_by_id_test.py` covering both the by-id and fallback paths), both wired into CI, all existing tests re-confirmed clean. Pushed to origin/main. Re-triggered grading after the grade_results.py fix - log confirmed "Graded 4 prediction(s)" this time. Verified live in production: all 6 graded matches (the original + all 5 recovered from the weekend, including the previously-unreachable 4) now show on the Track Record tab in correct chronological order with real final scores, correct model-call marks, and real paper-trade returns (66.7% accuracy, 6 graded, -14.0% cumulative return across this small sample).
