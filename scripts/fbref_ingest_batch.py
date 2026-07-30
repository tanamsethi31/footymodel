"""Parse one browser-tool-result file (from a fbref batch-fetch javascript_exec
call that returned JSON.stringify(results)) and append rows to the running
FBref scrape cache (JSONL, one row per player-match).

Usage: python scripts/fbref_ingest_batch.py <tool-result-file> <league> <season>
"""
import json
import sys
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "data" / "raw_fbref" / "player_match.jsonl"


def load_tool_result(path: str):
    with open(path) as f:
        d = json.load(f)
    text = "".join(part["text"] for part in d)
    decoder = json.JSONDecoder()
    val, _ = decoder.raw_decode(text)  # ignores trailing "(captured at origin...)" junk
    return json.loads(val) if isinstance(val, str) else val


def main():
    path, league, season = sys.argv[1], sys.argv[2], sys.argv[3]
    matches = load_tool_result(path)
    errors = [m for m in matches if "error" in m]
    if errors:
        print(f"  ! {len(errors)} failed matches: {[e['url'] for e in errors][:3]}")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with open(CACHE, "a") as out:
        for m in matches:
            if "rows" not in m:
                continue
            for r in m["rows"]:
                r["league"] = league
                r["season"] = season
                r["match_url"] = m["url"]
                out.write(json.dumps(r) + "\n")
                n_rows += 1
    print(f"Appended {n_rows} rows from {len(matches)} matches -> {CACHE}")


if __name__ == "__main__":
    main()
