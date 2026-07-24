#!/usr/bin/env python3
"""
Generate dashboard_data.json for today by running the Sniper master prompt
through the Anthropic API with live web search.

Requires env var: ANTHROPIC_API_KEY
Reads:  master_prompt.md   (your Sniper master prompt)
        dashboard_data.json (previous day -> used as the 'yesterday' reference)
Writes: dashboard_data.json (today)

Exits non-zero on a failed/empty/invalid result so the pipeline stops
instead of publishing a broken dashboard. (This is a sanity check, NOT an
approval gate — normal good output publishes with no human step.)
"""
import os, sys, json, datetime, urllib.request

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL   = "claude-opus-4-8"          # swap to "claude-sonnet-4-6" for lower cost
ENDPOINT = "https://api.anthropic.com/v1/messages"

# --- US market holidays to skip (extend yearly) ---
HOLIDAYS_2026 = {"2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25",
                 "2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25"}

def ny_today():
    # GitHub runs in UTC; ET morning shares the same calendar date.
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def skip_if_closed():
    today = ny_today()
    wd = datetime.date.fromisoformat(today).weekday()
    if wd >= 5 or today in HOLIDAYS_2026:
        print(f"Market closed {today} — skipping."); sys.exit(0)

# The exact data shape the renderer expects (kept in sync with build_html.py).
CONTRACT = open("dashboard_data.example.json", encoding="utf-8").read() \
           if os.path.exists("dashboard_data.example.json") else ""

def previous_day():
    try:
        return json.load(open("dashboard_data.json", encoding="utf-8"))
    except Exception:
        return None

def scanner_board():
    """Load today's sniper-scanner output (downloaded by the workflow into
    scanner_data/). Returns the parsed board, or None to fall back to
    web-search setups."""
    import glob
    files = sorted(glob.glob("scanner_data/**/sniper_universe_*.json", recursive=True))
    if not files:
        return None
    try:
        board = json.load(open(files[-1], encoding="utf-8"))
    except Exception as e:
        print(f"Scanner board unreadable ({e}) — falling back to web search.", file=sys.stderr)
        return None
    if not board.get("data_health", {}).get("safe_to_publish"):
        # Freshness guard tripped upstream: a board built on stale data must
        # not be published, so treat it as absent.
        print("Scanner board marked safe_to_publish=false — falling back to web search.", file=sys.stderr)
        return None
    return board

def scanner_prompt_section(board):
    if board is None:
        return """SCANNER STATUS: no verified scanner data is available today.
Build the "setups" table from web search as before, and append " (not
scanner-verified)" to each setup's check_note so readers know these names were
not machine-screened."""
    boarded = board.get("candidates", {}).get("boarded", [])
    headline = " | ".join(board.get("coverage", {}).get("headline", []))
    if not boarded:
        return f"""SCANNER RESULTS (authoritative): the full-universe scanner ran
successfully today and ZERO names met the criteria. Coverage: {headline}
The "setups" table must reflect that: no qualifying setups today — do NOT
invent setups from web search. Fill the setups section with a single row or
note stating the scan found no qualifying names."""
    return f"""SCANNER RESULTS (authoritative source for the "setups" table):
The full-universe scanner ran successfully today. Coverage: {headline}
Its boarded candidates are below. The "setups" table MUST contain exactly
these tickers — all of them, no additions, no substitutions. Use web search
only to verify current pre-market prices and to write each setup's read and
check_note; do not second-guess the scanner's grades or biases.

{json.dumps(boarded, indent=1)}"""

def call_model(master_prompt, prev, board=None):
    instruction = f"""Run the analysis in the master prompt below using live web search for
today's real market data. Then output ONLY a single JSON object for the dashboard — no
prose, no markdown fences, nothing else.

{scanner_prompt_section(board)}

The JSON MUST match this exact structure and field names (this is an example with last
session's data; replace every value with today's):

{CONTRACT}

Rules:
- Output strictly valid JSON, starting with {{ and ending with }}.
- Fill the "yesterday" section using the PREVIOUS session's numbers provided below.
- Keep HTML allowed only inside the fields that already contain it in the example
  (verdict.desc, focus.*, how_built[].name, snapshot[].val/delta, setups[].read/check_note,
  risks[], earnings intro/outro/rows, yesterday rows).
- Use real, current figures from web search; if a figure can't be verified, say so in the text.

PREVIOUS SESSION (for the 'yesterday' comparison):
{json.dumps(prev) if prev else "none available"}

=== MASTER PROMPT ===
{master_prompt}
"""
    body = {
        "model": MODEL,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": instruction}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(),
        headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # Surface the API's own error message — a bare "400 Bad Request" is undebuggable.
        print(f"Anthropic API error {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        raise
    # Concatenate all text blocks (skip web_search tool blocks)
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return text

def extract_json(text):
    # The model sometimes surrounds the JSON with prose or emits stray braces,
    # so a first-{ to last-} slice is not reliable. Scan every "{" and keep the
    # largest complete object that parses.
    dec = json.JSONDecoder()
    best = None
    idx = text.find("{")
    while idx != -1:
        try:
            obj, end = dec.raw_decode(text, idx)
            if isinstance(obj, dict) and (best is None or end - idx > best[1]):
                best = (obj, end - idx)
        except json.JSONDecodeError:
            pass
        idx = text.find("{", idx + 1)
    if best is None:
        raise ValueError("No JSON object found in model output")
    return best[0]

REQUIRED = ["meta","verdict","composite","gap","focus","how_built","snapshot","setups","scenarios","risks","earnings","yesterday"]

def validate(d):
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise ValueError(f"Missing required sections: {missing}")
    if not (0 <= float(d["composite"]["score"]) <= 100):
        raise ValueError("composite.score out of range")
    if not (0 <= float(d["gap"]["pct"]) <= 100):
        raise ValueError("gap.pct out of range")
    if len(d["how_built"]) != 5:
        raise ValueError("how_built must have exactly 5 bars")
    if not d["earnings"].get("rows"):
        raise ValueError("earnings.rows must not be empty")

def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set"); sys.exit(1)
    skip_if_closed()
    master = open("master_prompt.md", encoding="utf-8").read()
    prev = previous_day()
    board = scanner_board()
    print("Scanner board:", "loaded" if board else "unavailable — web-search fallback")
    # The model occasionally emits malformed JSON; a fresh call almost always
    # succeeds, so retry the whole generate->parse->validate cycle.
    attempts = 3
    for i in range(1, attempts + 1):
        try:
            text = call_model(master, prev, board)
            data = extract_json(text)
            validate(data)
            break
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            print(f"Attempt {i}/{attempts} failed: {e}", file=sys.stderr)
            print(f"--- model output ({len(text)} chars) ---\n{text}\n---", file=sys.stderr)
            if i == attempts:
                raise
    json.dump(data, open("dashboard_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Wrote dashboard_data.json for", data["meta"].get("stamp", ny_today()))

if __name__ == "__main__":
    main()
