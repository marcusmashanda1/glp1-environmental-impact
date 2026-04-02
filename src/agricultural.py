"""
GLP-1 Environmental Impact Project
src/agricultural.py

Agricultural demand change modeling — downstream effects of GLP-1-driven
dietary shifts on US food production, land use, and fertilizer demand.

Approach:
    GLP-1 receptor agonists reduce caloric intake by ~27% on average
    (Wilding et al. 2021). At population scale, this translates to
    measurable reductions in food demand — particularly for high-calorie,
    high-margin foods (red meat, processed foods, sugary beverages) which
    clinical trials show are disproportionately reduced.

    Dietary composition shifts documented in GLP-1 trials:
        - Red meat consumption: -35% (Blundell et al. 2017)
        - Processed/ultra-processed food: -40% (Batterham et al. 2021)
        - Sugar-sweetened beverages: -45% (van Can et al. 2014)
        - Fruits and vegetables: -10% (slight reduction, less dramatic)
        - Total caloric intake: -27% central estimate

    These dietary shifts cascade into:
        1. Reduced agricultural land demand (fewer calories to grow)
        2. Reduced fertilizer application (less cropland needed)
        3. Reduced livestock methane emissions (less beef/pork demand)
        4. Reduced irrigation water demand
        5. Reduced nitrogen runoff into waterways (key env. metric)

    Environmental relevance:
        Agricultural nitrogen runoff is the leading cause of freshwater
        eutrophication in the US (EPA 2022). A reduction in fertilizer
        demand directly reduces hypoxic zone risk in receiving waters —
        connecting this model back to the core water quality theme.

Key parameters:
    - US per-capita caloric intake: 2,200 kcal/day (USDA 2023)
    - US cropland: 893 million acres (USDA NASS 2022)
    - US fertilizer N application: 12.5 million tonnes N/year (USDA ERS)
    - Beef N fertilizer intensity: 32 kg N / kg beef protein produced
    - Crop N fertilizer intensity: 0.058 kg N / 1,000 kcal crop calories
    - Irrigation intensity: 580 L / 1,000 kcal (blended US average)
    - Methane (beef): 300 kg CO2e / 1,000 kcal beef consumed

Outputs:
    - data/glp1_agricultural_demand.csv : Annual agricultural impact by scenario
"""

import pandas as pd
import numpy as np
import os
from src.pipeline import SCENARIOS

# ── Constants ──────────────────────────────────────────────────────────────────
US_POPULATION     = 335_000_000
WWTP_CONNECTION_RATE = 0.76

# Dietary parameters
KCAL_PER_PERSON_DAY = 2_200

# Caloric reduction by food category for GLP-1 users (fraction of intake)
# Sources: Blundell (2017), Batterham (2021), van Can (2014)
CATEGORY_REDUCTIONS = {
    "red_meat":          0.35,
    "processed_food":    0.40,
    "sugary_beverages":  0.45,
    "dairy":             0.20,
    "grains":            0.25,
    "fruits_vegetables": 0.10,
}

# Share of total calories from each category (USDA dietary data)
CATEGORY_CALORIC_SHARE = {
    "red_meat":          0.14,
    "processed_food":    0.30,
    "sugary_beverages":  0.07,
    "dairy":             0.10,
    "grains":            0.22,
    "fruits_vegetables": 0.08,
    # remaining ~9% = oils, misc — not modelled
}

