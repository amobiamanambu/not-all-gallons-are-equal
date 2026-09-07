#!/usr/bin/env python3
"""Build source-linked manuscript tables and repository metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
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


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def source_register() -> pd.DataFrame:
    columns = [
        "source_id", "organization_or_authors", "year", "title", "source_type",
        "primary_url", "source_locator", "variables_supported", "retrieved_or_accessed",
        "archived_source_sha256", "verification_status", "scientific_boundary",
    ]
    rows = [
        ["GOOGLE_ENV_2023", "Google", 2023, "2023 Environmental Report", "operator report", "https://sustainability.google/reports/google-2023-environmental-report/", "printed p. 95, Water use by data center location", "FY2022 location withdrawal, discharge, consumption and selected source splits", "2026-09-05 archive audit", "111780cb32516f4541ca7078e9efcf0602579c4bd345f56dad608fbcd92a1c15", "verified against archived report", "Operator disclosure; consumption is operator-estimated."],
        ["GOOGLE_ENV_2024", "Google", 2024, "Google 2024 Environmental Report", "operator report", "https://sustainability.google/reports/google-2024-environmental-report/", "printed p. 79, Water use by data center location", "FY2023 location withdrawal, discharge, consumption and selected source splits", "2026-09-05 archive audit", "29ade2be2f75e33b94e88fc676a31aaaab205e4ae7f146bc284c57d93d858645", "verified against archived report", "Operator disclosure; consumption is operator-estimated."],
        ["GOOGLE_ENV_2025", "Google", 2025, "Google 2025 Environmental Report", "operator report", "https://sustainability.google/reports/google-2025-environmental-report/", "printed p. 114, Water use by data center location", "FY2024 location withdrawal, discharge, consumption and selected source splits", "2026-09-05 archive audit", "00bf26d9a1899c6d034e9b6f8ba8943dc3902e177038921283c74936264c5c10", "verified with one documented source inconsistency", "The aggregate Other locations row prints consumption 786.9 MG although withdrawal minus discharge is 768.9 MG; printed value retained and excluded from named-location consumption analyses."],
        ["GOOGLE_ENV_2026", "Google", 2026, "Google 2026 Environmental Report", "operator report", "https://sustainability.google/google-2026-environmental-report/", "printed p. 97, Water use by data center location; endnote 224 on p. 116", "FY2025 location withdrawal, discharge, estimated consumption, cooling notes and source splits", "2026-09-05 archive audit", "6a23a6db212d5d7da8d887e773e98e78ee16b98eaf8d627a4e31f98b6f487ca3", "verified against archived report", "Location values may represent campuses; endnote states withdrawals are potable unless specified."],
        ["META_EDI_2024", "Meta", 2024, "2024 Environmental Data Index", "operator report", "https://sustainability.atmeta.com/resources/", "printed p. 29 electricity; printed p. 32 water", "FY2019-FY2023 site electricity and water", "2026-09-05 archive audit", "2b36549ca82f0cbbf2b922f34755b53212a5bbdcc26ae055d42295d67f83ff64", "verified against archived report", "Electricity is total-facility, not IT electricity; derived ratio is not WUE."],
        ["META_EDI_2025", "Meta", 2025, "Meta 2025 Environmental Data Index", "operator report", "https://sustainability.atmeta.com/wp-content/uploads/2025/10/Meta_2025-Environmental-Data-Index.pdf", "printed p. 6 electricity; printed p. 9 water", "FY2020-FY2024 site electricity and water", "2026-09-05 archive audit", "d7527cd23308869105b404b486117603bb3f5ee10e30499367f8698110afb66d", "verified against archived report", "Electricity is total-facility, not IT electricity; derived ratio is not WUE."],
        ["AWS_CLOUD_2026", "Amazon Web Services", 2026, "AWS Cloud Sustainability: PUE and WUE", "operator webpage", "https://sustainability.aboutamazon.com/products-services/aws-cloud?waterType=true", "regional PUE and WUE table archived 2026-09-05", "regional PUE and withdrawal WUE, FY2022-FY2025 where disclosed", "2026-09-05", "dcd8edfdb38503f39a7497f2dccd9adeb8072773c066514592303683b5819e4e", "verified against archived official webpage", "Only matched years and regions are compared; WUE uses IT-energy denominator."],
        ["WRI_AQUEDUCT_4", "Kuzma et al.; World Resources Institute", 2023, "Aqueduct 4.0: Updated Decision-Relevant Global Water Risk Indicators", "screening dataset and methods", "https://doi.org/10.46830/writn.23.00061", "baseline annual indicators; baseline period 1979-2019", "baseline water stress screen at reported locality centroids", "2026-09-05", "bd3ed2bce88d6ff1b89191632ad134a2436e1e1d49599382f23a04d513624fc3", "verified against WRI archive and methods", "Prioritization screen, not facility-source attribution or local impact assessment."],
        ["USGS_02336000", "U.S. Geological Survey", "n.d.", "USGS 02336000 Chattahoochee River at Atlanta, Georgia", "daily hydrological observations", "https://waterdata.usgs.gov/monitoring-location/USGS-02336000/", "daily mean discharge, parameter 00060, 1995-10-01 through 2025-09-30", "Atlanta source-component discharge", "retrieved 2026-08-20", "", "10,958 dates, station and units revalidated", "Managed source-component flow is not available water or facility allocation."],
        ["USGS_12117500", "U.S. Geological Survey", "n.d.", "USGS 12117500 Cedar River near Landsburg, Washington", "daily hydrological observations", "https://waterdata.usgs.gov/monitoring-location/USGS-12117500/", "daily mean discharge, parameter 00060, 1995-10-01 through 2025-09-30", "Seattle Cedar source-component discharge", "retrieved 2026-08-20", "", "10,958 dates, station and units revalidated", "Gauge is approximately 1.8 miles upstream of the intake; it is a component screen, not facility allocation."],
        ["USGS_06610000", "U.S. Geological Survey", "n.d.", "USGS 06610000 Missouri River at Omaha, Nebraska", "daily hydrological observations", "https://waterdata.usgs.gov/monitoring-location/USGS-06610000/", "daily mean discharge, parameter 00060, 1995-10-01 through 2025-09-30", "Council Bluffs Missouri River source-family discharge", "retrieved 2026-08-20", "", "10,958 dates, station and units revalidated", "Gauge is downstream and does not resolve river/alluvium shares, managed availability, rights or ecological effects."],
        ["LEI_MASANET_2022", "Lei and Masanet", 2022, "Climate- and technology-specific PUE and WUE estimations for U.S. data centers using a hybrid statistical and thermodynamics-based approach", "peer-reviewed model", "https://doi.org/10.1016/j.resconrec.2022.106323", "methods and archived central scenario vector", "cooling architecture equations and parameters", "verified 2026-09-05", "", "DOI and model archive verified", "Central is a named parameter vector, not an arithmetic midpoint."],
        ["ENERGYPLUS_TMY3_ATLANTA", "U.S. Department of Energy EnergyPlus", "archived", "Atlanta Hartsfield-Jackson TMY3 weather file", "weather input", "https://energyplus.net/weather", "USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw", "hourly Atlanta weather for cooling model", "frozen project archive", "", "local archive retained", "Typical meteorological year, not observed 1996-2025 daily weather."],
        ["ENERGYPLUS_TMY3_SEATTLE", "U.S. Department of Energy EnergyPlus", "archived", "Seattle-Tacoma TMY3 weather file", "weather input", "https://energyplus.net/weather", "USA_WA_Seattle-Tacoma.Intl.AP.727930_TMY3.epw", "hourly Seattle weather for cooling model", "frozen project archive", "", "local archive retained", "Typical meteorological year, not observed 1996-2025 daily weather."],
        ["ENERGYPLUS_TMY3_CHICAGO", "U.S. Department of Energy EnergyPlus", "archived", "Chicago O'Hare TMY3 weather file", "weather input", "https://energyplus.net/weather", "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw", "hourly proxy weather for Council Bluffs cooling model", "frozen project archive", "", "local archive retained", "Declared climate proxy; not local observed Council Bluffs weather."],
        ["MESA_OPEN_DATA_2026", "City of Mesa Water Resources", 2026, "Reclaimed Water Management PUBLIC", "municipal open dataset", "https://data.mesaaz.gov/d/5zhe-5nig", "dataset 5zhe-5nig; retrieved 2026-08-22", "daily municipal reuse, recharge, exchange and return pathways", "2026-08-22", "346a7e6d4f7da3fd50a6b243d44149cf5113eb6c46fc7f7bd6cad73a4f16d208", "raw file hash and QA gates verified", "Municipal pathways are not assigned to individual data centers."],
        ["QUINCY_OPS_2020", "City of Quincy", 2021, "2020 Annual Operations Report", "municipal operations report", "https://quincy.civicweb.net/document/82731/F-2%200803212020%20Quincy%20Annual%20Report_Final.pdf?handle=DDF5AEC43AE84B2EAF0A93EBDE56D987", "PDF pp. 3 and 15", "254.48 million gallons delivered through reuse system to Microsoft in 2020", "2026-08-22", "", "phrase and value verified on two report pages", "Reuse delivery is not freshwater withdrawal or consumption."],
        ["EPA_QUINCY_REUSE", "U.S. Environmental Protection Agency", 2026, "Water Reuse Case Study: Quincy, Washington", "government case-study webpage", "https://www.epa.gov/waterreuse/water-reuse-case-study-quincy-washington", "Project Highlights and Solution sections", "138 MG/year potable-demand offset; 260 MG/year canal make-up; 5% potable-groundwater share", "2026-08-22", "", "values verified against official webpage", "Metrics have different roles and unspecified or different periods; do not sum into a facility balance."],
        ["PHOENIX_WRP_2021", "City of Phoenix Water Services Department", 2021, "2021 Water Resource Plan", "utility plan", "https://www.phoenix.gov/content/dam/phoenix/waterservicessite/documents/2021_Water_Resource_Plan.pdf", "portfolio sections", "Phoenix municipal supply portfolio", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only; not allocated to a facility."],
        ["SNWA_SOURCES_2026", "Southern Nevada Water Authority", 2026, "Where your water comes from", "utility webpage", "https://www.snwa.com/water-resources/where-water-comes-from/index.html", "source portfolio overview", "Colorado River and groundwater sources", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only."],
        ["SNWA_WRP_2026", "Southern Nevada Water Authority", 2026, "2026 Water Resource Plan, Chapter 3", "utility plan", "https://www.snwa.com/assets/pdf/water-resource-plan-chapter-3-2026.pdf?lang=en", "Chapter 3", "allocations, groundwater and return-flow credits", "accessed 2026-09-06", "", "institutional source verified", "Managed-system context; a return-path gauge is not a supply denominator."],
        ["SAWS_WMP_2025", "San Antonio Water System", 2025, "2025 Water Management Plan", "utility plan", "https://apps.saws.org/your_water/waterresources/docs/SAWS_2025_Water_Management_Plan_20250812.pdf", "source portfolio sections", "San Antonio municipal supply portfolio", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only."],
        ["DALLAS_LRWSP_2024", "Dallas Water Utilities", 2024, "2024 Long Range Water Supply Plan", "utility plan", "https://dallascityhall.com/departments/waterutilities/Documents/DWU%20LRWSP%202024_with%20Appendices.pdf", "regional supply-system sections", "Dallas-Fort Worth multi-reservoir and reuse context", "accessed 2026-09-06", "", "institutional source verified", "Multi-utility regional context; no single gauge is representative."],
        ["ATLANTA_DWM_OVERVIEW", "Atlanta Department of Watershed Management", "n.d.", "Water and Wastewater System Overview", "utility report", "https://www.atlantawatershed.org/wp-content/uploads/2019/10/CEIP-SystemOverview_final.pdf", "PDF p. 2", "Chattahoochee utility source family", "archived project copy", "", "source statement verified in archived PDF", "Supports source-component screening, not facility allocation."],
        ["LOUDOUN_WATER_2026", "Loudoun Water", 2026, "Your Drinking Water Quality", "utility webpage", "https://www.loudounwater.org/residential-customers/your-drinking-water-quality", "supply-source overview", "Northern Virginia supply portfolio", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only."],
        ["VALLEY_WATER_2026", "Santa Clara Valley Water District", 2026, "Where Your Water Comes From: Imported Water", "utility webpage", "https://www.valleywater.org/your-water/where-your-water-comes-from/imported-water", "water-source overview", "Silicon Valley imported and local supply portfolio", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only."],
        ["SEATTLE_WSP_2019", "Seattle Public Utilities", 2019, "2019 Water System Plan, Volume 1", "utility plan", "https://www.seattle.gov/documents/departments/spu/documents/plans/spufinal2019_wsp_volume1.pdf", "PDF p. 23; Cedar supplies approximately 60-70%", "Cedar and South Fork Tolt portfolio; Cedar fraction", "archived project copy", "", "source statement and page verified", "The 0.70 Cedar fraction is a documented upper-bound scenario, not a facility allocation."],
        ["DALLES_WQR_2024", "City of The Dalles", 2024, "2024 Water Quality Report", "utility report", "https://ormswd2.synergydcs.com/HPRMWebDrawer/Record/6884165/File/document", "source-water section", "protected watershed and municipal wells", "2026-09-05 archive audit", "5547c37fcb6a97affc92b357bc9c00d2986533ea5738694d7d0f828b6c0cff8a", "verified against archived report", "The Columbia River is outside the documented municipal supply portfolio."],
        ["QUINCY_ECOLOGY_2019", "Washington State Department of Ecology", 2019, "Microsoft Columbia Data Center Draft Technical Support Document", "regulatory technical document", "https://ecology.wa.gov/getattachment/26e593fe-7ea0-4b34-bd46-c6b2f58aad33/20191209MSColumbiaDraftTSD.pdf", "water-supply and discharge sections", "Quincy potable groundwater and reuse context", "accessed 2026-09-06", "", "institutional source verified", "Does not support a Columbia River facility-pressure calculation."],
        ["PRINEVILLE_WMP_2023", "City of Prineville", 2023, "2023 Water System Master Plan, Volume 1", "utility plan", "https://www.cityofprineville.com/1261/Ordinances", "source and mitigation sections", "Prineville groundwater, mitigation and ASR context", "accessed 2026-09-06", "", "institutional source verified", "Crooked River gauge is not a direct municipal-supply denominator."],
        ["IOWA_DNR_PWS_2026", "Iowa Department of Natural Resources", 2026, "Public Water Supply 706012 Facility Inventory", "regulatory database", "https://programs.iowadnr.gov/iowadrinkingwater/search/pwsdetails?tinwsysIsNumber=706012", "facility inventory", "Altoona-Des Moines multi-source system", "accessed 2026-09-06", "", "institutional source verified", "Portfolio context only."],
        ["GOOGLE_IOWA_DC", "Google Data Centers", "n.d.", "Iowa Data Center Location", "operator facility webpage", "https://datacenters.google/locations/iowa/", "Council Bluffs facility description", "named facility location", "archived project copy", "", "facility identity verified", "Does not identify the actual 2025 utility billing source or river/alluvium split."],
        ["CB_PLANNING_2012", "Council Bluffs Planning Commission", 2012, "Minutes of the May 8, 2012 Meeting", "municipal record", "https://www.councilbluffs-ia.gov/ArchiveCenter/ViewFile/Item/668", "PDF p. 10", "public-water and sanitary-sewer infrastructure to Google expansion", "archived project copy", "", "source statement and page verified", "Historical infrastructure link; greywater discussion is not treated as 2025 evidence."],
        ["CB_WATER_WORKS_2024", "Council Bluffs Water Works", 2024, "General Information: General Description of System Operations", "utility webpage", "https://www.cbwaterworks.com/about/general-information/", "source-system description", "Missouri River primary source and Missouri River Alluvium secondary source", "archived project copy", "", "source statement verified", "Actual 2025 river/alluvium mix is not available."],
        ["IOWA_DNR_MISSOURI_2022", "Iowa Department of Natural Resources", 2022, "2022 Assessment for Missouri River Segment IA 06-WEM-1709", "regulatory database", "https://programs.iowadnr.gov/adbnet/Segments/1709/Assessment/2022", "segment/intake description", "intake river mile 619", "archived project copy", "615af5b46145e84a2aaa5c5e3bd3f3cffecc2b4b940f7cad1e54b94ade944288", "source locator verified", "Used only to establish approximate gauge-to-intake geography."],
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if frame["source_id"].duplicated().any():
        raise ValueError("Duplicate source IDs in source register")
    return frame


def source_display(register: pd.DataFrame, source_ids: str) -> str:
    indexed = register.set_index("source_id")
    values = []
    for source_id in [item.strip() for item in source_ids.split(";") if item.strip()]:
        row = indexed.loc[source_id]
        values.append(
            f"{row.organization_or_authors} ({row.year}), {row.source_locator}"
        )
    return "; ".join(values)


def build_table_1(register: pd.DataFrame) -> pd.DataFrame:
    rows = [
        ["Phoenix, AZ", "Salt-Verde, Colorado River, groundwater, and reuse", "PHOENIX_WRP_2021", "A single Salt River gauge omits major portfolio components", "Managed-system context"],
        ["Las Vegas, NV", "Colorado River allocation, groundwater, and return-flow credits", "SNWA_SOURCES_2026; SNWA_WRP_2026", "Las Vegas Wash records a return pathway rather than Colorado River supply", "Source-system context"],
        ["San Antonio, TX", "Aquifers, imported surface water, ASR, desalination, and recycled water", "SAWS_WMP_2025", "The San Antonio River does not represent the municipal supply portfolio", "Source-system context"],
        ["Dallas-Fort Worth, TX", "Multi-utility, multi-reservoir network with reuse", "DALLAS_LRWSP_2024", "A single Trinity River gauge does not represent the regional network", "Source-system context"],
        ["Atlanta, GA", "Chattahoochee River utility source family", "ATLANTA_DWM_OVERVIEW", "USGS 02336000 represents a managed utility source component", "Standardized source-component analysis"],
        ["Northern Virginia", "Potomac, Goose Creek, wholesale, reservoir, and reclaimed supplies", "LOUDOUN_WATER_2026", "A single Potomac component omits other documented supplies", "Source-system context"],
        ["Silicon Valley, CA", "Imported projects, local reservoirs, groundwater, and recycled water", "VALLEY_WATER_2026", "The Guadalupe River gauge does not represent the regional portfolio", "Source-system context"],
        ["Seattle, WA", "Cedar River (60-70%) and South Fork Tolt River (30-40%)", "SEATTLE_WSP_2019", "USGS 12117500 is 1.8 miles upstream from the Landsburg intake", "Standardized 70% Cedar-component analysis"],
        ["The Dalles, OR", "Protected headwater watershed and municipal wells", "DALLES_WQR_2024", "The Columbia River is outside the documented municipal source portfolio", "Source-system context"],
        ["Quincy, WA", "Potable groundwater plus facility-specific reuse", "QUINCY_OPS_2020; QUINCY_ECOLOGY_2019; EPA_QUINCY_REUSE", "The Columbia River does not supply the potable component", "Reuse-system case"],
        ["Prineville, OR", "Municipal groundwater, mitigation, and ASR", "PRINEVILLE_WMP_2023", "The Crooked River is not a direct municipal supply", "Source-system context"],
        ["Council Bluffs, IA", "Missouri River and Missouri River Alluvium", "CB_WATER_WORKS_2024; IOWA_DNR_MISSOURI_2022", "USGS 06610000 is approximately 3.1 river miles downstream from the surface-water intake", "Standardized source-family analysis"],
        ["Altoona-Des Moines, IA", "Two rivers, infiltration gallery, wells, and storage", "IOWA_DNR_PWS_2026", "A single Raccoon River gauge omits other documented supplies", "Source-system context"],
    ]
    frame = pd.DataFrame(rows, columns=["candidate_location", "documented_supply_system", "evidence_source_ids", "gauge_relationship", "role_in_analysis"])
    frame["evidence_sources"] = frame["evidence_source_ids"].map(lambda value: source_display(register, value))
    return frame


def build_table_2() -> pd.DataFrame:
    rows = [
        ["Room air or chilled-water loop", "Airside economizer with evaporative or chiller backup", "Climate-dependent; may be zero", "Hourly model", "Primary seasonal case"],
        ["Room air or chilled-water loop", "Water-cooled chiller and evaporative tower", "Evaporation and drift; positive blowdown retained", "Hourly model", "Wet-cooling comparison"],
        ["Room air or closed liquid loop", "Air-cooled refrigeration or dry cooler", "Zero routine heat-rejection water", "Boundary only", "Energy penalty not quantified"],
        ["Direct-to-chip liquid", "Dry cooler", "Zero routine heat-rejection water", "Not parameterized", "Dedicated data required"],
        ["Direct-to-chip liquid", "Evaporative tower", "Potentially positive and climate-dependent", "Not parameterized", "Dedicated data required"],
    ]
    frame = pd.DataFrame(rows, columns=["it_to_room_or_loop_transfer", "heat_rejection", "direct_on_site_water_boundary", "treatment", "analytical_role"])
    frame["model_source_id"] = "LEI_MASANET_2022"
    frame["value_status"] = ["modeled", "modeled", "conceptual boundary", "conceptual boundary", "conceptual boundary"]
    return frame


def build_numeric_tables() -> None:
    t3 = pd.read_csv(RESULTS / "table_3_source_component_results.csv")
    order_locations = {"Atlanta": 0, "Seattle": 1, "Council Bluffs": 2}
    order_arch = {"climate_responsive_hybrid": 0, "water_cooled_evaporative": 1}
    t3["_location_order"] = t3["location_label"].map(order_locations)
    t3["_arch_order"] = t3["architecture_id"].map(order_arch)
    t3 = t3.sort_values(["_location_order", "_arch_order"]).drop(columns=["_location_order", "_arch_order"])
    t3["location_and_source_component"] = t3["location_label"].map({
        "Atlanta": "Atlanta / Chattahoochee River",
        "Seattle": "Seattle / Cedar River",
        "Council Bluffs": "Council Bluffs / Missouri River family",
    })
    t3["source_basis"] = t3.apply(
        lambda row: f"{row.utility_source_id}; {row.source_id}; {row.method_source_id}", axis=1
    )
    t3["source_fraction"] = t3["source_fraction"].round(2)
    t3["mean_consumption_ml_day"] = t3["mean_consumption_ml_day"].round(3)
    for column in ["pressure_p50_pct", "pressure_p95_pct", "pressure_max_pct"]:
        t3[column] = t3[column].round(4)
    columns = [
        "location_and_source_component", "architecture_label", "source_fraction",
        "mean_consumption_ml_day", "pressure_p50_pct", "pressure_p95_pct",
        "pressure_max_pct", "source_basis", "source_fraction_status",
    ]
    save_csv(t3[columns], RESULTS / "manuscript_table_3_source_component_results.csv")

    t4 = pd.read_csv(RESULTS / "table_4_flow_regime_descriptors.csv")
    t4["_location_order"] = t4["location_label"].map(order_locations)
    t4 = t4.sort_values("_location_order").drop(columns="_location_order")
    t4["location_and_source_component"] = t4["location_label"].map({
        "Atlanta": "Atlanta / Chattahoochee River",
        "Seattle": "Seattle / Cedar River",
        "Council Bluffs": "Council Bluffs / Missouri River family",
    })
    t4["usgs_station"] = t4["source_id"].str.replace("USGS_", "", regex=False)
    t4["q_mean_ml_day"] = t4["q_mean_ml_day"].round(1)
    t4["q_drought_p10_ml_day"] = t4["q_drought_p10_ml_day"].round(1)
    t4["baseline_scarcity_b"] = t4["baseline_scarcity_b"].round(3)
    t4["drought_amplification_factor"] = t4["drought_amplification_factor"].round(3)
    columns = ["location_and_source_component", "usgs_station", "daily_records", "q_mean_ml_day", "q_drought_p10_ml_day", "baseline_scarcity_b", "drought_amplification_factor", "source_id", "source_url"]
    save_csv(t4[columns], RESULTS / "manuscript_table_4_flow_regime_descriptors.csv")

    t5 = pd.read_csv(RESULTS / "table_5_aws_pue_wue.csv")
    t5["pue_change"] = t5["pue_change"].round(2)
    t5["wue_change"] = t5["wue_change"].round(2)
    columns = ["location", "pue_2024", "pue_2025", "pue_change", "wue_2024", "wue_2025", "wue_change", "source_id", "source_url", "source_locator"]
    save_csv(t5[columns], RESULTS / "manuscript_table_5_aws_pue_wue.csv")


def build_table_6(register: pd.DataFrame) -> pd.DataFrame:
    mesa = pd.read_csv(RESULTS / "mesa_summary.csv").iloc[0]
    cases = pd.read_csv(READY / "source_resolved_case_evidence.csv")
    google = pd.read_csv(READY / "google_global_fy2025.csv")
    source_mix = pd.read_csv(READY / "google_reported_source_mix.csv")
    council = pd.read_csv(RESULTS / "council_bluffs_source_family_summary.csv").iloc[0]
    quincy_2020 = float(cases.loc[(cases["case_id"].eq("quincy_qwru")) & cases["metric"].eq("reuse_water_delivered"), "value"].iloc[0])
    douglas = source_mix.loc[source_mix["location"].eq("Douglas County, GA") & source_mix["year"].eq(2025)]
    reclaimed = float(douglas.loc[douglas["source_type"].eq("reclaimed wastewater"), "withdrawal_mg"].iloc[0] / douglas["withdrawal_mg"].sum())
    cb = google.loc[google["location"].eq("Council Bluffs, IA")].iloc[0]
    rows = [
        ["Phoenix-Mesa", "City of Mesa portfolio with eight reuse, recharge, exchange, and return pathways", f"{int(mesa.complete_days):,} complete daily observations after QA", "Municipal pathways are not allocated to individual facilities", "Managed-system scale comparison", "MESA_OPEN_DATA_2026"],
        ["Microsoft Quincy QWRU", "Closed reuse loop with irrigation-canal and potable-groundwater make-up", f"{quincy_2020:.2f} million gallons delivered to Microsoft in 2020; EPA annual system estimates retained separately", "Different years and accounting bases are not combined into a facility balance", "Reuse-system boundary case", "QUINCY_OPS_2020; EPA_QUINCY_REUSE"],
        ["Google Douglas County", "Operator-reported potable and reclaimed-water split", f"Reclaimed wastewater supplied {100*reclaimed:.1f}% of FY2025 withdrawal", "Facility split is distinct from Google's broader reporting-rule classification", "Facility source-portfolio interpretation", "GOOGLE_ENV_2026"],
        ["Google Council Bluffs", "Public-water infrastructure linked to the Missouri River and alluvium", f"FY2025 withdrawal {cb.withdrawal_mg:,.1f} MG and estimated consumption {cb.consumption_mg:,.1f} MG; river context uses 10,958 daily observations", "Downstream gauge does not allocate river/alluvial supply, utility capacity, water rights or ecological effects to the facility", "Source-family hydrological context", "GOOGLE_ENV_2026; GOOGLE_IOWA_DC; CB_PLANNING_2012; CB_WATER_WORKS_2024; IOWA_DNR_MISSOURI_2022; USGS_06610000"],
    ]
    frame = pd.DataFrame(rows, columns=["case", "documented_system_or_source", "observation", "interpretive_boundary", "analytical_contribution", "source_ids"])
    frame["sources_and_locators"] = frame["source_ids"].map(lambda value: source_display(register, value))
    return frame


def build_figure_source_map(register: pd.DataFrame) -> pd.DataFrame:
    rows = [
        ["Figure 1", "Conceptual synthesis; no plotted dataset", "LEI_MASANET_2022", "Cooling-water accounting and heat-rejection boundary"],
        ["Figure 2", "Thirteen candidate locations and evaluated control reaches", "PHOENIX_WRP_2021; SNWA_SOURCES_2026; SNWA_WRP_2026; SAWS_WMP_2025; DALLAS_LRWSP_2024; ATLANTA_DWM_OVERVIEW; LOUDOUN_WATER_2026; VALLEY_WATER_2026; SEATTLE_WSP_2019; DALLES_WQR_2024; QUINCY_OPS_2020; QUINCY_ECOLOGY_2019; PRINEVILLE_WMP_2023; IOWA_DNR_PWS_2026; CB_WATER_WORKS_2024; IOWA_DNR_MISSOURI_2022", "Locality coordinates and source-system eligibility; not facility or intake coordinates"],
        ["Figure 3", "U.S. Google FY2022 and FY2025 water with Aqueduct screen", "GOOGLE_ENV_2023; GOOGLE_ENV_2026; WRI_AQUEDUCT_4", "Operator-reported water and locality-centroid screening"],
        ["Figure 4", "U.S. Google FY2022-FY2025 location panel", "GOOGLE_ENV_2023; GOOGLE_ENV_2024; GOOGLE_ENV_2025; GOOGLE_ENV_2026", "Operator-reported annual location values"],
        ["Figure 5", "U.S. Google FY2025 balances and FY2022/FY2023/FY2025 source classifications", "GOOGLE_ENV_2023; GOOGLE_ENV_2024; GOOGLE_ENV_2026", "Operator-reported water balance and documented reporting rule"],
        ["Figure 6", "Modeled cooling demand divided by observed source-component flow", "LEI_MASANET_2022; ENERGYPLUS_TMY3_ATLANTA; ENERGYPLUS_TMY3_SEATTLE; ENERGYPLUS_TMY3_CHICAGO; ATLANTA_DWM_OVERVIEW; SEATTLE_WSP_2019; CB_WATER_WORKS_2024; USGS_02336000; USGS_12117500; USGS_06610000", "Standardized source-component screen; not facility impact"],
        ["Figure 7", "Meta U.S. facility water and total-facility electricity", "META_EDI_2024; META_EDI_2025", "Derived intensity is not WUE"],
        ["Figure 8", "Mesa managed pathways, U.S. facility scale comparison, and Council Bluffs river context", "MESA_OPEN_DATA_2026; GOOGLE_ENV_2026; META_EDI_2025; CB_PLANNING_2012; CB_WATER_WORKS_2024; IOWA_DNR_MISSOURI_2022; USGS_06610000", "Municipal and source-family context only"],
        ["Figure 9", "Google FY2025 global accounting comparison", "GOOGLE_ENV_2026", "Accounting comparison only; no cross-country hydrological comparison"],
    ]
    frame = pd.DataFrame(rows, columns=["figure", "plotted_evidence", "source_ids", "scientific_boundary"])
    frame["sources_and_locators"] = frame["source_ids"].map(lambda value: source_display(register, value))
    return frame


def build_manuscript_data_map() -> pd.DataFrame:
    rows = [
        ["Figure 3", "figures/Figure_03/figure_03_google_panel.csv", "83 U.S. location-years; FY2022 and FY2025 plotted"],
        ["Figure 4", "figures/Figure_04/figure_04_google_panel.csv", "83 U.S. location-years, FY2022-FY2025"],
        ["Figure 5", "figures/Figure_05/figure_05_google_balance.csv; figures/Figure_05/figure_05_source_boundary.csv", "26 FY2025 balances and documented source classes"],
        ["Figure 6", "figures/Figure_06/figure_06_daily_pressure.csv; figures/Figure_06/figure_06_volume_pressure.csv", "65,748 daily scenario records and 72 monthly summaries"],
        ["Figure 7", "figures/Figure_07/figure_07_meta_panel.csv", "70 U.S. facility-years; 51 consecutive changes calculated by figure code"],
        ["Figure 8", "figures/Figure_08/figure_08_mesa_monthly.csv; figures/Figure_08/figure_08_system_scale.csv; figures/Figure_08/figure_08_council_bluffs.csv", "800 Mesa pathway-month rows, 5,407 scale observations, and 10,958 Council Bluffs flow days"],
        ["Figure 9", "figures/Figure_09/figure_09_google_accounting_context.csv", "40 named FY2025 locations"],
        ["Table 1", "results/manuscript_table_1_source_systems.csv", "13 evidence-gated candidate locations"],
        ["Table 2", "results/manuscript_table_2_cooling_architectures.csv", "Five cooling-boundary cases"],
        ["Table 3", "results/manuscript_table_3_source_component_results.csv", "Three source components by two heat-rejection architectures"],
        ["Table 4", "results/manuscript_table_4_flow_regime_descriptors.csv", "Three USGS station records"],
        ["Table 5", "results/manuscript_table_5_aws_pue_wue.csv", "Four matched U.S. AWS regions"],
        ["Table 6", "results/manuscript_table_6_managed_system_cases.csv", "Four managed-system and source-portfolio cases"],
    ]
    return pd.DataFrame(rows, columns=["manuscript_item", "dataset_files", "records_used"])


def build_manuscript_value_source_map(register: pd.DataFrame) -> pd.DataFrame:
    """Create an explicit row-level bridge from Tables 1-6 to the source register."""
    locator = register.set_index("source_id")["source_locator"].to_dict()
    rows: list[dict[str, str]] = []

    def add(table: int, row_key: str, fields: str, status: str, source_ids: str, calculation: str, script: str) -> None:
        identifiers = [item.strip() for item in source_ids.split(";") if item.strip()]
        missing = [item for item in identifiers if item not in locator]
        if missing:
            raise ValueError(f"Unregistered table source IDs: {missing}")
        rows.append({
            "table": f"Table {table}",
            "row_key": row_key,
            "reported_or_derived_fields": fields,
            "value_status": status,
            "source_ids": "; ".join(identifiers),
            "source_locators": " | ".join(f"{item}: {locator[item]}" for item in identifiers),
            "calculation_or_boundary": calculation,
            "analysis_script": script,
        })

    table1 = pd.read_csv(RESULTS / "manuscript_table_1_source_systems.csv")
    for row in table1.itertuples(index=False):
        add(1, row.candidate_location, "documented supply system and gauge relationship", "institutionally documented plus bounded study interpretation", row.evidence_source_ids, "No facility allocation is inferred from the utility portfolio.", "03_build_tables_and_metadata.py")

    table2 = pd.read_csv(RESULTS / "manuscript_table_2_cooling_architectures.csv")
    for index, row in enumerate(table2.itertuples(index=False), start=1):
        add(2, f"architecture {index}: {row.heat_rejection}", "cooling architecture and direct-water boundary", row.value_status, row.model_source_id, "Parameterized only where the table states Hourly model.", "03_build_tables_and_metadata.py")

    table3 = pd.read_csv(RESULTS / "manuscript_table_3_source_component_results.csv")
    for row in table3.itertuples(index=False):
        add(3, f"{row.location_and_source_component} / {row.architecture_label}", "source fraction, mean consumption, p50, p95 and maximum pressure", "modeled and study-derived", row.source_basis, "C = P_ref*24*WUE_C/1000; pressure = 100*s*C/Q.", "01_prepare_analysis_data.py; 02_run_statistical_analysis.py")

    table4 = pd.read_csv(RESULTS / "manuscript_table_4_flow_regime_descriptors.csv", dtype={"usgs_station": str})
    for row in table4.itertuples(index=False):
        add(4, row.location_and_source_component, "daily records, Qmean, Q10, B and p10 DAF", "observed flow plus study-derived descriptors", row.source_id, "B = 1-Q10/Qmean; DAF = Qmean/Q10.", "02_run_statistical_analysis.py")

    table5 = pd.read_csv(RESULTS / "manuscript_table_5_aws_pue_wue.csv")
    for row in table5.itertuples(index=False):
        add(5, row.location, "FY2024/FY2025 PUE and WUE; annual changes", "operator-reported levels and study-derived differences", row.source_id, "Change = FY2025-FY2024; only matched regions retained.", "01_prepare_analysis_data.py")

    table6 = pd.read_csv(RESULTS / "manuscript_table_6_managed_system_cases.csv")
    for row in table6.itertuples(index=False):
        add(6, row.case, "documented system, observation and interpretive boundary", "reported and/or quality-controlled as stated in row", row.source_ids, row.interpretive_boundary, "01_prepare_analysis_data.py; 02_run_statistical_analysis.py; 03_build_tables_and_metadata.py")
    return pd.DataFrame(rows)


DESCRIPTION = {
    "source_id": "Stable identifier linking a value to metadata/source_register.csv.",
    "source_url": "Primary public URL for the source.",
    "source_locator": "Printed page, table, station, dataset identifier, or webpage section containing the value.",
    "source_ids": "Semicolon-separated source identifiers resolving to metadata/source_register.csv.",
    "sources_and_locators": "Human-readable source citations with report pages, stations, datasets, or webpage sections.",
    "evidence_sources": "Human-readable institutional evidence sources and exact locators for the row.",
    "manuscript_item": "Figure or table number in the manuscript.",
    "dataset_files": "Released machine-readable files used to construct the manuscript item.",
    "records_used": "Analytical subset or observation count represented by the manuscript item.",
    "location": "Operator-reported location or analytical location identifier.",
    "location_label": "Display label for the analytical location.",
    "year": "Fiscal or calendar year as reported by the source.",
    "withdrawal_mg": "Operator-reported annual water withdrawal in million U.S. gallons.",
    "discharge_mg": "Operator-reported annual discharge in million U.S. gallons.",
    "consumption_mg": "Operator-reported estimated annual consumption in million U.S. gallons.",
    "consumptive_fraction": "Consumption divided by withdrawal.",
    "balance_derived_consumption_mg": "Withdrawal minus discharge in million U.S. gallons.",
    "balance_error_mg": "Reported consumption minus withdrawal-plus-discharge balance in million U.S. gallons.",
    "bws_score": "Aqueduct 4.0 baseline-water-stress score used only for screening.",
    "bws_label": "Aqueduct 4.0 categorical baseline-water-stress label.",
    "electricity_mwh": "Operator-reported annual total-facility electricity in megawatt-hours.",
    "withdrawal_ml": "Operator-reported annual water withdrawal in megaliters.",
    "withdrawal_intensity_l_per_total_kwh": "Study-derived withdrawal divided by total-facility electricity; not WUE.",
    "pue_2024": "Operator-reported FY2024 power usage effectiveness.",
    "pue_2025": "Operator-reported FY2025 power usage effectiveness.",
    "wue_2024": "Operator-reported FY2024 water usage effectiveness in liters withdrawn per IT kWh.",
    "wue_2025": "Operator-reported FY2025 water usage effectiveness in liters withdrawn per IT kWh.",
    "station_id": "Eight-digit USGS station identifier.",
    "date": "Observation date.",
    "discharge_cfs": "USGS daily mean discharge in cubic feet per second.",
    "discharge_m3s": "Daily mean discharge converted to cubic meters per second.",
    "discharge_ML_day": "Daily mean discharge converted to megaliters per day.",
    "architecture_id": "Cooling-architecture scenario identifier.",
    "month": "Calendar month or month-start date, depending on dataset.",
    "withdrawal_wue_l_per_kwh": "Modeled direct withdrawal WUE in liters per IT kWh.",
    "consumption_wue_l_per_kwh": "Modeled direct consumptive WUE in liters per IT kWh.",
    "consumption_ml_day": "Standardized direct cooling consumption in megaliters per day.",
    "source_fraction": "Documented or declared fraction assigned to the screened source component.",
    "source_relative_pressure_pct": "100 times source-attributed modeled consumption divided by observed component flow.",
    "beneficial_reuse_mgd": "Sum of Mesa pathways classified as beneficial reuse in million gallons per day.",
    "total_system_flow_mgd": "Sum of complete-day Mesa pathway values in million gallons per day.",
    "beneficial_fraction": "Beneficial-reuse pathway flow divided by total system pathway flow.",
    "metric": "Metric name as reported in a curated evidence record.",
    "value": "Reported numeric value retained on its original basis.",
    "unit": "Unit supplied by the source or declared conversion.",
    "value_status": "Whether a value is reported, estimated, modeled, or study-derived.",
    "interpretation": "Permitted interpretation and boundary for the record.",
}

UNIT = {
    "withdrawal_mg": "million U.S. gallons/year", "discharge_mg": "million U.S. gallons/year",
    "consumption_mg": "million U.S. gallons/year", "balance_derived_consumption_mg": "million U.S. gallons/year",
    "balance_error_mg": "million U.S. gallons/year", "electricity_mwh": "MWh/year",
    "withdrawal_ml": "ML/year", "withdrawal_intensity_l_per_total_kwh": "L/total-facility kWh",
    "wue_2024": "L/IT kWh", "wue_2025": "L/IT kWh", "discharge_cfs": "ft3/s",
    "discharge_m3s": "m3/s", "discharge_ML_day": "ML/day", "withdrawal_wue_l_per_kwh": "L/IT kWh",
    "consumption_wue_l_per_kwh": "L/IT kWh", "consumption_ml_day": "ML/day",
    "source_relative_pressure_pct": "%", "beneficial_reuse_mgd": "million U.S. gallons/day",
    "total_system_flow_mgd": "million U.S. gallons/day", "beneficial_fraction": "fraction",
}


def build_dataset_catalog_and_dictionary() -> None:
    catalog = []
    dictionary = []
    candidates = (
        sorted((ROOT / "data" / "input").rglob("*.csv"))
        + sorted(READY.glob("*.csv"))
        + sorted(RESULTS.glob("*.csv"))
        + sorted((ROOT / "figures").glob("Figure_*/figure_*.csv"))
    )
    for path in candidates:
        frame = pd.read_csv(path, nrows=20)
        relative = path.relative_to(ROOT).as_posix()
        full = pd.read_csv(path, usecols=[frame.columns[0]])
        catalog.append({
            "dataset_file": relative,
            "stage": relative.split("/")[1] if relative.startswith("data/") else ("figure-ready" if relative.startswith("figures/") else "result"),
            "rows": len(full),
            "columns": len(frame.columns),
            "sha256": sha256(path),
            "purpose": "Canonical input" if "/input/" in relative else ("Analysis-ready table" if "/analysis_ready/" in relative else ("Exact source-linked plotting data" if relative.startswith("figures/") else "Reproduced result or manuscript table")),
        })
        for column in frame.columns:
            dictionary.append({
                "dataset_file": relative,
                "column": column,
                "description": DESCRIPTION.get(column, "Field retained from the cited source or created by the declared analysis; see README and source register."),
                "unit_or_format": UNIT.get(column, "text, count, fraction, or source-defined; see column description"),
                "provenance_link": "Use source_id/source_url/source_locator fields in this dataset or metadata/source_register.csv.",
            })
    save_csv(pd.DataFrame(catalog), METADATA / "dataset_catalog.csv")
    save_csv(pd.DataFrame(dictionary), METADATA / "variable_dictionary.csv")


def main() -> None:
    METADATA.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    register = source_register()
    save_csv(register, METADATA / "source_register.csv")
    save_csv(build_table_1(register), RESULTS / "manuscript_table_1_source_systems.csv")
    save_csv(build_table_2(), RESULTS / "manuscript_table_2_cooling_architectures.csv")
    build_numeric_tables()
    save_csv(build_table_6(register), RESULTS / "manuscript_table_6_managed_system_cases.csv")
    known_issues = pd.DataFrame([
        {
            "issue_id": "GOOGLE_FY2024_OTHER_CONSUMPTION",
            "source_id": "GOOGLE_ENV_2025",
            "record": "Other data center locations, FY2024 aggregate",
            "published_values": "withdrawal 828.9 MG; discharge 60.0 MG; consumption 786.9 MG",
            "independent_check": "withdrawal minus discharge = 768.9 MG",
            "treatment": "Preserve the published value; exclude the aggregate row from named-location consumption figures and headline calculations.",
            "status": "documented source inconsistency; no silent correction",
        },
        {
            "issue_id": "AWS_2025_ARCHIVE_VERSION",
            "source_id": "AWS_CLOUD_2026",
            "record": "FY2025 regional PUE/WUE values",
            "published_values": "17 regions displayed on archived official webpage",
            "independent_check": "Four U.S. matched rows reproduced exactly from the archived official webpage table",
            "treatment": "Retain retrieval date and archive hash; do not silently refresh the webpage.",
            "status": "passed with source-version warning",
        },
    ])
    save_csv(known_issues, METADATA / "known_source_issues.csv")
    save_csv(build_manuscript_value_source_map(register), METADATA / "manuscript_value_source_map.csv")
    save_csv(build_figure_source_map(register), METADATA / "figure_source_map.csv")
    save_csv(build_manuscript_data_map(), METADATA / "manuscript_data_map.csv")
    build_dataset_catalog_and_dictionary()
    summary = {
        "sources_registered": len(register),
        "manuscript_tables": 6,
        "manuscript_figures": 9,
        "known_source_issues": len(known_issues),
        "status": "PASS",
    }
    (QA / "metadata_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
