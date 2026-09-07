#!/usr/bin/env python3
"""Reproduce every numerical result reported in the manuscript.

The analyses preserve incompatible denominators as separate evidence streams:
Google location water accounting, Meta total-facility electricity and water,
AWS PUE/WUE, standardized cooling-source pressure, and managed-system cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
READY = ROOT / "data" / "analysis_ready"
RESULTS = ROOT / "results"
QA = ROOT / "qa"
SEED = 20260905
MILLION_M3_PER_MILLION_US_GALLONS = 0.003785411784


def save_csv(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(RESULTS / name, index=False, lineterminator="\n")


def spearman(left: object, right: object) -> float:
    left_rank = pd.Series(np.asarray(left)).rank(method="average").to_numpy(float)
    right_rank = pd.Series(np.asarray(right)).rank(method="average").to_numpy(float)
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def row_bootstrap_ci(frame: pd.DataFrame, left: str, right: str, iterations: int = 10_000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    values = frame[[left, right]].dropna().to_numpy(float)
    estimates = []
    for _ in range(iterations):
        sample = values[rng.integers(0, len(values), len(values))]
        estimate = spearman(sample[:, 0], sample[:, 1])
        if np.isfinite(estimate):
            estimates.append(estimate)
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def cluster_bootstrap_ci(changes: pd.DataFrame, iterations: int = 10_000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    sites = changes["location"].unique()
    grouped = {site: changes.loc[changes["location"].eq(site)] for site in sites}
    estimates = []
    for _ in range(iterations):
        sampled_sites = rng.choice(sites, size=len(sites), replace=True)
        sample = pd.concat([grouped[site] for site in sampled_sites], ignore_index=True)
        estimate = spearman(sample["electricity_change_fraction"], sample["withdrawal_change_fraction"])
        if np.isfinite(estimate):
            estimates.append(estimate)
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def consecutive_meta_changes(panel: pd.DataFrame) -> pd.DataFrame:
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


def near_equal_volume_pairs(summary: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    records = summary.loc[
        summary["mean_consumption_ml_day"].gt(0) & summary["pressure_p95_pct"].gt(0)
    ].reset_index(drop=True)
    rows = []
    for left_index, left in records.iterrows():
        for right_index in range(left_index + 1, len(records)):
            right = records.iloc[right_index]
            if left["location"] == right["location"]:
                continue
            difference = abs(left["mean_consumption_ml_day"] - right["mean_consumption_ml_day"]) / max(
                left["mean_consumption_ml_day"], right["mean_consumption_ml_day"]
            )
            if difference <= 0.03:
                ratio = max(left["pressure_p95_pct"], right["pressure_p95_pct"]) / min(
                    left["pressure_p95_pct"], right["pressure_p95_pct"]
                )
                rows.append({
                    "first_location": left["location_label"],
                    "first_architecture": left["architecture_label"],
                    "first_month": int(left["month"]),
                    "first_consumption_ml_day": float(left["mean_consumption_ml_day"]),
                    "first_pressure_p95_pct": float(left["pressure_p95_pct"]),
                    "second_location": right["location_label"],
                    "second_architecture": right["architecture_label"],
                    "second_month": int(right["month"]),
                    "second_consumption_ml_day": float(right["mean_consumption_ml_day"]),
                    "second_pressure_p95_pct": float(right["pressure_p95_pct"]),
                    "consumption_difference_pct": float(100 * difference),
                    "pressure_ratio": float(ratio),
                    "hydrology_source_ids": f"{left['hydrology_source_id']}; {right['hydrology_source_id']}",
                    "model_source_id": "LEI_MASANET_2022",
                })
    pairs = pd.DataFrame(rows).sort_values("pressure_ratio", ascending=False).reset_index(drop=True)
    quantiles = pairs["pressure_ratio"].quantile([0.25, 0.50, 0.75])
    maximum = pairs.iloc[0]
    summary_values = {
        "eligibility_rule": "different locations; positive p95 pressure; 100*abs(C_i-C_j)/max(C_i,C_j) <= 3",
        "eligible_pairs": int(len(pairs)),
        "pressure_ratio_min": float(pairs["pressure_ratio"].min()),
        "pressure_ratio_q25": float(quantiles.loc[0.25]),
        "pressure_ratio_median": float(quantiles.loc[0.50]),
        "pressure_ratio_q75": float(quantiles.loc[0.75]),
        "pressure_ratio_max": float(pairs["pressure_ratio"].max()),
        "maximum_pair": maximum.to_dict(),
        "interpretive_status": "descriptive pair distribution; rows are not statistically independent",
    }
    return pairs, summary_values


def analyze_google() -> tuple[dict, pd.DataFrame]:
    us = pd.read_csv(READY / "google_us_location_year.csv")
    global_2025 = pd.read_csv(READY / "google_global_fy2025.csv")
    latest = us.loc[us["year"].eq(2025)].copy()
    rho = spearman(latest["withdrawal_mg"], latest["bws_score"])
    ci = row_bootstrap_ci(latest, "withdrawal_mg", "bws_score")
    yearly = us.groupby("year", as_index=False).agg(
        locations=("location", "nunique"),
        withdrawal_mg=("withdrawal_mg", "sum"),
        discharge_mg=("discharge_mg", "sum"),
        consumption_mg=("consumption_mg", "sum"),
    )
    for metric in ("withdrawal_mg", "consumption_mg"):
        yearly[f"{metric}_share_bws_ge_3"] = yearly["year"].map(
            lambda year: float(
                us.loc[us["year"].eq(year) & us["bws_score"].ge(3), metric].sum()
                / us.loc[us["year"].eq(year), metric].sum()
            )
        )
    yearly["source_ids"] = yearly["year"].map(
        {2022: "GOOGLE_ENV_2023", 2023: "GOOGLE_ENV_2024", 2024: "GOOGLE_ENV_2025", 2025: "GOOGLE_ENV_2026"}
    )
    yearly["screen_source_id"] = "WRI_AQUEDUCT_4"
    save_csv(yearly, "google_us_annual_summary.csv")

    wide = us.pivot(index="location", columns="year", values="withdrawal_mg")
    paired_2425 = wide.dropna(subset=[2024, 2025])
    paired_2225 = wide.dropna(subset=[2022, 2025])
    net_change = float(wide[2025].sum() - wide[2022].sum())
    continuing_change = float((paired_2225[2025] - paired_2225[2022]).sum())

    global_2025["scope"] = np.where(global_2025["name_0"].eq("United States"), "U.S. named locations", "Non-U.S. named locations")
    global_rows = []
    for scope, subset in [
        ("All named locations", global_2025),
        ("U.S. named locations", global_2025.loc[global_2025["scope"].eq("U.S. named locations")]),
        ("Non-U.S. named locations", global_2025.loc[global_2025["scope"].eq("Non-U.S. named locations")]),
    ]:
        withdrawal = float(subset["withdrawal_mg"].sum())
        discharge = float(subset["discharge_mg"].sum())
        consumption = float(subset["consumption_mg"].sum())
        global_rows.append({
            "scope": scope,
            "locations": len(subset),
            "withdrawal_mg": withdrawal,
            "discharge_mg": discharge,
            "estimated_consumption_mg": consumption,
            "estimated_consumption_fraction": consumption / withdrawal,
            "source_id": "GOOGLE_ENV_2026",
            "source_locator": "printed p. 97",
        })
    global_summary = pd.DataFrame(global_rows)
    save_csv(global_summary, "google_global_fy2025_accounting_summary.csv")

    results = {
        "location_year_observations": len(us),
        "locations": us["location"].nunique(),
        "fy2025_withdrawal_mg": float(latest["withdrawal_mg"].sum()),
        "fy2025_consumption_mg": float(latest["consumption_mg"].sum()),
        "fy2025_withdrawal_consumed_fraction": float(latest["consumption_mg"].sum() / latest["withdrawal_mg"].sum()),
        "fy2025_withdrawal_stress_spearman_rho": rho,
        "fy2025_withdrawal_stress_bootstrap_ci_95": list(ci),
        "continuing_locations_2024_2025": len(paired_2425),
        "locations_increasing_2024_2025": int((paired_2425[2025] > paired_2425[2024]).sum()),
        "fy2022_2025_net_reported_growth_mg": net_change,
        "continuing_location_share_of_growth": continuing_change / net_change,
        "global_fy2025_named_locations": len(global_2025),
        "global_fy2025_named_withdrawal_mg": float(global_2025["withdrawal_mg"].sum()),
        "global_fy2025_named_consumption_mg": float(global_2025["consumption_mg"].sum()),
    }
    return results, global_summary


def analyze_source_pressure() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    daily = pd.read_csv(READY / "source_component_daily_pressure.csv")
    monthly = pd.read_csv(READY / "source_component_monthly_pressure.csv")
    flow = daily[["location", "location_label", "date", "discharge_ML_day", "source_id", "source_url"]].drop_duplicates()
    if flow.duplicated(["location", "date"]).any():
        raise ValueError("Duplicate location-date keys remain in daily flow")
    flow_regime = flow.groupby(["location", "location_label", "source_id", "source_url"], as_index=False).agg(
        daily_records=("date", "count"),
        q_mean_ml_day=("discharge_ML_day", "mean"),
        q_drought_p10_ml_day=("discharge_ML_day", lambda values: values.quantile(0.10)),
    )
    flow_regime["baseline_scarcity_b"] = 1 - flow_regime["q_drought_p10_ml_day"] / flow_regime["q_mean_ml_day"]
    flow_regime["drought_amplification_factor"] = flow_regime["q_mean_ml_day"] / flow_regime["q_drought_p10_ml_day"]
    flow_regime["identity_error"] = abs(
        flow_regime["drought_amplification_factor"] - 1 / (1 - flow_regime["baseline_scarcity_b"])
    )
    save_csv(flow_regime, "table_4_flow_regime_descriptors.csv")

    source_summary = daily.groupby(
        ["location", "location_label", "architecture_id", "source_fraction", "source_fraction_status", "source_id", "utility_source_id", "method_source_id"],
        as_index=False,
    ).agg(
        mean_consumption_ml_day=("consumption_ml_day", "mean"),
        pressure_p50_pct=("source_relative_pressure_pct", "median"),
        pressure_p95_pct=("source_relative_pressure_pct", lambda values: values.quantile(0.95)),
        pressure_max_pct=("source_relative_pressure_pct", "max"),
    )
    source_summary["architecture_label"] = source_summary["architecture_id"].map({
        "climate_responsive_hybrid": "Climate-responsive hybrid",
        "water_cooled_evaporative": "Water-cooled evaporative",
    })
    save_csv(source_summary, "table_3_source_component_results.csv")
    pairs, pair_summary = near_equal_volume_pairs(monthly)
    save_csv(pairs, "near_equal_volume_pair_distribution.csv")
    results = {
        "daily_architecture_records": len(daily),
        "source_components": daily["location"].nunique(),
        "maximum_pressure_pct": float(daily["source_relative_pressure_pct"].max()),
        "near_equal_volume_pairs": pair_summary,
        "flow_regime_descriptors": flow_regime[["location_label", "baseline_scarcity_b", "drought_amplification_factor"]].to_dict(orient="records"),
    }
    return results, source_summary, flow_regime


def analyze_meta() -> tuple[dict, pd.DataFrame]:
    meta = pd.read_csv(READY / "meta_us_facility_year.csv")
    check = 1000 * meta["withdrawal_ml"] / meta["electricity_mwh"]
    if not np.allclose(meta["withdrawal_intensity_l_per_total_kwh"], check, equal_nan=True):
        raise ValueError("Meta derived intensity does not reproduce")
    changes = consecutive_meta_changes(meta)
    changes["derived_status"] = "within-site consecutive annual change"
    save_csv(changes, "meta_us_consecutive_changes.csv")
    rho = spearman(changes["electricity_change_fraction"], changes["withdrawal_change_fraction"])
    ci = cluster_bootstrap_ci(changes)
    positive = meta.loc[meta["withdrawal_intensity_l_per_total_kwh"].gt(0)]
    return {
        "facility_year_observations": len(meta),
        "facilities": meta["location"].nunique(),
        "positive_intensity_min_l_per_total_kwh": float(positive["withdrawal_intensity_l_per_total_kwh"].min()),
        "positive_intensity_max_l_per_total_kwh": float(positive["withdrawal_intensity_l_per_total_kwh"].max()),
        "consecutive_changes": len(changes),
        "change_sites": changes["location"].nunique(),
        "change_spearman_rho": rho,
        "site_cluster_bootstrap_ci_95": list(ci),
    }, changes


def analyze_managed_systems() -> tuple[dict, dict]:
    mesa = pd.read_csv(READY / "mesa_daily_pathways_qc.csv")
    mesa_summary = {
        "complete_days": len(mesa),
        "median_total_pathway_mgd": float(mesa["total_system_flow_mgd"].median()),
        "median_beneficial_pathway_mgd": float(mesa["beneficial_reuse_mgd"].median()),
        "mean_beneficial_fraction": float(mesa["beneficial_fraction"].mean()),
        "source_id": "MESA_OPEN_DATA_2026",
    }
    save_csv(pd.DataFrame([mesa_summary]), "mesa_summary.csv")

    google = pd.read_csv(READY / "google_global_fy2025.csv")
    row = google.loc[google["location"].eq("Council Bluffs, IA")].iloc[0]
    flow = pd.read_csv(READY / "usgs_daily_flow_three_components.csv")
    flow = flow.loc[flow["location"].eq("Council_Bluffs_IA")].copy()
    withdrawal_ml_day = row["withdrawal_mg"] * MILLION_M3_PER_MILLION_US_GALLONS * 1000 / 365
    consumption_ml_day = row["consumption_mg"] * MILLION_M3_PER_MILLION_US_GALLONS * 1000 / 365
    withdrawal_ratio = 100 * withdrawal_ml_day / flow["discharge_ML_day"]
    consumption_ratio = 100 * consumption_ml_day / flow["discharge_ML_day"]
    council = {
        "daily_records": len(flow),
        "withdrawal_ml_day": float(withdrawal_ml_day),
        "estimated_consumption_ml_day": float(consumption_ml_day),
        "withdrawal_to_river_flow_p50_pct": float(withdrawal_ratio.quantile(0.50)),
        "withdrawal_to_river_flow_p95_pct": float(withdrawal_ratio.quantile(0.95)),
        "consumption_to_river_flow_p50_pct": float(consumption_ratio.quantile(0.50)),
        "consumption_to_river_flow_p95_pct": float(consumption_ratio.quantile(0.95)),
        "operator_source_id": "GOOGLE_ENV_2026",
        "hydrology_source_id": "USGS_06610000",
        "source_chain_ids": "GOOGLE_IOWA_DC; CB_PLANNING_2012; CB_WATER_WORKS_2024; IOWA_DNR_MISSOURI_2022",
        "interpretive_status": "source-family river context only; not facility impact, allocation, or available supply",
    }
    save_csv(pd.DataFrame([council]), "council_bluffs_source_family_summary.csv")
    return mesa_summary, council


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    google, global_summary = analyze_google()
    source_pressure, table3, table4 = analyze_source_pressure()
    meta, meta_changes = analyze_meta()
    aws = pd.read_csv(READY / "aws_us_matched_regions.csv")
    save_csv(aws, "table_5_aws_pue_wue.csv")
    mesa, council = analyze_managed_systems()
    source_mix = pd.read_csv(READY / "google_reported_source_mix.csv")
    douglas = source_mix.loc[
        source_mix["location"].eq("Douglas County, GA")
        & source_mix["year"].eq(2025)
        & source_mix["source_type"].eq("reclaimed wastewater")
    ]
    total = source_mix.loc[source_mix["location"].eq("Douglas County, GA") & source_mix["year"].eq(2025), "withdrawal_mg"].sum()
    reclaimed_share = float(douglas["withdrawal_mg"].iloc[0] / total)

    results = {
        "google": google | {"douglas_county_fy2025_reclaimed_share": reclaimed_share},
        "source_timing": source_pressure,
        "meta": meta,
        "aws": {
            "matched_us_regions": len(aws),
            "regions_with_lower_2025_wue": int((aws["wue_2025"] < aws["wue_2024"]).sum()),
            "wue_change_min": float(aws["wue_change"].min()),
            "wue_change_max": float(aws["wue_change"].max()),
        },
        "mesa": mesa,
        "council_bluffs": council,
    }

    # Frozen assertions: any changed input or analysis result must fail loudly.
    assert google["location_year_observations"] == 83 and google["locations"] == 26
    assert abs(google["fy2025_withdrawal_mg"] - 10_807.6) < 1e-9
    assert abs(google["fy2025_consumption_mg"] - 8_446.9) < 1e-9
    assert abs(google["fy2025_withdrawal_stress_spearman_rho"] - (-0.2076)) < 1e-4
    assert google["continuing_locations_2024_2025"] == 23
    assert google["locations_increasing_2024_2025"] == 20
    assert google["global_fy2025_named_locations"] == 40
    assert abs(google["global_fy2025_named_withdrawal_mg"] - 12_541.5) < 1e-9
    assert abs(google["global_fy2025_named_consumption_mg"] - 9_603.75) < 1e-9
    assert source_pressure["daily_architecture_records"] == 65_748
    pairs = source_pressure["near_equal_volume_pairs"]
    assert pairs["eligible_pairs"] == 282
    assert abs(pairs["pressure_ratio_median"] - 25.142842) < 1e-6
    assert abs(pairs["pressure_ratio_max"] - 87.5902473) < 1e-3
    expected_flow = {
        "Atlanta": (0.587959, 2.426943),
        "Council Bluffs": (0.558189, 2.263410),
        "Seattle": (0.569717, 2.324052),
    }
    for row in table4.itertuples(index=False):
        expected_b, expected_daf = expected_flow[row.location_label]
        assert abs(row.baseline_scarcity_b - expected_b) < 1e-6
        assert abs(row.drought_amplification_factor - expected_daf) < 1e-6
    assert meta["consecutive_changes"] == 51 and abs(meta["change_spearman_rho"] - 0.3775) < 1e-4
    assert len(aws) == 4 and (aws["wue_2025"] < aws["wue_2024"]).all()
    assert mesa["complete_days"] == 2_676
    assert abs(mesa["mean_beneficial_fraction"] - 0.8776347171) < 1e-10
    assert council["daily_records"] == 10_958

    (RESULTS / "headline_statistics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("[PASS] all manuscript statistics reproduced from source-linked CSV inputs")


if __name__ == "__main__":
    main()
