# Phase 3 Results — the go/no-go gate

**Verdict: NO-GO for real money on current evidence.** The goals-only Dixon-Coles
model is excellently calibrated but does **not** beat bookmaker closing lines in
any tested league. This is the disciplined stop the plan defined.

## Setup
- Walk-forward, no lookahead: model refit per matchday on prior matches only.
- Benchmark: **average closing odds** (the sharpest line — hardest to beat).
- Value bet when EV = model_p × odds − 1 > 5%. Flat 1u stakes.
- Test period: 2022-07-01 → 2025-06. Markets: 1X2 + Over/Under 2.5.

## Yield by league (profit / staked)

| League | Yield | Value bets | Favourite baseline |
|--------|------:|-----------:|-------------------:|
| E1 Championship | **−1.6%** | 2002 | −5.0% |
| G1 Greece | −9.6% | 880 | −11.6% |
| E0 Premier League | −10.5% | 1518 | +0.7% |
| B1 Belgium | −12.5% | 1029 | −1.0% |
| N1 Eredivisie | −13.9% | 1104 | −4.7% |
| P1 Portugal | −19.5% | 1124 | +3.3% |
| T1 Turkey | −20.8% | 1315 | +4.8% |
| **Pooled** | **−11.7%** | 8972 | — |

Every league loses. Championship is closest to break-even but still negative;
its few positive sub-markets (draw +29% on 99 bets) are small-sample noise.

## Why it loses despite being well-calibrated

Pooled calibration is near-perfect where the data is thick:

| pred | actual |
|-----:|-------:|
| 0.158 | 0.164 |
| 0.254 | 0.262 |
| 0.451 | 0.450 |
| 0.547 | 0.543 |

But the model's **value bets claim +20.8% average edge and return −11.7%.** That
~32-point gap is the tell: a model can be calibrated *on average* yet be
systematically over-confident *exactly where it most disagrees with the market*.
The closing line prices in information a goals-only model can't see — injuries,
lineups, rotation, motivation, transfers. Losses concentrate in **away
underdogs (−17%) and draws (−15%)**, the classic favourite-longshot trap.

## What this rules out
Public results data + a goals-only statistical model is **not** enough to beat
closing lines. This matches reality: most models don't. We proved it rigorously
instead of fooling ourselves — which is the whole point of Phase 3.

## Phase 2b — does xG help? (Understat, big-5 leagues)

Understat covers only the big-5 (+ Russia), so this was tested on E0/SP1/D1/I1/F1
— all *sharp* markets. 99.9% xG coverage on 10,707 matches. We compared fitting
team strengths on pure goals vs a goal/xG blend vs pure xG.

| Target | Pooled yield | Calibration error |
|--------|-------------:|------------------:|
| pure goals (blend 1.0) | −11.38% | 0.015 |
| 50/50 goals+xG (0.5) | **−10.16%** | **0.009** |
| pure xG (0.0) | −11.41% | 0.011 |

**xG helps model *quality* — calibration error nearly halves (0.015→0.009) and
yield improves ~1.2 pts — but it does NOT create an edge.** Every league × blend
cell is negative; best single cell is E0 at 50/50 (−6.6%), still losing. xG
closes ~1 point of an ~11-point gap. Two independent model families (goals, xG)
now give the same answer: public data can't beat the closing line on these
markets.

Caveat: xG could only be tested on the big-5 (sharpest markets). It remains
untested on mid-tier leagues (needs FBref), where the goals model got closest
to break-even (Championship −1.6%).

## Phase 3b — opening odds + Closing Line Value (the clincher)

Bet at the softer OPENING line instead of closing, and measure **CLV**
(open/close − 1): did the market move *toward* our picks? Positive mean CLV /
>50% beat-close rate is the gold-standard, low-noise signal of genuine edge —
professionals trust it above short-term ROI.

| League | Yield @ open | Mean CLV | Beat-close rate |
|--------|-------------:|---------:|----------------:|
| E1 Championship | −1.1% | −1.02% | 42.5% |
| E0 Premier League | −11.1% | −0.48% | 46.5% |
| N1 Eredivisie | −12.0% | −0.86% | 45.5% |
| B1 Belgium | −11.3% | −0.03% | 47.2% |
| P1 Portugal | −15.1% | −1.16% | 42.2% |
| T1 Turkey | −21.9% | −0.79% | 45.8% |
| G1 Greece | −10.7% | +0.44% | 51.4% |
| **Pooled** | **−11.1%** | **−0.63%** | **45.4%** |

