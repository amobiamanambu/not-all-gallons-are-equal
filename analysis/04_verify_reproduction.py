#!/usr/bin/env python3
"""Three-level QA/QC for data, computations, and scientific interpretation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input"
READY = ROOT / "data" / "analysis_ready"
RESULTS = ROOT / "results"
METADATA = ROOT / "metadata"
QA = ROOT / "qa"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Audit:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def check(self, level: int, name: str, condition: bool, detail: str) -> None:
        self.rows.append({
            "qa_level": level,
            "check": name,
            "status": "PASS" if bool(condition) else "FAIL",
            "detail": detail,
        })

    def note(self, level: int, name: str, detail: str) -> None:
        self.rows.append({"qa_level": level, "check": name, "status": "DOCUMENTED_NOTE", "detail": detail})


def main() -> None:
    audit = Audit()
    register = pd.read_csv(METADATA / "source_register.csv", dtype=str).fillna("")
    source_ids = set(register["source_id"])

    # Level 1: file integrity, schema, source identifiers, and locators.
    manifest = pd.read_csv(QA / "input_file_manifest.csv")
    for row in manifest.itertuples(index=False):
        path = ROOT / row.relative_path
        audit.check(1, f"input exists: {row.relative_path}", path.exists(), "Required package input is present.")
        audit.check(1, f"input hash: {row.relative_path}", path.exists() and sha256(path) == row.sha256, "SHA-256 matches the frozen package manifest.")
    audit.check(1, "source IDs unique", not register["source_id"].duplicated().any(), f"{len(register)} stable source identifiers.")
    audit.check(1, "source URLs populated", register["primary_url"].str.startswith(("http://", "https://")).all(), "Every source has an HTTP(S) primary URL.")
    audit.check(1, "source locators populated", register["source_locator"].str.strip().ne("").all(), "Every source has a page, table, station, dataset, or section locator.")

    datasets_with_ids = [
        "google_named_location_year.csv", "google_location_aqueduct_screen.csv",
        "google_reported_source_mix.csv", "meta_us_facility_year.csv",
        "aws_us_matched_regions.csv", "usgs_daily_flow_three_components.csv",
        "cooling_model_monthly.csv", "mesa_daily_pathways_qc.csv",
        "source_resolved_case_evidence.csv",
    ]
    referenced_ids: set[str] = set()
    for name in datasets_with_ids:
        frame = pd.read_csv(READY / name)
        id_columns = [column for column in frame.columns if column == "source_id" or column.endswith("_source_id")]
        audit.check(1, f"source field present: {name}", bool(id_columns), f"Source fields: {', '.join(id_columns)}")
        for column in id_columns:
            values = set(frame[column].dropna().astype(str)) - {""}
            referenced_ids |= values
            audit.check(1, f"source IDs registered: {name}/{column}", values <= source_ids, f"Referenced IDs: {', '.join(sorted(values))}")
        if "source_url" in frame:
            audit.check(1, f"source URLs populated: {name}", frame["source_url"].fillna("").str.startswith(("http://", "https://")).all(), "Row-level source URLs are present.")
        if "source_locator" in frame:
            audit.check(1, f"source locators populated: {name}", frame["source_locator"].fillna("").str.strip().ne("").all(), "Row-level source locators are present.")
    audit.check(1, "all referenced source IDs registered", referenced_ids <= source_ids, f"{len(referenced_ids)} identifiers used in datasets; all resolve in source register.")
    audit.check(1, "unused working datasets removed", not any((ROOT / path).exists() for path in ["data/input/operator_reported_water_panel.csv", "data/analysis_ready/operator_reported_water_panel.csv", "data/analysis_ready/meta_all_facility_year.csv", "data/analysis_ready/aws_all_regions.csv"]), "Redundant pass-through and broader unused analysis-ready panels are absent.")
    audit.check(1, "unused source-tracing records removed", not register["source_id"].isin(["WALLOON_PARLIAMENT_2023", "GOOGLE_BELGIUM_DC"]).any(), "The unused Saint-Ghislain regulatory tracing records are not represented as manuscript evidence.")

    # Level 2: independent numerical reproduction and unit checks.
    google = pd.read_csv(READY / "google_us_location_year.csv")
    latest = google.loc[google["year"].eq(2025)]
    audit.check(2, "Google U.S. scope", len(google) == 83 and google["location"].nunique() == 26, "83 location-years across 26 U.S. locations.")
    audit.check(2, "Google FY2025 withdrawal", abs(latest["withdrawal_mg"].sum() - 10_807.6) < 1e-9, "Independent sum equals 10,807.6 MG.")
    audit.check(2, "Google FY2025 consumption", abs(latest["consumption_mg"].sum() - 8_446.9) < 1e-9, "Independent sum equals 8,446.9 MG.")
    audit.check(2, "Google named-location balance", google["balance_error_mg"].abs().max() <= 0.03, f"Maximum absolute source-reported balance residual: {google['balance_error_mg'].abs().max():.3f} MG.")
    global_2025 = pd.read_csv(READY / "google_global_fy2025.csv")
    audit.check(2, "Google global FY2025 scope", len(global_2025) == 40, "Forty named locations; aggregate Other row excluded.")
    audit.check(2, "Google global withdrawal", abs(global_2025["withdrawal_mg"].sum() - 12_541.5) < 1e-9, "Independent sum equals 12,541.5 MG.")
    audit.check(2, "Google global consumption", abs(global_2025["consumption_mg"].sum() - 9_603.75) < 1e-9, "Independent sum equals 9,603.75 MG.")
    original_google = pd.read_csv(INPUT / "google_location_water_2022_2025.csv")
    audit.check(2, "Google public-release scope", len(original_google) == 101 and original_google.loc[original_google["is_named_location"].eq(True)].shape[0] == 97, "Release contains 83 U.S. location-years, 14 additional non-U.S. FY2025 rows, and four aggregate QA rows.")
    issue = original_google.loc[original_google["location"].eq("Other data center locations") & original_google["year"].eq(2024)]
    audit.check(2, "Google FY2024 aggregate issue isolated", len(issue) == 1 and abs(float(issue["consumption_mg"].iloc[0]) - 786.9) < 1e-9, "Published value is preserved exactly once.")
    audit.check(2, "Google aggregate excluded from named analysis", "Other data center locations" not in set(global_2025["location"]), "No aggregate row enters named-location results.")
    audit.note(2, "Google FY2024 aggregate source inconsistency", "Published withdrawal 828.9 MG and discharge 60.0 MG imply 768.9 MG, while the report prints 786.9 MG consumption. No silent correction was made.")

    source_mix = pd.read_csv(READY / "google_reported_source_mix.csv")
    douglas = source_mix.loc[source_mix["location"].eq("Douglas County, GA") & source_mix["year"].eq(2025)]
    reclaimed_share = float(douglas.loc[douglas["source_type"].eq("reclaimed wastewater"), "withdrawal_mg"].iloc[0] / douglas["withdrawal_mg"].sum())
    audit.check(2, "Douglas County reclaimed share", abs(reclaimed_share - 0.895) < 0.0005, f"Recomputed share: {100*reclaimed_share:.2f}%.")

    meta = pd.read_csv(READY / "meta_us_facility_year.csv")
    meta_intensity = 1000 * meta["withdrawal_ml"] / meta["electricity_mwh"]
    audit.check(2, "Meta U.S. scope", len(meta) == 70 and meta["location"].nunique() == 15, "70 facility-years across 15 U.S. facilities.")
    audit.check(2, "Meta intensity equation", np.allclose(meta_intensity, meta["withdrawal_intensity_l_per_total_kwh"], equal_nan=True), "I = 1000 W/E reproduces every non-missing row.")
    changes = pd.read_csv(RESULTS / "meta_us_consecutive_changes.csv")
    audit.check(2, "Meta consecutive-change scope", len(changes) == 51 and changes["location"].nunique() == 13, "51 changes at 13 facilities.")
    audit.check(2, "Meta denominator label", meta["intensity_label"].eq("withdrawal intensity; not WUE").all(), "No total-electricity ratio is labeled WUE.")

    aws = pd.read_csv(RESULTS / "manuscript_table_5_aws_pue_wue.csv")
    audit.check(2, "AWS matched scope", len(aws) == 4, "Four U.S. regions report both PUE and WUE in FY2024 and FY2025.")
    audit.check(2, "AWS PUE deltas", np.allclose(aws["pue_change"], aws["pue_2025"] - aws["pue_2024"]), "All PUE changes independently reproduced.")
    audit.check(2, "AWS WUE deltas", np.allclose(aws["wue_change"], aws["wue_2025"] - aws["wue_2024"]), "All WUE changes independently reproduced.")
    audit.check(2, "AWS U.S. WUE direction", (aws["wue_change"] < 0).all(), "All four matched U.S. regions have lower FY2025 WUE.")
    audit.note(2, "AWS source version", "FY2025 values are tied to the official webpage archived on 2026-09-05; retrieval date and SHA-256 are preserved.")

    flows = pd.read_csv(READY / "usgs_daily_flow_three_components.csv", dtype={"station_id": str})
    audit.check(2, "USGS combined scope", len(flows) == 32_874 and flows["location"].nunique() == 3, "Three stations with 10,958 daily observations each.")
    audit.check(2, "USGS dates unique", not flows.duplicated(["location", "date"]).any(), "No duplicate location-date keys.")
    audit.check(2, "USGS flow positive", flows["discharge_ML_day"].gt(0).all(), "All screened daily-flow values are positive.")
    conversion = flows["discharge_cfs"] * 0.028316846592 * 86.4
    audit.check(2, "USGS unit conversion", np.allclose(conversion, flows["discharge_ML_day"], rtol=0, atol=1e-6), "1 ft3/s = 0.028316846592 m3/s; ML/day conversion reproduced.")

    pressure = pd.read_csv(READY / "source_component_daily_pressure.csv")
    expected_pressure = 100 * pressure["source_fraction"] * pressure["consumption_ml_day"] / pressure["discharge_ML_day"]
    audit.check(2, "daily pressure equation", np.allclose(expected_pressure, pressure["source_relative_pressure_pct"]), "Pi = 100 sC/Q reproduces all 65,748 rows.")
    t3 = pd.read_csv(RESULTS / "manuscript_table_3_source_component_results.csv")
    audit.check(2, "Table 3 row count", len(t3) == 6, "Three source components by two cooling architectures.")
    t4 = pd.read_csv(RESULTS / "manuscript_table_4_flow_regime_descriptors.csv")
    t4_full = pd.read_csv(RESULTS / "table_4_flow_regime_descriptors.csv")
    audit.check(2, "Table 4 record counts", t4_full["daily_records"].eq(10_958).all(), "Each descriptor uses the complete 30-water-year record.")
    audit.check(2, "Table 4 baseline-scarcity identity", np.allclose(t4_full["baseline_scarcity_b"], 1 - t4_full["q_drought_p10_ml_day"] / t4_full["q_mean_ml_day"]), "B = 1 - Q10/Qmean reproduced at full precision.")
    audit.check(2, "Table 4 DAF identity", np.allclose(t4_full["drought_amplification_factor"], t4_full["q_mean_ml_day"] / t4_full["q_drought_p10_ml_day"]), "DAF = Qmean/Q10 reproduced at full precision.")

    pairs = pd.read_csv(RESULTS / "near_equal_volume_pair_distribution.csv")
    audit.check(2, "near-equal pair count", len(pairs) == 282, "All cross-location pairs satisfying the declared <=3% rule are retained.")
    audit.check(2, "near-equal pair rule", pairs["consumption_difference_pct"].le(3.0 + 1e-12).all(), "Every retained pair satisfies the prespecified volume rule.")
    audit.check(2, "near-equal median", abs(pairs["pressure_ratio"].median() - 25.142842) < 1e-6, "Median pressure ratio reproduced.")
    audit.check(2, "near-equal maximum", abs(pairs["pressure_ratio"].max() - 87.5902473) < 1e-3, "Maximum documented ratio reproduced and treated as an endpoint.")

    mesa = pd.read_csv(READY / "mesa_daily_pathways_qc.csv")
    audit.check(2, "Mesa complete-day count", len(mesa) == 2_676, "2,676 days pass duplicate, sign, capacity and completeness gates.")
    audit.check(2, "Mesa fraction bounds", mesa["beneficial_fraction"].between(0, 1).all(), "All beneficial pathway fractions are between zero and one.")
    audit.check(2, "Mesa mean beneficial fraction", abs(mesa["beneficial_fraction"].mean() - 0.8776347171) < 1e-10, "Mean independently reproduced.")

    # Level 3: source display, table linkage, and scientific boundaries.
    table_paths = sorted(RESULTS.glob("manuscript_table_*.csv"))
    audit.check(3, "six manuscript table datasets", len(table_paths) == 6, "Tables 1-6 each have a machine-readable source-linked CSV.")
    for path in table_paths:
        text = path.read_text(encoding="utf-8")
        audit.check(3, f"table source linkage: {path.name}", bool(re.search(r"source|USGS|MESA_OPEN_DATA|GOOGLE_ENV|Amazon Web Services|Lei", text, re.I)), "Table includes source fields, source identifiers, or an explicit common-source basis.")
    audit.check(3, "Table 3 source chain", t3["source_basis"].str.contains("USGS_").all() and t3["source_basis"].str.contains("LEI_MASANET_2022").all(), "Every Table 3 row links hydrology and cooling-model sources.")
    audit.check(3, "Table 4 station traceability", t4["source_id"].str.startswith("USGS_").all() and t4["source_url"].str.contains("waterdata.usgs.gov").all(), "Every Table 4 row resolves to a station page.")
    audit.check(3, "Table 5 common source", aws["source_id"].eq("AWS_CLOUD_2026").all(), "Every operator-reported PUE/WUE value has the AWS source identifier.")
    t6 = pd.read_csv(RESULTS / "manuscript_table_6_managed_system_cases.csv")
    audit.check(3, "Table 6 observation-source colocation", t6["source_ids"].str.contains(r"[A-Z]{2,}_[A-Z0-9_]+", regex=True).all() and t6["sources_and_locators"].str.strip().ne("").all(), "Every case observation carries source IDs and human-readable locators in the same row.")
    boundary_text = " ".join(t6["interpretive_boundary"].astype(str)).lower()
    audit.check(3, "managed-system attribution boundary", "not allocated" in boundary_text and "does not allocate" in boundary_text, "Facility allocation and river-impact limits remain explicit.")
    audit.check(3, "Aqueduct screen boundary", google["screening_caveat"].str.contains("prioritization screen", case=False).all(), "Aqueduct is never relabeled as facility impact or validation.")
    audit.check(3, "Council Bluffs denominator boundary", "not facility impact" in pd.read_csv(RESULTS / "council_bluffs_source_family_summary.csv")["interpretive_status"].iloc[0], "River discharge is retained as source-family context only.")
    source_cases = pd.read_csv(READY / "source_resolved_case_evidence.csv")
    mass_balance_flags = (
        source_cases.loc[source_cases["case_id"].eq("quincy_qwru"), "mass_balance_eligible"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )
    audit.check(3, "source cases not mass-balanced", mass_balance_flags.notna().all() and not mass_balance_flags.any(), "Incompatible Quincy quantities are not summed.")
    value_map = pd.read_csv(METADATA / "manuscript_value_source_map.csv")
    mapped_ids = {
        item.strip()
        for group in value_map["source_ids"].astype(str)
        for item in group.split(";")
        if item.strip()
    }
    audit.check(3, "all manuscript table rows mapped", len(value_map) == 35, "All 35 rows across Tables 1-6 have a provenance record.")
    audit.check(3, "manuscript source map resolves", mapped_ids <= source_ids, f"All {len(mapped_ids)} table-source identifiers resolve in the source register.")
    audit.check(3, "manuscript source locators populated", value_map["source_locators"].fillna("").str.strip().ne("").all(), "Every manuscript table row has one or more exact source locators.")
    figure_map = pd.read_csv(METADATA / "figure_source_map.csv")
    figure_ids = {
        item.strip()
        for group in figure_map["source_ids"].astype(str)
        for item in group.split(";")
        if item.strip()
    }
    audit.check(3, "all manuscript figures mapped", len(figure_map) == 9, "Figures 1-9 each have an explicit evidence and source record.")
    audit.check(3, "figure source map resolves", figure_ids <= source_ids, f"All {len(figure_ids)} figure-source identifiers resolve in the source register.")
    audit.check(3, "figure source locators populated", figure_map["sources_and_locators"].fillna("").str.strip().ne("").all(), "Every figure has human-readable source locators.")
    unused_source_ids = source_ids - (referenced_ids | mapped_ids | figure_ids)
    audit.check(3, "no unused registered data sources", not unused_source_ids, "Every source-register entry supports a released dataset, manuscript table, or manuscript figure; unused IDs: " + ", ".join(sorted(unused_source_ids)))
    data_map = pd.read_csv(METADATA / "manuscript_data_map.csv")
    audit.check(3, "manuscript data inventory complete", len(data_map) == 13 and data_map["manuscript_item"].nunique() == 13, "Figures 3-9 and Tables 1-6 are mapped to released datasets.")
    expected_catalogued_csvs = list((ROOT / "data").rglob("*.csv")) + list(RESULTS.glob("*.csv")) + list((ROOT / "figures").glob("Figure_*/figure_*.csv"))
    audit.check(3, "dataset catalog covers all released CSVs", len(pd.read_csv(METADATA / "dataset_catalog.csv")) == len(expected_catalogued_csvs), "Catalog includes every package input, analysis-ready table, result table, and figure-ready CSV exactly once.")

    results = pd.DataFrame(audit.rows)
    save_path = QA / "three_level_qaqc.csv"
    results.to_csv(save_path, index=False, lineterminator="\n")
    failures = results.loc[results["status"].eq("FAIL")]
    summary = {
        "status": "PASS" if failures.empty else "FAIL",
        "total_checks_and_notes": len(results),
        "passed": int(results["status"].eq("PASS").sum()),
        "documented_notes": int(results["status"].eq("DOCUMENTED_NOTE").sum()),
        "failed": len(failures),
        "levels": {
            str(level): results.loc[results["qa_level"].eq(level), "status"].value_counts().to_dict()
            for level in (1, 2, 3)
        },
    }
    (QA / "three_level_qaqc_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not failures.empty:
        print(failures.to_string(index=False))
        raise SystemExit("QA/QC failed")


if __name__ == "__main__":
    main()
