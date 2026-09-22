"""
forward_tracker.py — join scorecard.py's weekly calls against what the real
proxy instrument actually did over the following 3 weeks. This is what
turns the scorecard from "a plausible-looking read" into evidence: every
week adds one more resolved (or still-pending) data point.

Needs market_prices.csv (see market_data.py — run that first, on your own
machine, since this sandbox can't reach Yahoo Finance directly).

Run: python forward_tracker.py
Reads:  scorecard.csv, market_prices.csv
Writes: tracker_results.csv — one row per (week_of, category, proxy symbol)
"""
import csv
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SCORECARD_CSV = os.path.join(DATA_DIR, "scorecard.csv")
PRICES_CSV = os.path.join(DATA_DIR, "market_prices.csv")
OUT_CSV = os.path.join(DATA_DIR, "tracker_results.csv")

FORWARD_DAYS = 21  # "3 weeks" per Socrates' own "Within 3 weeks" language

FIELDS = ["week_of", "category", "proxy_symbol", "call", "score",
          "price_at_signal", "signal_date_used", "target_date",
          "price_3wk_later", "date_3wk_used", "realized_return_pct",
          "window_max", "window_min", "status"]


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nearest_on_or_before(prices_by_symbol, symbol, target: str):
    """Most recent close on or before `target` (YYYY-MM-DD). None if none exists."""
    rows = prices_by_symbol.get(symbol, [])
    candidates = [r for r in rows if r["date"] <= target]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["date"])


def nearest_on_or_after(prices_by_symbol, symbol, target: str):
    rows = prices_by_symbol.get(symbol, [])
    candidates = [r for r in rows if r["date"] >= target]
    if not candidates:
        return None
    return min(candidates, key=lambda r: r["date"])


def window_extremes(prices_by_symbol, symbol, start: str, end: str):
    rows = [r for r in prices_by_symbol.get(symbol, []) if start <= r["date"] <= end]
    if not rows:
        return None, None
    closes = [float(r["close"]) for r in rows]
    return max(closes), min(closes)


def main():
    scorecard = load_csv(SCORECARD_CSV)
    if not scorecard:
        raise SystemExit("No scorecard.csv found/empty — run scorecard.py first.")
    price_rows = load_csv(PRICES_CSV)
    if not price_rows:
        raise SystemExit(
            "No market_prices.csv found. Run market_data.py on your own machine "
            "first (this sandbox can't reach Yahoo Finance — see that script's "
            "docstring), then copy market_prices.csv in here and re-run this."
        )

    prices_by_symbol = {}
    for r in price_rows:
        prices_by_symbol.setdefault(r["symbol"], []).append(r)

    out_rows = []
    for row in scorecard:
        proxies = [p for p in row["proxy"].split("/") if p and p != "—"]
        for symbol in proxies:
            signal = nearest_on_or_before(prices_by_symbol, symbol, row["week_of"])
            if signal is None:
                out_rows.append({**{k: "" for k in FIELDS}, "week_of": row["week_of"],
                                  "category": row["category"], "proxy_symbol": symbol,
                                  "call": row["call"], "score": row["score"],
                                  "status": "NO_PRICE_DATA"})
                continue

            target_date = (datetime.strptime(row["week_of"], "%Y-%m-%d")
                            + timedelta(days=FORWARD_DAYS)).strftime("%Y-%m-%d")
            future = nearest_on_or_after(prices_by_symbol, symbol, target_date)
            wmax, wmin = window_extremes(prices_by_symbol, symbol, row["week_of"], target_date)

            if future is None:
                status = "PENDING"  # window hasn't happened yet (or data doesn't reach there) — not guessed
                price_later, date_used, ret = "", "", ""
            else:
                status = "RESOLVED"
                price_later = future["close"]
                date_used = future["date"]
                ret = round((float(price_later) / float(signal["close"]) - 1) * 100, 2)

            out_rows.append({
                "week_of": row["week_of"], "category": row["category"], "proxy_symbol": symbol,
                "call": row["call"], "score": row["score"],
                "price_at_signal": signal["close"], "signal_date_used": signal["date"],
                "target_date": target_date,
                "price_3wk_later": price_later, "date_3wk_used": date_used,
                "realized_return_pct": ret,
                "window_max": round(wmax, 4) if wmax is not None else "",
                "window_min": round(wmin, 4) if wmin is not None else "",
                "status": status,
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    resolved = sum(1 for r in out_rows if r["status"] == "RESOLVED")
    pending = sum(1 for r in out_rows if r["status"] == "PENDING")
    missing = sum(1 for r in out_rows if r["status"] == "NO_PRICE_DATA")
    print(f"Wrote {len(out_rows)} rows to {os.path.basename(OUT_CSV)}: "
          f"{resolved} resolved, {pending} pending (window not elapsed yet), "
          f"{missing} missing price data.")
    if resolved < 20:
        print(f"NOTE: only {resolved} resolved rows — nowhere near enough to draw a "
              f"statistical conclusion (rule of thumb: don't trust a hit-rate claim "
              f"until this is in the dozens, ideally 50+, spanning different market "
              f"regimes, not just a few consecutive similar weeks).")


if __name__ == "__main__":
    main()