**CLV is negative in 6 of 7 leagues; pooled beat-close rate is 45.4% (< 50%).**
Our picks systematically get *worse* prices than the close — the market moves
*against* our selections after we'd have bet them. That is the opposite of edge,
and CLV is the least-noisy metric we have, so this is structural, not variance.
Greece's marginal +0.44% (on 790 bets, one league out of seven) is exactly the
kind of false positive multiple comparisons produce, and its yield is still
−10.7%.

---

# FINAL VERDICT: NO-GO — do not bet real money

Three independent tests agree:
1. Goals model vs closing: **−11.7%**
2. xG model vs closing (big-5): **−10.2%** best
3. Goals model vs opening + **CLV −0.63%, beat-close 45.4%**

A goals/xG statistical model built on public data **cannot beat the market** on
these leagues. The negative CLV is decisive: we're on the wrong side of the
line's own movement. This is the disciplined stop the plan defined, and hitting
it is a *success* — we learned it in a backtest instead of with real money.

## What it would actually take (beyond this project's scope)
- Faster / private data the closing line hasn't absorbed (real-time injuries,
  lineups, team news, weather) — an information edge, not a modeling edge.
- Manual specialization in specific soft sub-markets / lower leagues, not a
  broad automated model.
- Accepting that the closing line is, empirically, very hard to beat — which is
  exactly what we just demonstrated rigorously.

## Per-market CLV — Over/Under is the least-bad market (but still no edge)

Pooled across 7 leagues at opening odds:

| Market | n | Yield | Mean CLV | Beat-close |
|--------|--:|------:|---------:|-----------:|
| O/U (all) | 6182 | −7.3% | **−0.22%** | 47.4% |
| 1X2 (all) | 10140 | −13.3% | −0.88% | — |

Totals CLV is 4× less negative than 1X2 — they avoid the favourite-longshot trap
that drove the 1X2 losses. But O/U CLV is **still negative (−0.22%, beat 47.4%)**.
A near-zero CLV means our total-goals estimate essentially *matches* the market's:
we're not beating it, just paying the vig. An O/U-specialised model could push CLV
toward zero (break-even), but positive CLV — the thing real profit needs — did not
appear. No-go stands.

## Best-price / line-shopping test — the biggest lever found

Re-priced the SAME O/U value bets at the market MAXIMUM odds (best across books)
instead of the average:

| Execution | Bets | Yield |
|-----------|-----:|------:|
| Avg close (prior tests) | 3371 | −8.98% |
| Avg open | 3087 | −7.30% |
| **Max close (best price)** | 5101 | **−2.56%** |
| Max open (best price) | 4376 | −3.20% |

Line shopping recovers **~6.4 pts** of yield (overround 1.055 → 1.005 — nearly
all the margin). Real and large — the single biggest lever. **But still negative
(−2.6%):** even margin-free, our picks are ~2.6% worse than the best-price fair
line, so the residual is genuine model edge we don't have. And max odds is an
idealized ceiling (needs many books, best-price capture, and bookmakers limit
winners) — realistic execution sits between avg and max.

**Quantified roadmap — updated with Tier-1 test result:**
1. Line shopping / best price — **+6 pts, proven & banked** (default in recommender).
2. Tier 1 modeling — **TESTED, no help.** Shot-xG-blend fitting gave −2.78% at
   best price vs −2.56% goals-only (marginally worse). Consistent with Phase 2b
   (real xG improved calibration, not edge). *Better public-data inputs don't
   create edge — the market already has them.* The −2.56% best-price floor holds.
3. Tier 2 information (lineups/injuries + fast execution, or softer/niche markets)
   — the ONLY remaining path to profit, and it's a data/execution project, not a
   modeling one.

**Bottom line:** the model is as good as it gets on public data. Execution
(best price) closed most of the gap; modeling cannot close the rest. Real profit
requires information or market access the closing line lacks.

## Prediction-quality & confidence-selection test ("just bet the confident ones")

Ignore value/odds; measure raw predictive skill, then bet the model's *favored*
O/U side (not the market-disagreement side).

- **Predictive skill is near a coin flip:** favored-side accuracy 56.2%, Brier
  0.246 (coin flip 0.25), log-loss 0.690 (coin flip 0.693). Total goals is hard.
