#!/usr/bin/env python3
"""Figure 8. Managed-system scale and river-source context."""

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
from matplotlib.colors import LinearSegmentedColormap


HERE = Path(__file__).resolve().parent
MESA = HERE / "figure_08_mesa_monthly.csv"
SCALE = HERE / "figure_08_system_scale.csv"
COUNCIL = HERE / "figure_08_council_bluffs.csv"
OUTPUT = HERE / "output"
STEM = "Figure_8_Managed_Systems_and_River_Context"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"
BLUE = "#315A7D"
TEAL = "#2A9D8F"
CORAL = "#D65A4A"
GOLD = "#D5A13E"
PATHWAYS = ["GRIC exchange", "91st Ave / Palo Verde", "Aquifer recharge", "Percolation recharge", "Local reuse", "Salt River discharge", "East Maricopa Floodway", "Baseline sewer return"]
PATHWAY_COLORS = {
    "GRIC exchange": "#237A75", "91st Ave / Palo Verde": "#3FA6A0", "Aquifer recharge": "#287FA3",
    "Percolation recharge": "#70BBD0", "Local reuse": "#A8D8C8", "Salt River discharge": "#E5C35F",
    "East Maricopa Floodway": "#E78B51", "Baseline sewer return": "#8A98A2",
}
SCALE_COLORS = {
    "Municipal total pathways": "#315A7D", "Municipal beneficial reuse": "#2A9D8F",
    "U.S. Google locations: withdrawal": "#1F6E8C", "U.S. Google locations: consumption": "#D65A4A",
}
# Same heatmap colormap used in Figure 6 panel a, for a consistent visual
# language across the paper's two heatmap panels.
HEATMAP_CMAP = LinearSegmentedColormap.from_list("pressure", ["#123B5D", "#168AAD", "#8ECAE6", "#F6C85F", "#D65A4A", "#7F1D1D"])


def fmt_flow(value: float) -> str:
    if value == 0:
        return "0"
    if value < 0.01:
        return f"{value:.4f}"
    if value < 1:
        return f"{value:.3f}"
    return f"{value:.1f}"


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
            "legend.frameon": False,
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-8",
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


def clean(ax: plt.Axes, axis: str = "both") -> None:
    ax.grid(True, axis=axis, which="major", color=GRID, linewidth=0.65, alpha=0.75)
    if axis in ("x", "both") and ax.get_xscale() == "log":
        ax.grid(True, axis="x", which="minor", color=GRID, linewidth=0.3, alpha=0.3)
    if axis in ("y", "both") and ax.get_yscale() == "log":
        ax.grid(True, axis="y", which="minor", color=GRID, linewidth=0.3, alpha=0.3)
    ax.set_axisbelow(True)


