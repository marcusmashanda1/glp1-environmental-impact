"""
GLP-1 Environmental Impact Project
src/pipeline.py

Importable pipeline module for building GLP-1 environmental risk datasets.
Called directly or imported into Jupyter notebooks for Day 3 modeling.
"""

import pandas as pd
import numpy as np
import os


# ── Constants ──────────────────────────────────────────────────────────────────
US_POPULATION = 335_000_000
WWTP_CONNECTION_RATE = 0.76
WASTEWATER_FLOW_L_PER_PERSON_DAY = 200  # L/person/day, US EPA average

SCENARIOS = {
    "conservative": {"label": "Conservative (2024 ~2.5%)", "uptake_fraction": 0.025},
    "baseline":     {"label": "Baseline (2027 ~7%)",        "uptake_fraction": 0.070},
    "high":         {"label": "High Adoption (2030 ~15%)",  "uptake_fraction": 0.150},
}


# ══════════════════════════════════════════════════════════════════════════════
def build_drug_properties() -> pd.DataFrame:
    """
    Returns a DataFrame of GLP-1 drug properties.
    Sources:
        - WHO ATC/DDD Index (A10BJ), updated 2026-01-20
        - Drucker (2022) - semaglutide pharmacokinetics
        - Brinch et al. (2020) - semaglutide PNEC
        - Kling et al. (2022) - WWTP removal efficiency
        - Knudsen et al. (2010) - liraglutide excretion
    """
    return pd.DataFrame([
        {
            "drug":               "Semaglutide",
            "atc_code":           "A10BJ06",
            "route":              "oral",
            "ddd_mg":             10.5,
            "mw_g_mol":           4113.6,
            "excretion_fraction": 0.70,
            "wwtp_removal":       0.30,
            "pnec_ng_L":          0.084,
            "notes":              "Ozempic/Wegovy; primary focus compound"
        },
        {
            "drug":               "Semaglutide",
            "atc_code":           "A10BJ06",
            "route":              "injectable",
            "ddd_mg":             0.11,
            "mw_g_mol":           4113.6,
            "excretion_fraction": 0.70,
            "wwtp_removal":       0.30,
            "pnec_ng_L":          0.084,
            "notes":              "Injectable form; lower DDD, same excretion profile"
        },
        {
            "drug":               "Liraglutide",
            "atc_code":           "A10BJ02",
            "route":              "injectable",
            "ddd_mg":             1.5,
            "mw_g_mol":           3751.2,
            "excretion_fraction": 0.60,
            "wwtp_removal":       0.25,
            "pnec_ng_L":          1.0,
            "notes":              "Victoza/Saxenda; declining market share"
        },
        {
            "drug":               "Dulaglutide",
            "atc_code":           "A10BJ05",
            "route":              "injectable",
            "ddd_mg":             0.16,
            "mw_g_mol":           59700.0,
            "excretion_fraction": 0.50,
            "wwtp_removal":       0.40,
            "pnec_ng_L":          10.0,
            "notes":              "Trulicity; large MW likely reduces persistence"
        },
        {
            "drug":               "Exenatide",
            "atc_code":           "A10BJ01",
            "route":              "injectable",
            "ddd_mg":             0.015,
            "mw_g_mol":           4186.6,
            "excretion_fraction": 0.65,
            "wwtp_removal":       0.30,
            "pnec_ng_L":          5.0,
            "notes":              "Byetta/Bydureon; first GLP-1 to market, declining use"
        },
    ])