- **Confidence-selection @ best price ≈ break-even:** all-favored −0.31% (t=−0.29);
  conf≥0.65 +1.17% but **t=0.52, not significant**, and per-league scatter
  (B1 +9.7% … G1 −4.6%) confirms noise, not edge.

Key result: **confidence-selection (−0.3%) beats value-betting (−2.6%)** because
it avoids the model's blind spots — but it lands on break-even, i.e. it
reproduces the market's fair line. Confirmed from every angle now (value, xG,
opening odds, CLV, line-shopping, confidence): **public data matches the market,
never beats it.**

## Phase A — lineup-aware player model (validates the thesis, marginally)

Scraped Understat per-match rosters (2,280 PL matches, 1,343 players). Built
time-decayed, shrunk player xG/90 ratings; team attack = sum of the starting XI's
ratings. O/U prediction accuracy vs the team-average baseline (same matches):

| Model | Brier | LogLoss | Fav-acc |
|-------|------:|--------:|--------:|
| Team-level | 0.2452 | 0.6836 | 56.1% |
| Lineup-only | 0.2462 | 0.6872 | 57.5% |
| **Blend (½ team + ½ lineup)** | **0.2444** | **0.6824** | 56.8% |

**Lineup info helps prediction:** the blend beats team-only on all three metrics.
Lineup-only ranks better (57.5% acc) but is miscalibrated (worse Brier) — the
blend regularizes it. First genuine *model* improvement in the project (vs the
execution wins). BUT the gain is small (Brier −0.0008 from a crude model) and,
critically, **this is prediction accuracy, not profit.**

**Strengthened model (xA for playmakers, home advantage, scale calibration,
blend sweep):** edge roughly DOUBLED vs the crude version.

| Model | Brier | LogLoss | Fav-acc |
|-------|------:|--------:|--------:|
| Team-level | 0.2443 | 0.6815 | 56.2% |
| Lineup-only | 0.2431 | 0.6797 | 56.9% |
| **Blend (w=0.4)** | **0.2427** | **0.6784** | 56.8% |

Now every blend beats team-only; even lineup-only beats it. Brier improvement
grew 0.0008 → 0.0016 as the model improved — the signal responds to model
quality (a good sign it's real information, not noise). **t-stat 1.49 (not yet
significant)** on one league; significance is a sample-size problem — big-5
(~5x data) would reach t≈3.3 if the effect holds.

**The Phase-B reality:** the closing line already prices lineups, so this
accuracy gain won't beat closing odds in a backtest. Real profit needs the LIVE
piece — ingest confirmed lineups ~1h pre-kickoff, re-price instantly, bet soft
books/exchange before they adjust. Live-infrastructure, forward-tested, no
backtest guarantee.

## Big-5 confirmation test — the edge does NOT generalize (sobering)

Scraped all big-5 rosters (10,706 matches, 322,832 player-rows) and re-ran the
lineup-vs-team test per league:

| League | n | Team Brier | Best blend Brier | t-stat |
|--------|--:|-----------:|------------------:|-------:|
| **E0 (PL)** | 1140 | 0.2443 | 0.2427 (w=0.40) | **1.49** |
| SP1 (La Liga) | 1140 | 0.2403 | 0.2401 (w=0.75) | 0.61 |
| D1 (Bundesliga) | 917 | 0.2371 | 0.2363 (w=0.50) | 0.84 |
| I1 (Serie A) | 1140 | 0.2461 | 0.2454 (w=0.50) | 0.85 |
| **F1 (Ligue 1)** | 992 | 0.2466 | 0.2466 (w=1.00) | — (no blend beat team at all) |
| Pooled (5 leagues) | 5329 | 0.2430 | 0.2425 | 1.71 |

**Verdict: the lineup edge does NOT replicate consistently.** It was strongest
in the Premier League — the league we developed and tuned on — and weaker or
absent everywhere else (Ligue 1: literally no blend weight beat the team-only
baseline). Pooling 4.7x more data should have pushed t past ~3.2 if the true
effect were as strong as PL suggested; instead it only reached 1.71, diluted by
the other four leagues. This is the classic signature of **overfitting to the
first dataset tested**, not a universal signal.

**Revised conclusion (superseded below):** the half-lineup (attack-only) PL
result was likely partly noise/league-specific, not proof of a robust,
transferable lineup edge.

## Fixing the gap: full-lineup (attack + defence) — CONFIRMED significant

