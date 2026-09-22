"""
study_scorecard.py — check the scorecard's calls against what actually
happened (tracker_results.csv). This is the "does it work" check, not just
a data browser — read the sample-size warnings, they're not boilerplate.

Open in VS Code, run cell-by-cell (# %%). Needs pandas.
"""
# %%
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent
tracker = pd.read_csv(DATA_DIR / "tracker_results.csv", parse_dates=["week_of", "target_date"])
tracker.tail(20)

# %%
resolved = tracker[tracker["status"] == "RESOLVED"].copy()
n = len(resolved)
print(f"{n} resolved (week_of, category, proxy) rows.")
if n < 20:
    print("Too few to mean anything statistically yet — read the numbers below as "
          "\"what's happened so far,\" not as a validated hit rate. Keep logging weeks.")
elif n < 50:
    print("Getting somewhere, but still thin — treat any pattern below as provisional "
          "until this clears ~50 resolved rows across more than one market regime.")

# %%
# Average realized 3-week forward return by call, split off the volatility
# flag so it doesn't get averaged in with the directional read.
resolved["base_call"] = resolved["call"].str.replace("+VOLATILITY_FLAG", "", regex=False)
resolved.groupby("base_call")["realized_return_pct"].agg(["count", "mean", "median", "std"])

# %%
# Same, but per proxy symbol — a category's call might work for one
# instrument in it and not another (e.g. Bonds' HYG vs TLT).
resolved.groupby(["base_call", "proxy_symbol"])["realized_return_pct"].agg(["count", "mean"])

# %%
# Did weeks flagged VOLATILITY (pct_panic_cycle > 20) actually see a wider
# realized range (window_max vs window_min) than weeks that weren't flagged?
resolved["window_range_pct"] = (
    (resolved["window_max"] - resolved["window_min"]) / resolved["price_at_signal"] * 100
)
resolved["volatility_flagged"] = resolved["call"].str.contains("VOLATILITY_FLAG")
resolved.groupby("volatility_flagged")["window_range_pct"].agg(["count", "mean", "median"])

# %%
# Simple directional hit rate: did CAUTION weeks realize a negative return,
# and CONSTRUCTIVE weeks a positive one? (NEUTRAL has no directional claim
# to score.) Only meaningful once n (above) is well past the noise floor.
directional = resolved[resolved["base_call"].isin(["CAUTION", "CONSTRUCTIVE"])].copy()
directional["hit"] = (
    ((directional["base_call"] == "CAUTION") & (directional["realized_return_pct"] < 0))
    | ((directional["base_call"] == "CONSTRUCTIVE") & (directional["realized_return_pct"] > 0))
)
print(f"Directional calls: {len(directional)}, hit rate: "
      f"{directional['hit'].mean() * 100:.1f}%" if len(directional) else "No directional calls resolved yet.")
directional.groupby("base_call")["hit"].agg(["count", "mean"])
