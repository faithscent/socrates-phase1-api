"""
study_breadth.py — explore platform_breadth.csv (the whole-platform
weekly breadth summary, by category: Stocks/Currencies/Stock Indices/
Bonds/Commodities/ETFs/Crypto).

This is the macro-trend-finding layer: instead of one market at a time,
it shows whether a *whole asset class* is tilting bullish/bearish/volatile
this week, and how that's shifting week over week — the kind of read that
tells you which category to go looking for a specific trade in (e.g. "bonds
just flipped net-bearish on reversals" -> go pull TLT data).

Open in VS Code, run cell-by-cell (# %%). Needs pandas + matplotlib.
"""
# %%
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent
breadth = pd.read_csv(DATA_DIR / "platform_breadth.csv", parse_dates=["week_of"])
breadth.tail(20)

# %%
# Net reversal bias per category per week: % elected bearish minus % elected
# bullish. Positive = more of the category electing bearish reversals than
# bullish ones (net bearish breadth); negative = net bullish breadth.
rev = breadth[breadth["section"] == "reversal_system"]
rev_pivot = rev.pivot_table(index=["week_of", "category"], columns="metric", values="pct").reset_index()
rev_pivot["net_bearish_pct"] = (
    rev_pivot.get("Elected a Bearish Reversal", 0) - rev_pivot.get("Elected a Bullish Reversal", 0)
)
net_bearish_by_week = rev_pivot.pivot(index="week_of", columns="category", values="net_bearish_pct")
net_bearish_by_week

# %%
# Panic Cycle exposure per category per week — categories with a rising
# Panic Cycle % are the ones where volatility (not direction) is the story.
pc = breadth[(breadth["section"] == "timing_array") &
             (breadth["metric"] == "Panic Cycle Signal Within 3 weeks")]
pc_by_week = pc.pivot(index="week_of", columns="category", values="pct")
pc_by_week

# %%
# Aggregate High vs Low signal balance per category — a category with far
# more "Aggregate High Signal" than "Aggregate Low Signal" markets is
# broadly topping; the reverse is broadly bottoming.
ta = breadth[breadth["section"] == "timing_array"]
ta_pivot = ta.pivot_table(index=["week_of", "category"], columns="metric", values="pct").reset_index()
ta_pivot["high_minus_low_pct"] = (
    ta_pivot.get("Aggregate High Signal Within 3 weeks", 0) - ta_pivot.get("Aggregate Low Signal Within 3 weeks", 0)
)
high_low_by_week = ta_pivot.pivot(index="week_of", columns="category", values="high_minus_low_pct")
high_low_by_week

# %%
# Which category moved the most week-over-week on net reversal bias —
# the "what changed" scan, useful once you have 2+ weeks loaded.
if len(net_bearish_by_week) >= 2:
    delta = net_bearish_by_week.diff().iloc[-1].sort_values(key=abs, ascending=False)
    print("Biggest net-bearish-bias swings, most recent week vs prior:")
    print(delta)
else:
    print("Need at least 2 weeks loaded to show week-over-week deltas.")

# %%
# Visual: net bearish reversal bias by category over time.
import matplotlib.pyplot as plt

ax = net_bearish_by_week.plot(marker="o", figsize=(9, 5))
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("Net bearish reversal bias by category (elected bearish % − elected bullish %)")
ax.set_ylabel("percentage points")
plt.tight_layout()
plt.show()