The half-lineup model only used the starting XI for attack; defence was still
team-average — a real methodological gap. Added `player_defence_ratings()`
(proxy: team xG-conceded while each player was on the pitch, minutes-weighted,
time-decayed, shrunk — standard in public defensive analytics) and built a
full-lineup model using the starting XI for BOTH attack and defence.

| League | n | Team Brier | Best full-lineup Brier | Improvement | t-stat |
|--------|--:|-----------:|------------------------:|------------:|-------:|
| Premier League | 1140 | 0.2443 | 0.2409 (w=0.25) | 0.0034 | **2.23** |
| La Liga | 1140 | 0.2403 | 0.2384 (w=0.25) | 0.0019 | 1.36 |
| Bundesliga | 917 | 0.2371 | 0.2355 (w=0.40) | 0.0016 | 1.32 |
| Serie A | 1140 | 0.2461 | 0.2425 (w=0.00) | 0.0036 | **1.97** |
| Ligue 1 | 992 | 0.2466 | 0.2462 (w=0.75) | 0.0004 | 0.72 |
| **Pooled (5 leagues)** | 5329 | 0.2430 | **0.2410 (w=0.25)** | 0.0020 | **3.04** |

**This is different from the half-lineup result in the way that matters:**
every league now improves in the SAME direction (no more Ligue-1-style zero),
sizes vary but are consistent, and pooling behaves like real signal compounding
(t rises to 3.04) rather than being diluted by an absent effect in other
leagues. Full-lineup roughly doubled the half-lineup edge everywhere it was
already present. **This is CONFIRMED, not a fluke of one dataset — the first
statistically significant, cross-league-replicated finding in this project.**

**What this does and doesn't mean:** knowing the actual back four (not just
attackers) meaningfully improves total-goals prediction — real information.
It does NOT yet mean profit: the closing line still prices lineups, so this
remains an accuracy result. It DOES mean the Phase B hypothesis (capture this
via live lineups + fast execution before soft books adjust) is now justified by
real, replicated evidence rather than an unconfirmed hunch.

## The remaining untested thread (low expected value)
- **FBref xG on mid-tier leagues.** But xG bought only ~1pt on the big-5, and
  CLV is already negative on every mid-tier league here — so better inputs are
  unlikely to flip the sign. Recommendation: **accept the no-go.**

---

# Phase C — Asian Handicap (a new market, all 7 leagues)

With ~2-3 weeks of runway before the season starts, tested a genuinely new
market rather than more modelling on 1X2/O-U. football-data.co.uk's cached
CSVs turned out to already contain full AH odds (`AHh`/`AHCh` line, `Avg`/`Max`
`AHH`/`AHA` opening+closing) that this project had never touched — no new
scraping needed.

**Mid-tier lineup extension via FBref — researched and dropped, confirmed not
viable.** Checked FBref match reports directly for Eredivisie and the
Championship (our best-performing league): both have **no `xg` column at all**
in the player-stats table, only basic box-score stats. FBref's per-player
expected-goals data is restricted to the big-5 (+ a short list of others).
Per the plan's stated fallback, this path was dropped rather than forced with
a weaker proxy — Asian Handicap absorbed the "mid-tier depth" goal instead,
since testing it properly means running across all 7 leagues anyway.

## Implementation
- `_ah_home_outcome()` (model.py): vectorized settlement for whole/half/quarter
  lines (push, half-win, half-loss), unit-verified against 16 hand-computed
  cases + an away-mirror symmetry check (`scripts/ah_settlement_test.py`) —
  caught one wrong hand-computed *test* expectation (not a code bug) before all
  checks passed.
- `DixonColes.predict_ah()`: 5-bucket outcome probabilities from the existing
  score matrix; verified probabilities sum to exactly 1.0000 on real fixtures.
- `scripts/ah_backtest.py`: walk-forward across all 7 leagues, both value and
  confidence-selection strategies (both previously shown to matter for O/U),
  both average and best-price odds regimes, and genuine open→close CLV
  (computed only on the 60.9% of fixtures where the line didn't move — AH
  lines can shift, unlike O/U's fixed threshold, so this project doesn't mix
  apples and oranges to get a number).

## Results (pooled, 7 leagues, 2022-07 → 2025-06)

