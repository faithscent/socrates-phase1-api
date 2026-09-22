"""
iv_snapshot.py — MVP for the "is this still cheap?" question the breadth
report can't answer on its own.

WHAT THIS IS: a same-discipline sibling to market_data.py — run it on your
own machine (this sandbox can't reach Yahoo Finance, confirmed the same
way as before: a 403 policy denial, not a timeout), and it appends one
row per proxy per day to iv_snapshot.csv. It does NOT give you an IV Rank
on day one — that needs a history of its own IV readings to rank against,
same as breadth needed weeks to accumulate before scorecard.py meant
anything. What it gives you immediately is today's real number: current
ATM implied vol and put/call skew for the instruments you'd actually use
to express each category's breadth call.

WHY THE PROXY LIST DIFFERS SLIGHTLY FROM scorecard.py's CATEGORY_PROXIES:
scorecard.py maps each Socrates category to the instrument that best
represents it (EURUSD=X spot, BTC-USD spot). Spot FX and spot crypto don't
have standard listed options, so for THIS script only, Currencies and
Crypto point at the nearest listed-options equivalent instead. Both are
one step further removed from the thing Socrates is actually reading than
QQQ/HYG/TLT/USO/GLD are, and IBIT specifically tracks a fund NAV, not raw
BTC-USD spot, so treat its skew as directionally useful, not exact.

CURRENCIES IS NOW FIVE SYMBOLS, NOT ONE: originally this only pulled FXE
(Euro), because "Currencies" as a Socrates category was being expressed
through a single instrument. That undersold what's actually tradeable —
FXY (Yen), FXB (Pound), FXF (Franc), and FXC (Canadian Dollar) are all
real, liquid, optionable Invesco CurrencyShares ETFs too, and a Currencies
CAUTION/CONSTRUCTIVE call doesn't tell you which specific pair to act on.
Pulling IV/skew for all five means you can compare them against each
other under the same category-level breadth read, rather than only ever
seeing the Euro side of it. SGD, TWD, INR, and CNY don't have a
comparably liquid listed-options ETF, so they're left out here (same as
market_data.py leaves them spot-only).

WHAT "OTM" MEANS HERE: yfinance's option chain gives you each contract's
own implied volatility but not its delta (no Greeks in the free feed), so
rather than claim a "25-delta" read I don't actually have, this measures
skew using the nearest strike ~5% above and ~5% below spot and says so
plainly. It's a real, honest number — just not delta-precise. If you get
real delta from IBKR's own option chain later, swap it in.

Run: python iv_snapshot.py
Reads:  nothing (hits Yahoo Finance live)
Writes: iv_snapshot.csv (appends one row per symbol per day; running it
        again same day just updates today's rows rather than duplicating)
"""
import csv
import os
from datetime import date, datetime

import yfinance as yf

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(DATA_DIR, "iv_snapshot.csv")

# category -> (symbol or [symbols], note)
# Same instruments as scorecard.py's CATEGORY_PROXIES wherever they're
# optionable; swapped to the nearest listed-options equivalent where not.
OPTIONABLE_PROXIES = {
    "Stocks": ["QQQ"],
    "Stock Indices": ["QQQ"],
    "Currencies": ["FXE", "FXY", "FXB", "FXF", "FXC"],  # scorecard.py uses EURUSD=X spot only — not optionable; these five ARE
    "Commodities": ["USO", "GLD"],
    "Bonds": ["HYG", "TLT"],
    "Crypto": ["IBIT"],          # scorecard.py uses BTC-USD spot — not optionable
}

TARGET_DTE = 35     # aim for ~5-week options — long enough to matter for a campaign trade, short enough to stay liquid
DTE_WINDOW = (20, 55)  # acceptable range if the exact target isn't listed
OTM_BAND_PCT = 0.05  # "~5% OTM" — see module docstring for why not delta-based

FIELDS = ["date", "category", "symbol", "spot", "expiry_used", "dte",
          "atm_call_iv", "atm_put_iv", "atm_iv_avg",
          "otm_call_iv_5pct", "otm_put_iv_5pct", "put_call_skew_5pct"]


def select_expiry(available_expiries, today, target_dte=TARGET_DTE, window=DTE_WINDOW):
    """Pick the listed expiry closest to target_dte, but only if it falls
    inside window. Returns (expiry_str, dte) or (None, None) if nothing in
    range — refuse to silently pick something outside the intended horizon."""
    best = None
    best_diff = None
    for exp_str in available_expiries:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if dte < window[0] or dte > window[1]:
            continue
        diff = abs(dte - target_dte)
        if best is None or diff < best_diff:
            best, best_diff, best_dte = exp_str, diff, dte
    if best is None:
        return None, None
    return best, best_dte


def nearest_row(chain_df, target_strike):
    """Row in a calls/puts DataFrame with strike closest to target_strike."""
    if chain_df is None or len(chain_df) == 0:
        return None
    idx = (chain_df["strike"] - target_strike).abs().idxmin()
    return chain_df.loc[idx]


