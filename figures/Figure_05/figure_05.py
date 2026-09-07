#!/usr/bin/env python3
"""Figure 5. Withdrawal, consumption and disclosed water source."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "earth-futures-mpl"))

import matplotlib as mpl


def _use_interactive_backend() -> None:
    """Pick a GUI backend so plt.show() actually pops a window.

    Matplotlib silently falls back to the headless "Agg" backend in many
    setups (no display server, a non-framework Python build on macOS, etc.),
    and plt.show() is a documented no-op under Agg -- it does not raise, it
    just does nothing. Try a few common interactive backends in order and
    keep whichever one can actually open a figure window; if none work
    (e.g. running somewhere with no display at all) fall back to the
    default so the script still runs and still saves its files.
    """
    for candidate in ("MacOSX", "TkAgg", "QtAgg", "Qt5Agg"):
        try:
            mpl.use(candidate, force=True)
            import matplotlib.pyplot as _plt
            _test_figure = _plt.figure()
            _plt.close(_test_figure)
            return
        except Exception:
            # Reset to the always-available headless backend before trying the
            # next candidate, so a failed switch never leaves rcParams pointed
            # at a backend that will crash the real plt.figure() call below.
            mpl.use("Agg", force=True)
            continue


_use_interactive_backend()

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter


HERE = Path(__file__).resolve().parent
BALANCE = HERE / "figure_05_google_balance.csv"
SOURCE = HERE / "figure_05_source_boundary.csv"
OUTPUT = HERE / "output"
STEM = "Figure_5_Withdrawal_Consumption_and_Source"

INK = "#182B3A"
MUTED = "#6B7176"
GRID = "#DEE1E3"
SPINE_MUTED = "#AEB4B8"
CONSUMPTION = "#2B2F33"
DISCHARGE = "#C3C8CC"
SOURCE_COLORS = {
    "Explicitly potable": "#2B2F33",
    "Potable under reporting rule": "#8A9096",
    "Explicitly reclaimed": "#C9CDD0",
}
SOURCE_TEXT_COLORS = {
    "Explicitly potable": "white",
    "Potable under reporting rule": "white",
    "Explicitly reclaimed": INK,
}


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
            "legend.frameon": False,
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-5",
            "savefig.bbox": "tight", "savefig.pad_inches": 0.10,
        }
    )


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.075, 1.02, f"({label})", transform=ax.transAxes, fontsize=17, fontweight="bold", color=INK, ha="left", va="bottom")


def bold_ticks(ax: plt.Axes, axis: str = "both") -> None:
    if axis in ("x", "both"):
        for label in ax.get_xticklabels():
            label.set_fontweight("bold")
    if axis in ("y", "both"):
        for label in ax.get_yticklabels():
            label.set_fontweight("bold")


def short(value: str) -> str:
    return value.replace("Council Bluffs, IA", "Council Bluffs").replace("Douglas County, GA", "Douglas County").replace("Berkeley County, SC", "Berkeley County").replace("Montgomery County, TN", "Montgomery County")


def main() -> None:
    configure()
    balance = pd.read_csv(BALANCE)
    source = pd.read_csv(SOURCE)
    if len(balance) != 26 or balance["location"].nunique() != 26:
        raise ValueError("Figure 5 requires all 26 FY2025 U.S. Google locations")
    if not np.allclose(balance["withdrawal_mg"] - balance["discharge_mg"], balance["consumption_mg"], atol=1e-9):
        raise ValueError("Figure 5 water balances do not close")
    if not np.allclose(source.groupby(["scope", "year"])["share"].sum().to_numpy(), 1.0, atol=1e-9):
        raise ValueError("Figure 5 source shares do not sum to one")

    fig = plt.figure(figsize=(15.2, 9.4))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.18, 0.82], wspace=0.22)
    balance_ax = fig.add_subplot(grid[0, 0])
    source_ax = fig.add_subplot(grid[0, 1])
    panel_label(balance_ax, "a")
    panel_label(source_ax, "b")

    # Panel a: diverging bars -- Consumption (left of zero) vs. Discharge (right of zero).
    # Both are reported in the same units as total withdrawal (MG).
    plotted = balance.sort_values("withdrawal_mg", ascending=True).reset_index(drop=True)
    y = np.arange(len(plotted))
    balance_ax.barh(y, -plotted["consumption_mg"], height=0.62, color=CONSUMPTION, edgecolor="none", label="Consumption", zorder=3)
    balance_ax.barh(y, plotted["discharge_mg"], height=0.62, color=DISCHARGE, edgecolor="none", label="Discharge", zorder=3)
    balance_ax.axvline(0, color=INK, linewidth=1.0, zorder=4)
    balance_ax.set_yticks(y, [short(value) for value in plotted["location"]], fontsize=10.5, fontweight="bold")
    balance_ax.tick_params(axis="y", length=0)

    max_span = max(plotted["consumption_mg"].max(), plotted["discharge_mg"].max()) * 1.18
    balance_ax.set_xlim(-max_span, max_span)
    balance_ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{abs(value):,.0f}"))
    balance_ax.set_xlabel("FY2025 reported water balance (MG)", fontsize=20, fontweight="bold", labelpad=16)
    balance_ax.set_ylabel("U.S. Google location", fontsize=20, fontweight="bold", labelpad=16)
    balance_ax.tick_params(axis="x", labelsize=12, length=3)
    bold_ticks(balance_ax, axis="x")
    balance_ax.grid(True, axis="x", which="major", color=GRID, linewidth=0.55, alpha=0.65, linestyle=(0, (1, 2)))
    balance_ax.set_axisbelow(True)
    for spine in ("left", "bottom"):
        balance_ax.spines[spine].set_color(SPINE_MUTED)
    legend_a = balance_ax.legend(loc="lower center", fontsize=12.5, ncol=2, borderaxespad=0.4)
    for text in legend_a.get_texts():
        text.set_fontweight("bold")

    # Panel b: unchanged -- stacked share of reported withdrawal by disclosed source class.
    row_order = [
        ("Douglas County", 2022), ("Douglas County", 2023), ("Douglas County", 2025),
        ("U.S. named locations", 2022), ("U.S. named locations", 2023), ("U.S. named locations", 2025),
    ]
    positions = np.array([5.3, 4.3, 3.3, 1.7, 0.7, -0.3])
    class_order = ["Explicitly potable", "Potable under reporting rule", "Explicitly reclaimed"]
    for position, (scope, year) in zip(positions, row_order):
        rows = source.loc[source["scope"].eq(scope) & source["year"].eq(year)]
        left = 0.0
        for source_class in class_order:
            match = rows.loc[rows["source_class"].eq(source_class)]
            share = 100 * float(match["share"].iloc[0]) if len(match) else 0.0
            if share <= 0:
                continue
            source_ax.barh(position, share, left=left, height=0.58, color=SOURCE_COLORS[source_class], edgecolor="white", linewidth=0.65)
            if share >= 8:
                source_ax.text(left + share / 2, position, f"{share:.1f}%", ha="center", va="center", fontsize=9.0, color=SOURCE_TEXT_COLORS[source_class], fontweight="semibold")
            left += share
        source_ax.text(101.5, position, f"{rows['total_mg'].iloc[0]:,.0f} MG", ha="left", va="center", fontsize=8.5, color=MUTED)
    source_ax.set_yticks(positions, [f"FY{str(year)[-2:]}" for _, year in row_order], fontsize=12, fontweight="bold")
    source_ax.set_xlim(0, 118)
    source_ax.set_xticks([0, 25, 50, 75, 100])
    source_ax.tick_params(axis="x", labelsize=12)
    bold_ticks(source_ax, axis="x")
    source_ax.set_xlabel("Share of reported withdrawal (%)", fontsize=20, fontweight="bold", labelpad=16)
    source_ax.set_ylabel("Reporting scope and fiscal year", fontsize=20, fontweight="bold", labelpad=16)
    source_ax.grid(True, axis="x", color=GRID, linewidth=0.65, alpha=0.75)
    source_ax.set_axisbelow(True)
    source_ax.set_ylim(-0.85, 6.1)
    source_ax.text(4, 5.72, "Douglas County: explicit source split", fontsize=10.0, fontweight="semibold", color=INK, ha="left")
    source_ax.text(4, 2.10, "All named U.S. locations: reporting-rule boundary", fontsize=10.0, fontweight="semibold", color=INK, ha="left")
    legend_b = fig.legend(
        handles=[Patch(facecolor=SOURCE_COLORS[key], label=key) for key in class_order],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.075),
        ncol=3,
        fontsize=12.5,
        frameon=False,
        columnspacing=1.3,
        handlelength=1.8,
    )
    for text in legend_b.get_texts():
        text.set_fontweight("bold")

    fig.subplots_adjust(left=0.135, right=0.985, top=0.95, bottom=0.20, wspace=0.22)
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