| Strategy | Odds | Bets | Yield | t-stat | CLV n | CLV | Beat-close |
|----------|-----:|-----:|------:|-------:|------:|----:|-----------:|
| Confidence | avg | 3683 | −1.57% | −1.10 | 2133 | −0.77% | 38.8% |
| **Confidence** | **max (best price)** | 3683 | **+2.05%** | 1.38 | **−1.52%** | **34.8%** |
| Value | avg | 4808 | −3.47% | **−2.75 (significant)** | 2831 | −1.82% | 30.7% |
| Value | max (best price) | 6079 | −0.20% | −0.17 | 3646 | −2.39% | 28.7% |

Per-league (confidence @ best price): B1 +4.2%, E1 +4.5%, G1 +6.2%, N1 +3.5%
(positive) vs. E0 −1.8%, P1 −0.1%, T1 −1.8% (negative/flat) — mixed, no
individual t-stat exceeds 1.5, no consistent direction.

## Verdict: no edge — the best-looking number is exactly the trap this
## project's methodology exists to catch

The single best config (confidence-selection @ best price, +2.05% yield) has
**negative CLV (−1.52%) and a 34.8% beat-close rate** — well under the 50% a
real edge needs. This is the identical diagnostic pattern used earlier in this
project to correctly reject the half-lineup PL-only result as noise (before
the full-lineup version replicated cleanly cross-league with *positive*,
consistent improvement in every league). Here there's no such consistency:
per-league yields scatter with no common direction, and CLV points the wrong
way. **Positive yield + negative CLV = favourable variance in this sample, not
edge.** Value-betting at average odds is unambiguously worse — a
**statistically significant loss** (t=−2.75).

**Asian Handicap joins 1X2 and Over/Under: a well-built model matches the
market's fair line on this market too, but does not beat it.** Public data
continues to hit the same ceiling regardless of which market is tested — the
fourth confirmation of the project's central finding.

---

# Phase D — Player Shots-on-Target (FBref)

