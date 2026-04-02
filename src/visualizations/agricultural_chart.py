"""
GLP-1 Environmental Impact Project
src/visualizations/agricultural_chart.py

Publication-quality agricultural impact cascade chart.
Shows annual reductions in N fertilizer, irrigation water, GHG emissions,
and land use across three adoption scenarios and food categories.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.agricultural import run_agricultural_model, summarise_by_metric

os.makedirs("figures", exist_ok=True)


def plot_agricultural_chart(save_path: str = "figures/agricultural_impact.png") -> None:
    """
    Generates and saves the agricultural cascade chart.
    """
    # ── Data ──────────────────────────────────────────────────────────────────
    df      = run_agricultural_model()
    summary = summarise_by_metric(df)

    scenarios       = ["conservative", "baseline", "high"]
    scenario_labels = ["Conservative\n(2024)", "Baseline\n(2027)", "High Adoption\n(2030)"]
    scenario_colors = ["#3498db", "#2ecc71", "#e74c3c"]

    metrics = [
        ("N_fertilizer_kg_per_1000kcal", "N Fertilizer\nReduction",    "billion kg N/year",  1e9),
        ("irrigation_L_per_1000kcal",    "Irrigation Water\nReduction", "trillion L/year",    1e12),
        ("ghg_kgCO2e_per_1000kcal",      "GHG Emissions\nReduction",    "billion kg CO₂e/yr", 1e9),
        ("land_m2_per_1000kcal",         "Land Use\nReduction",         "billion m²/year",    1e9),
    ]

    # Food category colours for stacked bars
    category_colors = {
        "red_meat":          "#e74c3c",
        "processed_food":    "#e67e22",
        "sugary_beverages":  "#f1c40f",
        "dairy":             "#2ecc71",
        "grains":            "#3498db",
        "fruits_vegetables": "#9b59b6",
    }
    category_labels = {
        "red_meat":          "Red Meat",
        "processed_food":    "Processed Food",
        "sugary_beverages":  "Sugary Beverages",
        "dairy":             "Dairy",
        "grains":            "Grains",
        "fruits_vegetables": "Fruits & Veg",
    }

    # ── Figure: 2x2 grid ───────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor("#0f1117")
    axes_flat = axes.flatten()

    for ax_idx, (metric_key, metric_label, unit_label, scale) in enumerate(metrics):
        ax = axes_flat[ax_idx]
        ax.set_facecolor("#1a1d26")

        x     = np.arange(len(scenarios))
        width = 0.55

        categories = list(category_colors.keys())
        bottoms    = np.zeros(len(scenarios))

        for cat in categories:
            vals = []
            for scenario in scenarios:
                v = df[
                    (df["scenario"] == scenario) &
                    (df["food_category"] == cat) &
                    (df["metric"] == metric_key)
                ]["reduction_per_year"].sum()
                vals.append(v / scale)

            ax.bar(x, vals, width, bottom=bottoms,
                   color=category_colors[cat], label=category_labels[cat],
                   edgecolor="#222", alpha=0.9)
            bottoms += np.array(vals)

        # Total value labels on top of each bar
        for i, (scenario, total) in enumerate(zip(scenarios, bottoms)):
            ax.text(i, total + total * 0.02, f"{total:.1f}",
                    ha="center", va="bottom", color="white",
                    fontsize=9, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(scenario_labels, color="white", fontsize=9)
        ax.set_ylabel(unit_label, color="white", fontsize=9)
        ax.set_title(metric_label, color="white", fontsize=11, fontweight="bold")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        ax.grid(axis="y", color="#333", linewidth=0.5)
        ax.yaxis.label.set_color("white")

        # Legend only on first panel
        if ax_idx == 0:
            ax.legend(frameon=False, labelcolor="white", fontsize=8,
                      loc="upper left", ncol=2)

    # ── Main title ─────────────────────────────────────────────────────────────
    fig.suptitle(
        "Agricultural and Environmental Impact of GLP-1-Driven Dietary Shifts\n"
        "Stacked by food category — red meat and processed food dominate each metric",
        color="white", fontsize=13, fontweight="bold", y=1.01
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"✓ Agricultural chart saved → {save_path}")


if __name__ == "__main__":
    plot_agricultural_chart()
