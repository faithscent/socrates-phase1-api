"""
study_trends.py — explore weekly_macro_trends.csv / weekly_macro_read.csv.

Open this in VS Code with the Python extension and run cell-by-cell
(each "# %%" is a cell — "Run Cell" appears above it, or Shift+Enter).
Needs pandas (`pip install pandas`) and, for the heatmap cell, matplotlib
(`pip install matplotlib`).
"""
# %%
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent
trends = pd.read_csv(DATA_DIR / "weekly_macro_trends.csv", parse_dates=["week_of"])
reads = pd.read_csv(DATA_DIR / "weekly_macro_read.csv", parse_dates=["week_of"])
trends.tail(20)

# %%
# Pivot: one row per week, one column per market, cell = weekly L-Wave color.
# This is the fast "does everything agree this week" view.
color_pivot = trends.pivot_table(
    index="week_of", columns="market", values="weekly_lwave", aggfunc="first"
)
color_pivot

# %%
# Alignment score per week: how lopsided is GREEN vs PURPLE across markets.
# +1 = every tracked market GREEN, -1 = every market PURPLE, 0 = split.
def alignment_score(row):
    vals = [v for v in row if v in ("GREEN", "PURPLE")]
    if not vals:
        return None
    green = vals.count("GREEN")
    purple = vals.count("PURPLE")
    return (green - purple) / len(vals)

alignment = color_pivot.apply(alignment_score, axis=1).rename("alignment_score")
alignment_table = pd.concat([color_pivot, alignment], axis=1)
alignment_table

# %%
# Weeks with a Panic Cycle flag on ANY market — per Section 12 rule 5c,
# these are "exit/stand-aside" weeks regardless of color, worth a second look.
pc_weeks = trends[trends["pc_flag_date"].notna() & (trends["pc_flag_date"] != "")]
pc_weeks[["week_of", "market", "pc_flag_date", "source"]]

# %%
# Rows sitting close to a reversal level (the live decision points) —
# fill in reversal_above/reversal_below as numbers to use this; skipped
# automatically if they're blank or non-numeric for a given row.
numeric = trends.copy()
for col in ("reversal_above", "reversal_below"):
    numeric[col] = pd.to_numeric(numeric[col], errors="coerce")
numeric[["week_of", "market", "reversal_above", "reversal_below", "notes"]].dropna(
    subset=["reversal_above", "reversal_below"], how="all"
)

# %%
# The macro read you logged each week, alongside the alignment score computed
# above — sanity-check your own narrative call against the numeric one.
reads.merge(alignment.reset_index(), on="week_of", how="outer").sort_values("week_of")

# %%
# Optional visual: GREEN/PURPLE heatmap across weeks x markets.
import matplotlib.pyplot as plt

code = color_pivot.replace({"GREEN": 1, "PURPLE": -1, "": None}).astype(float)
fig, ax = plt.subplots(figsize=(1.2 * max(len(code.columns), 1) + 2, 0.4 * max(len(code), 1) + 2))
im = ax.imshow(code.fillna(0).to_numpy(), cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(len(code.columns)))
ax.set_xticklabels(code.columns, rotation=45, ha="right")
ax.set_yticks(range(len(code.index)))
ax.set_yticklabels([d.strftime("%Y-%m-%d") for d in code.index])
ax.set_title("Weekly L-Wave color by market (green=GREEN, red=PURPLE, white=blank)")
fig.colorbar(im, ax=ax, ticks=[-1, 0, 1], label="PURPLE .. blank .. GREEN")
plt.tight_layout()
plt.show()
