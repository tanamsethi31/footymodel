"""Unit-check € paper props bankroll placement + settlement (no network)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.paper_props_bankroll import place_paper_bets_for_fixture, settle_open_bets

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
    assert float(placed[0]["stake_eur"]) > 0

    graded_path.write_text(
        "fixture_id,kickoff,home,away,player,team,proxy_xi,actual_shots,actual_sot\n"
        "us_1,2026-10-26T15:00:00+00:00,Arsenal,Chelsea,Bukayo Saka,Arsenal,False,3,1\n"
    )
    n = settle_open_bets(graded_path, state_path=state_path, ledger_path=ledger_path)
    assert n == 1
    import csv

    with ledger_path.open(newline="") as f:
        bet = list(csv.DictReader(f))[0]
    assert bet["status"] == "won"
    assert float(bet["pnl_eur"]) > 0

print("paper_props_bankroll_test: OK")
