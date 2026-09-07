#!/usr/bin/env python3
"""Figure 6. Source-trace-to-timing hydrological test."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "earth-futures-mpl"))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D


HERE = Path(__file__).resolve().parent
DAILY = HERE / "figure_06_daily_pressure.csv"
VOLUME = HERE / "figure_06_volume_pressure.csv"
OUTPUT = HERE / "output"
STEM = "Figure_6_Source_Trace_to_Timing"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"
SITES = ["Atlanta_GA", "Seattle_WA", "Council_Bluffs_IA"]
SITE_LABELS = {"Atlanta_GA": "Atlanta", "Seattle_WA": "Seattle", "Council_Bluffs_IA": "Council Bluffs"}
SITE_COLORS = {"Atlanta_GA": "#D65A4A", "Seattle_WA": "#168AAD", "Council_Bluffs_IA": "#315A7D"}
ARCHITECTURES = {
    "climate_responsive_hybrid": ("Climate-responsive hybrid", "-", "o"),
    "water_cooled_evaporative": ("Water-cooled evaporative", "--", "s"),
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PLOT_FLOOR = 3e-5

# Restyled typography (matches the finalized Manuscript/ALWRC b+d figure),
# now applied uniformly across all four panels.
RESTYLE_LABEL_SIZE = 12.7
RESTYLE_TICK_SIZE = 10.5
RESTYLE_PANEL_LABEL_SIZE = 19


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 9.5, "axes.labelsize": 10.7, "axes.labelweight": "semibold",
            "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
            "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.frameon": False,
            "svg.fonttype": "none", "svg.hashsalt": "earth-futures-final-figure-6",
            "savefig.bbox": "tight", "savefig.pad_inches": 0.10,
        }
    )


def panel_label(ax: plt.Axes, label: str, fontsize: float = 12.5, y: float = 1.025) -> None:
    ax.text(-0.075, y, f"({label})", transform=ax.transAxes, fontsize=fontsize, fontweight="bold", color=INK, ha="left", va="bottom")


def bold_ticks(ax: plt.Axes, axis: str = "both") -> None:
    if axis in ("x", "both"):
        for label in ax.get_xticklabels():
            label.set_fontweight("bold")
    if axis in ("y", "both"):
        for label in ax.get_yticklabels():
            label.set_fontweight("bold")


def grid_axis(ax: plt.Axes, axis: str = "both") -> None:
    ax.grid(True, axis=axis, which="major", color=GRID, linewidth=0.6, alpha=0.75)
    if ax.get_yscale() == "log":
        ax.grid(True, axis="y", which="minor", color=GRID, linewidth=0.3, alpha=0.32)
    ax.set_axisbelow(True)


def largest_near_equal_contrast(monthly: pd.DataFrame) -> dict:
    records = monthly.loc[(monthly["mean_consumption_ml_day"] > 0) & (monthly["pressure_p95_pct"] > 0)].reset_index(drop=True)
    candidates = []
    for left_index, left in records.iterrows():
        for right_index in range(left_index + 1, len(records)):
            right = records.iloc[right_index]
            if left["location"] == right["location"]:
                continue
            difference = abs(left["mean_consumption_ml_day"] - right["mean_consumption_ml_day"]) / max(left["mean_consumption_ml_day"], right["mean_consumption_ml_day"])
            if difference > 0.03:
                continue
            ratio = max(left["pressure_p95_pct"], right["pressure_p95_pct"]) / min(left["pressure_p95_pct"], right["pressure_p95_pct"])
            candidates.append({"ratio": ratio, "difference": difference, "left": left, "right": right})
    if not candidates:
        raise ValueError("No near-equal-volume contrast found")
    return max(candidates, key=lambda item: item["ratio"])


def main() -> None:
    configure()
    daily = pd.read_csv(DAILY, parse_dates=["date"])
    volume = pd.read_csv(VOLUME)
    if len(daily) != 65748 or len(volume) != 72:
        raise ValueError("Figure 6 frozen input dimensions changed")
    if set(daily["location"]) != set(SITES) or set(daily["architecture_id"]) != set(ARCHITECTURES):
        raise ValueError("Figure 6 site or architecture set changed")
    monthly = daily.groupby(["location", "architecture_id", "month"], as_index=False).agg(pressure_p95_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.95)))
    annual = daily.groupby(["location", "architecture_id", "water_year"], as_index=False).agg(pressure_p95_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.95)))
    if len(monthly) != 72 or len(annual) != 180:
        raise ValueError("Figure 6 temporal aggregation changed")
    contrast = largest_near_equal_contrast(volume)
    if not (87.58 < contrast["ratio"] < 87.60):
        raise ValueError("Figure 6 near-equal-volume contrast changed")

    hybrid = daily.loc[daily["architecture_id"].eq("climate_responsive_hybrid")]
    matrices, labels, row_start = [], [], 0
    for location in SITES:
        matrix = hybrid.loc[hybrid["location"].eq(location)].pivot_table(index="water_year", columns="water_year_day", values="source_relative_pressure_pct", aggfunc="mean").reindex(columns=np.arange(1, 367))
        matrices.append(matrix.to_numpy())
        labels.append((location, row_start, row_start + len(matrix)))
        row_start += len(matrix)
    heat = np.vstack(matrices)
    positive = heat[np.isfinite(heat) & (heat > 0)]
    vmin, vmax = np.quantile(positive, [0.01, 0.99])
    heat_display = heat.copy()
    heat_display[heat_display == 0] = vmin * 0.5
    cmap = LinearSegmentedColormap.from_list("pressure", ["#123B5D", "#168AAD", "#8ECAE6", "#F6C85F", "#D65A4A", "#7F1D1D"])
    cmap.set_bad("#F0F3F4")
    cmap.set_under("#071E2E")

    fig = plt.figure(figsize=(15.2, 11.1))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.04, 0.96], height_ratios=[1.0, 1.0], wspace=0.24, hspace=0.24)
    heat_ax = fig.add_subplot(grid[0, 0])
    month_ax = fig.add_subplot(grid[0, 1])
    year_ax = fig.add_subplot(grid[1, 0])
    volume_ax = fig.add_subplot(grid[1, 1])
    # All four panels get the same restyled (larger) panel-label treatment.
    panel_label(heat_ax, "a", fontsize=RESTYLE_PANEL_LABEL_SIZE, y=1.02)
    panel_label(year_ax, "c", fontsize=RESTYLE_PANEL_LABEL_SIZE, y=1.02)
    panel_label(month_ax, "b", fontsize=RESTYLE_PANEL_LABEL_SIZE, y=1.02)
    panel_label(volume_ax, "d", fontsize=RESTYLE_PANEL_LABEL_SIZE, y=1.02)

    image = heat_ax.imshow(np.ma.masked_invalid(heat_display), aspect="auto", interpolation="nearest", cmap=cmap, norm=LogNorm(vmin=vmin, vmax=vmax), origin="upper")
    for _, _, end in labels[:-1]:
        heat_ax.axhline(end - 0.5, color="white", linewidth=2.0)
    heat_ax.set_yticks([(start + end - 1) / 2 for _, start, end in labels], [SITE_LABELS[location] for location, start, end in labels], fontsize=RESTYLE_TICK_SIZE, fontweight="bold")
    heat_ax.set_xticks([0, 92, 182, 273, 365], ["Oct", "Jan", "Apr", "Jul", "Oct"])
    heat_ax.set_xlabel("Day of water year", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    heat_ax.tick_params(axis="x", labelsize=RESTYLE_TICK_SIZE)
    bold_ticks(heat_ax, axis="x")
    colorbar = fig.colorbar(image, ax=heat_ax, fraction=0.035, pad=0.025)
    colorbar.set_label("Consumption / source flow (%)", fontsize=10.5, fontweight="bold")
    colorbar.ax.tick_params(labelsize=9.0)
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")

    # Panel b: seasonal interaction of demand and source flow (restyled).
    for location in SITES:
        for architecture, (_, linestyle, marker) in ARCHITECTURES.items():
            series = monthly.loc[monthly["location"].eq(location) & monthly["architecture_id"].eq(architecture)].sort_values("month")
            values = series["pressure_p95_pct"].to_numpy()
            month_ax.plot(series["month"], np.maximum(values, PLOT_FLOOR), color=SITE_COLORS[location], linestyle=linestyle, marker=marker, markersize=3.6, markerfacecolor="white" if architecture == "climate_responsive_hybrid" else SITE_COLORS[location], linewidth=1.75)
    month_ax.set_yscale("log")
    month_ax.set_xlim(0.7, 12.3)
    month_ax.set_ylim(2e-5, 4)
    month_ax.set_xticks(np.arange(1, 13), MONTHS)
    month_ax.set_xlabel("Calendar month", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    month_ax.set_ylabel("Monthly p95 pressure (%)", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    month_ax.tick_params(axis="both", labelsize=RESTYLE_TICK_SIZE)
    bold_ticks(month_ax)
    grid_axis(month_ax)

    for location in SITES:
        for architecture, (_, linestyle, marker) in ARCHITECTURES.items():
            series = annual.loc[annual["location"].eq(location) & annual["architecture_id"].eq(architecture)].sort_values("water_year")
            year_ax.plot(series["water_year"], series["pressure_p95_pct"], color=SITE_COLORS[location], linestyle=linestyle, marker=marker, markersize=2.8, markerfacecolor="white" if architecture == "climate_responsive_hybrid" else SITE_COLORS[location], linewidth=1.55)
    year_ax.set_yscale("log")
    year_ax.set_ylim(5e-4, 4)
    year_ax.set_xlim(1995.3, 2025.7)
    year_ax.set_xlabel("Water year", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    year_ax.set_ylabel("Water-year p95 pressure (%)", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    year_ax.tick_params(axis="both", labelsize=RESTYLE_TICK_SIZE)
    bold_ticks(year_ax)
    grid_axis(year_ax)

    # Panel d: near-equal liters, different source pressure (restyled).
    for (_, group) in volume.groupby(["location", "month"]):
        if len(group) == 2:
            volume_ax.plot(group["mean_consumption_ml_day"], np.maximum(group["pressure_p95_pct"], 1e-5), color=SITE_COLORS[group["location"].iloc[0]], linewidth=0.55, alpha=0.20, zorder=1)
    for location in SITES:
        for architecture, (_, _, marker) in ARCHITECTURES.items():
            subset = volume.loc[volume["location"].eq(location) & volume["architecture_id"].eq(architecture)]
            volume_ax.scatter(subset["mean_consumption_ml_day"], np.maximum(subset["pressure_p95_pct"], 1e-5), s=36, marker=marker, facecolor="white" if architecture == "climate_responsive_hybrid" else SITE_COLORS[location], edgecolor=SITE_COLORS[location], linewidth=1.0, zorder=3)
    endpoints = sorted([contrast["left"], contrast["right"]], key=lambda row: row["pressure_p95_pct"])
    arrow_x = 19.2
    volume_ax.annotate("", xy=(arrow_x, endpoints[1]["pressure_p95_pct"]), xytext=(arrow_x, endpoints[0]["pressure_p95_pct"]), arrowprops={"arrowstyle": "<->", "color": INK, "linewidth": 1.0})
    volume_ax.text(18.8, np.sqrt(endpoints[0]["pressure_p95_pct"] * endpoints[1]["pressure_p95_pct"]), f"{contrast['ratio']:.1f}-fold difference", ha="right", va="center", fontsize=11.0, fontweight="bold", color=INK)
    for row, offset in zip(endpoints, [(4, -24), (-5, 8)]):
        volume_ax.annotate(f"{row['location_label']}, month {int(row['month'])}\n{row['mean_consumption_ml_day']:.2f} ML/day", (row["mean_consumption_ml_day"], row["pressure_p95_pct"]), xytext=offset, textcoords="offset points", fontsize=9.3, fontweight="bold", color=INK, ha="left" if offset[0] > 0 else "right")
    volume_ax.set_yscale("log")
    volume_ax.set_xlim(-0.4, 20.3)
    volume_ax.set_ylim(7e-6, 4)
    volume_ax.set_xlabel("Modeled direct consumption (ML/day)", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    volume_ax.set_ylabel("Monthly p95 pressure (%)", fontsize=RESTYLE_LABEL_SIZE, fontweight="bold")
    volume_ax.tick_params(axis="both", labelsize=RESTYLE_TICK_SIZE)
    bold_ticks(volume_ax)
    grid_axis(volume_ax)

    site_handles = [Line2D([0], [0], color=SITE_COLORS[location], linewidth=2.5, label=SITE_LABELS[location]) for location in SITES]
    architecture_handles = [Line2D([0], [0], color=INK, linewidth=1.8, linestyle=style[1], marker=style[2], markersize=4, label=style[0]) for style in ARCHITECTURES.values()]
    legend = fig.legend(handles=site_handles + architecture_handles, loc="lower center", ncol=5, frameon=False, fontsize=11.2, bbox_to_anchor=(0.5, 0.008), handlelength=2.2, columnspacing=1.2)
    for text in legend.get_texts():
        text.set_fontweight("bold")

    fig.subplots_adjust(left=0.085, right=0.985, top=0.95, bottom=0.095)
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    fig.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
