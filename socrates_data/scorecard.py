"""
scorecard.py — turn platform_breadth.csv into a transparent, rule-based
weekly call per category, and map each category to the real instrument(s)
you'd actually check it against.

WHY RULE-BASED, NOT A FITTED MODEL: you have 2 weeks of paired data as of
this run (growing by one a week, plus whatever older weeks you can pull
from the Socrates archive). No model — regression, ML, anything with
learned parameters — can be honestly fit or validated on that. What this
script produces instead is a fixed, documented formula: same inputs always
produce the same call, nothing is tuned to make past weeks look good. It
becomes real backtestable evidence once forward_tracker.py has enough
resolved weeks behind it — see tracker_results.csv once that exists.

Run: python scorecard.py
Reads:  platform_breadth.csv
Writes: scorecard.csv (one row per week_of x category)
"""
import csv
import os
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BREADTH_CSV = os.path.join(DATA_DIR, "platform_breadth.csv")
SCORECARD_CSV = os.path.join(DATA_DIR, "scorecard.csv")

FIELDS = ["week_of", "category", "proxy", "pct_bull_elected", "pct_bear_elected",
          "net_reversal_bias", "pct_aggregate_high", "pct_aggregate_low",
          "net_high_low", "pct_panic_cycle", "score", "call"]

# Real instrument(s) each Socrates category maps to, per your own book.
# ETFs is intentionally unmapped: QQQ/GLD/USO/HYG/TLT are themselves
# classified as ETFs on the platform, so that category substantially
# overlaps the others already covered rather than needing its own series.
CATEGORY_PROXIES = {
    "Stocks": ["QQQ"],
    "Stock Indices": ["QQQ"],
    "Currencies": ["EURUSD=X"],
    "Commodities": ["USO", "GLD"],
    "Bonds": ["HYG", "TLT"],
    "Crypto": ["BTC-USD"],
}

# Fixed formula, documented not fitted (see module docstring):
#   score = 0.4 * net_reversal_bias + 0.4 * net_high_low + 0.2 * pct_panic_cycle
# net_reversal_bias = pct elected bearish - pct elected bullish (this week's
#   NEW elections, not the stock of prior ones)
# net_high_low      = pct aggregate-high-within-3wk - pct aggregate-low-within-3wk
# All three are already in comparable "percentage of category" units.
SCORE_WEIGHTS = {"net_reversal_bias": 0.4, "net_high_low": 0.4, "pct_panic_cycle": 0.2}
CAUTION_THRESHOLD = 8.0      # score above this -> CAUTION
CONSTRUCTIVE_THRESHOLD = -8.0  # score below this -> CONSTRUCTIVE
PANIC_FLAG_THRESHOLD = 20.0    # pct_panic_cycle above this -> volatility flag, regardless of score


def load_breadth():
    with open(BREADTH_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_scorecard(rows):
    by_week_cat = defaultdict(dict)
    for r in rows:
        key = (r["week_of"], r["category"])
        if r["section"] == "reversal_system" and r["metric"] == "Elected a Bullish Reversal":
            by_week_cat[key]["pct_bull_elected"] = float(r["pct"])
        elif r["section"] == "reversal_system" and r["metric"] == "Elected a Bearish Reversal":
            by_week_cat[key]["pct_bear_elected"] = float(r["pct"])
        elif r["section"] == "timing_array" and r["metric"] == "Aggregate High Signal Within 3 weeks":
            by_week_cat[key]["pct_aggregate_high"] = float(r["pct"])
        elif r["section"] == "timing_array" and r["metric"] == "Aggregate Low Signal Within 3 weeks":
            by_week_cat[key]["pct_aggregate_low"] = float(r["pct"])
        elif r["section"] == "timing_array" and r["metric"] == "Panic Cycle Signal Within 3 weeks":
            by_week_cat[key]["pct_panic_cycle"] = float(r["pct"])

    out_rows = []
    for (week_of, category), vals in sorted(by_week_cat.items()):
        needed = ("pct_bull_elected", "pct_bear_elected", "pct_aggregate_high",
                  "pct_aggregate_low", "pct_panic_cycle")
        if not all(k in vals for k in needed):
            continue  # incomplete week/category — skip rather than guess

        net_reversal_bias = vals["pct_bear_elected"] - vals["pct_bull_elected"]
        net_high_low = vals["pct_aggregate_high"] - vals["pct_aggregate_low"]
        score = (SCORE_WEIGHTS["net_reversal_bias"] * net_reversal_bias
                 + SCORE_WEIGHTS["net_high_low"] * net_high_low
                 + SCORE_WEIGHTS["pct_panic_cycle"] * vals["pct_panic_cycle"])

        if score > CAUTION_THRESHOLD:
            call = "CAUTION"
        elif score < CONSTRUCTIVE_THRESHOLD:
            call = "CONSTRUCTIVE"
        else:
            call = "NEUTRAL"
        if vals["pct_panic_cycle"] > PANIC_FLAG_THRESHOLD:
            call += "+VOLATILITY_FLAG"

        proxies = CATEGORY_PROXIES.get(category, [])
        out_rows.append({
            "week_of": week_of, "category": category, "proxy": "/".join(proxies) or "—",
            "pct_bull_elected": vals["pct_bull_elected"], "pct_bear_elected": vals["pct_bear_elected"],
            "net_reversal_bias": round(net_reversal_bias, 2),
            "pct_aggregate_high": vals["pct_aggregate_high"], "pct_aggregate_low": vals["pct_aggregate_low"],
            "net_high_low": round(net_high_low, 2),
            "pct_panic_cycle": vals["pct_panic_cycle"],
            "score": round(score, 2), "call": call,
        })
    return out_rows


def write_scorecard(out_rows):
    with open(SCORECARD_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)


def main():
    rows = load_breadth()
    out_rows = build_scorecard(rows)
    write_scorecard(out_rows)
    print(f"Wrote {len(out_rows)} scorecard rows to {os.path.basename(SCORECARD_CSV)} "
          f"({len(set(r['week_of'] for r in out_rows))} week(s))")
    for r in out_rows:
        print(f"  {r['week_of']} {r['category']:14s} score={r['score']:>7.2f}  {r['call']:<24s} proxy={r['proxy']}")


if __name__ == "__main__":
    main()
