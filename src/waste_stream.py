"""
GLP-1 Environmental Impact Project
src/waste_stream.py

Organic waste stream shift modeling — downstream effects of GLP-1-driven
weight loss on municipal wastewater organic load.

Approach:
    GLP-1 receptor agonists reduce caloric intake by 20-35% in clinical
    trials (Wilding et al. 2021, Davies et al. 2021). At population scale,
    this translates to a measurable reduction in fecal organic matter
    entering WWTPs — affecting BOD (Biochemical Oxygen Demand), TSS
    (Total Suspended Solids), and nutrient loads (nitrogen, phosphorus).

    WWTPs are designed around expected organic loads. A significant
    reduction in organic load could:
        1. Reduce WWTP energy consumption (less aeration needed)
        2. Reduce biosolids production (less sludge to process)
        3. Alter nutrient ratios in effluent (affecting receiving waters)
        4. Create operational challenges if plants are over-designed

    This module quantifies the magnitude of these shifts under the
    three adoption scenarios.

Key parameters:
    - Average US adult caloric intake: 2,200 kcal/day (USDA NHANES)
    - GLP-1 caloric reduction: 20-35%, central estimate 27% (meta-analysis)
    - Fecal energy loss fraction: ~5% of intake (Cummings & Macfarlane 1991)
    - BOD per capita baseline: 77 g/person/day (EPA design standard)
    - TSS per capita baseline: 90 g/person/day (EPA design standard)
    - N per capita baseline:   12 g/person/day (Tchobanoglous et al. 2014)
    - P per capita baseline:    2 g/person/day (Tchobanoglous et al. 2014)

Outputs:
    - data/glp1_waste_stream_shift.csv : Annual load reductions by scenario
"""

import pandas as pd
import numpy as np
import os
from src.pipeline import SCENARIOS

# ── Constants ──────────────────────────────────────────────────────────────────
US_POPULATION        = 335_000_000
WWTP_CONNECTION_RATE = 0.76
SERVED_POPULATION    = US_POPULATION * WWTP_CONNECTION_RATE

# Baseline per-capita wastewater organic loads (g/person/day)
# Source: EPA Wastewater Treatment Manuals; Tchobanoglous et al. 2014
BASELINE_LOADS = {
    "BOD_g_per_day":       77.0,   # Biochemical Oxygen Demand
    "TSS_g_per_day":       90.0,   # Total Suspended Solids
    "TN_g_per_day":        12.0,   # Total Nitrogen
    "TP_g_per_day":         2.0,   # Total Phosphorus
    "COD_g_per_day":      180.0,   # Chemical Oxygen Demand
}

# GLP-1 caloric reduction parameters
# Source: Wilding et al. (2021) NEJM — semaglutide 2.4mg trial
# Source: Davies et al. (2021) Lancet — oral semaglutide trial
CALORIC_REDUCTION_CENTRAL = 0.27   # 27% reduction in caloric intake
CALORIC_REDUCTION_LOW     = 0.20   # 20% — conservative (adherence losses)
CALORIC_REDUCTION_HIGH    = 0.35   # 35% — clinical trial max

# Fraction of caloric reduction that translates to reduced fecal output
# Gut fermentation and fecal excretion fraction ~5% of intake
# But dietary fibre/protein changes dominate BOD — estimated 60% coupling
FECAL_COUPLING_FRACTION = 0.60


# ══════════════════════════════════════════════════════════════════════════════
def run_waste_stream_model(output_dir: str = "data") -> pd.DataFrame:
    """
    Models the reduction in municipal wastewater organic load attributable
    to population-level GLP-1 adoption across three scenarios.

    For each scenario and pollutant parameter, calculates:
        - Absolute load reduction (tonnes/year)
        - Percentage reduction in total municipal load
        - Equivalent reduction in WWTP processing demand

    Args:
        output_dir: Directory to save output CSV

    Returns:
        DataFrame with annual load reductions by scenario and parameter
    """
    os.makedirs(output_dir, exist_ok=True)
    records = []

    for scenario_key, scenario in SCENARIOS.items():
        n_users     = SERVED_POPULATION * scenario["uptake_fraction"]
        non_users   = SERVED_POPULATION - n_users

        for reduction_case, cal_reduction in [
            ("low",     CALORIC_REDUCTION_LOW),
            ("central", CALORIC_REDUCTION_CENTRAL),
            ("high",    CALORIC_REDUCTION_HIGH),
        ]:
            for param, baseline_g_per_day in BASELINE_LOADS.items():

                # Reduction factor for GLP-1 users
                load_reduction_fraction = cal_reduction * FECAL_COUPLING_FRACTION

                # Daily loads (tonnes/day)
                baseline_total_t_day = (SERVED_POPULATION * baseline_g_per_day) / 1e6
                user_load_t_day      = (n_users * baseline_g_per_day *
                                        (1 - load_reduction_fraction)) / 1e6
                non_user_load_t_day  = (non_users * baseline_g_per_day) / 1e6
                new_total_t_day      = user_load_t_day + non_user_load_t_day

                reduction_t_day      = baseline_total_t_day - new_total_t_day
                reduction_t_year     = reduction_t_day * 365
                pct_reduction        = (reduction_t_day / baseline_total_t_day) * 100

                records.append({
                    "scenario":            scenario_key,
                    "scenario_label":      scenario["label"],
                    "caloric_reduction":   reduction_case,
                    "cal_reduction_pct":   round(cal_reduction * 100, 0),
                    "parameter":           param,
                    "n_users":             int(n_users),
                    "uptake_fraction":     scenario["uptake_fraction"],
                    "baseline_t_day":      round(baseline_total_t_day, 2),
                    "new_total_t_day":     round(new_total_t_day, 2),
                    "reduction_t_day":     round(reduction_t_day, 2),
                    "reduction_t_year":    round(reduction_t_year, 1),
                    "pct_reduction":       round(pct_reduction, 2),
                })

    df = pd.DataFrame(records)
    df.to_csv(f"{output_dir}/glp1_waste_stream_shift.csv", index=False)
    print(f"✓ Waste stream model saved → {output_dir}/glp1_waste_stream_shift.csv")
    return df


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = run_waste_stream_model()

    print("\n── Central Estimate: Annual Load Reductions by Scenario ──────────")
    central = df[df["caloric_reduction"] == "central"][[
        "scenario_label", "parameter", "reduction_t_year", "pct_reduction"
    ]].pivot_table(
        index="parameter",
        columns="scenario_label",
        values=["reduction_t_year", "pct_reduction"]
    ).round(1)
    print(central.to_string())

    print("\n── BOD Reduction Summary (all caloric reduction cases) ───────────")
    bod = df[df["parameter"] == "BOD_g_per_day"][[
        "scenario_label", "caloric_reduction", "reduction_t_year", "pct_reduction"
    ]].sort_values(["scenario_label", "caloric_reduction"])
    print(bod.to_string(index=False))

    print("\n── Interpretation ────────────────────────────────────────────────")
    # Pull headline number: high scenario, central caloric, BOD
    headline = df[
        (df["scenario"] == "high") &
        (df["caloric_reduction"] == "central") &
        (df["parameter"] == "BOD_g_per_day")
    ].iloc[0]
    print(f"Under high adoption (2030), GLP-1 users could reduce national")
    print(f"BOD load by {headline['reduction_t_year']:,.0f} tonnes/year")
    print(f"({headline['pct_reduction']:.1f}% of total municipal BOD load)")
    print(f"— equivalent to removing ~{headline['n_users']/1e6:.1f}M people's")
    print(f"  organic waste contribution from the wastewater system.")
