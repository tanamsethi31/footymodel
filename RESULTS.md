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

**Revised conclusion:** the PL result was likely partly noise/league-specific,
not proof of a robust, transferable lineup edge. This does not fully kill the
lineup hypothesis (team news is real information in principle), but it means we
do **not** have the confident "go" signal needed to justify building the
expensive Phase B live-infrastructure project. Building live lineup ingestion +
fast execution on this evidence would be gambling on an unconfirmed effect.

## The remaining untested thread (low expected value)
- **FBref xG on mid-tier leagues.** But xG bought only ~1pt on the big-5, and
  CLV is already negative on every mid-tier league here — so better inputs are
  unlikely to flip the sign. Recommendation: **accept the no-go.**
