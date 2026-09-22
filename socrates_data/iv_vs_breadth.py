"""
iv_vs_breadth.py — the actual "get more clarity" step: puts each
category's latest breadth call next to today's real options data for its
proxy, side by side, so you can answer "is this still cheap?" yourself.

Deliberately does NOT compute a cheap/rich verdict. There's no IV history
to rank today's reading against yet — same situation breadth was in before
6 weeks accumulated. Run iv_snapshot.py regularly (daily or weekly, your
call) and once you've got a few weeks of iv_snapshot.csv, this script can
be extended to say "today's IV is in the Nth percentile of the last N
readings" honestly, instead of guessing against nothing.

Run: python iv_vs_breadth.py
Reads:  scorecard.csv, iv_snapshot.csv
Writes: nothing — prints a table
"""
import csv
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SCORECARD_CSV = os.path.join(DATA_DIR, "scorecard.csv")
IV_CSV = os.path.join(DATA_DIR, "iv_snapshot.csv")

# Must match iv_snapshot.py's OPTIONABLE_PROXIES — kept as a separate,
# explicit mapping (not imported) so this script still runs even if
# iv_snapshot.py's proxy list changes shape; if you edit one, edit both.
OPTIONABLE_PROXIES = {
    "Stocks": ["QQQ"],
    "Stock Indices": ["QQQ"],
    "Currencies": ["FXE"],
    "Commodities": ["USO", "GLD"],
    "Bonds": ["HYG", "TLT"],
    "Crypto": ["IBIT"],
}


def latest_scorecard_by_category(rows):
    latest = {}
    for r in rows:
        cat = r["category"]
        if cat not in latest or r["week_of"] > latest[cat]["week_of"]:
            latest[cat] = r
    return latest


def latest_iv_by_symbol(rows):
    latest = {}
    for r in rows:
        sym = r["symbol"]
        if sym not in latest or r["date"] > latest[sym]["date"]:
            latest[sym] = r
    return latest


def build_report(scorecard_rows, iv_rows):
    """Pure function — no file I/O — so it's testable with synthetic rows.
    Returns a list of dicts, one per (category, symbol) pair, with breadth
    and IV data joined (IV fields are None if no snapshot exists yet)."""
    latest_score = latest_scorecard_by_category(scorecard_rows)
    latest_iv = latest_iv_by_symbol(iv_rows)

    out = []
    for category, symbols in OPTIONABLE_PROXIES.items():
        score_row = latest_score.get(category)
        for symbol in symbols:
            iv_row = latest_iv.get(symbol)
            out.append({
                "category": category,
                "breadth_week": score_row["week_of"] if score_row else None,
                "breadth_call": score_row["call"] if score_row else None,
                "breadth_score": score_row["score"] if score_row else None,
                "symbol": symbol,
                "iv_date": iv_row["date"] if iv_row else None,
                "atm_iv": iv_row["atm_iv_avg"] if iv_row else None,
                "skew": iv_row["put_call_skew_5pct"] if iv_row else None,
            })
    return out


def print_report(report_rows):
    print(f"{'Category':<14} {'Breadth call':<24} {'Score':>7}  {'Symbol':<7} "
          f"{'ATM IV':>8} {'Skew':>7}  {'IV as of'}")
    print("-" * 90)
    for r in report_rows:
        call = r["breadth_call"] or "no data"
        score = f"{float(r['breadth_score']):.2f}" if r["breadth_score"] not in (None, "") else "—"
        has_iv = r["atm_iv"] not in (None, "")
        iv = f"{float(r['atm_iv']):.2f}%" if has_iv else "no snapshot"
        skew = f"{float(r['skew']):+.2f}" if has_iv else "—"
        iv_date = r["iv_date"] or "—"
        print(f"{r['category']:<14} {call:<24} {score:>7}  {r['symbol']:<7} {iv:>8} {skew:>7}  {iv_date}")

    print("\nSkew = OTM put IV minus OTM call IV, ~5% either side of spot (see iv_snapshot.py "
          "docstring for what that does and doesn't mean). Positive = the options market is "
          "already paying more for downside than upside at that distance — worth asking "
          "yourself whether that means the move breadth is calling is already partly priced in.")
    print("No IV Rank yet — that needs iv_snapshot.csv to accumulate its own history first. "
          "Run iv_snapshot.py regularly and this becomes a real percentile read, not a guess.")


def main():
    if not os.path.exists(SCORECARD_CSV):
        print(f"{os.path.basename(SCORECARD_CSV)} not found — run scorecard.py first.")
        return
    with open(SCORECARD_CSV, encoding="utf-8") as f:
        scorecard_rows = list(csv.DictReader(f))

    if os.path.exists(IV_CSV):
        with open(IV_CSV, encoding="utf-8") as f:
            iv_rows = list(csv.DictReader(f))
    else:
        iv_rows = []
        print(f"Note: {os.path.basename(IV_CSV)} doesn't exist yet — run iv_snapshot.py on your "
              "own machine first (this needs live Yahoo Finance access) to get real IV numbers. "
              "Showing breadth calls only for now.\n")

    report_rows = build_report(scorecard_rows, iv_rows)
    print_report(report_rows)


if __name__ == "__main__":
    main()
