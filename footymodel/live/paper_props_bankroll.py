"""Internal € paper bankroll for live player shots / SOT (SofaScore path only).

Starting balance defaults to €100. Stakes use fractional Kelly when book odds
are present; otherwise model-confidence flat stakes (1% of bankroll) when
probability clears a line-specific floor — SofaScore often has no player-prop
odds at all.

This is not connected to any bookmaker; ledger rows are the experiment record.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..data import PROCESSED_DIR
from ..staking import recommended_stake
from . import namematch

STATE_PATH = PROCESSED_DIR / "paper_props_bankroll.json"
LEDGER_PATH = PROCESSED_DIR / "paper_props_bets.csv"

DEFAULT_START_EUR = 100.0
DEFAULT_KELLY_MULT = 0.25
DEFAULT_MAX_FRACTION = 0.02
DEFAULT_MIN_EV = 0.02
DEFAULT_MAX_BETS_PER_FIXTURE = 12
DEFAULT_MAX_FIXTURE_STAKE_FRACTION = 0.08

# Model-only floors (no book odds) — primary lines only to limit noise.
MIN_P_MODEL_ONLY: dict[str, float] = {
    "shots_gt0.5": 0.68,
    "shots_gt1.5": 0.42,
    "shots_gt2.5": 0.22,
    "sot_gt0.5": 0.62,
    "sot_gt1.5": 0.38,
}

LEDGER_COLUMNS = [
    "bet_id",
    "placed_at",
    "fixture_id",
    "kickoff",
    "home",
    "away",
    "player",
    "market",
    "line",
    "model_p",
    "decimal_odds",
    "ev",
    "pricing",
    "stake_eur",
    "status",
    "pnl_eur",
    "settled_at",
    "actual_value",
]


@dataclass(frozen=True)
class _Candidate:
    player: str
    market: str
    line: float
    model_p: float
    decimal_odds: float | None
    ev: float | None
    pricing: str
    score: float


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return {
            "currency": "EUR",
            "starting_bankroll": DEFAULT_START_EUR,
            "bankroll": DEFAULT_START_EUR,
            "updated_at": _now_iso(),
        }
    with path.open() as f:
        data = json.load(f)
    if "bankroll" not in data:
        data["bankroll"] = data.get("starting_bankroll", DEFAULT_START_EUR)
    return data


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    state["updated_at"] = _now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def _load_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _write_ledger(rows: list[dict], path: Path = LEDGER_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in LEDGER_COLUMNS})


def _bet_id(fixture_id: str, player: str, market: str, line: float) -> str:
    return f"{fixture_id}|{player}|{market}|{line}"


def _norm_label(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _fixture_key(home: str, away: str, kickoff: str) -> tuple[str, str, str]:
    k = pd.Timestamp(kickoff)
    if k.tzinfo is not None:
        k = k.tz_convert("UTC")
    day = k.strftime("%Y-%m-%d")
    return (_norm_label(home), _norm_label(away), day)


def _candidates_from_row(row: dict, min_ev: float) -> list[_Candidate]:
    out: list[_Candidate] = []
    player = str(row["player"])
    for market, line in [
        ("shots_gt0.5", 0.5),
        ("shots_gt1.5", 1.5),
        ("shots_gt2.5", 2.5),
        ("sot_gt0.5", 0.5),
        ("sot_gt1.5", 1.5),
    ]:
        p_key = f"p_{market}"
        o_key = f"odds_{market}"
        e_key = f"ev_{market}"
        p_raw = row.get(p_key)
        if p_raw is None or p_raw == "":
            continue
        p = float(p_raw)
        odds_raw = row.get(o_key)
        ev_raw = row.get(e_key)
        odds = float(odds_raw) if odds_raw not in (None, "") else None
        ev = float(ev_raw) if ev_raw not in (None, "") else None

        if odds and ev is not None and ev >= min_ev:
            out.append(
                _Candidate(
                    player=player,
                    market=market,
                    line=line,
                    model_p=p,
                    decimal_odds=odds,
                    ev=ev,
                    pricing="sofascore_odds",
                    score=ev,
                )
            )
            continue

        floor = MIN_P_MODEL_ONLY.get(market)
        if odds is None and floor is not None and p >= floor:
            out.append(
                _Candidate(
                    player=player,
                    market=market,
                    line=line,
                    model_p=p,
                    decimal_odds=None,
                    ev=None,
                    pricing="model_confidence",
                    score=p - floor,
                )
            )
    return out


def place_paper_bets_for_fixture(
    fixture_id: str,
    prop_rows: list[dict],
    *,
    state_path: Path = STATE_PATH,
    ledger_path: Path = LEDGER_PATH,
    kelly_mult: float = DEFAULT_KELLY_MULT,
    max_fraction: float = DEFAULT_MAX_FRACTION,
    min_ev: float = DEFAULT_MIN_EV,
    max_bets_per_fixture: int = DEFAULT_MAX_BETS_PER_FIXTURE,
    max_fixture_stake_fraction: float = DEFAULT_MAX_FIXTURE_STAKE_FRACTION,
) -> list[dict]:
    """Append new open paper bets for one fixture; returns placed bet dicts."""
    if not prop_rows:
        return []

    state = load_state(state_path)
    bankroll = float(state["bankroll"])
    ledger = _load_ledger(ledger_path)
    existing_ids = {r["bet_id"] for r in ledger if r.get("bet_id")}

    kickoff = prop_rows[0]["kickoff"]
    home = prop_rows[0]["home"]
    away = prop_rows[0]["away"]

    candidates: list[_Candidate] = []
    for row in prop_rows:
        candidates.extend(_candidates_from_row(row, min_ev=min_ev))
    candidates.sort(key=lambda c: c.score, reverse=True)

    placed: list[dict] = []
    fixture_stake_cap = bankroll * max_fixture_stake_fraction
    fixture_stake_used = 0.0
    placed_count = 0

    for cand in candidates:
        if placed_count >= max_bets_per_fixture:
            break
        bid = _bet_id(fixture_id, cand.player, cand.market, cand.line)
        if bid in existing_ids:
            continue

        if cand.pricing == "sofascore_odds" and cand.decimal_odds:
            stake = recommended_stake(
                bankroll,
                cand.model_p,
                cand.decimal_odds,
                kelly_mult=kelly_mult,
                max_fraction=max_fraction,
            )
        else:
            stake = round(bankroll * 0.01, 2)

        if stake <= 0:
            continue
        if fixture_stake_used + stake > fixture_stake_cap:
            stake = round(max(0.0, fixture_stake_cap - fixture_stake_used), 2)
        if stake <= 0:
            break

        bet = {
            "bet_id": bid,
            "placed_at": _now_iso(),
            "fixture_id": fixture_id,
            "kickoff": kickoff,
            "home": home,
            "away": away,
            "player": cand.player,
            "market": cand.market,
            "line": cand.line,
            "model_p": cand.model_p,
            "decimal_odds": cand.decimal_odds if cand.decimal_odds else "",
            "ev": cand.ev if cand.ev is not None else "",
            "pricing": cand.pricing,
            "stake_eur": round(stake, 2),
            "status": "open",
            "pnl_eur": "",
            "settled_at": "",
            "actual_value": "",
        }
        ledger.append(bet)
        placed.append(bet)
        existing_ids.add(bid)
        fixture_stake_used += stake
        placed_count += 1
        bankroll -= stake  # reserve stake from available bankroll until settlement

    if placed:
        state["bankroll"] = round(float(state["bankroll"]) - sum(float(p["stake_eur"]) for p in placed), 2)
        save_state(state, state_path)
        _write_ledger(ledger, ledger_path)
        print(
            f"Paper props: placed {len(placed)} bet(s) on {home} v {away}; "
            f"bankroll now €{state['bankroll']:.2f} (stakes reserved until settled)"
        )
    return placed


def _grade_hit(market: str, line: float, actual_shots: int | None, actual_sot: int | None) -> bool | None:
    if market.startswith("shots_"):
        if actual_shots is None:
            return None
        return actual_shots > line
    if market.startswith("sot_"):
        if actual_sot is None:
            return None
        return actual_sot > line
    return None


def settle_open_bets(
    graded_players_path: Path | None = None,
    *,
    state_path: Path = STATE_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> int:
    """Settle open bets using graded_props_players.csv; returns count settled."""
    graded_players_path = graded_players_path or (PROCESSED_DIR / "graded_props_players.csv")
    if not graded_players_path.exists():
        print(f"No graded props at {graded_players_path} — nothing to settle.")
        return 0

    graded = pd.read_csv(graded_players_path)
    if graded.empty:
        return 0

    graded["_key"] = graded.apply(
        lambda r: _fixture_key(str(r["home"]), str(r["away"]), str(r["kickoff"])),
        axis=1,
    )
    by_key_player: dict[tuple, pd.Series] = {}
    for _, row in graded.iterrows():
        key = (row["_key"], _norm_label(str(row["player"])))
        by_key_player[key] = row

    state = load_state(state_path)
    ledger = _load_ledger(ledger_path)
    settled_n = 0
    bankroll = float(state["bankroll"])

    for bet in ledger:
        if bet.get("status") != "open":
            continue
        fkey = _fixture_key(str(bet["home"]), str(bet["away"]), str(bet["kickoff"]))
        player_key = (fkey, _norm_label(str(bet["player"])))
        row = by_key_player.get(player_key)
        if row is None:
            # Fuzzy player match within same fixture day.
            same_fixture = [r for (k, _), r in by_key_player.items() if k == fkey]
            names = [str(r["player"]) for r in same_fixture]
            match = namematch.best_match(str(bet["player"]), names, threshold=0.75)
            if match:
                row = next(r for r in same_fixture if str(r["player"]) == match)
        if row is None:
            continue

        actual_shots = row.get("actual_shots")
        actual_sot = row.get("actual_sot")
        if pd.isna(actual_shots):
            actual_shots = None
        else:
            actual_shots = int(actual_shots)
        if pd.isna(actual_sot):
            actual_sot = None
        else:
            actual_sot = int(actual_sot)

        market = str(bet["market"])
        line = float(bet["line"])
        hit = _grade_hit(market, line, actual_shots, actual_sot)
        if hit is None:
            continue

        stake = float(bet["stake_eur"])
        odds_raw = bet.get("decimal_odds")
        if odds_raw not in (None, ""):
            odds = float(odds_raw)
            pnl = stake * (odds - 1.0) if hit else -stake
            actual_stat = actual_shots if market.startswith("shots_") else actual_sot
        else:
            # Model-only: even-money style P&L for tracking (no book price).
            pnl = stake if hit else -stake
            actual_stat = actual_shots if market.startswith("shots_") else actual_sot

        bet["status"] = "won" if hit else "lost"
        bet["pnl_eur"] = round(pnl, 2)
        bet["settled_at"] = _now_iso()
        bet["actual_value"] = actual_stat
        bankroll += stake + pnl  # return reserved stake plus win/loss
        settled_n += 1

    if settled_n:
        state["bankroll"] = round(bankroll, 2)
        save_state(state, state_path)
        _write_ledger(ledger, ledger_path)
        print(f"Paper props: settled {settled_n} bet(s); bankroll now €{state['bankroll']:.2f}")
    return settled_n
