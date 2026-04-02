"""
GLP-1 Environmental Impact Project
src/visualizations/geographic_chart.py

Publication-quality geographic bar chart.
Shows semaglutide Risk Quotient for 20 US cities under baseline scenario,
ranked from highest to lowest risk, coloured by region.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.geographic import run_geographic_model

os.makedirs("figures", exist_ok=True)


def plot_geographic_chart(save_path: str = "figures/geographic_rq.png") -> None:
    """
    Generates and saves the geographic RQ bar chart.
    """
    # ── Data ──────────────────────────────────────────────────────────────────
    df       = run_geographic_model()
    baseline = df[df["scenario"] == "baseline"].sort_values("risk_quotient", ascending=True)

    cities       = baseline["city"].values
    rq_values    = baseline["risk_quotient"].values
    regions      = baseline["region"].values
    per_cap_flow = baseline["per_capita_flow_L"].values

    # Region colours
    region_colors = {
        "Northeast": "#3498db",
        "Midwest":   "#2ecc71",
        "South":     "#e74c3c",
        "West":      "#f39c12",
    }
    bar_colors = [region_colors[r] for r in regions]

    # ── Figure ─────────────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor("#0f1117")
    for ax in [ax1, ax2]:
        ax.set_facecolor("#1a1d26")

    # ── LEFT PANEL: RQ horizontal bar chart ───────────────────────────────────
    bars = ax1.barh(cities, rq_values, color=bar_colors, edgecolor="#333", height=0.7)

    # RQ threshold line at 1.0 (log scale so at log10(1)=0... use linear here)
    ax1.axvline(x=1, color="white", linewidth=1, linestyle="--", alpha=0.5,
                label="RQ = 1 (ecological risk threshold)")

    # Value labels on bars
    for bar, val in zip(bars, rq_values):
        ax1.text(val + 50, bar.get_y() + bar.get_height() / 2,
                 f"{val:,.0f}", va="center", color="white", fontsize=7.5)

    ax1.set_xlabel("Risk Quotient (RQ = MEC effluent / PNEC)", color="white", fontsize=10)
    ax1.set_title("Semaglutide Risk Quotient by City\nBaseline Scenario (2027, ~7% uptake)",
                  color="white", fontsize=11, fontweight="bold")
    ax1.tick_params(colors="white", labelsize=9)
    ax1.set_yticklabels(cities, color="white", fontsize=8.5)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#444")
    ax1.grid(axis="x", color="#333", linewidth=0.5)
    ax1.legend(frameon=False, labelcolor="white", fontsize=8, loc="lower right")

    # Region legend
    legend_patches = [mpatches.Patch(color=c, label=r)
                      for r, c in region_colors.items()]
    ax1.legend(handles=legend_patches, frameon=False, labelcolor="white",
               fontsize=8, loc="lower right")

    # ── RIGHT PANEL: Per-capita WWTP flow (explains the RQ variation) ─────────
    sorted_idx   = np.argsort(per_cap_flow)
    sorted_cities = cities[sorted_idx]
    sorted_flow   = per_cap_flow[sorted_idx]
    sorted_colors = [bar_colors[i] for i in sorted_idx]

    bars2 = ax2.barh(sorted_cities, sorted_flow,
                     color=sorted_colors, edgecolor="#333", height=0.7)

    # National average line
    national_avg = 200
    ax2.axvline(x=national_avg, color="white", linewidth=1,
                linestyle="--", alpha=0.5, label=f"US avg ({national_avg} L/person/day)")

    for bar, val in zip(bars2, sorted_flow):
        ax2.text(val + 10, bar.get_y() + bar.get_height() / 2,
                 f"{val:.0f} L", va="center", color="white", fontsize=7.5)

    ax2.set_xlabel("Per-Capita WWTP Flow (L/person/day)", color="white", fontsize=10)
    ax2.set_title("WWTP Flow Capacity by City\n(higher flow = more dilution = lower RQ)",
                  color="white", fontsize=11, fontweight="bold")
    ax2.tick_params(colors="white", labelsize=9)
    ax2.set_yticklabels(sorted_cities, color="white", fontsize=8.5)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#444")
    ax2.grid(axis="x", color="#333", linewidth=0.5)
    ax2.legend(handles=legend_patches + [
        mpatches.Patch(color="white", label=f"US avg: {national_avg} L/person/day")],
        frameon=False, labelcolor="white", fontsize=8, loc="lower right")

    # ── Main title ─────────────────────────────────────────────────────────────
    fig.suptitle(
        "Geographic Variation in GLP-1 Environmental Risk Across 20 US Cities\n"
        "Risk is driven by WWTP infrastructure capacity, not city size",
        color="white", fontsize=12, fontweight="bold", y=1.01
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"✓ Geographic chart saved → {save_path}")


if __name__ == "__main__":
    plot_geographic_chart()
