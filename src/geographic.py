"""
GLP-1 Environmental Impact Project
src/geographic.py

Geographic concentration modeling — RQ variation by US city.

Approach:
    MEC is sensitive to the ratio of drug load to wastewater flow volume.
    At the national level this ratio is constant, but at the city level it
    varies based on:
        - City population (determines absolute drug load)
        - WWTP daily flow capacity (determines dilution volume)
        - Per-capita flow rate (varies by infrastructure age and climate)

    A higher drug load per unit of WWTP flow = higher MEC = higher RQ.
    Smaller cities with older or undersized WWTPs may face disproportionate
    risk compared to large cities with high-capacity modern plants.

    This module models RQ for 20 representative US cities across the
    population spectrum, using publicly available WWTP flow data
    (EPA Clean Watersheds Needs Survey, 2022) and Census population data.

    Focus compound: Semaglutide (oral) — highest RQ, primary risk driver.

Outputs:
    - data/glp1_geographic_concentration.csv : City-level RQ by scenario
"""

import pandas as pd
import numpy as np
import os
from src.pipeline import SCENARIOS

# ── Constants ──────────────────────────────────────────────────────────────────
WWTP_CONNECTION_RATE = 0.76


# ══════════════════════════════════════════════════════════════════════════════
def build_city_data() -> pd.DataFrame:
    """
    Returns a DataFrame of US cities with population and WWTP flow data.

    WWTP flow data sourced from:
        - EPA Clean Watersheds Needs Survey (CWNS) 2022
        - Individual utility annual reports where CWNS data unavailable
    Population: US Census Bureau 2023 estimates (city proper)

    Per-capita flow varies by city — older cities (NYC, Chicago) have
    combined sewer systems with higher per-capita flows; newer Sun Belt
    cities tend to be lower.
    """
    return pd.DataFrame([
        # Large metros
        {"city": "New York, NY",       "population": 8_336_000, "wwtp_flow_MGD": 1_300, "region": "Northeast"},
        {"city": "Los Angeles, CA",    "population": 3_898_000, "wwtp_flow_MGD": 480,   "region": "West"},
        {"city": "Chicago, IL",        "population": 2_697_000, "wwtp_flow_MGD": 700,   "region": "Midwest"},
        {"city": "Houston, TX",        "population": 2_304_000, "wwtp_flow_MGD": 310,   "region": "South"},
        {"city": "Phoenix, AZ",        "population": 1_608_000, "wwtp_flow_MGD": 220,   "region": "West"},
        # Mid-size cities
        {"city": "Philadelphia, PA",   "population": 1_567_000, "wwtp_flow_MGD": 330,   "region": "Northeast"},
        {"city": "San Antonio, TX",    "population": 1_435_000, "wwtp_flow_MGD": 140,   "region": "South"},
        {"city": "San Diego, CA",      "population": 1_387_000, "wwtp_flow_MGD": 175,   "region": "West"},
        {"city": "Dallas, TX",         "population": 1_304_000, "wwtp_flow_MGD": 165,   "region": "South"},
        {"city": "Denver, CO",         "population":   715_000, "wwtp_flow_MGD": 100,   "region": "West"},
        {"city": "Seattle, WA",        "population":   749_000, "wwtp_flow_MGD": 115,   "region": "West"},
        {"city": "Boston, MA",         "population":   675_000, "wwtp_flow_MGD": 380,   "region": "Northeast"},
        # Smaller cities
        {"city": "Minneapolis, MN",    "population":   429_000, "wwtp_flow_MGD": 70,    "region": "Midwest"},
        {"city": "Tampa, FL",          "population":   395_000, "wwtp_flow_MGD": 55,    "region": "South"},
        {"city": "St. Louis, MO",      "population":   301_000, "wwtp_flow_MGD": 120,   "region": "Midwest"},
        {"city": "Pittsburgh, PA",     "population":   303_000, "wwtp_flow_MGD": 90,    "region": "Northeast"},
        {"city": "Cincinnati, OH",     "population":   309_000, "wwtp_flow_MGD": 75,    "region": "Midwest"},
        # Small cities — potentially higher vulnerability
        {"city": "Boise, ID",          "population":   240_000, "wwtp_flow_MGD": 28,    "region": "West"},
        {"city": "Des Moines, IA",     "population":   215_000, "wwtp_flow_MGD": 32,    "region": "Midwest"},
        {"city": "Sioux Falls, SD",    "population":   196_000, "wwtp_flow_MGD": 22,    "region": "Midwest"},
    ])


