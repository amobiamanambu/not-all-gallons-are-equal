#!/usr/bin/env python3
"""Figure 3. U.S. reported volume and screened hydrological exposure.

Panel a: locations ranked by FY2025 withdrawal, colored by Aqueduct risk class (ranked lollipop).
Panel b: withdrawal- and consumption-weighted exposure curves for FY2022 and FY2025.
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
from matplotlib.lines import Line2D


HERE = Path(__file__).resolve().parent
DATA = HERE / "figure_03_google_panel.csv"
OUTPUT = HERE / "output"
STEM = "Figure_3_US_Portfolio_Exposure"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"
BLUE = "#1F6E8C"
TEAL = "#2A9D8F"
GOLD = "#D5A13E"
CORAL = "#D65A4A"
RISK_COLORS = {"Low": BLUE, "Low-medium": TEAL, "Medium-high": GOLD, "High": CORAL, "Extremely high": "#8E3B46"}
RISK_ORDER = ["Low", "Low-medium", "Medium-high", "High", "Extremely high"]


def spearman_statistic(left: object, right: object) -> float:
    left_ranks = pd.Series(np.asarray(left)).rank(method="average").to_numpy(float)
    right_ranks = pd.Series(np.asarray(right)).rank(method="average").to_numpy(float)
    return float(np.corrcoef(left_ranks, right_ranks)[0, 1])


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
            "legend.frameon": False,
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-3",
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


def bootstrap_ci(data: pd.DataFrame, iterations: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(20260905)
    values = data[["withdrawal_mg", "bws_score"]].to_numpy(float)
    estimates = []
    for _ in range(iterations):
        sample = values[rng.integers(0, len(values), len(values))]
        result = spearman_statistic(sample[:, 0], sample[:, 1])
        if np.isfinite(result):
            estimates.append(result)
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def exposure_curve(data: pd.DataFrame, year: int, metric: str, thresholds: np.ndarray) -> np.ndarray:
    subset = data.loc[data["year"].eq(year), [metric, "bws_score"]].dropna()
    total = subset[metric].sum()
    return np.array([subset.loc[subset["bws_score"].ge(value), metric].sum() / total for value in thresholds])


def main() -> None:
    configure()
    data = pd.read_csv(DATA)
    if len(data) != 83 or data["location"].nunique() != 26 or set(data["year"]) != {2022, 2023, 2024, 2025}:
        raise ValueError("Figure 3 requires the verified 83-row, 26-location U.S. Google panel")
    latest = data.loc[data["year"].eq(2025)].copy()
    rho = spearman_statistic(latest["withdrawal_mg"], latest["bws_score"])
    ci_low, ci_high = bootstrap_ci(latest)

    fig = plt.figure(figsize=(19, 11.5))
    grid = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.02], wspace=0.18)
    rank_ax = fig.add_subplot(grid[0, 0])
    curve_ax = fig.add_subplot(grid[0, 1])
    panel_label(rank_ax, "a")
    panel_label(curve_ax, "b")

    # Panel a: ranked lollipop, colored by Aqueduct risk class
    ranked = latest.sort_values("withdrawal_mg", ascending=True)
    y = np.arange(len(ranked))
    colors = [RISK_COLORS[c] for c in ranked["risk_class"]]
    rank_ax.hlines(y, 0, ranked["withdrawal_mg"], color=colors, linewidth=1.8, alpha=0.85, zorder=2)
    rank_ax.scatter(ranked["withdrawal_mg"], y, s=75, color=colors, edgecolor="white", linewidth=0.9, zorder=3)
    rank_ax.set_yticks(y, [loc for loc in ranked["location"]], fontsize=13, fontweight="bold")
    rank_ax.set_xscale("log")
    rank_ax.set_ylim(-0.8, len(ranked) - 1 + 1.7)
    rank_ax.set_xlabel("FY2025 reported withdrawal (MG, log scale)", fontsize=20, fontweight="bold", labelpad=16)
    rank_ax.tick_params(axis="x", labelsize=15)
    bold_ticks(rank_ax, axis="x")
    clean(rank_ax, axis="x")
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=RISK_COLORS[c], markersize=9, label=c) for c in RISK_ORDER]
    legend_a = rank_ax.legend(handles=handles, title="Aqueduct risk class", loc="lower right", fontsize=12.8, title_fontsize=13.5)
    legend_a.get_title().set_fontweight("bold")
    for text in legend_a.get_texts():
        text.set_fontweight("bold")
    rank_ax.text(0.98, 0.985, f"Spearman ρ = {rho:.2f}  (n = 26)\n95% bootstrap CI  {ci_low:.2f} to {ci_high:.2f}",
                 transform=rank_ax.transAxes, fontsize=12.8, fontweight="bold", color=MUTED, ha="right", va="top")

    # Panel b: exposure curves
    thresholds = np.linspace(0, 5, 101)
    styles = {
        (2022, "withdrawal_mg"): (BLUE, "-", 2.0, "FY2022 withdrawal"),
        (2022, "consumption_mg"): (BLUE, "--", 1.7, "FY2022 consumption"),
        (2025, "withdrawal_mg"): (CORAL, "-", 2.5, "FY2025 withdrawal"),
        (2025, "consumption_mg"): (CORAL, "--", 2.0, "FY2025 consumption"),
    }
    for key, (color, linestyle, width, label) in styles.items():
        curve_ax.step(thresholds, 100 * exposure_curve(data, *key, thresholds), where="post", color=color, linestyle=linestyle, linewidth=width, label=label)
    curve_ax.axvspan(3, 5, color=CORAL, alpha=0.045, linewidth=0)
    curve_ax.axvline(3, color=MUTED, linewidth=0.9, linestyle=(0, (3, 3)))
    curve_ax.set_xlim(0, 5)
    curve_ax.set_ylim(0, 102)
    curve_ax.set_xticks(range(6))
    curve_ax.tick_params(axis="both", labelsize=15)
    bold_ticks(curve_ax)
    curve_ax.set_xlabel("Aqueduct stress threshold", fontsize=20, fontweight="bold", labelpad=16)
    curve_ax.set_ylabel("Reported U.S. volume at or above threshold (%)", fontsize=22, fontweight="bold", labelpad=16)
    clean(curve_ax)
    legend_b = curve_ax.legend(loc="upper right", fontsize=13, ncol=2, columnspacing=1.1, handlelength=2.5)
    for text in legend_b.get_texts():
        text.set_fontweight("bold")
    high22 = 100 * exposure_curve(data, 2022, "withdrawal_mg", np.array([3.0]))[0]
    high25 = 100 * exposure_curve(data, 2025, "withdrawal_mg", np.array([3.0]))[0]
    curve_ax.scatter([3, 3], [high22, high25], s=[38, 46], color=[BLUE, CORAL], edgecolor="white", linewidth=0.8, zorder=5)
    curve_ax.text(0.97, 0.045, f"Withdrawal at stress ≥ 3\nFY2022  {high22:.2f}%    FY2025  {high25:.2f}%", transform=curve_ax.transAxes, fontsize=12.8, fontweight="bold", color=MUTED, ha="right", va="bottom")

    fig.subplots_adjust(left=0.24, right=0.985, top=0.95, bottom=0.09, wspace=0.18)
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
