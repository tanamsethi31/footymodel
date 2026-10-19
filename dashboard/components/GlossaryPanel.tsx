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
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
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
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
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
          Timeline &amp; pre-match
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Preview vs Today</dt>
            <dd className="text-neutral-500 mt-0.5">
              Fixtures bucket by UTC kickoff date. &quot;Today&quot; includes live
              matches until full-time; &quot;Upcoming&quot; is the next scheduled
              matchdays in the saved calendar.
            </dd>
          </div>
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Players to watch</dt>
            <dd className="text-neutral-500 mt-0.5">
              Pre-lineup shortlist ranked by P(shots 1+) vs this opponent using recent
              starters — not the confirmed XI.
            </dd>
          </div>
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Confirmed starting XI</dt>
            <dd className="text-neutral-500 mt-0.5">
              Names from the live lineup feed once published (~20–40 min pre-kickoff).
              Prop probabilities are computed for those starters only.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Player props terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Shots 1+ / 2+ / 3+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Probability a player registers at least that many total shots in the
              match.
            </dd>
          </div>
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">SOT (Shots on Target) 1+ / 2+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Same idea, restricted to shots that were on target. SOT 3+ shows as
              &quot;-&quot; because that specific threshold has no underlying model
              built for it yet, not because of missing data for a particular player.
            </dd>
          </div>
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Most probable bets</dt>
            <dd className="text-neutral-500 mt-0.5">
              The single highest-probability pick across every player, market, and
              threshold combination logged for today&apos;s fixtures.
            </dd>
          </div>
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">85-minute assumption</dt>
            <dd className="text-neutral-500 mt-0.5">
              Starters are modeled for typical league-average minutes unless a
              player-specific minutes curve exists in the training data.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Notifications
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="border-l-2 border-blue-600 dark:border-blue-400 pl-3">
            <dt className="font-medium">Enable alerts</dt>
            <dd className="text-neutral-500 mt-0.5">
              Uses Web Push (no app store). Your browser must allow notifications for
              this site. A new alert fires when the live poll commits fresh player-prop
              rows to GitHub.
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