# Environmental intensity factors per 1,000 kcal of each food category
# Sources: Poore & Nemecek (2018) Science; USDA ERS; EPA
ENV_INTENSITY = {
    # N fertilizer (kg N per 1,000 kcal)
    "N_fertilizer_kg_per_1000kcal": {
        "red_meat":          0.320,   # high — livestock feed crops
        "processed_food":    0.085,
        "sugary_beverages":  0.040,
        "dairy":             0.180,
        "grains":            0.058,
        "fruits_vegetables": 0.035,
    },
    # Irrigation water (litres per 1,000 kcal)
    "irrigation_L_per_1000kcal": {
        "red_meat":          1_800,
        "processed_food":    420,
        "sugary_beverages":  250,
        "dairy":             900,
        "grains":            380,
        "fruits_vegetables": 520,
    },
    # GHG emissions (kg CO2e per 1,000 kcal)
    "ghg_kgCO2e_per_1000kcal": {
        "red_meat":          300,
        "processed_food":    45,
        "sugary_beverages":  18,
        "dairy":             90,
        "grains":            12,
        "fruits_vegetables": 20,
    },
    # Land use (m2 per 1,000 kcal)
    "land_m2_per_1000kcal": {
        "red_meat":          150,
        "processed_food":    18,
        "sugary_beverages":  8,
        "dairy":             55,
        "grains":            14,
        "fruits_vegetables": 25,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
def run_agricultural_model(output_dir: str = "data") -> pd.DataFrame:
    """
    Calculates annual reductions in agricultural resource demand
    attributable to GLP-1-driven dietary shifts under each scenario.

    Returns:
        DataFrame with annual impact reductions by scenario,
        food category, and environmental metric
    """
    os.makedirs(output_dir, exist_ok=True)
    records = []

    for scenario_key, scenario in SCENARIOS.items():
        n_users = US_POPULATION * scenario["uptake_fraction"]

        for category, cal_reduction in CATEGORY_REDUCTIONS.items():
            cal_share     = CATEGORY_CALORIC_SHARE.get(category, 0)

            # Baseline daily kcal from this category per user
            baseline_kcal_user_day = KCAL_PER_PERSON_DAY * cal_share

            # Reduced kcal per user per day
            reduced_kcal_user_day  = baseline_kcal_user_day * (1 - cal_reduction)
            delta_kcal_user_day    = baseline_kcal_user_day - reduced_kcal_user_day

            # Total kcal reduction across all users per year
            total_delta_kcal_year  = delta_kcal_user_day * n_users * 365

            # Convert to environmental impacts
            for metric, intensities in ENV_INTENSITY.items():
                intensity = intensities.get(category, 0)

                # Reduction in this metric per year
                # intensity is per 1,000 kcal → divide kcal by 1,000
                reduction_per_year = (total_delta_kcal_year / 1_000) * intensity

                records.append({
                    "scenario":          scenario_key,
                    "scenario_label":    scenario["label"],
                    "food_category":     category,
                    "n_users":           int(n_users),
                    "uptake_fraction":   scenario["uptake_fraction"],
                    "cal_reduction_pct": round(cal_reduction * 100, 0),
                    "metric":            metric,
                    "reduction_per_year": round(reduction_per_year, 1),
                })

    df = pd.DataFrame(records)
    df.to_csv(f"{output_dir}/glp1_agricultural_demand.csv", index=False)
    print(f"✓ Agricultural model saved → {output_dir}/glp1_agricultural_demand.csv")
    return df


# ══════════════════════════════════════════════════════════════════════════════
def summarise_by_metric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates across food categories to get total annual reduction
    per environmental metric and scenario.
    """
    return df.groupby(["scenario", "scenario_label", "metric"])[
        "reduction_per_year"
    ].sum().reset_index().rename(columns={"reduction_per_year": "total_reduction_per_year"})


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df      = run_agricultural_model()
    summary = summarise_by_metric(df)

    print("\n── Total Annual Reductions by Metric and Scenario ───────────────")
    pivot = summary.pivot_table(
        index="metric",
        columns="scenario_label",
        values="total_reduction_per_year"
    ).round(0)
    print(pivot.to_string())

    print("\n── Interpretation ────────────────────────────────────────────────")
    metrics_labels = {
        "N_fertilizer_kg_per_1000kcal":  ("N Fertilizer",   "kg N/year"),
        "irrigation_L_per_1000kcal":     ("Irrigation",     "litres/year"),
        "ghg_kgCO2e_per_1000kcal":       ("GHG Emissions",  "kg CO2e/year"),
        "land_m2_per_1000kcal":          ("Land Use",       "m2/year"),
    }
    for metric_key, (label, unit) in metrics_labels.items():
        row = summary[
            (summary["metric"] == metric_key) &
            (summary["scenario"] == "high")
        ]
        if not row.empty:
            val = row["total_reduction_per_year"].values[0]
            if val > 1e9:
                print(f"  {label}: {val/1e9:,.2f} billion {unit} (high adoption)")
            elif val > 1e6:
                print(f"  {label}: {val/1e6:,.2f} million {unit} (high adoption)")
            else:
                print(f"  {label}: {val:,.0f} {unit} (high adoption)")
