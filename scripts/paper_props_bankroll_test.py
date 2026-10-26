"""Unit-check € paper props bankroll placement + settlement (no network)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.paper_bankroll import (
    LEDGER_PATH,
    place_paper_bets_for_fixture,
    place_paper_goals_from_row,
    settle_open_bets,
)

with tempfile.TemporaryDirectory() as tmp:
    state_path = Path(tmp) / "bankroll.json"
    ledger_path = Path(tmp) / "bets.csv"
    graded_path = Path(tmp) / "graded_players.csv"

    rows = [
        {
            "fixture_id": "sofa_999",
            "kickoff": "2026-10-26T15:00:00+00:00",
            "home": "Arsenal",
            "away": "Chelsea",
            "team": "Arsenal",
            "player": "Bukayo Saka",
            "p_shots_gt0.5": 0.75,
            "odds_shots_gt0.5": 1.5,
            "ev_shots_gt0.5": 0.125,
            "p_shots_gt1.5": 0.3,
            "p_sot_gt0.5": 0.4,
        }
    ]
    placed = place_paper_bets_for_fixture(
        "sofa_999", rows, state_path=state_path, ledger_path=ledger_path, min_ev=0.05
    )
    assert len(placed) == 1
    assert placed[0]["market"] == "shots_gt0.5"
    assert placed[0]["bet_kind"] == "props"
    assert float(placed[0]["stake_eur"]) > 0

    goals_row = {
        "fixture_id": "sofa_1000",
        "kickoff": "2026-10-27T15:00:00+00:00",
        "home": "Liverpool",
        "away": "Arsenal",
        "model_p_over25": 0.58,
        "odds_over25": 1.85,
        "odds_under25": 2.0,
        "ev_over25": 0.073,
        "ev_under25": -0.16,
    }
    gplaced = place_paper_goals_from_row(
        goals_row, state_path=state_path, ledger_path=ledger_path, min_ev=0.05
    )
    assert len(gplaced) == 1 and gplaced[0]["bet_kind"] == "goals_ou"

    graded_path.write_text(
        "fixture_id,kickoff,home,away,player,team,proxy_xi,actual_shots,actual_sot\n"
        "us_1,2026-10-26T15:00:00+00:00,Arsenal,Chelsea,Bukayo Saka,Arsenal,False,3,1\n"
    )
    graded_results = Path(tmp) / "graded_results.csv"
    graded_results.write_text(
        "fixture_id,home,away,kickoff,actual_home_goals,actual_away_goals,actual_total_goals,actual_over_won,model_p_over25\n"
        "sofa_1000,Liverpool,Arsenal,2026-10-27T15:00:00+00:00,2,1,3,True,0.58\n"
    )
    n = settle_open_bets(
        state_path=state_path,
        ledger_path=ledger_path,
        graded_players_path=graded_path,
        graded_results_path=graded_results,
    )
    assert n == 2
    import csv

    with ledger_path.open(newline="") as f:
        bet = list(csv.DictReader(f))[0]
    assert bet["status"] == "won"
    assert float(bet["pnl_eur"]) > 0

print("paper_props_bankroll_test: OK")