# ══════════════════════════════════════════════════════════════════════════════
def run_geographic_model(output_dir: str = "data") -> pd.DataFrame:
    """
    Calculates city-level semaglutide MEC and RQ for each adoption scenario.

    Key difference from national model:
        - Uses actual reported WWTP flow (MGD) instead of
          per-capita flow × population estimate
        - This captures real infrastructure capacity constraints

    Args:
        output_dir: Directory to save output CSV

    Returns:
        DataFrame with city-level RQ values by scenario
    """
    os.makedirs(output_dir, exist_ok=True)

    cities = build_city_data()
    records = []

    # Semaglutide oral parameters (primary risk compound)
    ddd_mg             = 10.5
    excretion_fraction = 0.70
    wwtp_removal       = 0.30
    pnec_ng_L          = 0.084

    # MGD to L/day conversion: 1 MGD = 3,785,412 L/day
    MGD_TO_L_PER_DAY = 3_785_412

    for _, city in cities.iterrows():
        served_pop   = city["population"] * WWTP_CONNECTION_RATE
        flow_L_day   = city["wwtp_flow_MGD"] * MGD_TO_L_PER_DAY

        # Per-capita flow for this city (L/person/day) — for reference
        per_capita_flow = flow_L_day / city["population"]

        for scenario_key, scenario in SCENARIOS.items():
            n_users       = served_pop * scenario["uptake_fraction"]
            daily_load_mg = ddd_mg * excretion_fraction * n_users

            mec_influent_ng_L = (daily_load_mg * 1e6) / flow_L_day
            mec_effluent_ng_L = mec_influent_ng_L * (1 - wwtp_removal)
            rq                = mec_effluent_ng_L / pnec_ng_L

            records.append({
                "city":                city["city"],
                "region":              city["region"],
                "population":          city["population"],
                "wwtp_flow_MGD":       city["wwtp_flow_MGD"],
                "per_capita_flow_L":   round(per_capita_flow, 1),
                "scenario":            scenario_key,
                "scenario_label":      scenario["label"],
                "uptake_fraction":     scenario["uptake_fraction"],
                "n_users":             int(n_users),
                "daily_load_mg":       round(daily_load_mg, 2),
                "mec_effluent_ng_L":   round(mec_effluent_ng_L, 4),
                "risk_quotient":       round(rq, 3),
                "log10_rq":            round(float(np.log10(rq)), 4),
                "risk_flag":           "HIGH" if rq >= 1 else ("MODERATE" if rq >= 0.1 else "LOW"),
            })

    df = pd.DataFrame(records)
    df.to_csv(f"{output_dir}/glp1_geographic_concentration.csv", index=False)
    print(f"✓ Geographic model saved → {output_dir}/glp1_geographic_concentration.csv")
    return df


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = run_geographic_model()

    print("\n── Baseline Scenario: RQ by City (Semaglutide oral) ─────────────")
    baseline = df[df["scenario"] == "baseline"][[
        "city", "population", "wwtp_flow_MGD", "per_capita_flow_L",
        "mec_effluent_ng_L", "risk_quotient"
    ]].sort_values("risk_quotient", ascending=False)
    print(baseline.to_string(index=False))

    print("\n── Top 5 Highest Risk Cities (Baseline) ─────────────────────────")
    print(baseline.head(5)[["city", "risk_quotient"]].to_string(index=False))

    print("\n── Top 5 Lowest Risk Cities (Baseline) ──────────────────────────")
    print(baseline.tail(5)[["city", "risk_quotient"]].to_string(index=False))
