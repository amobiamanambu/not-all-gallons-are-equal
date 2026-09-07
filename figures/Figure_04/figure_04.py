#!/usr/bin/env python3
"""Figure 4. Four years of U.S. Google location-level change.

Panel a: FY2022-FY2025 reported withdrawal by U.S. Google location (grouped bar,
top 12 individually reported locations plus one aggregated "Other" bar).
Panel b: contribution to reported FY2022-FY2025 change, by location.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "earth-futures-mpl"))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


HERE = Path(__file__).resolve().parent
DATA = HERE / "figure_04_google_panel.csv"
OUTPUT = HERE / "output"
STEM = "Figure_4_US_Location_Level_Change"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"
BLUE = "#1F6E8C"
TEAL = "#2A9D8F"
GOLD = "#D5A13E"
CORAL = "#D65A4A"

YEARS = [2022, 2023, 2024, 2025]
TOP_N = 12
OCEAN_BLUE = {2022: "#BBDCE8", 2023: "#74AFC7", 2024: "#3C7FA0", 2025: "#0B4F6C"}


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
            "legend.frameon": False,
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-4",
            "savefig.bbox": "tight", "savefig.pad_inches": 0.10,
        }
    )


def panel_label(ax: plt.Axes, label: str, x: float = -0.075) -> None:
    ax.text(x, 1.02, f"({label})", transform=ax.transAxes, fontsize=17, fontweight="bold", color=INK, ha="left", va="bottom")


def bold_ticks(ax: plt.Axes, axis: str = "both") -> None:
    if axis in ("x", "both"):
        for label in ax.get_xticklabels():
            label.set_fontweight("bold")
    if axis in ("y", "both"):
        for label in ax.get_yticklabels():
            label.set_fontweight("bold")


def clean(ax: plt.Axes, axis: str = "both") -> None:
    ax.grid(True, axis=axis, which="major", color=GRID, linewidth=0.65, alpha=0.75)
    ax.set_axisbelow(True)


def short(label: str) -> str:
    replacements = {"Council Bluffs, IA": "Council Bluffs", "Douglas County, GA": "Douglas County", "Berkeley County, SC": "Berkeley County", "Montgomery County, TN": "Montgomery County"}
    return replacements.get(label, label.replace(", ", ", "))


def main() -> None:
    configure()
    data = pd.read_csv(DATA)
    if len(data) != 83 or data["location"].nunique() != 26:
        raise ValueError("Figure 4 requires the verified 83-row U.S. Google panel")
    matrix = data.pivot(index="location", columns="year", values="withdrawal_mg")
    order = matrix[2025].sort_values(ascending=False).index
    matrix = matrix.reindex(order)
    top_locs = order[:TOP_N]
    other_locs = order[TOP_N:]

    continuing = matrix.dropna(subset=[2022, 2025]).copy()
    changes = (continuing[2025] - continuing[2022]).rename("change_mg").reset_index()
    new_locations = matrix.loc[matrix[2022].isna() & matrix[2025].notna(), 2025].sum()
    contributions = pd.concat(
        [changes.assign(status="Continuing location"), pd.DataFrame([{"location": "First reported after FY2022", "change_mg": new_locations, "status": "First reported after FY2022"}])],
        ignore_index=True,
    ).sort_values("change_mg")
    total_change = matrix[2025].sum() - matrix[2022].sum()
    if not np.isclose(contributions["change_mg"].sum(), total_change):
        raise ValueError("Figure 4 growth decomposition does not reconcile")
    continuing_share = changes["change_mg"].sum() / total_change

    fig = plt.figure(figsize=(18.5, 10.2))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.05, 0.95], wspace=0.28)
    bar_ax = fig.add_subplot(grid[0, 0])
    change_ax = fig.add_subplot(grid[0, 1])
    panel_label(bar_ax, "a")
    panel_label(change_ax, "b")

    # Panel a: grouped bar chart, top 12 locations + "Other"
    labels = [short(loc).split(",")[0] for loc in top_locs] + [f"Other {len(other_locs)} locations"]
    x = np.arange(len(labels))
    width = 0.19
    for i, year in enumerate(YEARS):
        vals = [matrix.loc[loc, year] for loc in top_locs]
        vals.append(matrix.loc[other_locs, year].sum())
        vals = np.nan_to_num(np.array(vals, dtype=float))
        bar_ax.bar(x + (i - 1.5) * width, vals, width=width, color=OCEAN_BLUE[year], label=str(year))
    bar_ax.set_xticks(x)
    bar_ax.set_xticklabels(labels, fontsize=13, fontweight="bold", rotation=45, ha="right", rotation_mode="anchor")
    bar_ax.set_xlabel("U.S. Google location", fontsize=20, fontweight="bold", labelpad=16)
    bar_ax.set_ylabel("Withdrawal (MG)", fontsize=20, fontweight="bold", labelpad=16)
    bar_ax.tick_params(axis="y", labelsize=13)
    bold_ticks(bar_ax, axis="y")
    legend_a = bar_ax.legend(title="Fiscal year", fontsize=12.8, title_fontsize=13.5, loc="upper center", ncol=len(YEARS), columnspacing=1.1, handletextpad=0.5)
    legend_a.get_title().set_fontweight("bold")
    for text in legend_a.get_texts():
        text.set_fontweight("bold")
    clean(bar_ax, axis="y")

    # Panel b: growth-contribution horizontal bar chart
    colors = np.where(contributions["status"].eq("First reported after FY2022"), GOLD, np.where(contributions["change_mg"].ge(0), BLUE, CORAL))
    y = np.arange(len(contributions))
    change_ax.barh(y, contributions["change_mg"], color=colors, height=0.68, edgecolor="white", linewidth=0.5)
    change_ax.axvline(0, color=INK, linewidth=0.9)
    change_ax.set_yticks(y, [short(value) for value in contributions["location"]], fontsize=10.5, fontweight="bold")
    change_ax.set_xlabel("Contribution to reported FY2022–FY2025 change (MG)", fontsize=15, fontweight="bold", labelpad=12)
    change_ax.tick_params(axis="x", labelsize=12)
    bold_ticks(change_ax, axis="x")
    clean(change_ax, axis="x")
    change_ax.text(0.02, 0.985, f"Continuing locations: {continuing_share:.0%} of net reported growth", transform=change_ax.transAxes, ha="left", va="top", fontsize=10.5, fontweight="bold", color=MUTED)
    legend_handles = [Patch(facecolor=BLUE, label="Continuing location")]
    if contributions.loc[contributions["status"].eq("Continuing location"), "change_mg"].lt(0).any():
        legend_handles.append(Patch(facecolor=CORAL, label="Continuing: decrease"))
    legend_handles.append(Patch(facecolor=GOLD, label="First reported after FY2022"))
    legend_b = change_ax.legend(handles=legend_handles, loc="lower right", fontsize=10.5)
    for text in legend_b.get_texts():
        text.set_fontweight("bold")

    fig.subplots_adjust(left=0.055, right=0.985, top=0.95, bottom=0.24, wspace=0.28)
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
