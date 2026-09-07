#!/usr/bin/env python3
"""Run the complete analysis workflow and, optionally, reproduce Figures 3-9."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    "01_prepare_analysis_data.py",
    "02_run_statistical_analysis.py",
    "03_build_tables_and_metadata.py",
    "04_verify_reproduction.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", action="store_true", help="also regenerate manuscript Figures 3-9 as SVG and 600-dpi JPG files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    for script in SCRIPTS:
        print(f"\n--- {script} ---")
        subprocess.run([sys.executable, str(ROOT / "analysis" / script)], check=True)
    if args.figures:
        environment = os.environ.copy()
        environment["EARTH_FUTURES_NO_SHOW"] = "1"
        environment.setdefault("MPLBACKEND", "Agg")
        for number in range(3, 10):
            directory = ROOT / "figures" / f"Figure_{number:02d}"
            script = directory / f"figure_{number:02d}.py"
            print(f"\n--- {script.relative_to(ROOT)} ---")
            subprocess.run([sys.executable, str(script)], cwd=directory, env=environment, check=True)
        print("\n[PASS] Figures 3-9 regenerated as SVG and 600-dpi JPG files")
    print("\n[PASS] analysis, source-linked tables, metadata, and three-level QA/QC completed")


if __name__ == "__main__":
    main()
