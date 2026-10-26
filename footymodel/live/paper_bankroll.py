"""Shared €100 paper bankroll — player props + goals O/U 2.5 (SofaScore path)."""
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
LEDGER_PATH = PROCESSED_DIR / "paper_bankroll_bets.csv"
LEGACY_LEDGER_PATH = PROCESSED_DIR / "paper_props_bets.csv"

DEFAULT_START_EUR = 100.0
DEFAULT_KELLY_MULT = 0.25
DEFAULT_MAX_FRACTION = 0.02
DEFAULT_MIN_EV = 0.02
DEFAULT_MAX_BETS_PER_FIXTURE = 12
DEFAULT_MAX_GOALS_BETS_PER_FIXTURE = 1
DEFAULT_MAX_FIXTURE_STAKE_FRACTION = 0.08

MIN_P_MODEL_ONLY: dict[str, float] = {
    "shots_gt0.5": 0.68,
    "shots_gt1.5": 0.42,
    "shots_gt2.5": 0.22,
    "sot_gt0.5": 0.62,
    "sot_gt1.5": 0.38,
}

LEDGER_COLUMNS = [
    "bet_id",
    "bet_kind",
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
    bet_kind: str
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


def load_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    return _load_ledger(path)


def _load_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    for candidate in (path, LEGACY_LEDGER_PATH):
        if not candidate.exists():
            continue
        with candidate.open(newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if not r.get("bet_kind"):
                r["bet_kind"] = "props"
        return rows
    return []


def _write_ledger(rows: list[dict], path: Path = LEDGER_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            if not r.get("bet_kind"):
                r["bet_kind"] = "props"
            w.writerow({k: r.get(k, "") for k in LEDGER_COLUMNS})


def _bet_id_props(fixture_id: str, player: str, market: str, line: float) -> str:
    return f"{fixture_id}|props|{player}|{market}|{line}"


def _bet_id_goals(fixture_id: str, side: str) -> str:
    return f"{fixture_id}|goals_ou|{side}|2.5"


def _norm_label(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _fixture_key(home: str, away: str, kickoff: str) -> tuple[str, str, str]:
    k = pd.Timestamp(kickoff)
    if k.tzinfo is not None:
        k = k.tz_convert("UTC")
    day = k.strftime("%Y-%m-%d")
    return (_norm_label(home), _norm_label(away), day)


def _props_candidates_from_row(row: dict, min_ev: float) -> list[_Candidate]:
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
        p_raw = row.get(p_key)
        if p_raw is None or p_raw == "":
            continue
        p = float(p_raw)
        odds_raw = row.get(f"odds_{market}")
        ev_raw = row.get(f"ev_{market}")
        odds = float(odds_raw) if odds_raw not in (None, "") else None
        ev = float(ev_raw) if ev_raw not in (None, "") else None

        if odds and ev is not None and ev >= min_ev:
            out.append(_Candidate("props", player, market, line, p, odds, ev, "sofascore_odds", ev))
            continue
        floor = MIN_P_MODEL_ONLY.get(market)
        if odds is None and floor is not None and p >= floor:
            out.append(
                _Candidate("props", player, market, line, p, None, None, "model_confidence", p - floor)
            )
    return out


def _goals_candidate_from_row(row: dict, min_ev: float) -> _Candidate | None:
    over = row.get("odds_over25")
    under = row.get("odds_under25")
    if over in (None, "") or under in (None, ""):
        return None
    over_f, under_f = float(over), float(under)
    p_over = float(row["model_p_over25"])
    ev_over = float(row.get("ev_over25") if row.get("ev_over25") not in (None, "") else p_over * over_f - 1.0)
    ev_under = float(
        row.get("ev_under25") if row.get("ev_under25") not in (None, "") else (1 - p_over) * under_f - 1.0
    )
    if ev_over < min_ev and ev_under < min_ev:
        return None
    if ev_over >= ev_under:
        return _Candidate("goals_ou", "", "ou_over25", 2.5, p_over, over_f, ev_over, "sofascore_odds", ev_over)
    return _Candidate("goals_ou", "", "ou_under25", 2.5, 1 - p_over, under_f, ev_under, "sofascore_odds", ev_under)


def _place_candidates(
    fixture_id: str,
    kickoff: str,
    home: str,
    away: str,
    candidates: list[_Candidate],
    *,
    state_path: Path,
    ledger_path: Path,
    kelly_mult: float,
    max_fraction: float,
    max_bets: int,
    max_fixture_stake_fraction: float,
    label: str,
) -> list[dict]:
    if not candidates:
        return []

    state = load_state(state_path)
    bankroll = float(state["bankroll"])
    ledger = _load_ledger(ledger_path)
    existing_ids = {r["bet_id"] for r in ledger if r.get("bet_id")}

    candidates.sort(key=lambda c: c.score, reverse=True)
    placed: list[dict] = []
    fixture_stake_cap = bankroll * max_fixture_stake_fraction
    fixture_stake_used = 0.0
    placed_count = 0

    for cand in candidates:
        if placed_count >= max_bets:
            break
        if cand.bet_kind == "props":
            bid = _bet_id_props(fixture_id, cand.player, cand.market, cand.line)
        else:
            side = "over" if cand.market == "ou_over25" else "under"
            bid = _bet_id_goals(fixture_id, side)

        if bid in existing_ids:
            continue

        if cand.decimal_odds and cand.pricing == "sofascore_odds":
            stake = recommended_stake(
                bankroll, cand.model_p, cand.decimal_odds, kelly_mult=kelly_mult, max_fraction=max_fraction
            )
        elif cand.bet_kind == "props":
            stake = round(bankroll * 0.01, 2)
        else:
            continue

        if stake <= 0:
            continue
        if fixture_stake_used + stake > fixture_stake_cap:
            stake = round(max(0.0, fixture_stake_cap - fixture_stake_used), 2)
        if stake <= 0:
            break

        bet = {
            "bet_id": bid,
            "bet_kind": cand.bet_kind,
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
        bankroll -= stake

    if placed:
        state["bankroll"] = round(float(state["bankroll"]) - sum(float(p["stake_eur"]) for p in placed), 2)
        save_state(state, state_path)
        _write_ledger(ledger, ledger_path)
        print(f"Paper {label}: placed {len(placed)} bet(s) on {home} v {away}; bankroll €{state['bankroll']:.2f}")
    return placed


def place_paper_goals_from_row(
    row: dict,
    *,
    state_path: Path = STATE_PATH,
    ledger_path: Path = LEDGER_PATH,
    kelly_mult: float = DEFAULT_KELLY_MULT,
    max_fraction: float = DEFAULT_MAX_FRACTION,
    min_ev: float = DEFAULT_MIN_EV,
    max_fixture_stake_fraction: float = DEFAULT_MAX_FIXTURE_STAKE_FRACTION,
) -> list[dict]:
    cand = _goals_candidate_from_row(row, min_ev=min_ev)
    if cand is None:
        return []
    return _place_candidates(
        str(row["fixture_id"]),
        str(row["kickoff"]),
        str(row["home"]),
        str(row["away"]),
        [cand],
        state_path=state_path,
        ledger_path=ledger_path,
        kelly_mult=kelly_mult,
        max_fraction=max_fraction,
        max_bets=DEFAULT_MAX_GOALS_BETS_PER_FIXTURE,
        max_fixture_stake_fraction=max_fixture_stake_fraction,
        label="goals O/U",
    )


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
    if not prop_rows:
        return []
    kickoff = prop_rows[0]["kickoff"]
    home = prop_rows[0]["home"]
    away = prop_rows[0]["away"]
    candidates: list[_Candidate] = []
    for row in prop_rows:
        candidates.extend(_props_candidates_from_row(row, min_ev=min_ev))
    return _place_candidates(
        fixture_id,
        kickoff,
        home,
        away,
        candidates,
        state_path=state_path,
        ledger_path=ledger_path,
        kelly_mult=kelly_mult,
        max_fraction=max_fraction,
        max_bets=max_bets_per_fixture,
        max_fixture_stake_fraction=max_fixture_stake_fraction,
        label="props",
    )


def _grade_props_hit(market: str, line: float, actual_shots: int | None, actual_sot: int | None) -> bool | None:
    if market.startswith("shots_"):
        return None if actual_shots is None else actual_shots > line
    if market.startswith("sot_"):
        return None if actual_sot is None else actual_sot > line
    return None


def _settle_props(ledger, bankroll: float, graded_path: Path) -> tuple[int, float]:
    if not graded_path.exists():
        return 0, bankroll
    graded = pd.read_csv(graded_path)
    if graded.empty:
        return 0, bankroll
    graded["_key"] = graded.apply(
        lambda r: _fixture_key(str(r["home"]), str(r["away"]), str(r["kickoff"])), axis=1
    )
    by_key_player: dict[tuple, pd.Series] = {}
    for _, row in graded.iterrows():
        by_key_player[(row["_key"], _norm_label(str(row["player"])))] = row

    settled = 0
    for bet in ledger:
        if bet.get("status") != "open" or bet.get("bet_kind", "props") != "props":
            continue
        fkey = _fixture_key(str(bet["home"]), str(bet["away"]), str(bet["kickoff"]))
        player_key = (fkey, _norm_label(str(bet["player"])))
        row = by_key_player.get(player_key)
        if row is None:
            same_fixture = [r for (k, _), r in by_key_player.items() if k == fkey]
            names = [str(r["player"]) for r in same_fixture]
            match = namematch.best_match(str(bet["player"]), names, threshold=0.75)
            if match:
                row = next(r for r in same_fixture if str(r["player"]) == match)
        if row is None:
            continue
        actual_shots = row.get("actual_shots")
        actual_sot = row.get("actual_sot")
        actual_shots = int(actual_shots) if pd.notna(actual_shots) else None
        actual_sot = int(actual_sot) if pd.notna(actual_sot) else None
        hit = _grade_props_hit(str(bet["market"]), float(bet["line"]), actual_shots, actual_sot)
        if hit is None:
            continue
        stake = float(bet["stake_eur"])
        odds_raw = bet.get("decimal_odds")
        if odds_raw not in (None, ""):
            pnl = stake * (float(odds_raw) - 1.0) if hit else -stake
        else:
            pnl = stake if hit else -stake
        bet["status"] = "won" if hit else "lost"
        bet["pnl_eur"] = round(pnl, 2)
        bet["settled_at"] = _now_iso()
        bet["actual_value"] = actual_shots if str(bet["market"]).startswith("shots_") else actual_sot
        bankroll += stake + pnl
        settled += 1
    return settled, bankroll


def _settle_goals(ledger, bankroll: float, graded_path: Path) -> tuple[int, float]:
    if not graded_path.exists():
        return 0, bankroll
    graded = pd.read_csv(graded_path)
    if graded.empty:
        return 0, bankroll
    by_fid = {str(r["fixture_id"]): r for _, r in graded.iterrows()}

    settled = 0
    for bet in ledger:
        if bet.get("status") != "open" or bet.get("bet_kind") != "goals_ou":
            continue
        row = by_fid.get(str(bet["fixture_id"]))
        if row is None:
            continue
        if pd.isna(row.get("actual_total_goals")):
            continue
        total = float(row["actual_total_goals"])
        over_won = total > 2.5
        market = str(bet["market"])
        hit = over_won if market == "ou_over25" else not over_won
        stake = float(bet["stake_eur"])
        odds = float(bet["decimal_odds"])
        pnl = stake * (odds - 1.0) if hit else -stake
        bet["status"] = "won" if hit else "lost"
        bet["pnl_eur"] = round(pnl, 2)
        bet["settled_at"] = _now_iso()
        bet["actual_value"] = total
        bankroll += stake + pnl
        settled += 1
    return settled, bankroll


def settle_open_bets(
    *,
    state_path: Path = STATE_PATH,
    ledger_path: Path = LEDGER_PATH,
    graded_players_path: Path | None = None,
    graded_results_path: Path | None = None,
) -> int:
    state = load_state(state_path)
    ledger = _load_ledger(ledger_path)
    bankroll = float(state["bankroll"])
    n_props, bankroll = _settle_props(
        ledger, bankroll, graded_players_path or (PROCESSED_DIR / "graded_props_players.csv")
    )
    n_goals, bankroll = _settle_goals(
        ledger, bankroll, graded_results_path or (PROCESSED_DIR / "graded_results.csv")
    )
    settled_n = n_props + n_goals
    if settled_n:
        state["bankroll"] = round(bankroll, 2)
        save_state(state, state_path)
        _write_ledger(ledger, ledger_path)
        print(f"Paper bankroll: settled {settled_n} bet(s) ({n_props} props, {n_goals} goals); €{state['bankroll']:.2f}")
    return settled_n
