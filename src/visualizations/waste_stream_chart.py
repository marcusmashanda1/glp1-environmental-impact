"""
GLP-1 Environmental Impact Project
src/visualizations/waste_stream_chart.py

Publication-quality waste stream shift chart.
Shows annual reductions in BOD, COD, TSS, TN, TP across three scenarios
with uncertainty bands from low/central/high caloric reduction estimates.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.waste_stream import run_waste_stream_model

os.makedirs("figures", exist_ok=True)


def plot_waste_stream_chart(save_path: str = "figures/waste_stream_shift.png") -> None:
    """
    Generates and saves the waste stream shift chart.
    """
    # ── Data ──────────────────────────────────────────────────────────────────
    df = run_waste_stream_model()

    parameters  = ["BOD_g_per_day", "COD_g_per_day", "TSS_g_per_day",
                   "TN_g_per_day",  "TP_g_per_day"]
    param_labels = ["BOD\n(Biochemical\nOxygen Demand)",
                    "COD\n(Chemical\nOxygen Demand)",
                    "TSS\n(Total Suspended\nSolids)",
                    "TN\n(Total\nNitrogen)",
                    "TP\n(Total\nPhosphorus)"]

    scenarios       = ["conservative", "baseline", "high"]
    scenario_labels = ["Conservative\n(2024)", "Baseline\n(2027)", "High Adoption\n(2030)"]
    scenario_colors = ["#3498db", "#2ecc71", "#e74c3c"]

    # ── Figure ─────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#1a1d26")

    # ── LEFT PANEL: Annual reduction in tonnes/year by parameter and scenario ──
    ax1 = axes[0]
    x        = np.arange(len(parameters))
    n_groups = len(scenarios)
    width    = 0.22

    for i, (scenario, label, color) in enumerate(zip(scenarios, scenario_labels, scenario_colors)):
        central_vals = []
        low_vals     = []
        high_vals    = []

        for param in parameters:
            c = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "central") &
                   (df["parameter"] == param)]["reduction_t_year"].values[0]
            l = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "low") &
                   (df["parameter"] == param)]["reduction_t_year"].values[0]
            h = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "high") &
                   (df["parameter"] == param)]["reduction_t_year"].values[0]
            central_vals.append(c)
            low_vals.append(l)
            high_vals.append(h)

        offset = (i - n_groups / 2 + 0.5) * width
        bars   = ax1.bar(x + offset, central_vals, width,
                         label=label, color=color, alpha=0.85, edgecolor="#333")

        # Uncertainty whiskers
        for j, (c, l, h) in enumerate(zip(central_vals, low_vals, high_vals)):
            ax1.errorbar(x[j] + offset, c, yerr=[[c - l], [h - c]],
                         fmt="none", color="white", capsize=3, linewidth=1.2)

    ax1.set_xticks(x)
    ax1.set_xticklabels(param_labels, color="white", fontsize=8)
    ax1.set_ylabel("Annual Reduction (tonnes/year)", color="white", fontsize=10)
    ax1.set_title("Annual Wastewater Organic Load Reduction\nby Parameter and Scenario",
                  color="white", fontsize=11, fontweight="bold")
    ax1.tick_params(colors="white")
    ax1.legend(frameon=False, labelcolor="white", fontsize=9)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#444")
    ax1.grid(axis="y", color="#333", linewidth=0.5)
    ax1.yaxis.label.set_color("white")

    # ── RIGHT PANEL: Percentage reduction by scenario ─────────────────────────
    ax2 = axes[1]

    for i, (scenario, label, color) in enumerate(zip(scenarios, scenario_labels, scenario_colors)):
        pct_vals  = []
        pct_low   = []
        pct_high  = []

        for param in parameters:
            c = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "central") &
                   (df["parameter"] == param)]["pct_reduction"].values[0]
            l = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "low") &
                   (df["parameter"] == param)]["pct_reduction"].values[0]
            h = df[(df["scenario"] == scenario) &
                   (df["caloric_reduction"] == "high") &
                   (df["parameter"] == param)]["pct_reduction"].values[0]
            pct_vals.append(c)
            pct_low.append(l)
            pct_high.append(h)

        offset = (i - n_groups / 2 + 0.5) * width
        ax2.bar(x + offset, pct_vals, width,
                label=label, color=color, alpha=0.85, edgecolor="#333")

        for j, (c, l, h) in enumerate(zip(pct_vals, pct_low, pct_high)):
            ax2.errorbar(x[j] + offset, c, yerr=[[c - l], [h - c]],
                         fmt="none", color="white", capsize=3, linewidth=1.2)

    ax2.set_xticks(x)
    ax2.set_xticklabels(param_labels, color="white", fontsize=8)
    ax2.set_ylabel("Reduction (% of total municipal load)", color="white", fontsize=10)
    ax2.set_title("Percentage Reduction in Municipal\nWastewater Load by Parameter",
                  color="white", fontsize=11, fontweight="bold")
    ax2.tick_params(colors="white")
    ax2.legend(frameon=False, labelcolor="white", fontsize=9)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#444")
    ax2.grid(axis="y", color="#333", linewidth=0.5)
    ax2.yaxis.label.set_color("white")

    # ── Main title ─────────────────────────────────────────────────────────────
    fig.suptitle(
        "GLP-1 Adoption Impact on US Municipal Wastewater Organic Loads\n"
        "Error bars show uncertainty range across caloric reduction estimates (20–35%)",
        color="white", fontsize=12, fontweight="bold", y=1.01
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"✓ Waste stream chart saved → {save_path}")


if __name__ == "__main__":
    plot_waste_stream_chart()
