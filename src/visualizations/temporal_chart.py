"""
GLP-1 Environmental Impact Project
src/visualizations/temporal_chart.py

Publication-quality temporal projection chart.
Shows total semaglutide mass load in WWTP effluent (kg/day) from 2024-2030
across three adoption scenarios with uncertainty envelope.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.temporal import run_temporal_model, build_adoption_curves

os.makedirs("figures", exist_ok=True)


def plot_temporal_chart(save_path: str = "figures/temporal_projection.png") -> None:
    """
    Generates and saves the temporal mass load projection chart.
    """
    # ── Data ──────────────────────────────────────────────────────────────────
    df = run_temporal_model()

    # Focus on semaglutide oral — primary risk compound
    sema = df[
        (df["drug"] == "Semaglutide") &
        (df["route"] == "oral")
    ].copy()

    conservative = sema[sema["scenario"] == "conservative"].sort_values("year")
    baseline     = sema[sema["scenario"] == "baseline"].sort_values("year")
    high         = sema[sema["scenario"] == "high"].sort_values("year")

    years = baseline["year"].values

    # ── Figure ─────────────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#0f1117")
    for ax in [ax1, ax2]:
        ax.set_facecolor("#1a1d26")

    # Colours
    c_conservative = "#3498db"
    c_baseline     = "#2ecc71"
    c_high         = "#e74c3c"
    c_fill         = "#e74c3c"

    # ── LEFT PANEL: Total mass load (kg/day) ──────────────────────────────────
    ax1.fill_between(
        years,
        conservative["total_mass_effluent_kg"].values,
        high["total_mass_effluent_kg"].values,
        alpha=0.15, color=c_fill, label="Scenario range"
    )
    ax1.plot(years, conservative["total_mass_effluent_kg"].values,
             color=c_conservative, linewidth=2, linestyle="--",
             marker="o", markersize=5, label="Conservative (2.5%→8%)")
    ax1.plot(years, baseline["total_mass_effluent_kg"].values,
             color=c_baseline, linewidth=2.5,
             marker="o", markersize=5, label="Baseline (2.5%→17%)")
    ax1.plot(years, high["total_mass_effluent_kg"].values,
             color=c_high, linewidth=2,
             marker="o", markersize=5, label="High Adoption (2.5%→27%)")

    # Annotate 2024 and 2030 values
    ax1.annotate(f"{conservative['total_mass_effluent_kg'].iloc[0]:.1f} kg/day",
                 xy=(2024, conservative["total_mass_effluent_kg"].iloc[0]),
                 xytext=(2024.1, conservative["total_mass_effluent_kg"].iloc[0] * 1.15),
                 color="white", fontsize=8)
    ax1.annotate(f"{high['total_mass_effluent_kg'].iloc[-1]:.0f} kg/day",
                 xy=(2030, high["total_mass_effluent_kg"].iloc[-1]),
                 xytext=(2029.2, high["total_mass_effluent_kg"].iloc[-1] * 1.05),
                 color=c_high, fontsize=8, fontweight="bold")

    ax1.set_xlabel("Year", color="white", fontsize=10)
    ax1.set_ylabel("Semaglutide Mass in Effluent (kg/day)", color="white", fontsize=10)
    ax1.set_title("Total Semaglutide Mass Load\nin WWTP Effluent (kg/day)",
                  color="white", fontsize=11, fontweight="bold")
    ax1.tick_params(colors="white")
    ax1.set_xticks(years)
    ax1.set_xticklabels(years, color="white", fontsize=9)
    ax1.legend(frameon=False, labelcolor="white", fontsize=9)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#444")
    ax1.yaxis.label.set_color("white")
    ax1.grid(axis="y", color="#333", linewidth=0.5)

    # ── RIGHT PANEL: Adoption curves (% population) ───────────────────────────
    adoption = build_adoption_curves()
    for scenario, color, label in [
        ("conservative", c_conservative, "Conservative"),
        ("baseline",     c_baseline,     "Baseline"),
        ("high",         c_high,         "High Adoption"),
    ]:
        s = adoption[adoption["scenario"] == scenario].sort_values("year")
        ax2.plot(s["year"].values, s["uptake_fraction"].values * 100,
                 color=color, linewidth=2.5, marker="o", markersize=5, label=label)

    ax2.fill_between(
        adoption[adoption["scenario"] == "conservative"].sort_values("year")["year"].values,
        adoption[adoption["scenario"] == "conservative"].sort_values("year")["uptake_fraction"].values * 100,
        adoption[adoption["scenario"] == "high"].sort_values("year")["uptake_fraction"].values * 100,
        alpha=0.12, color=c_fill
    )

    ax2.set_xlabel("Year", color="white", fontsize=10)
    ax2.set_ylabel("GLP-1 Uptake (% of WWTP-served population)", color="white", fontsize=10)
    ax2.set_title("GLP-1 Adoption Curves\nby Scenario",
                  color="white", fontsize=11, fontweight="bold")
    ax2.tick_params(colors="white")
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, color="white", fontsize=9)
    ax2.legend(frameon=False, labelcolor="white", fontsize=9)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#444")
    ax2.yaxis.label.set_color("white")
    ax2.grid(axis="y", color="#333", linewidth=0.5)

    # ── Main title ─────────────────────────────────────────────────────────────
    fig.suptitle(
        "GLP-1 Environmental Burden 2024–2030: Semaglutide Mass Load Projections\n"
        "Left: Total kg/day discharged into waterways  |  Right: Underlying adoption assumptions",
        color="white", fontsize=11, fontweight="bold", y=1.02
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"✓ Temporal projection chart saved → {save_path}")


if __name__ == "__main__":
    plot_temporal_chart()
