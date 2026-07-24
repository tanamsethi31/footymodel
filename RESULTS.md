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

## Candidate next experiments (base rate: most still fail)
1. **Benchmark vs OPENING odds, not closing.** Edge, if it exists, usually lives
   in early prices before the market sharpens. Realistic (you bet when lines
   open). Uses data we already have. **Highest-value next test.**
2. **Add xG (Understat)** — Phase 2b. The plan's flagged upgrade; more predictive
   inputs. Real work (multi-source join), uncertain payoff.
3. **Restrict markets / raise edge threshold.** Diagnostic-driven, but no market
   is robustly positive, so unlikely to rescue it alone.
4. **Accept the no-go.** The honest, plan-mandated option: do not bet real money.
