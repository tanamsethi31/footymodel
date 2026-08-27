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
