"""
GLP-1 Environmental Impact Project
src/uncertainty.py

Monte Carlo simulation for uncertainty analysis on Risk Quotient values.

Approach:
    Key parameters (excretion fraction, WWTP removal rate) are not single
    fixed values — they vary across individuals, facilities, and studies.
    This module samples those parameters from realistic distributions
    (10,000 iterations per drug/scenario) to produce confidence intervals
    around each RQ estimate.

Parameter distributions:
    - excretion_fraction: Beta distribution fitted to literature range
    - wwtp_removal:       Beta distribution fitted to reported removal ranges
    - Both constrained to [0, 1] by nature of Beta distribution

Outputs:
    - data/glp1_monte_carlo_raw.csv     : Full simulation results
    - data/glp1_uncertainty_summary.csv : RQ percentiles per drug/scenario
"""

import pandas as pd
import numpy as np
import os
from src.pipeline import build_drug_properties, SCENARIOS

# ── Simulation settings ────────────────────────────────────────────────────────
N_ITERATIONS = 10_000
RANDOM_SEED  = 42

US_POPULATION                    = 335_000_000
WWTP_CONNECTION_RATE             = 0.76
WASTEWATER_FLOW_L_PER_PERSON_DAY = 200


# ══════════════════════════════════════════════════════════════════════════════
def _beta_params(mean: float, uncertainty: float) -> tuple:
    """
    Convert a mean and uncertainty (half-width) into Beta distribution
    alpha and beta parameters using method of moments.

    Args:
        mean:        Central estimate (0–1)
        uncertainty: Approximate ± range (e.g. 0.10 for ±10%)

    Returns:
        (alpha, beta) parameters for np.random.beta
    """
    variance = (uncertainty / 2) ** 2
    # Clamp to avoid degenerate distributions
    variance = min(variance, mean * (1 - mean) * 0.99)
    alpha = mean * ((mean * (1 - mean) / variance) - 1)
    beta  = (1 - mean) * ((mean * (1 - mean) / variance) - 1)
    return max(alpha, 0.5), max(beta, 0.5)


# ══════════════════════════════════════════════════════════════════════════════
def run_monte_carlo(
    n_iterations: int = N_ITERATIONS,
    seed: int = RANDOM_SEED,
    output_dir: str = "data"
) -> tuple:
    """
    Runs Monte Carlo simulation across all drugs and scenarios.

    For each iteration, excretion_fraction and wwtp_removal are sampled
    from Beta distributions centred on their literature-derived means,
    with uncertainty widths based on reported ranges in the literature.

    Args:
        n_iterations: Number of simulation iterations (default 10,000)
        seed:         Random seed for reproducibility
        output_dir:   Directory to save output CSVs

    Returns:
        (raw_df, summary_df) — full simulation results and percentile summary
    """
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    drug_props       = build_drug_properties()
    served_pop       = US_POPULATION * WWTP_CONNECTION_RATE
    records          = []
    summary_records  = []

    # Uncertainty widths (± range) sourced from literature review
    # Semaglutide excretion: Drucker (2022) reports 60–80% → ±0.10
    # WWTP removal: Kling (2022) reports 20–40% → ±0.10
    # Liraglutide excretion: Knudsen (2010) reports 50–70% → ±0.10
    # Dulaglutide/Exenatide: limited data → wider uncertainty ±0.15
    EXCRETION_UNCERTAINTY = {
        "Semaglutide": 0.10,
        "Liraglutide": 0.10,
        "Dulaglutide": 0.15,
        "Exenatide":   0.15,
    }
    WWTP_UNCERTAINTY = {
        "Semaglutide": 0.10,
        "Liraglutide": 0.10,
        "Dulaglutide": 0.12,
        "Exenatide":   0.10,
    }

    for _, drug in drug_props.iterrows():
        exc_unc  = EXCRETION_UNCERTAINTY.get(drug["drug"], 0.12)
        wwtp_unc = WWTP_UNCERTAINTY.get(drug["drug"], 0.10)

        # Fit Beta distributions
        exc_a,  exc_b  = _beta_params(drug["excretion_fraction"], exc_unc)
        wwtp_a, wwtp_b = _beta_params(drug["wwtp_removal"],       wwtp_unc)

        # Sample parameters
        exc_samples  = np.random.beta(exc_a,  exc_b,  n_iterations)
        wwtp_samples = np.random.beta(wwtp_a, wwtp_b, n_iterations)

        for scenario_key, scenario in SCENARIOS.items():
            n_users      = served_pop * scenario["uptake_fraction"]
            total_flow_L = n_users * WASTEWATER_FLOW_L_PER_PERSON_DAY

            # Vectorised MEC and RQ calculation across all iterations
            daily_load_mg     = drug["ddd_mg"] * exc_samples * n_users
            mec_influent_ng_L = (daily_load_mg * 1e6) / total_flow_L
            mec_effluent_ng_L = mec_influent_ng_L * (1 - wwtp_samples)
            rq_samples        = mec_effluent_ng_L / drug["pnec_ng_L"]

            # Store raw results (sampled down to 500 rows for CSV size)
            sample_idx = np.random.choice(n_iterations, size=500, replace=False)
            for i in sample_idx:
                records.append({
                    "drug":               drug["drug"],
                    "route":              drug["route"],
                    "scenario":           scenario_key,
                    "excretion_fraction": round(exc_samples[i],  4),
                    "wwtp_removal":       round(wwtp_samples[i], 4),
                    "mec_effluent_ng_L":  round(mec_effluent_ng_L[i], 4),
                    "risk_quotient":      round(rq_samples[i], 3),
                })

            # Percentile summary
            summary_records.append({
                "drug":            drug["drug"],
                "route":           drug["route"],
                "scenario":        scenario_key,
                "scenario_label":  scenario["label"],
                "rq_p5":           round(float(np.percentile(rq_samples, 5)),  3),
                "rq_p25":          round(float(np.percentile(rq_samples, 25)), 3),
                "rq_p50":          round(float(np.percentile(rq_samples, 50)), 3),
                "rq_p75":          round(float(np.percentile(rq_samples, 75)), 3),
                "rq_p95":          round(float(np.percentile(rq_samples, 95)), 3),
                "rq_mean":         round(float(np.mean(rq_samples)),           3),
                "rq_std":          round(float(np.std(rq_samples)),            3),
                "prob_exceeds_1":  round(float(np.mean(rq_samples >= 1.0)),    4),
                "prob_exceeds_01": round(float(np.mean(rq_samples >= 0.1)),    4),
            })

    raw_df     = pd.DataFrame(records)
    summary_df = pd.DataFrame(summary_records)

    raw_df.to_csv(    f"{output_dir}/glp1_monte_carlo_raw.csv",     index=False)
    summary_df.to_csv(f"{output_dir}/glp1_uncertainty_summary.csv", index=False)

    print(f"✓ Monte Carlo complete ({n_iterations:,} iterations, seed={seed})")
    print(f"✓ Raw results saved     → {output_dir}/glp1_monte_carlo_raw.csv")
    print(f"✓ Summary saved         → {output_dir}/glp1_uncertainty_summary.csv")

    return raw_df, summary_df


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    raw, summary = run_monte_carlo()

    print("\n── Uncertainty Summary (Baseline Scenario) ───────────────────────")
    baseline = summary[summary["scenario"] == "baseline"][[
        "drug", "route", "rq_p5", "rq_p50", "rq_p95", "prob_exceeds_1"
    ]]
    print(baseline.to_string(index=False))
    print("\nprob_exceeds_1 = probability that RQ > 1 across all simulations")
