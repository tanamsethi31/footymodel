"""Scrape Understat per-match player rosters and save the player-match table."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel import config
from footymodel.understat import build_player_dataset, PLAYER_OUTPUT

DIVS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["E0"]
YEARS = config.DEFAULT_START_YEARS

print(f"Scraping player rosters for {DIVS}, seasons {YEARS}")
df = build_player_dataset(DIVS, YEARS)
df.to_parquet(PLAYER_OUTPUT, index=False)
print(f"\nSaved {len(df)} player-match rows -> {PLAYER_OUTPUT}")
print(f"Unique players: {df['player_id'].nunique()}  matches: {df['match_id'].nunique()}")
