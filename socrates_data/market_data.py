"""
market_data.py — pull real daily OHLCV (open/high/low/close/volume) for the
scorecard proxies plus your full macro watchlist.

⚠ RUN THIS ON YOUR OWN MACHINE, NOT IN THIS SANDBOX. The cloud workspace
this conversation runs in has its outbound network access restricted to an
allowlist (package registries, a few API hosts) and Yahoo Finance is not
on it — confirmed directly (query2.finance.yahoo.com and fc.yahoo.com both
come back "403 policy denial" from the proxy here, not a transient error).
Rather than approximate real prices — which would quietly break the "no
inference, only sourced data" rule this whole project runs on — this
script is meant for you to run in VS Code on your own machine, where
yfinance can actually reach Yahoo.

WHAT CHANGED FROM THE OLD VERSION: it used to fetch only Close for the 7
scorecard proxies. It now fetches full OHLCV, and the symbol list has
grown to match the instruments in your actual Socrates Watchlist
screenshots (Tech/momentum names, global indices, rates, commodities
futures, FX spot, crypto).

IMPORTANT — READ THIS BEFORE TRUSTING THE OUTPUT: I mapped each of your
Watchlist's display names ("US BMK 10 Yr Index", "S&P Global 100 Index",
etc.) to what I believe is the matching Yahoo Finance ticker, from general
knowledge of Yahoo's ticker conventions — I could NOT verify a single one
of these against live Yahoo data, because this sandbox can't reach Yahoo
at all (see above). Every entry below has a confidence note. "high"
entries are standard, well-known tickers (^GSPC, ^VIX, QQQ, major FX
pairs) I'd bet on. "medium" and "low" entries are real uncertainty — when
you run this the first time, READ THE OUTPUT: this script prints a
WARNING and skips (never fabricates) any symbol Yahoo doesn't recognize
or returns empty data for. If a medium/low-confidence symbol shows up as
skipped, that's expected — tell me and I'll find the right ticker with
you rather than guess again. A few instruments have NO Yahoo ticker at
all and are marked skip_reason accordingly, so you know they were never
attempted, not that they failed silently:
  - Japan BMK 10 Yr Index, Euro BMK 10 Yr Index: no reliable Yahoo
    equivalent found for either sovereign yield index.
  - USD/EUR Cross Rate: this is just 1 / EURUSD=X — mathematically
    derivable from data you already have, not a separate fetch.
  - Ethereum/Bitcoin "Per USD (Binance)" (ETHUSDT, BTCUSDT): yfinance
    doesn't carry Binance-specific quotes. ETH-USD and BTC-USD (the
    Coinbase-sourced pairs, already tracked) are the closest Yahoo has.

Usage:
    pip install yfinance pandas
    python market_data.py

Writes: market_prices.csv — long format: date, symbol, open, high, low,
close, volume. forward_tracker.py and push_to_supabase.py both read this
by column name, so old columns (date, symbol, close) are unchanged —
open/high/low/volume are new columns added alongside them, not a
breaking change.
"""
import os
from datetime import date, timedelta

import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(DATA_DIR, "market_prices.csv")

# Pull enough history to cover older Socrates weeks and give moving
# averages something real to compute over.
LOOKBACK_DAYS = 730

