#!/usr/bin/env python3
"""Prepare the analysis-ready, source-linked datasets used by the manuscript.

The script performs only declared filtering, joins, unit conversions, and
quality-control gates. It does not scrape websites or extract new values from
reports. Every operator value remains linked to a source identifier and an
exact report page or web-table locator in ``metadata/source_register.csv``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input"
READY = ROOT / "data" / "analysis_ready"
QA = ROOT / "qa"

GOOGLE_REPORTS = {
    2023: ("GOOGLE_ENV_2023", "https://sustainability.google/reports/google-2023-environmental-report/"),
    2024: ("GOOGLE_ENV_2024", "https://sustainability.google/reports/google-2024-environmental-report/"),
    2025: ("GOOGLE_ENV_2025", "https://sustainability.google/reports/google-2025-environmental-report/"),
    2026: ("GOOGLE_ENV_2026", "https://sustainability.google/google-2026-environmental-report/"),
}

META_REPORTS = {
    "2024_Meta-Environmental-Data-Index.pdf": (
        "META_EDI_2024",
        "https://sustainability.atmeta.com/resources/",
    ),
    "Meta_2025-Environmental-Data-Index.pdf": (
        "META_EDI_2025",
        "https://sustainability.atmeta.com/wp-content/uploads/2025/10/Meta_2025-Environmental-Data-Index.pdf",
    ),
}

US_META_LOCATIONS = {
    "Altoona (IA)", "DeKalb (IL)", "Eagle Mountain (UT)", "Forest City (NC)",
    "Fort Worth (TX)", "Gallatin (TN)", "Henrico (VA)", "Huntsville (AL)",
    "Kansas City (MO)", "Los Lunas (NM)", "Mesa (AZ)", "New Albany (OH)",
    "Prineville (OR)", "Sarpy (NE)", "Stanton Springs (GA)",
}

US_AWS_REGIONS = {
    "U.S. East (Northern Virginia)", "U.S. East (Ohio)",
    "U.S. West (Northern California)", "U.S. West (Oregon)",
}

FLOW_SITES = {
    "Atlanta_GA": {
        "label": "Atlanta",
        "station_id": "02336000",
        "file": "USGS_02336000_Atlanta_GA.csv",
        "source_fraction": 1.0,
        "source_fraction_status": "standardized source-component assignment",
        "usgs_source_id": "USGS_02336000",
        "utility_source_id": "ATLANTA_DWM_OVERVIEW",
        "weather_source_id": "ENERGYPLUS_TMY3_ATLANTA",
    },
    "Seattle_WA": {
        "label": "Seattle",
        "station_id": "12117500",
        "file": "USGS_12117500_Seattle_WA.csv",
        "source_fraction": 0.70,
        "source_fraction_status": "upper bound of documented 60-70% utility share",
        "usgs_source_id": "USGS_12117500",
        "utility_source_id": "SEATTLE_WSP_2019",
        "weather_source_id": "ENERGYPLUS_TMY3_SEATTLE",
    },
    "Council_Bluffs_IA": {
        "label": "Council Bluffs",
        "station_id": "06610000",
        "file": "USGS_06610000_Council_Bluffs_IA.csv",
        "source_fraction": 1.0,
        "source_fraction_status": "standardized source-family assignment",
        "usgs_source_id": "USGS_06610000",
        "utility_source_id": "CB_WATER_WORKS_2024",
        "weather_source_id": "ENERGYPLUS_TMY3_CHICAGO",
    },
}

REFERENCE_LOAD_MW = 250.0
MILLION_M3_PER_MILLION_US_GALLONS = 0.003785411784
MESA_SOURCE_SHA256 = "346a7e6d4f7da3fd50a6b243d44149cf5113eb6c46fc7f7bd6cad73a4f16d208"
MESA_PATHWAYS = {
    "npdes_outfall_005": ("Aquifer recharge", True),
    "reuse": ("Local reuse", True),
    "ponds": ("Percolation recharge", True),
    "gric": ("GRIC exchange", True),
    "me01_southern_ave": ("91st Ave / Palo Verde", True),
    "me02_baseline": ("91st Ave / Palo Verde", True),
    "me03_8th_street": ("91st Ave / Palo Verde", True),
    "azpdes_outfall_003": ("Salt River discharge", False),
    "outfall_001_gwrp": ("East Maricopa Floodway", False),
    "outfall_001_sewrp": ("East Maricopa Floodway", False),
    "effluent_to_baseline": ("Baseline sewer return", False),
}
MESA_PLANT_CAPACITY_MGD = {"NWWRP": 18.0, "GWRP": 30.0, "SEWRP": 8.0, "SROG": 230.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_csv(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(READY / name, index=False, lineterminator="\n")


def prepare_google() -> tuple[pd.DataFrame, pd.DataFrame]:
    water = pd.read_csv(INPUT / "google_location_water_2022_2025.csv")
    context = pd.read_csv(INPUT / "google_locations_aqueduct26.csv")
    if water.shape != (101, 16):
        raise ValueError(f"Unexpected Google water-panel shape: {water.shape}")
    if len(context) != 26 or context["location"].nunique() != 26:
        raise ValueError("Google-Aqueduct screen must contain the 26 U.S. locations used in Figure 3")

    water["source_id"] = water["report_publication_year"].map(lambda y: GOOGLE_REPORTS[int(y)][0])
    water["source_url"] = water["report_publication_year"].map(lambda y: GOOGLE_REPORTS[int(y)][1])
    water["source_locator"] = water["report_printed_page"].map(
        lambda page: f"printed p. {int(page)}, Water use by data center location"
    )
    water["withdrawal_status"] = "operator-reported"
    water["discharge_status"] = "operator-reported"
    water["consumption_status"] = "operator-reported; identified as estimated by operator"
    water["known_source_issue"] = ""
    issue = (
        water["year"].eq(2024)
        & water["location"].eq("Other data center locations")
        & water["consumption_mg"].eq(786.9)
    )
    if issue.sum() != 1:
        raise ValueError("The documented Google FY2024 aggregate inconsistency was not found exactly once")
    water.loc[issue, "known_source_issue"] = (
        "Published consumption is 786.9 MG; published withdrawal minus discharge is 768.9 MG. "
        "The printed value is preserved and excluded from named-location consumption results."
    )
    named = water.loc[water["is_named_location"].eq(True)].copy()
    if len(named) != 97:
        raise ValueError(f"Expected 97 manuscript-scope named Google location-years; found {len(named)}")

    aqueduct = context.copy()
    aqueduct["source_id"] = "WRI_AQUEDUCT_4"
    aqueduct["source_url"] = "https://doi.org/10.46830/writn.23.00061"
    aqueduct["source_locator"] = "Aqueduct 4.0 baseline annual indicators; baseline period 1979-2019"
    save_csv(aqueduct, "google_location_aqueduct_screen.csv")

    panel = named.merge(
        aqueduct[["location", "latitude", "longitude", "name_0", "macro_region", "bws_raw", "bws_score", "bws_label", "screening_dataset", "screening_baseline_period", "screening_caveat"]],
        on="location",
        how="left",
        validate="many_to_one",
    )
    us_mask = panel["location"].isin(set(aqueduct["location"]))
    if panel.loc[us_mask, ["latitude", "bws_score"]].isna().any().any():
        raise ValueError("One or more U.S. Google locations did not join to the Aqueduct screen")
    if panel.loc[~us_mask, "year"].ne(2025).any():
        raise ValueError("The public release contains unused non-U.S. historical rows")
    panel.loc[~us_mask, "name_0"] = "Non-U.S."
    panel["aqueduct_source_id"] = np.where(us_mask, "WRI_AQUEDUCT_4", "")
    panel["aqueduct_source_url"] = np.where(
        us_mask, "https://doi.org/10.46830/writn.23.00061", ""
    )
    panel["aqueduct_source_locator"] = np.where(
        us_mask, "Aqueduct 4.0 baseline annual indicators; baseline period 1979-2019", ""
    )
    save_csv(panel, "google_named_location_year.csv")

    us = panel.loc[panel["name_0"].eq("United States")].copy()
    if len(us) != 83 or us["location"].nunique() != 26:
        raise ValueError(f"Expected 83 U.S. rows across 26 locations; found {len(us)} and {us['location'].nunique()}")
    save_csv(us, "google_us_location_year.csv")
    global_2025 = panel.loc[panel["year"].eq(2025)].copy()
    if len(global_2025) != 40:
        raise ValueError("Expected 40 named Google FY2025 locations")
    save_csv(global_2025, "google_global_fy2025.csv")

    source_mix = pd.read_csv(INPUT / "google_reported_source_mix.csv")
    source_mix["source_id"] = source_mix["report_publication_year"].map(lambda y: GOOGLE_REPORTS[int(y)][0])
    source_mix["source_url"] = source_mix["report_publication_year"].map(lambda y: GOOGLE_REPORTS[int(y)][1])
    source_mix["source_locator"] = source_mix["report_printed_page"].map(
        lambda page: f"printed p. {int(page)}, Water use by data center location"
    )
    source_mix["value_status"] = "operator-reported"
    save_csv(source_mix, "google_reported_source_mix.csv")
    return us, global_2025


def prepare_meta() -> pd.DataFrame:
    meta = pd.read_csv(INPUT / "meta_site_water_electricity_2019_2024.csv")
    if meta.shape != (70, 11):
        raise ValueError(f"Unexpected Meta panel shape: {meta.shape}")
    meta["source_id"] = meta["report_file"].map(lambda f: META_REPORTS[f][0])
    meta["source_url"] = meta["report_file"].map(lambda f: META_REPORTS[f][1])
    meta["source_locator"] = meta.apply(
        lambda row: (
            f"printed p. {int(row.report_printed_page_electricity)} (electricity); "
            f"printed p. {int(row.report_printed_page_water)} (water)"
        ),
        axis=1,
    )
    meta["electricity_status"] = "operator-reported total-facility electricity"
    meta["withdrawal_status"] = "operator-reported water withdrawal"
    meta["intensity_status"] = "study-derived; not WUE because IT electricity is unavailable"
    us = meta.loc[meta["location"].isin(US_META_LOCATIONS)].copy()
    if len(us) != 70 or us["location"].nunique() != 15:
        raise ValueError(f"Expected 70 U.S. Meta observations across 15 facilities; found {len(us)} and {us['location'].nunique()}")
    save_csv(us, "meta_us_facility_year.csv")
    return us


def prepare_aws() -> pd.DataFrame:
    aws = pd.read_csv(INPUT / "aws_region_pue_wue_2022_2025.csv")
    if len(aws) != 4:
        raise ValueError(f"Expected four manuscript-scope U.S. AWS regions; found {len(aws)}")
    aws["source_id"] = "AWS_CLOUD_2026"
    aws["source_url"] = "https://sustainability.aboutamazon.com/products-services/aws-cloud?waterType=true"
    aws["source_locator"] = "regional PUE and WUE table archived 2026-09-05"
    aws["pue_status"] = "operator-reported"
    aws["wue_status"] = "operator-reported withdrawal WUE"
    us = aws.loc[aws["location"].isin(US_AWS_REGIONS)].copy()
    if len(us) != 4:
        raise ValueError(f"Expected four matched U.S. AWS regions; found {len(us)}")
    us["pue_change"] = us["pue_2025"] - us["pue_2024"]
    us["wue_change"] = us["wue_2025"] - us["wue_2024"]
    save_csv(us, "aws_us_matched_regions.csv")
    return us


def prepare_flow_and_cooling() -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly = pd.read_csv(INPUT / "monthly_cooling_water_intensity.csv")
    if len(monthly) != 72:
        raise ValueError(f"Expected 72 monthly cooling-model rows; found {len(monthly)}")
    monthly["method_source_id"] = "LEI_MASANET_2022"
    monthly["weather_source_id"] = monthly["location"].map(
        {location: metadata["weather_source_id"] for location, metadata in FLOW_SITES.items()}
    )
    monthly["value_status"] = "modeled from archived central parameter vector and TMY3 weather"
    save_csv(monthly, "cooling_model_monthly.csv")

    flow_frames: list[pd.DataFrame] = []
    pressure_frames: list[pd.DataFrame] = []
    multiplier = REFERENCE_LOAD_MW * 1000.0 * 24.0 / 1_000_000.0
    for location, metadata in FLOW_SITES.items():
        flow = pd.read_csv(INPUT / "usgs" / metadata["file"], dtype={"station_id": str})
        flow["station_id"] = flow["station_id"].str.zfill(8)
        flow["date"] = pd.to_datetime(flow["date"])
        if len(flow) != 10_958 or not flow["station_id"].eq(metadata["station_id"]).all():
            raise ValueError(f"{location}: station identity or record count changed")
        if flow["date"].min() != pd.Timestamp("1995-10-01") or flow["date"].max() != pd.Timestamp("2025-09-30"):
            raise ValueError(f"{location}: daily-flow coverage changed")
        if flow["date"].duplicated().any() or not flow["discharge_ML_day"].gt(0).all():
            raise ValueError(f"{location}: duplicate date or non-positive flow")
        flow["location"] = location
        flow["location_label"] = metadata["label"]
        flow["source_id"] = metadata["usgs_source_id"]
        flow["source_url"] = f"https://waterdata.usgs.gov/monitoring-location/USGS-{metadata['station_id']}/"
        flow["source_locator"] = "daily mean discharge, parameter 00060, 1995-10-01 through 2025-09-30"
        flow_frames.append(flow.copy())

        flow["month"] = flow["date"].dt.month
        flow["water_year"] = flow["date"].dt.year + (flow["date"].dt.month >= 10)
        flow["source_fraction"] = metadata["source_fraction"]
        flow["source_fraction_status"] = metadata["source_fraction_status"]
        flow["utility_source_id"] = metadata["utility_source_id"]
        for architecture in sorted(monthly["architecture_id"].unique()):
            wue = monthly.loc[
                monthly["location"].eq(location) & monthly["architecture_id"].eq(architecture),
                ["month", "withdrawal_wue_l_per_kwh", "consumption_wue_l_per_kwh", "method_source_id", "weather_source_id"],
            ]
            joined = flow.merge(wue, on="month", how="left", validate="many_to_one")
            joined["architecture_id"] = architecture
            joined["withdrawal_ml_day"] = multiplier * joined["withdrawal_wue_l_per_kwh"]
            joined["consumption_ml_day"] = multiplier * joined["consumption_wue_l_per_kwh"]
            joined["source_consumption_ml_day"] = joined["source_fraction"] * joined["consumption_ml_day"]
            joined["source_relative_pressure_pct"] = 100 * joined["source_consumption_ml_day"] / joined["discharge_ML_day"]
            joined["equation_status"] = "study-derived standardized screen; not facility impact or available supply"
            pressure_frames.append(joined)

    flow_all = pd.concat(flow_frames, ignore_index=True).sort_values(["location", "date"])
    pressure = pd.concat(pressure_frames, ignore_index=True).sort_values(["location", "architecture_id", "date"])
    if len(flow_all) != 32_874 or len(pressure) != 65_748:
        raise ValueError("Combined daily-flow or pressure row count changed")
    save_csv(flow_all, "usgs_daily_flow_three_components.csv")
    save_csv(pressure, "source_component_daily_pressure.csv")

    monthly_pressure = pressure.groupby(
        ["location", "location_label", "architecture_id", "month"], as_index=False
    ).agg(
        daily_records=("date", "size"),
        water_years=("water_year", "nunique"),
        mean_withdrawal_ml_day=("withdrawal_ml_day", "mean"),
        mean_consumption_ml_day=("consumption_ml_day", "mean"),
        flow_q10_ml_day=("discharge_ML_day", lambda values: values.quantile(0.10)),
        flow_median_ml_day=("discharge_ML_day", "median"),
        pressure_p50_pct=("source_relative_pressure_pct", "median"),
        pressure_p90_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.90)),
        pressure_p95_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.95)),
        pressure_p99_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.99)),
    )
    monthly_pressure["architecture_label"] = monthly_pressure["architecture_id"].map({
        "climate_responsive_hybrid": "Climate-responsive hybrid",
        "water_cooled_evaporative": "Water-cooled evaporative",
    })
    monthly_pressure["hydrology_source_id"] = monthly_pressure["location"].map(
        {location: metadata["usgs_source_id"] for location, metadata in FLOW_SITES.items()}
    )
    monthly_pressure["utility_source_id"] = monthly_pressure["location"].map(
        {location: metadata["utility_source_id"] for location, metadata in FLOW_SITES.items()}
    )
    monthly_pressure["model_source_id"] = "LEI_MASANET_2022"
    save_csv(monthly_pressure, "source_component_monthly_pressure.csv")
    return flow_all, pressure


def prepare_mesa() -> pd.DataFrame:
    source = INPUT / "mesa_reclaimed_water_management.csv"
    if sha256(source) != MESA_SOURCE_SHA256:
        raise ValueError("The frozen City of Mesa source checksum changed")
    raw = pd.read_csv(source)
    if raw.shape != (53_954, 19):
        raise ValueError(f"Unexpected Mesa source shape: {raw.shape}")
    raw["reporting_date"] = pd.to_datetime(raw["reporting_date"])
    raw["date"] = raw["reporting_date"].dt.normalize()
    path_columns = list(MESA_PATHWAYS)
    core = raw.loc[raw["plant"].isin(MESA_PLANT_CAPACITY_MGD)].copy()
    duplicate_rows = int(core.duplicated(["plant", "description", "date"]).sum())
    core = core.groupby(["plant", "description", "date"], as_index=False)[path_columns].mean()

    invalid_row = core[path_columns].lt(0).any(axis=1)
    negative_cells = int(core[path_columns].lt(0).sum().sum())
    over_capacity_cells = 0
    for plant, capacity in MESA_PLANT_CAPACITY_MGD.items():
        mask = core["plant"].eq(plant)
        over = core.loc[mask, path_columns].gt(capacity)
        over_capacity_cells += int(over.sum().sum())
        invalid_row.loc[mask] |= over.any(axis=1)
    clean = core.loc[~invalid_row].copy()
    daily = clean.groupby("date")[path_columns].sum(min_count=1)
    daily = daily.join(clean.groupby("date").size().rename("valid_meter_records")).reset_index()
    expected_meters = int(core.groupby("date").size().mode().iloc[0])
    beneficial_columns = [key for key, (_, beneficial) in MESA_PATHWAYS.items() if beneficial]
    daily["beneficial_reuse_mgd"] = daily[beneficial_columns].sum(axis=1)
    daily["total_system_flow_mgd"] = daily[path_columns].sum(axis=1)
    daily["complete_day"] = daily["valid_meter_records"].eq(expected_meters) & daily["total_system_flow_mgd"].gt(0)
    daily["beneficial_fraction"] = daily["beneficial_reuse_mgd"] / daily["total_system_flow_mgd"]
    complete = daily.loc[daily["complete_day"]].copy()
    complete["month"] = complete["date"].dt.to_period("M").dt.to_timestamp()
    complete["source_id"] = "MESA_OPEN_DATA_2026"
    complete["source_url"] = "https://data.mesaaz.gov/d/5zhe-5nig"
    complete["source_locator"] = "dataset 5zhe-5nig; retrieved 2026-08-22"
    complete["value_status"] = "study-derived after declared sensor and completeness QA"
    if len(complete) != 2_676 or not complete["beneficial_fraction"].between(0, 1).all():
        raise ValueError("Mesa complete-day QA result changed")
    save_csv(complete, "mesa_daily_pathways_qc.csv")
    diagnostics = {
        "source_rows": len(raw),
        "source_columns": 19,
        "duplicate_key_rows_removed": duplicate_rows,
        "negative_measurement_cells": negative_cells,
        "over_capacity_measurement_cells": over_capacity_cells,
        "expected_meter_records_per_day": expected_meters,
        "complete_days": len(complete),
        "source_sha256": MESA_SOURCE_SHA256,
    }
    (QA / "mesa_preparation_qc.json").write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")
    return complete


def prepare_cases() -> None:
    cases = pd.read_csv(INPUT / "source_resolved_case_evidence.csv")
    if len(cases) != 4 or not cases["case_id"].eq("quincy_qwru").all():
        raise ValueError("Source-resolved evidence must contain only the four Quincy records used in Table 6")
    save_csv(cases, "source_resolved_case_evidence.csv")


def write_input_manifest() -> None:
    rows = []
    for path in sorted(p for p in INPUT.rglob("*") if p.is_file()):
        rows.append({
            "relative_path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    pd.DataFrame(rows).to_csv(QA / "input_file_manifest.csv", index=False, lineterminator="\n")


def main() -> None:
    READY.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    us_google, global_google = prepare_google()
    us_meta = prepare_meta()
    us_aws = prepare_aws()
    flow, pressure = prepare_flow_and_cooling()
    mesa = prepare_mesa()
    prepare_cases()
    write_input_manifest()
    summary = {
        "status": "PASS",
        "google_manuscript_location_years": 97,
        "google_us_location_years": len(us_google),
        "google_global_fy2025_locations": len(global_google),
        "meta_us_facility_years": len(us_meta),
        "aws_matched_us_regions": len(us_aws),
        "usgs_daily_records": len(flow),
        "source_component_daily_architecture_records": len(pressure),
        "mesa_complete_days": len(mesa),
    }
    (QA / "preparation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
