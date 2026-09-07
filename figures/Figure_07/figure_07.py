#!/usr/bin/env python3
"""Figure 7. Meta facility water and electricity evidence."""

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

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
META = HERE / "figure_07_meta_panel.csv"
OUTPUT = HERE / "output"
STEM = "Figure_7_Operator_Specific_Water_Energy"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"

# A single hue family (light to dark) shared by both panels so the figure reads
# as one coherent color story rather than two unrelated palettes.
GRADIENT = mcolors.LinearSegmentedColormap.from_list("teal_grad", ["#D9ECF2", "#8FC2D6", "#4B93B4", "#1F6E8C", "#0B4F6C"])
BIN_LABELS = ["Decrease\n(<0)", "Small increase\n(0 to 0.5)", "Moderate increase\n(0.5 to 1.0)", "Large increase\n(>1.0)"]
BIN_EDGES = [-np.inf, 0, 0.5, 1.0, np.inf]
BIN_SHADES = [0.12, 0.42, 0.68, 0.94]


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
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-7",
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


def short_meta(value: str) -> str:
    return value.replace("Stanton Springs (GA)", "Stanton Spgs. (GA)")


def consecutive_changes(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(["location", "year"]).copy()
    grouped = ordered.groupby("location", sort=False)
    ordered["previous_year"] = grouped["year"].shift(1)
    ordered["previous_electricity_mwh"] = grouped["electricity_mwh"].shift(1)
    ordered["previous_withdrawal_ml"] = grouped["withdrawal_ml"].shift(1)
    keep = (
        ordered["previous_year"].notna()
        & ordered["year"].sub(ordered["previous_year"]).eq(1)
        & ordered["previous_electricity_mwh"].gt(0)
        & ordered["previous_withdrawal_ml"].gt(0)
        & ordered["electricity_mwh"].gt(0)
        & ordered["withdrawal_ml"].gt(0)
    )
    result = ordered.loc[keep].copy()
    result["electricity_change_fraction"] = result["electricity_mwh"] / result["previous_electricity_mwh"] - 1
    result["withdrawal_change_fraction"] = result["withdrawal_ml"] / result["previous_withdrawal_ml"] - 1
    result["electricity_log2_ratio"] = np.log2(result["electricity_mwh"] / result["previous_electricity_mwh"])
    result["withdrawal_log2_ratio"] = np.log2(result["withdrawal_ml"] / result["previous_withdrawal_ml"])
    return result


def cluster_bootstrap(changes: pd.DataFrame, iterations: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(20260905)
    sites = changes["location"].unique()
    estimates = []
    grouped = {site: changes.loc[changes["location"].eq(site)] for site in sites}
    for _ in range(iterations):
        sample_sites = rng.choice(sites, size=len(sites), replace=True)
        sample = pd.concat([grouped[site] for site in sample_sites], ignore_index=True)
        estimate = spearman_statistic(sample["electricity_change_fraction"], sample["withdrawal_change_fraction"])
        if np.isfinite(estimate):
            estimates.append(float(estimate))
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def main() -> None:
    configure()
    meta = pd.read_csv(META)
    if len(meta) != 70 or meta["location"].nunique() != 15:
        raise ValueError("Figure 7 requires 70 observations from 15 U.S. Meta facilities")
    changes = consecutive_changes(meta)
    if len(changes) != 51 or changes["location"].nunique() != 13:
        raise ValueError("Figure 7 consecutive-change panel changed")
    rho = spearman_statistic(changes["electricity_change_fraction"], changes["withdrawal_change_fraction"])
    ci_low, ci_high = cluster_bootstrap(changes)

    fig = plt.figure(figsize=(9.6, 15.5))
    grid = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.85], hspace=0.52)
    bar_ax = fig.add_subplot(grid[0, 0])
    violin_ax = fig.add_subplot(grid[1, 0])
    panel_label(bar_ax, "a", x=-0.22)
    panel_label(violin_ax, "b", x=-0.22)

    # Panel a: ranked 2024 snapshot, one bar per facility, close-set with a
    # single-hue gradient (dark = highest intensity, light = lowest).
    matrix = meta.pivot(index="location", columns="year", values="withdrawal_intensity_l_per_total_kwh")
    matrix = matrix.where(matrix > 0)
    order = matrix[2024].sort_values(ascending=False).index
    vals2024 = matrix[2024].reindex(order)
    labels = [short_meta(value) for value in order]
    x = np.arange(len(labels))
    n = len(order)
    bar_colors = [GRADIENT(1 - i / (n - 1)) for i in range(n)]
    bar_ax.bar(x, vals2024, width=0.5, color=bar_colors, edgecolor="white", linewidth=0.6, zorder=3)
    bar_ax.set_yscale("log")
    bar_ax.set_ylim(0.02, 3.2)
    bar_ax.set_xlim(-0.6, n - 0.4)
    bar_ax.set_xticks(x)
    bar_ax.set_xticklabels(labels, fontsize=13, fontweight="bold", rotation=45, ha="right", rotation_mode="anchor")
    bar_ax.set_xlabel("U.S. Meta facility", fontsize=20, fontweight="bold", labelpad=16)
    bar_ax.set_ylabel("2024 withdrawal per total-facility electricity (L kWh$^{-1}$)", fontsize=16.5, fontweight="bold", labelpad=16)
    bar_ax.tick_params(axis="y", labelsize=13)
    bold_ticks(bar_ax, axis="y")
    clean(bar_ax, axis="y")

    # Panel b: within-site annual change, shown as a polished violin plot by
    # electricity-change bin, using the same color family as panel a.
    changes = changes.copy()
    changes["bin"] = pd.cut(changes["electricity_log2_ratio"], bins=BIN_EDGES, labels=BIN_LABELS)
    datasets = [changes.loc[changes["bin"].eq(label), "withdrawal_log2_ratio"].to_numpy() for label in BIN_LABELS]
    spacing = 0.62
    positions = np.arange(1, len(BIN_LABELS) + 1) * spacing

    violin_ax.axhline(0, color=GRID, linewidth=0.9, zorder=1)
    parts = violin_ax.violinplot(datasets, positions=positions, widths=0.46, showmeans=False, showmedians=False, showextrema=False)
    rng = np.random.default_rng(7)
    for i, (body, data) in enumerate(zip(parts["bodies"], datasets)):
        shade = GRADIENT(BIN_SHADES[i])
        body.set_facecolor(shade)
        body.set_edgecolor(INK)
        body.set_linewidth(1.3)
        body.set_alpha(0.88)

        q1, median, q3 = np.percentile(data, [25, 50, 75])
        whisker_low = data[data >= q1 - 1.5 * (q3 - q1)].min()
        whisker_high = data[data <= q3 + 1.5 * (q3 - q1)].max()
        pos = positions[i]
        violin_ax.plot([pos, pos], [whisker_low, whisker_high], color=INK, linewidth=1.3, zorder=4)
        violin_ax.add_patch(plt.Rectangle((pos - 0.04, q1), 0.08, q3 - q1, facecolor="white", edgecolor=INK, linewidth=1.2, zorder=5))
        violin_ax.plot([pos - 0.04, pos + 0.04], [median, median], color=INK, linewidth=2.0, zorder=6)

        jitter = rng.uniform(-0.065, 0.065, size=len(data))
        violin_ax.scatter(np.full(len(data), pos) + jitter, data, s=20, facecolor="black", edgecolor="black", linewidth=0.4, alpha=0.95, zorder=3)

    violin_ax.set_xlim(positions[0] - 0.42, positions[-1] + 0.42)
    violin_ax.set_xticks(positions, BIN_LABELS, fontsize=11.5, fontweight="bold")
    violin_ax.set_xlabel("Annual electricity change", fontsize=16.5, fontweight="bold", labelpad=16)
    violin_ax.set_ylabel("Annual withdrawal change (log$_2$ ratio)", fontsize=16.5, fontweight="bold", labelpad=16)
    violin_ax.tick_params(axis="y", labelsize=13)
    bold_ticks(violin_ax, axis="y")
    clean(violin_ax, axis="y")
    violin_ax.text(
        0.02, 0.965,
        f"Spearman ρ = {rho:.2f}  (n = {len(changes)})\nSite-cluster bootstrap CI  {ci_low:.2f} to {ci_high:.2f}",
        transform=violin_ax.transAxes, fontsize=18.0, fontweight="bold", color=INK, va="top", ha="left",
    )

    fig.subplots_adjust(left=0.185, right=0.98, top=0.965, bottom=0.11, hspace=0.52)
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
