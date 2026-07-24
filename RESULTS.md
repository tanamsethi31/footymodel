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

## The remaining untested thread (low expected value)
- **FBref xG on mid-tier leagues.** But xG bought only ~1pt on the big-5, and
  CLV is already negative on every mid-tier league here — so better inputs are
  unlikely to flip the sign. Recommendation: **accept the no-go.**