# ══════════════════════════════════════════════════════════════════════════════
def calculate_daily_loads(
    drug_properties: pd.DataFrame,
    scenarios: dict = SCENARIOS,
    served_population: float = US_POPULATION * WWTP_CONNECTION_RATE,
    flow_L_per_person: float = WASTEWATER_FLOW_L_PER_PERSON_DAY,
) -> pd.DataFrame:
    """
    Calculates daily GLP-1 mass loads and effluent MECs for each
    drug-route-scenario combination.

    MEC formula:
        mec_influent (ng/L) = (DDD_mg × excretion_fraction × N_users × 1e6)
                               ÷ (N_users × flow_L_per_person)
        mec_effluent (ng/L) = mec_influent × (1 - wwtp_removal)
        RQ                  = mec_effluent ÷ pnec_ng_L

    Args:
        drug_properties:    Output of build_drug_properties()
        scenarios:          Dict of scenario definitions (see SCENARIOS constant)
        served_population:  Population connected to WWTPs
        flow_L_per_person:  Per-capita daily wastewater flow (L/day)

    Returns:
        DataFrame with daily loads, MECs, and risk quotients
    """
    records = []

    for _, drug in drug_properties.iterrows():
        for scenario_key, scenario in scenarios.items():

            n_users = served_population * scenario["uptake_fraction"]

            daily_load_mg = drug["ddd_mg"] * drug["excretion_fraction"] * n_users
            daily_load_kg = daily_load_mg / 1e6

            total_flow_L      = n_users * flow_L_per_person
            mec_influent_ng_L = (daily_load_mg * 1e6) / total_flow_L
            mec_effluent_ng_L = mec_influent_ng_L * (1 - drug["wwtp_removal"])

            rq = mec_effluent_ng_L / drug["pnec_ng_L"]

            records.append({
                "drug":               drug["drug"],
                "route":              drug["route"],
                "atc_code":           drug["atc_code"],
                "scenario":           scenario_key,
                "scenario_label":     scenario["label"],
                "n_users":            int(n_users),
                "daily_load_mg":      round(daily_load_mg, 2),
                "daily_load_kg":      round(daily_load_kg, 6),
                "mec_influent_ng_L":  round(mec_influent_ng_L, 4),
                "mec_effluent_ng_L":  round(mec_effluent_ng_L, 4),
                "pnec_ng_L":          drug["pnec_ng_L"],
                "risk_quotient":      round(rq, 3),
                "risk_flag":          "HIGH" if rq >= 1 else ("MODERATE" if rq >= 0.1 else "LOW"),
            })

    return pd.DataFrame(records)


# ══════════════════════════════════════════════════════════════════════════════
def build_mec_inputs(daily_loads: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a clean, modeling-ready subset of the daily loads DataFrame.
    Used as the primary input for Day 3 risk modeling.
    """
    return daily_loads[[
        "drug", "route", "scenario", "scenario_label",
        "n_users", "mec_influent_ng_L", "mec_effluent_ng_L",
        "pnec_ng_L", "risk_quotient", "risk_flag"
    ]].copy()


# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(output_dir: str = "data") -> dict:
    """
    Runs the full Day 2 pipeline and saves all output CSVs.

    Args:
        output_dir: Directory to save output CSV files

    Returns:
        Dict with keys: drug_properties, daily_loads, mec_inputs (DataFrames)
    """
    os.makedirs(output_dir, exist_ok=True)

    drug_properties = build_drug_properties()
    daily_loads     = calculate_daily_loads(drug_properties)
    mec_inputs      = build_mec_inputs(daily_loads)

    drug_properties.to_csv(f"{output_dir}/glp1_drug_properties.csv", index=False)
    daily_loads.to_csv(f"{output_dir}/glp1_daily_loads.csv",         index=False)
    mec_inputs.to_csv(f"{output_dir}/glp1_mec_inputs.csv",           index=False)

    print(f"✓ glp1_drug_properties.csv saved → {output_dir}/")
    print(f"✓ glp1_daily_loads.csv saved     → {output_dir}/")
    print(f"✓ glp1_mec_inputs.csv saved      → {output_dir}/")

    return {
        "drug_properties": drug_properties,
        "daily_loads":     daily_loads,
        "mec_inputs":      mec_inputs,
    }


# ── Run directly if called as a script ────────────────────────────────────────
if __name__ == "__main__":
    results = run_pipeline()

    print("\n── Risk Quotient Summary ─────────────────────────────────────────")
    summary = results["daily_loads"].pivot_table(
        index=["drug", "route"],
        columns="scenario",
        values="risk_quotient"
    ).round(3)
    print(summary.to_string())