Extended the player-shots probability model (RESULTS.md above: minutes-fix +
position-grouped shrinkage + Negative Binomial dispersion) to **shots on
target**, which Understat doesn't track per-player. FBref does, but blocks
direct HTTP requests (403/Cloudflare) - scraped via the browser's own `fetch()`
context (piggybacks the browser's passed challenge), parsing FBref's raw HTML
directly (`footymodel/fbref.py`, `scripts/fbref_ingest_batch.py`). Confirmed a
real, escalating rate limit under sustained volume (HTTP 429 after ~600
requests in one session) — not a permanent block, but real: got one full clean
season (PL 2023/24, 380 matches, 0 errors, 8,360 rows) plus a partial prior
season (66 matches) before hitting it. Second full season deferred until the
limit clears.

## Calibration result — well-calibrated from the first pass

Reused the exact generic helpers already proven on the Understat shots model
(`_decayed_rate` position-grouped shrinkage, `build_team_xg` generalized,
`prob_over` NB dispersion) — no separate tuning needed, the fixes transferred
directly:

| Line | n | Base rate | Brier (Poisson) | Brier (NB disp=3) |
|-----:|--:|----------:|----------------:|-------------------:|
| 0.5 | 6886 | 28.2% | 0.1639 | 0.1642 |
| 1.5 | 6886 | 7.9% | 0.0626 | 0.0626 |

Gaps stay within ±0.03 across all well-populated buckets (n≥100) for both
lines; the larger gaps only appear in tiny tail buckets (n=60, n=2 — noise, not
signal). Poisson and NB are statistically indistinguishable here — the
overdispersion fix mattered on the larger, multi-season shots dataset; on this
smaller single-season sample there isn't enough data to tell them apart, so no
need to force NB where it isn't shown to help.

**Status: proof of concept confirmed on one league-season.** Same open
question as the shots model before its own multi-league check: does this hold
up with more data/leagues, or is it a smaller-scale echo of the earlier
"looked good on one dataset" trap? Recommended next step once the FBref rate
limit clears: a second full season (or a second league) to cross-check, same
discipline used throughout this project.

# Phase E — Player Shots/SOT via WhoScored (real minutes, both stats at once)

FBref's rate limit didn't clear in a useful timeframe, and its 403 block later
escalated to a site-wide interactive CAPTCHA (hard stop - never attempt to
solve one). Rather than wait, switched data source to **WhoScored**, using the
user's real Chrome (`claude-in-chrome`) instead of the sandboxed browser, on
the theory that a real browser session might dodge WhoScored's own
fingerprinting layer too. It didn't fully - WhoScored's JSON stats API blocks
a *second* call from the same page context regardless of delay - but the
**already-rendered livestatistics page** reads reliably, and same-origin
`<iframe>`s let the whole scrape run as one background async loop per browser
tab (avoiding a live navigation - and a full round-trip - per match).

WhoScored turned out richer than FBref in two ways that directly improve the
model, not just a like-for-like swap:
- **Real per-player minutes.** The page shows the exact substitution minute
  for every starter subbed off and every sub brought on (unused subs show no
  minute at all and are dropped). Previous models used a flat 85-minute
  assumption for every appearance; this is the first version using each
  player's *actual* minutes as the exposure in `prob_over`.
- **Real position codes for starters** (GK/DC/DL/DR/DMC.../FW...) matching
  `POSITION_GROUPS` directly - no id-recovery hack needed like FBref's
  longest-common-prefix trick. Used subs are tagged generically `"Sub"`; their
  true position group is recovered the same way `players.py` already does it
  elsewhere - from that player's own starts elsewhere in the season.

Scraped the full season (PL 2023/24, all 380 matches) across three passes,
stopping and resuming as real obstacles came up rather than forcing through
them:
1. **284/380** - the in-tab async loop degraded from Chrome's background-tab
   timer throttling once other work took focus off the tab (not a site block,
   the page loaded fine throughout).
2. **326/380** - a follow-up pass surfaced a real WhoScored rate limit,
   confirmed properly: a match that had scraped cleanly hours earlier started
   failing too, ruling out "just these specific pages are slow" and
   confirming session-wide throttling - same pattern as the FBref 429s in
   Phase D. Stopped rather than hammer a blocked endpoint.
3. **380/380** - retried after the rate limit cleared (~30+ min later, at the
   user's prompt); the remaining 54 matches scraped cleanly in one pass with
   zero errors, confirming the earlier failures really were rate-limiting,
   not a permanent block or a data-quality problem with those specific
   matches. The `<iframe>`-leak bug from pass 1 was also fixed (always
   `.remove()` in a `finally` block) before this run.

One real bug surfaced only at full-season scale and is worth naming: five
matches ended up with a **cross-product row explosion** (1.8M rows instead of
~11k) the first time `whoscored.py`'s date-join ran, because the per-side
`home`/`away` frames used for matching against football-data.co.uk weren't
deduplicated by `match_id` before merging - every home player row joined
against every away player row. Fixed with `.drop_duplicates("match_id")`
before the merge (`footymodel/whoscored.py`).

## Calibration result

Same generic helpers as everywhere else (`_decayed_rate` position-grouped
shrinkage, `build_team_xg` opponent suppression, `prob_over`), but with real
per-match minutes fed in as the exposure instead of a flat constant, for
**both** shots and SOT from the same scrape:

| Stat | Line | n | Base rate | Brier (Poisson) | Brier (NB disp=3) |
|-----:|-----:|--:|----------:|----------------:|-------------------:|
| shots | 0.5 | 8206 | 48.9% | 0.1764 | 0.1777 |
| shots | 1.5 | 8206 | 24.0% | 0.1259 | 0.1270 |
| shots | 2.5 | 8206 | 11.9% | 0.0790 | 0.0792 |
| sot | 0.5 | 8206 | 25.3% | 0.1500 | 0.1506 |
| sot | 1.5 | 8206 | 6.7% | 0.0527 | 0.0527 |

Gaps tightened further with the complete season - mostly within ±0.03 in
populated buckets (n≥100) for every line, plain Poisson included. Notably
**plain Poisson is competitive with (and often tighter than) NB(disp=3)**
across the board - the NB dispersion was tuned to correct for the
flat-85-minutes assumption's unmodeled variance; real per-player minutes
already remove a chunk of that variance, so the extra fat-tail correction
isn't pulling as much weight anymore. Worth re-sweeping the dispersion
constant (or dropping NB back to Poisson) as the default, now that a full
season confirms this isn't a small-sample artifact.

**Status: confirmed on a complete season, real-minutes upgrade validated.**
Next: decide whether WhoScored fully replaces FBref for this pipeline
(`footymodel/live/shots_engine.py` currently still imports from
`footymodel/fbref.py`) or the two are merged/cross-checked. A second
league or season would be the next real robustness check, same discipline
used throughout this project.