def main() -> None:
    configure()
    mesa = pd.read_csv(MESA, parse_dates=["month"])
    scale = pd.read_csv(SCALE)
    council = pd.read_csv(COUNCIL)
    usable_months = mesa.loc[(mesa["valid_days"] >= 20) & (mesa["month"] >= pd.Timestamp("2021-01-01")), "month"].unique()
    if len(usable_months) != 66:
        raise ValueError("Figure 8 Mesa series requires 66 complete-QA months")
    if set(PATHWAYS) - set(mesa["pathway"]):
        raise ValueError("Figure 8 is missing a Mesa pathway")
    if len(council) != 10958 or not council["discharge_ML_day"].is_monotonic_decreasing:
        raise ValueError("Figure 8 Council Bluffs duration data changed")

    fig = plt.figure(figsize=(18.0, 6.3))
    # Explicit axes rectangles (not a GridSpec) so panel b can be nudged
    # independently while panel c stays pixel-for-pixel fixed. Equal GridSpec
    # wspace gives equal *axes-fraction* gaps, but panel b's long category
    # tick labels visually eat into the a-b gap more than panel c's labels
    # eat into the b-c gap, so the true whitespace reads as unequal.
    PANEL_BOTTOM, PANEL_HEIGHT = 0.285, 0.595
    A_RIGHT = 0.07 + 0.26755181347150253  # preserve original panel-a right edge
    A_HEATMAP_LEFT = 0.185  # more left margin than before: room for pathway-name row labels
    A_HEATMAP_WIDTH = A_RIGHT - A_HEATMAP_LEFT  # panel a's actual plot width -- b and c now match it
    B_WIDTH = A_HEATMAP_WIDTH
    C_WIDTH = A_HEATMAP_WIDTH
    # Tight, equal gap between all three panels -- closes up the whitespace
    # that was left over from the panels' old (wider) proportions. Wide
    # enough that panel b's left-extending two-line row labels still clear
    # panel a's colorbar.
    PANEL_GAP = 0.093
    C_LEFT = A_RIGHT + PANEL_GAP + B_WIDTH + PANEL_GAP  # fixed -- panel c stays put
    B_SHIFT = 0.02  # nudge panel b right of its gap-based position; c does not follow, so the b-c gap narrows
    B_LEFT = A_RIGHT + PANEL_GAP + B_SHIFT

    mesa_ax = fig.add_axes([A_HEATMAP_LEFT, PANEL_BOTTOM, A_RIGHT - A_HEATMAP_LEFT, PANEL_HEIGHT])
    scale_ax = fig.add_axes([B_LEFT, PANEL_BOTTOM, B_WIDTH, PANEL_HEIGHT])
    council_ax = fig.add_axes([C_LEFT, PANEL_BOTTOM, C_WIDTH, PANEL_HEIGHT])
    for ax, label in zip([mesa_ax, scale_ax, council_ax], "abc"):
        panel_label(ax, label)

    # Panel a: per-pathway-normalized heatmap (each row scaled to its own
    # min-max) instead of a stacked area. A shared color scale would flatten
    # small pathways like Local reuse (max 0.005 MGD) against GRIC exchange
    # (max ~19.5 MGD); per-row scaling keeps every pathway's own temporal
    # pattern visible, with its true MGD range printed under its name.
    usable = mesa.loc[mesa["month"].isin(usable_months)]
    pivot = usable.pivot(index="month", columns="pathway", values="flow_mgd").fillna(0.0)
    order = [pathway for pathway in PATHWAYS if pathway in pivot.columns]
    raw = pivot[order].to_numpy().T
    row_min = raw.min(axis=1, keepdims=True)
    row_max = raw.max(axis=1, keepdims=True)
    normalized = (raw - row_min) / np.where((row_max - row_min) == 0, 1, row_max - row_min)

    heatmap_image = mesa_ax.imshow(normalized, aspect="auto", cmap=HEATMAP_CMAP, interpolation="nearest", vmin=0, vmax=1)

    mesa_ax.set_yticks(range(len(order)))
    mesa_ax.set_yticklabels([])
    mesa_ax.tick_params(axis="y", length=0)
    label_transform = mesa_ax.get_yaxis_transform()
    for i, pathway in enumerate(order):
        mesa_ax.text(-0.05, i - 0.17, pathway, transform=label_transform, fontsize=10.5, fontweight="bold", color=INK, ha="right", va="center")
        mesa_ax.text(-0.05, i + 0.24, f"{fmt_flow(row_min[i, 0])}–{fmt_flow(row_max[i, 0])} MGD", transform=label_transform, fontsize=8.3, fontweight="normal", color=MUTED, ha="right", va="center")

    # Major ticks label only the years (readable at this panel width); small
    # unlabeled minor ticks at every month signal the underlying monthly
    # resolution without adding more text to a narrow panel.
    month_index = pivot.index
    year_tick_positions = [i for i, d in enumerate(month_index) if d.month == 1]
    year_tick_labels = [f"'{month_index[i].year % 100:02d}" for i in year_tick_positions]
    mesa_ax.set_xticks(year_tick_positions, year_tick_labels, fontsize=11, fontweight="bold")
    mesa_ax.set_xticks(range(len(month_index)), minor=True)
    mesa_ax.tick_params(axis="x", which="minor", length=2.5, color=MUTED)
    mesa_ax.tick_params(axis="x", which="major", length=4.5)
    mesa_ax.set_xlabel("Year", fontsize=14, fontweight="bold", labelpad=10)

    heatmap_cbar = fig.colorbar(heatmap_image, ax=mesa_ax, fraction=0.07, pad=0.03)
    heatmap_cbar.set_ticks([0, 1])
    heatmap_cbar.set_ticklabels(["low", "high"])
    heatmap_cbar.ax.tick_params(labelsize=8.3)
    for cbar_label in heatmap_cbar.ax.get_yticklabels():
        cbar_label.set_fontweight("bold")
    heatmap_cbar.set_label("Relative intensity", fontsize=9.5, fontweight="bold", labelpad=-2)

    distribution_order = ["Municipal total pathways", "Municipal beneficial reuse", "U.S. Google locations: withdrawal", "U.S. Google locations: consumption"]
    focal_order = ["Google Mesa: withdrawal", "Google Mesa: consumption", "Meta Mesa: withdrawal"]
    labels = distribution_order + focal_order
    positions = dict(zip(labels, np.arange(len(labels))[::-1]))
    rng = np.random.default_rng(20260905)
    for category in distribution_order:
        values = scale.loc[scale["category"].eq(category), "value_mgd"].dropna().to_numpy()
        position = positions[category]
        color = SCALE_COLORS[category]
        jitter = rng.normal(0, 0.055, len(values))
        scale_ax.scatter(values, position + jitter, s=7, color=color, alpha=0.055 if len(values) > 100 else 0.30, linewidth=0)
        q10, q25, median, q75, q90 = np.quantile(values, [0.10, 0.25, 0.50, 0.75, 0.90])
        scale_ax.plot([q10, q90], [position, position], color=color, linewidth=1.8, solid_capstyle="round")
        scale_ax.plot([q25, q75], [position, position], color=color, linewidth=6.5, solid_capstyle="round")
        scale_ax.scatter(median, position, s=34, color=INK, edgecolor="white", linewidth=0.65, zorder=5)
    focal_styles = {"Google Mesa: withdrawal": (BLUE, "o"), "Google Mesa: consumption": (CORAL, "s"), "Meta Mesa: withdrawal": ("#76528B", "D")}
    for category in focal_order:
        value = float(scale.loc[scale["category"].eq(category), "value_mgd"].iloc[0])
        color, marker = focal_styles[category]
        position = positions[category]
        scale_ax.scatter(value, position, s=72, color=color, marker=marker, edgecolor="white", linewidth=1.0, zorder=5)
        scale_ax.text(value * 1.30, position, f"{value:.3f}", va="center", fontsize=10, fontweight="bold", color=INK)
    scale_ax.set_xscale("log")
    scale_ax.set_xlim(0.015, 90)
    scale_ax.set_ylim(-0.6, 6.6)
    # Two-line y labels (source, then variable smaller/muted underneath) --
    # same folded-label idea as panel a's pathway names. A single-line label
    # like "Google U.S. withdrawal" needed too much horizontal room once
    # this panel matched panel a's narrower width; splitting it halves that.
    source_label = {
        "Municipal total pathways": "Municipal", "Municipal beneficial reuse": "Beneficial",
        "U.S. Google locations: withdrawal": "Google U.S.", "U.S. Google locations: consumption": "Google U.S.",
        "Google Mesa: withdrawal": "Google Mesa", "Google Mesa: consumption": "Google Mesa",
        "Meta Mesa: withdrawal": "Meta Mesa",
    }
    variable_label = {
        "Municipal total pathways": "pathways", "Municipal beneficial reuse": "pathways",
        "U.S. Google locations: withdrawal": "withdrawal", "U.S. Google locations: consumption": "consumption",
        "Google Mesa: withdrawal": "withdrawal", "Google Mesa: consumption": "consumption",
        "Meta Mesa: withdrawal": "withdrawal",
    }
    scale_ax.set_yticks([positions[label] for label in labels])
    scale_ax.set_yticklabels([])
    scale_ax.tick_params(axis="y", length=0)
    scale_label_transform = scale_ax.get_yaxis_transform()
    for category in labels:
        position = positions[category]
        scale_ax.text(-0.03, position - 0.16, source_label[category], transform=scale_label_transform, fontsize=10.5, fontweight="bold", color=INK, ha="right", va="center")
        scale_ax.text(-0.03, position + 0.20, variable_label[category], transform=scale_label_transform, fontsize=8.6, fontweight="normal", color=MUTED, ha="right", va="center")
    scale_ax.set_xlabel("Daily-equivalent water flow (MGD, log scale)", fontsize=11.5, fontweight="bold", labelpad=10)
    scale_ax.tick_params(axis="x", labelsize=11)
    bold_ticks(scale_ax, axis="x")
    clean(scale_ax, axis="x")

    x = council["flow_exceedance_percent"].to_numpy()
    withdrawal = council["withdrawal_to_river_flow_pct"].to_numpy()
    consumption = council["estimated_consumption_to_river_flow_pct"].to_numpy()
    council_ax.fill_between(x, consumption, withdrawal, color="#79B7C9", alpha=0.18, linewidth=0)
    council_ax.plot(x, withdrawal, color=BLUE, linewidth=2.2, label="Withdrawal / river flow")
    council_ax.plot(x, consumption, color=CORAL, linewidth=2.2, linestyle="--", label="Consumption / river flow")
    council_ax.set_yscale("log")
    council_ax.set_xlim(0, 100)
    council_ax.set_ylim(0.002, 0.22)
    council_ax.set_xlabel("Missouri River flow exceedance (%)", fontsize=11.5, fontweight="bold", labelpad=10)
    council_ax.set_ylabel("Operator water / observed river flow (%)", fontsize=14, fontweight="bold", labelpad=5)
    council_ax.tick_params(axis="both", labelsize=11)
    bold_ticks(council_ax)
    clean(council_ax)
    legend_c = council_ax.legend(loc="upper left", fontsize=10.5)
    for text in legend_c.get_texts():
        text.set_fontweight("bold")
    for percentile in (50, 95):
        index = np.abs(x - percentile).argmin()
        council_ax.scatter([x[index], x[index]], [withdrawal[index], consumption[index]], s=36, color=[BLUE, CORAL], edgecolor="white", linewidth=0.65, zorder=5)
        withdrawal_clearance = 1.65 if percentile == 50 else 1.12
        council_ax.text(x[index] + (-2 if percentile == 95 else 2), withdrawal[index] * withdrawal_clearance, f"p{percentile}  {withdrawal[index]:.3f}%", ha="right" if percentile == 95 else "left", fontsize=9.5, fontweight="bold", color=BLUE)
        consumption_offset = 3 if percentile == 95 else 2
        council_ax.text(x[index] + consumption_offset, consumption[index] / 1.12, f"{consumption[index]:.3f}%", ha="left", va="top", fontsize=9.5, fontweight="bold", color=CORAL)

    # Axes were placed with explicit rectangles above, so no subplots_adjust
    # is needed (and it would be a no-op on fig.add_axes-created axes anyway).

    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