# One row per instrument. symbol=None means "intentionally not fetched" —
# see the confidence notes in the module docstring for why. group/display
# match your Watchlist screenshots as closely as I could read them.
# Mirrored into supabase_schema.sql's `instruments` table — if you add or
# change an entry here, update that table too (same pattern as
# OPTIONABLE_PROXIES / iv_proxy_map elsewhere in this project).
INSTRUMENT_UNIVERSE = [
    # --- already tracked (scorecard.py's CATEGORY_PROXIES) ---
    {"symbol": "QQQ", "display": "Invesco QQQ Trust", "group": "Tech/Momentum", "confidence": "high (already tracked)"},
    {"symbol": "EURUSD=X", "display": "Euro Adjusted Spot (EUR/USD)", "group": "FX", "confidence": "high (already tracked)"},
    {"symbol": "USO", "display": "United States Oil Fund LP", "group": "Commodities", "confidence": "high (already tracked)"},
    {"symbol": "GLD", "display": "SPDR Gold Shares", "group": "Commodities", "confidence": "high (already tracked)"},
    {"symbol": "HYG", "display": "iShares iBoxx $ High Yield Corporate Bond ETF", "group": "Bonds", "confidence": "high (already tracked)"},
    {"symbol": "TLT", "display": "iShares 20+ Year Treasury Bond", "group": "Bonds", "confidence": "high (already tracked)"},
    {"symbol": "BTC-USD", "display": "Bitcoin Per USD (Coinbase)", "group": "Crypto", "confidence": "high (already tracked)"},

    # --- new, from your Watchlist screenshots ---
    {"symbol": "PLTR", "display": "Palantir Technologies Inc", "group": "Tech/Momentum", "confidence": "high"},
    {"symbol": "MU", "display": "Micron Technology", "group": "Tech/Momentum", "confidence": "high"},
    {"symbol": "^NDX", "display": "NASDAQ 100 Index", "group": "Tech/Momentum", "confidence": "high"},
    {"symbol": "NQ=F", "display": "NASDAQ 100 Index Futures", "group": "Tech/Momentum", "confidence": "high"},
    {"symbol": "^IXIC", "display": "NASDAQ Composite Index", "group": "Tech/Momentum", "confidence": "high"},

    {"symbol": "^GSPC", "display": "S&P 500 Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^DJI", "display": "Dow Jones Industrials Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^FTSE", "display": "FTSE 100 Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^N225", "display": "NIKKEI 225 Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^HSI", "display": "Hang Seng Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^GDAXI", "display": "DAX Performance Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "^FCHI", "display": "CAC-40 Index", "group": "Global Indices", "confidence": "high"},
    {"symbol": "000001.SS", "display": "Shanghai Composite", "group": "Global Indices", "confidence": "medium — Yahoo's mainland China exchange data has been unreliable in the past, spot-check it"},
    {"symbol": "^OEX", "display": "S&P Global 100 Index", "group": "Global Indices", "confidence": "LOW — ^OEX is the S&P 100 (US-only megacaps). Socrates' 'S&P Global 100' is a different, broader multinational index; this is a placeholder guess, not a confirmed match"},
    {"symbol": "EEM", "display": "MSCI Emerging Markets $ Index", "group": "Global Indices", "confidence": "LOW — this is the EEM ETF (a tracker fund), not the index itself. Treated as an approximation, not the real thing"},
    {"symbol": "FTSEMIB.MI", "display": "Milano Italia Borsa (MIB) Index", "group": "Global Indices", "confidence": "medium"},

    {"symbol": "GC=F", "display": "Gold Futures (COMEX, continuous front-month)", "group": "Commodities", "confidence": "high, but note: your Watchlist shows a specific dated contract (e.g. GC20621N) — this is the continuous front-month contract, not that exact expiry"},
    {"symbol": "SI=F", "display": "Silver Futures (COMEX, continuous front-month)", "group": "Commodities", "confidence": "high, same dated-contract caveat as gold"},
    {"symbol": "CL=F", "display": "NY Crude Oil Futures", "group": "Commodities", "confidence": "high"},

    {"symbol": "^TNX", "display": "US BMK 10 Yr Index", "group": "Rates", "confidence": "medium — ^TNX is CBOE's 10-Year Treasury Yield Index; it quotes yield times 10 (e.g. a reading of 42.5 means 4.25%), stored raw as Yahoo returns it, not converted"},
    {"symbol": None, "display": "Japan BMK 10 Yr Index", "group": "Rates", "confidence": "UNAVAILABLE — no reliable Yahoo ticker found, not attempted"},
    {"symbol": None, "display": "Euro BMK 10 Yr Index", "group": "Rates", "confidence": "UNAVAILABLE — no reliable Yahoo ticker found, not attempted"},

    {"symbol": "^VIX", "display": "CBOE VIX Index", "group": "Volatility", "confidence": "high"},
    # Added from your pasted "Equity Volatility, Options Market &
    # Corporate Credit Risk" table — checked each via web search (not
    # memory) for a real, currently-listed free ticker before adding.
    # All three confirmed as real Yahoo Finance tickers, same fetch path
    # as every other ^-prefixed index above, but tagged "medium" (not
    # "high" like ^VIX) since this sandbox's network can't reach Yahoo to
    # verify them live — see this file's top-of-file network caveat.
    {"symbol": "^VVIX", "display": "CBOE VVIX Index (volatility of VIX)", "group": "Volatility", "confidence": "medium — real, well-known Cboe ticker, not verified against live data from this sandbox"},
    {"symbol": "^COR1M", "display": "Cboe 1-Month Implied Correlation Index", "group": "Volatility", "confidence": "medium — same caveat. Cboe's older S&P 500 Implied Correlation Index (ICJ) was discontinued; this 1-month tenor from Cboe's 2021+ replacement suite is the closest free match to a pasted '(1M)' correlation reading"},
    {"symbol": "V2TX.DE", "display": "EURO STOXX 50 Volatility (VSTOXX)", "group": "Volatility", "confidence": "medium — European-exchange-listed ticker (.DE suffix), spot-check this resolves on your first real run, same discipline as FTSEMIB.MI below"},

    {"symbol": "DX-Y.NYB", "display": "US Dollar Index", "group": "FX", "confidence": "medium — Yahoo's DXY coverage has had reliability gaps historically, worth spot-checking"},
    {"symbol": "SGD=X", "display": "Singapore Dollar Spot (USD/SGD)", "group": "FX", "confidence": "high"},
    {"symbol": "TWD=X", "display": "Taiwanese Dollar Spot (USD/TWD)", "group": "FX", "confidence": "medium — less liquid pair, spot-check it returns data"},
    {"symbol": "CAD=X", "display": "Canadian Dollar Spot (USD/CAD)", "group": "FX", "confidence": "high"},
    {"symbol": "CHF=X", "display": "Swiss Franc Spot (USD/CHF)", "group": "FX", "confidence": "high"},
    {"symbol": "INR=X", "display": "Indian Rupee Spot (USD/INR)", "group": "FX", "confidence": "high"},
    {"symbol": "CNY=X", "display": "Chinese Yuan Spot (USD/CNY)", "group": "FX", "confidence": "high"},
    {"symbol": "GBPUSD=X", "display": "British Pound Spot (GBP/USD)", "group": "FX", "confidence": "high"},
    {"symbol": "JPY=X", "display": "Japanese Yen Spot (USD/JPY)", "group": "FX", "confidence": "high"},
    {"symbol": "6E=F", "display": "Euro Adjusted Futures (EUR/USD futures)", "group": "FX", "confidence": "medium — verify this CME Euro FX futures symbol still resolves on Yahoo"},
    {"symbol": None, "display": "USD/EUR Cross Rate", "group": "FX", "confidence": "NOT FETCHED — mathematically 1 / EURUSD=X, derivable from data you already have rather than a separate pull"},

    # --- FX ETFs: the actual tradeable/optionable instrument, not the spot
    # rate. Everything above this block (EURUSD=X, JPY=X, etc.) is the spot
    # cross rate — the number Socrates' own report reads and the cleanest
    # read of the currency itself, but you can't buy options on a spot
    # rate. These five are the Invesco CurrencyShares ETFs that DO have a
    # listed, liquid options chain — the actual instrument behind a
    # "buy FXE calls" or "buy FXY puts" decision. iv_snapshot.py already
    # pulls IV/skew for these (see OPTIONABLE_PROXIES there); adding them
    # here too means they also get their own real price/SMA/trend history
    # instead of only IV, so a specific instrument's price move and its
    # option pricing come from the same tracked series rather than
    # borrowing the spot rate's price for an ETF-based decision. SGD, TWD,
    # INR, and CNY don't have a comparably liquid listed-options ETF, so
    # they stay spot-only above.
    {"symbol": "FXE", "display": "Invesco CurrencyShares Euro Trust", "group": "FX-ETF", "confidence": "high"},
    {"symbol": "FXY", "display": "Invesco CurrencyShares Japanese Yen Trust", "group": "FX-ETF", "confidence": "high"},
    {"symbol": "FXB", "display": "Invesco CurrencyShares British Pound Sterling Trust", "group": "FX-ETF", "confidence": "high"},
    {"symbol": "FXF", "display": "Invesco CurrencyShares Swiss Franc Trust", "group": "FX-ETF", "confidence": "high"},
    {"symbol": "FXC", "display": "Invesco CurrencyShares Canadian Dollar Trust", "group": "FX-ETF", "confidence": "high"},

    # Same reasoning as the FX-ETF block above: IBIT is already
    # iv_snapshot.py's optionable proxy for Crypto (BTC-USD spot has no
    # listed options), but its own price/SMA history wasn't tracked here
    # before, so its IV and its price trend came from two different
    # instruments. Now both come from IBIT itself.
    {"symbol": "IBIT", "display": "iShares Bitcoin Trust ETF", "group": "Crypto", "confidence": "high"},
    {"symbol": "ETH-USD", "display": "Ethereum Per USD (Coinbase)", "group": "Crypto", "confidence": "high"},
    {"symbol": None, "display": "Ethereum Per USD (Binance)", "group": "Crypto", "confidence": "UNAVAILABLE — yfinance doesn't carry Binance-specific quotes; ETH-USD (Coinbase) above is the closest Yahoo has"},
    {"symbol": None, "display": "Bitcoin Per USD (Binance)", "group": "Crypto", "confidence": "UNAVAILABLE — same reason; BTC-USD (Coinbase) above is the closest Yahoo has"},
]

SYMBOLS = sorted({row["symbol"] for row in INSTRUMENT_UNIVERSE if row["symbol"]})


def fetch_yfinance(symbols, start, end):
    import yfinance as yf
    frames = []
    for sym in symbols:
        df = yf.download(sym, start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            print(f"WARNING: no data returned for {sym} — skipped, not filled in.")
            continue
        # yfinance sometimes returns a MultiIndex column frame even for a
        # single symbol (varies by version) — flatten defensively.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        cols_needed = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in cols_needed if c not in df.columns]
        if missing:
            print(f"WARNING: {sym} response missing columns {missing} — skipped, not filled in "
                  f"(no partial/fabricated rows).")
            continue
        frame = df[cols_needed].reset_index()
        frame = frame.rename(columns={
            frame.columns[0]: "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        frame["symbol"] = sym
        frames.append(frame[["date", "symbol", "open", "high", "low", "close", "volume"]])
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    return pd.concat(frames, ignore_index=True)


def main():
    not_attempted = [row for row in INSTRUMENT_UNIVERSE if row["symbol"] is None]
    if not_attempted:
        print("Not attempting these (no usable Yahoo ticker — see market_data.py's docstring):")
        for row in not_attempted:
            print(f"  - {row['display']}: {row['confidence']}")
        print()

    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    print(f"Pulling {len(SYMBOLS)} symbols from {start} to {end} ...")
    df = fetch_yfinance(SYMBOLS, start.isoformat(), end.isoformat())
    if df.empty:
        raise SystemExit("Nothing was fetched — check your network/yfinance install and try again.")

    fetched_symbols = set(df["symbol"].unique())
    missing_symbols = set(SYMBOLS) - fetched_symbols
    if missing_symbols:
        print(f"\n{len(missing_symbols)} symbol(s) attempted but returned nothing (see WARNINGs above): "
              f"{', '.join(sorted(missing_symbols))}")
        print("These are the ones worth telling me about if any are medium/low-confidence tickers above.")

    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df = df.sort_values(["symbol", "date"])
    df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {len(df)} rows to {os.path.basename(OUT_CSV)} "
          f"({df['symbol'].nunique()} of {len(SYMBOLS)} attempted symbols, "
          f"{df['date'].min()} to {df['date'].max()})")


if __name__ == "__main__":
    main()
