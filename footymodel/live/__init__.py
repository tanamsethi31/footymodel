"""Phase B — live lineup pipeline (detection + paper-trade, not execution).

Ties the CONFIRMED full-lineup model (Phase A: pooled t=3.04 across big-5) to a
live data feed: watch upcoming fixtures, detect when starting lineups are
confirmed (~20-40 min pre-kickoff per API-Football's own docs), recompute the
Over/Under prediction from the actual XI, compare to current market odds, and
log a timestamped recommendation. Ships in DETECTION/PAPER-TRADE mode — no
staking, no live odds execution, no exchange integration yet.

Requires an API-FOOTBALL_KEY environment variable (get one at api-football.com;
the free tier — 100 req/day — is enough to watch a handful of fixtures/day).
"""