def compute_snapshot_row(symbol, category, today, spot, calls_df, puts_df, expiry, dte):
    """Pure function, no network — takes calls/puts DataFrames (as yfinance's
    option_chain() returns them: columns include 'strike', 'impliedVolatility')
    and returns one output row as a dict, or None if the chain has nothing
    usable (don't fabricate a reading)."""
    if calls_df is None or puts_df is None or len(calls_df) == 0 or len(puts_df) == 0:
        return None

    atm_call = nearest_row(calls_df, spot)
    atm_put = nearest_row(puts_df, spot)
    otm_call = nearest_row(calls_df, spot * (1 + OTM_BAND_PCT))
    otm_put = nearest_row(puts_df, spot * (1 - OTM_BAND_PCT))

    if atm_call is None or atm_put is None or otm_call is None or otm_put is None:
        return None

    atm_call_iv = round(float(atm_call["impliedVolatility"]) * 100, 2)
    atm_put_iv = round(float(atm_put["impliedVolatility"]) * 100, 2)
    otm_call_iv = round(float(otm_call["impliedVolatility"]) * 100, 2)
    otm_put_iv = round(float(otm_put["impliedVolatility"]) * 100, 2)

    return {
        "date": today.isoformat(),
        "category": category,
        "symbol": symbol,
        "spot": round(float(spot), 4),
        "expiry_used": expiry,
        "dte": dte,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv_avg": round((atm_call_iv + atm_put_iv) / 2, 2),
        "otm_call_iv_5pct": otm_call_iv,
        "otm_put_iv_5pct": otm_put_iv,
        "put_call_skew_5pct": round(otm_put_iv - otm_call_iv, 2),
    }


def fetch_symbol_snapshot(symbol, category, today):
    """The only function that touches the network. Kept thin and separate
    from compute_snapshot_row so the math above is unit-testable without
    Yahoo Finance being reachable."""
    ticker = yf.Ticker(symbol)
    expiries = ticker.options  # tuple of "YYYY-MM-DD" strings
    if not expiries:
        print(f"  SKIPPED {symbol}: no listed options returned")
        return None

    expiry, dte = select_expiry(expiries, today)
    if expiry is None:
        print(f"  SKIPPED {symbol}: no expiry within {DTE_WINDOW[0]}-{DTE_WINDOW[1]} days "
              f"(available: {list(expiries)[:5]}...)")
        return None

    spot = ticker.fast_info.get("lastPrice") if hasattr(ticker, "fast_info") else None
    if not spot:
        hist = ticker.history(period="1d")
        if hist.empty:
            print(f"  SKIPPED {symbol}: couldn't get a spot price")
            return None
        spot = float(hist["Close"].iloc[-1])

    chain = ticker.option_chain(expiry)
    row = compute_snapshot_row(symbol, category, today, spot, chain.calls, chain.puts, expiry, dte)
    if row is None:
        print(f"  SKIPPED {symbol}: option chain for {expiry} had no usable strikes near spot")
    return row


def load_existing_keys():
    if not os.path.exists(OUT_CSV):
        return set()
    with open(OUT_CSV, encoding="utf-8") as f:
        return {(r["date"], r["symbol"]) for r in csv.DictReader(f)}


def append_rows(new_rows):
    file_exists = os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)


def symbols_to_categories():
    """QQQ serves both Stocks and Stock Indices — same instrument, two
    breadth categories. Reverse the category->symbols mapping into
    symbol->[categories] so each symbol is only ever fetched (and priced)
    ONCE per day, not once per category it happens to represent. The row's
    'category' field becomes a joined label (e.g. "Stocks/Stock Indices")
    for readability only — it is NOT part of what makes a row unique;
    (date, symbol) is, matching the Supabase iv_snapshots table."""
    out = {}
    for category, symbols in OPTIONABLE_PROXIES.items():
        for symbol in symbols:
            out.setdefault(symbol, []).append(category)
    return out


def main():
    today = date.today()
    existing = load_existing_keys()
    new_rows = []

    for symbol, categories in symbols_to_categories().items():
        category_label = "/".join(categories)
        if (today.isoformat(), symbol) in existing:
            print(f"SKIPPED {symbol}: already have a {today.isoformat()} row (delete it first to re-pull)")
            continue
        print(f"Fetching {symbol} ({category_label})...")
        row = fetch_symbol_snapshot(symbol, category_label, today)
        if row:
            new_rows.append(row)
            print(f"  {symbol}: spot={row['spot']} ATM IV={row['atm_iv_avg']}% "
                  f"skew(put-call, ~5% OTM)={row['put_call_skew_5pct']}pts "
                      f"[{row['expiry_used']}, {row['dte']}d]")

    if new_rows:
        append_rows(new_rows)
        print(f"\nWrote {len(new_rows)} row(s) to {os.path.basename(OUT_CSV)}")
    else:
        print("\nNothing new to write.")


if __name__ == "__main__":
    main()
