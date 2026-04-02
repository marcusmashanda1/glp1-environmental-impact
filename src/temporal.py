"""
GLP-1 Environmental Impact Project
src/temporal.py

Temporal modeling of GLP-1 environmental risk from 2024 to 2030.

Approach:
    Models year-by-year growth in GLP-1 prescription uptake based on
    market projections, and calculates how RQ evolves over time for
    each drug. Three adoption curves are modelled:
        - Conservative: linear growth from 2.5% → 8%
        - Baseline:     logistic (S-curve) growth from 2.5% → 15%
        - High:         logistic growth from 2.5% → 25%

    The logistic curve reflects real adoption dynamics — slow initial
    uptake, rapid acceleration as supply constraints ease and coverage
    expands, then plateau as the addressable population saturates.

    Market projection basis:
        - 2024 baseline: ~2.5% US adults on GLP-1 (IQVIA 2024)
        - 2030 high:     ~24% US adults projected (Goldman Sachs 2023)

Outputs:
    - data/glp1_temporal_projections.csv : RQ by year, drug, and scenario
"""

import pandas as pd
import numpy as np
import os
from src.pipeline import build_drug_properties

# ── Constants ──────────────────────────────────────────────────────────────────
YEARS                            = list(range(2024, 2031))
US_POPULATION                    = 335_000_000
WWTP_CONNECTION_RATE             = 0.76
WASTEWATER_FLOW_L_PER_PERSON_DAY = 200


# ══════════════════════════════════════════════════════════════════════════════
def _logistic(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
    """
    Logistic (S-curve) growth function.

    Args:
        t:   Array of time values (years)
        L:   Carrying capacity (maximum uptake fraction)
        k:   Growth rate
        t0:  Inflection point (year of fastest growth)

    Returns:
        Array of uptake fractions at each time point
    """
    return L / (1 + np.exp(-k * (t - t0)))


# ══════════════════════════════════════════════════════════════════════════════
def build_adoption_curves() -> pd.DataFrame:
    """
    Builds year-by-year adoption curves for three scenarios.

    Conservative: linear growth, supply-constrained market
    Baseline:     logistic growth, moderate market penetration
    High:         logistic growth, aggressive adoption (GLP-1 becomes
                  standard of care for obesity and T2D)

    Returns:
        DataFrame with columns: year, scenario, uptake_fraction
    """
    years_arr = np.array(YEARS)
    records   = []

    # Conservative — linear from 2.5% to 8% over 6 years
    conservative = np.linspace(0.025, 0.08, len(YEARS))

    # Baseline — logistic, inflection ~2026, plateau ~15%
    # Anchored: 2024 = 2.5%, 2030 = ~15%
    baseline_raw = _logistic(years_arr, L=0.175, k=0.9, t0=2026.5)
    # Normalise to anchor 2024 at 0.025
    baseline = baseline_raw - baseline_raw[0] + 0.025
    baseline = np.clip(baseline, 0.025, 0.175)

    # High — logistic, faster growth, plateau ~24%
    high_raw = _logistic(years_arr, L=0.28, k=1.1, t0=2026.0)
    high     = high_raw - high_raw[0] + 0.025
    high     = np.clip(high, 0.025, 0.28)

    for i, year in enumerate(YEARS):
        records.append({"year": year, "scenario": "conservative",
                        "scenario_label": "Conservative", "uptake_fraction": round(conservative[i], 4)})
        records.append({"year": year, "scenario": "baseline",
                        "scenario_label": "Baseline",     "uptake_fraction": round(float(baseline[i]), 4)})
        records.append({"year": year, "scenario": "high",
                        "scenario_label": "High Adoption","uptake_fraction": round(float(high[i]),     4)})

    return pd.DataFrame(records)


# ══════════════════════════════════════════════════════════════════════════════
def run_temporal_model(output_dir: str = "data") -> pd.DataFrame:
    """
    Calculates RQ for each drug, year, and adoption scenario.

    Args:
        output_dir: Directory to save output CSV

    Returns:
        DataFrame with temporal RQ projections
    """
    os.makedirs(output_dir, exist_ok=True)

    drug_props    = build_drug_properties()
    adoption      = build_adoption_curves()
    served_pop    = US_POPULATION * WWTP_CONNECTION_RATE
    records       = []

    for _, drug in drug_props.iterrows():
        for _, row in adoption.iterrows():
            n_users           = served_pop * row["uptake_fraction"]
            total_flow_L      = n_users * WASTEWATER_FLOW_L_PER_PERSON_DAY
            daily_load_mg     = drug["ddd_mg"] * drug["excretion_fraction"] * n_users
            mec_influent_ng_L = (daily_load_mg * 1e6) / total_flow_L
            mec_effluent_ng_L = mec_influent_ng_L * (1 - drug["wwtp_removal"])
            rq                = mec_effluent_ng_L / drug["pnec_ng_L"]

            # Total daily mass load — varies with n_users (unlike MEC)
            total_mass_kg = (daily_load_mg * (1 - drug["wwtp_removal"])) / 1e6

            records.append({
                "year":               row["year"],
                "drug":               drug["drug"],
                "route":              drug["route"],
                "scenario":           row["scenario"],
                "scenario_label":     row["scenario_label"],
                "uptake_fraction":    row["uptake_fraction"],
                "n_users":            int(n_users),
                "daily_load_mg":      round(daily_load_mg, 2),
                "total_mass_effluent_kg": round(total_mass_kg, 4),
                "mec_effluent_ng_L":  round(mec_effluent_ng_L, 4),
                "risk_quotient":      round(rq, 3),
                "log10_rq":           round(float(np.log10(rq)), 4),
            })

    df = pd.DataFrame(records)
    df.to_csv(f"{output_dir}/glp1_temporal_projections.csv", index=False)

    print(f"✓ Temporal projections saved → {output_dir}/glp1_temporal_projections.csv")
    return df


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = run_temporal_model()

    print("\n── Adoption Curve Summary ────────────────────────────────────────")
    adoption = build_adoption_curves()
    pivot = adoption.pivot_table(index="year", columns="scenario", values="uptake_fraction")
    print((pivot * 100).round(1).to_string())
    print("(% of WWTP-served population actively dosing)")

    print("\n── Semaglutide (oral) RQ Trajectory ─────────────────────────────")
    sema = df[(df["drug"] == "Semaglutide") & (df["route"] == "oral")]
    pivot_rq = sema.pivot_table(index="year", columns="scenario", values="risk_quotient")
    print(pivot_rq.round(0).to_string())

    print("\n── Total Semaglutide Mass in Effluent (kg/day) ───────────────────")
    pivot_mass = sema.pivot_table(index="year", columns="scenario", values="total_mass_effluent_kg")
    print(pivot_mass.round(2).to_string())
