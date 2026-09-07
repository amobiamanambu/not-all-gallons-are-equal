#!/usr/bin/env python3
"""Figure 9. Global operating-water accounting context.

Recreates panel 5b of the September 4 manuscript as a standalone figure.  The
forty named FY2025 Google locations are a descriptive external comparator for
the U.S.-focused analysis.  They are not pooled with the U.S. statistical
sample and do not validate the source-traced cooling model.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "earth-futures-mpl")
)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize


HERE = Path(__file__).resolve().parent
DATA = HERE / "figure_09_google_accounting_context.csv"
OUTPUT = HERE / "output"
STEM = "Figure_9_Accounting_and_Hydrological_Context"

INK = "#182B3A"
MUTED = "#60727F"
GRID = "#D7E0E5"
CONSUMPTION_MAP = LinearSegmentedColormap.from_list(
    "estimated_consumption_fraction",
    ["#168AAD", "#8ECAE6", "#F6C85F", "#D1495B"],
)


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica Neue", "DejaVu Sans"],
            "font.size": 10,
            "axes.labelsize": 13.2,
            "axes.labelweight": "semibold",
            "axes.titlesize": 11.8,
            "axes.titleweight": "semibold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": INK,
            "xtick.labelsize": 11.0,
            "ytick.labelsize": 11.0,
            "svg.fonttype": "none",
            "svg.hashsalt": "earth-futures-global-accounting-figure-9",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.08,
        }
    )


def load_data() -> pd.DataFrame:
    data = pd.read_csv(DATA)
    required = {
        "location_reported",
        "data_year",
        "estimated_consumption",
        "discharge",
        "withdrawal",
        "balance_error_mgd",
        "estimated_consumption_fraction",
        "highlight",
        "consumption_value_status",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Figure 9 CSV is missing columns: {sorted(missing)}")
    if len(data) != 40 or data["location_reported"].nunique() != 40:
        raise ValueError("Figure 9 requires exactly 40 named Google locations")
    if set(data["data_year"]) != {2025}:
        raise ValueError("Figure 9 must use FY2025 only")
    if (data[["withdrawal", "discharge", "estimated_consumption"]] < 0).any().any():
        raise ValueError("Water accounting values cannot be negative")
    if (data[["withdrawal", "estimated_consumption"]] == 0).any().any():
        raise ValueError("Logarithmic axes require positive withdrawal and consumption")
    balance_error = (
        data["withdrawal"] - data["discharge"] - data["estimated_consumption"]
    ).abs()
    if float(balance_error.max()) > 2e-9:
        raise ValueError("Figure 9 withdrawal-consumption-discharge balance failed")
    fraction_error = (
        data["estimated_consumption_fraction"]
        - data["estimated_consumption"] / data["withdrawal"]
    ).abs()
    if float(fraction_error.max()) > 1e-9:
        raise ValueError("Figure 9 consumptive fractions do not reproduce C/W")
    if set(data["consumption_value_status"]) != {"OPERATOR_ESTIMATE"}:
        raise ValueError("Consumption status must remain operator-estimated")
    return data


def main() -> None:
    configure()
    data = load_data()
    normalization = Normalize(vmin=0, vmax=1)

    figure, axis = plt.subplots(figsize=(8.25, 7.0))
    scatter = axis.scatter(
        data["withdrawal"],
        data["estimated_consumption"],
        c=data["estimated_consumption_fraction"],
        cmap=CONSUMPTION_MAP,
        norm=normalization,
        s=66,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.94,
        zorder=3,
    )

    limits = np.logspace(-4, 1, 200)
    axis.plot(
        limits,
        limits,
        color=INK,
        linewidth=1.15,
        linestyle=(0, (4, 3)),
        alpha=0.78,
        zorder=1,
    )
    label_offsets = {
        "Council Bluffs, IA": (14, 16, "left"),
        "Douglas County, GA": (-44, 6, "center"),
        "Mesa, AZ": (8, 12, "left"),
        "Phoenix, AZ": (8, -18, "left"),
        "St. Ghislain, Belgium": (12, -42, "left"),
        "The Dalles, OR": (-16, 23, "center"),
        "Eemshaven, Netherlands": (-55, -34, "right"),
        "Quilicura, Chile": (10, -22, "left"),
    }
    for row in data.loc[data["highlight"]].itertuples(index=False):
        axis.scatter(
            row.withdrawal,
            row.estimated_consumption,
            s=92,
            facecolor=CONSUMPTION_MAP(
                normalization(row.estimated_consumption_fraction)
            ),
            edgecolor=INK,
            linewidth=1.05,
            zorder=4,
        )
        dx, dy, alignment = label_offsets[row.location_reported]
        axis.annotate(
            row.location_reported.replace(", ", "\n"),
            xy=(row.withdrawal, row.estimated_consumption),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=7.8,
            color=INK,
            ha=alignment,
            va="center",
            arrowprops={
                "arrowstyle": "-",
                "color": "#91A2AD",
                "linewidth": 0.6,
            },
        )

    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlim(7e-5, 20)
    axis.set_ylim(7e-5, 8)
    axis.set_xlabel("Operator-reported withdrawal (MGD)")
    axis.set_ylabel("Operator-estimated consumption (MGD)")
    axis.grid(True, which="major", color=GRID, linewidth=0.65, alpha=0.78)
    axis.grid(True, which="minor", color=GRID, linewidth=0.34, alpha=0.34)
    axis.set_axisbelow(True)

    colorbar = figure.colorbar(scatter, ax=axis, fraction=0.046, pad=0.035)
    colorbar.set_label(
        "Estimated consumption / withdrawal (%)",
        fontsize=9.8,
        fontweight="semibold",
    )
    colorbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    colorbar.set_ticklabels(["0", "25", "50", "75", "100"])
    colorbar.ax.tick_params(labelsize=8.5)
    colorbar.outline.set_linewidth(0.55)
    colorbar.outline.set_edgecolor("#8FA0AA")

    figure.subplots_adjust(left=0.13, right=0.92, top=0.96, bottom=0.13)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        OUTPUT / f"{STEM}.svg",
        facecolor="white",
        metadata={"Date": None},
    )
    figure.savefig(OUTPUT / f"{STEM}.jpg", dpi=600, facecolor="white")
    if os.environ.get('EARTH_FUTURES_NO_SHOW') != '1':
        plt.show()
    plt.close(figure)


if __name__ == "__main__":
    main()
