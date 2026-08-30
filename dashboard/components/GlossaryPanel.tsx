export default function GlossaryPanel() {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Glossary</h2>
        <p className="text-sm text-neutral-500">
          What the numbers on the other tabs actually mean.
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          General concepts
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Expected Value (EV)</dt>
            <dd className="text-neutral-500 mt-0.5">
              For a bet with model probability p and decimal odds o: EV = p x o - 1.
              Positive EV means the price pays out more than it should on average,
              given how often the model thinks the outcome actually happens; negative
              EV means the price is worse than fair value even if the outcome is
              likely. Shown as a percentage (+7.3% means staking 1 unit is expected to
              return 1.073 units on average, across many repeats).
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Decimal odds</dt>
            <dd className="text-neutral-500 mt-0.5">
              &quot;@ 1.77&quot; means: stake 1 unit, get back 1.77 total if it wins
              (0.77 profit). Implied probability = 1 / odds (1.77 -&gt; 56.5%). Fair
              (breakeven) odds for a given probability p = 1 / p. A market price above
              that is positive EV, below it is negative.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Track Record terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Model accuracy</dt>
            <dd className="text-neutral-500 mt-0.5">
              Fraction of graded goals predictions where the model&apos;s Over/Under
              2.5 pick matched the real result, whether or not there was a bet on it.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Bets placed</dt>
            <dd className="text-neutral-500 mt-0.5">
              Count of graded predictions where the model showed positive EV on a
              side at the time it was logged (paper-trade only, no real stakes).
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Bet win rate</dt>
            <dd className="text-neutral-500 mt-0.5">Of those bets, the fraction that actually won.</dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Cumulative return</dt>
            <dd className="text-neutral-500 mt-0.5">
              Total realized profit/loss across all bets, in stake units (each bet
              assumed 1 unit).
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">model &#10003; / &#10007;</dt>
            <dd className="text-neutral-500 mt-0.5">
              Whether the model&apos;s Over/Under pick matched the real final score.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Goals O/U terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Model P(O2.5)</dt>
            <dd className="text-neutral-500 mt-0.5">
              The model&apos;s probability that the match finishes with over 2.5
              total goals.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">xG total</dt>
            <dd className="text-neutral-500 mt-0.5">
              The model&apos;s expected combined goals for both teams (Dixon-Coles
              model blended with the confirmed starting lineups).
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Odds O / U</dt>
            <dd className="text-neutral-500 mt-0.5">
              The best available market price for Over 2.5 / Under 2.5, fetched live.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">EV Over / Under</dt>
            <dd className="text-neutral-500 mt-0.5">
              See Expected Value above, computed separately for each side.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">starters matched</dt>
            <dd className="text-neutral-500 mt-0.5">
              How many of the confirmed starting XI (out of 11 per side) were
              successfully matched to the model&apos;s historical player database. A
              prediction needs at least 8 of 11 matched per side to be logged at all.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Player Props terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Shots 1+ / 2+ / 3+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Probability a player registers at least that many total shots in the
              match.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">SOT (Shots on Target) 1+ / 2+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Same idea, restricted to shots that were on target. SOT 3+ shows as
              &quot;-&quot; because that specific threshold has no underlying model
              built for it yet, not because of missing data for a particular player.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Most probable bets</dt>
            <dd className="text-neutral-500 mt-0.5">
              The single highest-probability pick across every player, market, and
              threshold combination logged for today&apos;s fixtures.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Staking terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Kelly criterion</dt>
            <dd className="text-neutral-500 mt-0.5">
              A formula for how much of your bankroll to stake on a positive-EV bet
              to maximize long-run growth, based on the size of your edge and the
              odds. Full Kelly can be aggressive; &quot;1/4 Kelly&quot; means staking
              a quarter of what full Kelly recommends, trading some growth for much
              less variance.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Flat stake</dt>
            <dd className="text-neutral-500 mt-0.5">
              A fixed 1% of starting bankroll every bet, regardless of edge size. The
              baseline comparison against the Kelly strategies.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">median final bankroll</dt>
            <dd className="text-neutral-500 mt-0.5">
              Across 10,000 simulated seasons, the middle outcome, shown as a
              multiple of the starting bankroll (e.g. &quot;5.43x&quot; means the
              bankroll grew to 5.43 times its starting value in the median
              simulation).
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Max drawdown</dt>
            <dd className="text-neutral-500 mt-0.5">
              The largest peak-to-trough drop in bankroll within a single simulated
              season, median across all simulations.
            </dd>
          </div>
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">Risk of ruin</dt>
            <dd className="text-neutral-500 mt-0.5">
              How often, across all simulations, the bankroll fell to 5% or less of
              its starting value.
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
