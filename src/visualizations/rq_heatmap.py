"""
GLP-1 Environmental Impact Project
src/visualizations/rq_heatmap.py

Publication-quality Risk Quotient heatmap — drugs × scenarios.

Displays log10(RQ) values for all drug/route combinations across
three adoption scenarios, with risk threshold annotations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.pipeline import run_pipeline

# ── Output directory ───────────────────────────────────────────────────────────
os.makedirs("figures", exist_ok=True)


def plot_rq_heatmap(save_path: str = "figures/rq_heatmap.png") -> None:
    """
    Generates and saves the RQ heatmap figure.
    """
    # ── Data ──────────────────────────────────────────────────────────────────
    results     = run_pipeline()
    daily_loads = results["daily_loads"]

    # Create drug label combining name and route
    daily_loads["drug_label"] = daily_loads.apply(
        lambda r: f"{r['drug']}\n({r['route']})", axis=1
    )

    pivot = daily_loads.pivot_table(
        index="drug_label",
        columns="scenario_label",
        values="risk_quotient"
    )

    # Sort by mean RQ descending
    pivot["mean_rq"] = pivot.mean(axis=1)
    pivot = pivot.sort_values("mean_rq", ascending=True).drop(columns="mean_rq")

    log_pivot = np.log10(pivot)

    # ── Figure ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    # Custom colormap: green → yellow → red
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "rq_cmap",
        ["#2ecc71", "#f1c40f", "#e74c3c", "#8e44ad"],
        N=256
    )

    im = ax.imshow(
        log_pivot.values,
        cmap=cmap,
        aspect="auto",
        vmin=0,
        vmax=log_pivot.values.max() * 1.05
    )

    # ── Annotations ───────────────────────────────────────────────────────────
    for i in range(log_pivot.shape[0]):
        for j in range(log_pivot.shape[1]):
            rq_val    = pivot.values[i, j]
            log_val   = log_pivot.values[i, j]
            text_color = "white"

            if rq_val >= 1_000_000:
                label = f"{rq_val/1e6:.0f}M"
            elif rq_val >= 1_000:
                label = f"{rq_val/1e3:.0f}K"
            else:
                label = f"{rq_val:.0f}"

            ax.text(j, i, f"RQ\n{label}",
                    ha="center", va="center",
                    fontsize=9, color=text_color, fontweight="bold")

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, color="white", fontsize=10)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, color="white", fontsize=9)

    ax.tick_params(colors="white", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Colorbar ──────────────────────────────────────────────────────────────
    cbar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.03)
    cbar.set_label("log₁₀(Risk Quotient)", color="white", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white", fontsize=8)
    cbar.outline.set_edgecolor("#444")

    # ── Risk threshold legend ─────────────────────────────────────────────────
    legend_elements = [
        Patch(facecolor="#2ecc71", label="Low risk  (RQ < 0.1)"),
        Patch(facecolor="#f1c40f", label="Moderate  (RQ 0.1–1)"),
        Patch(facecolor="#e74c3c", label="High risk (RQ > 1)"),
        Patch(facecolor="#8e44ad", label="Severe    (RQ > 1,000)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(0, -0.12),
        ncol=4,
        frameon=False,
        fontsize=8,
        labelcolor="white"
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.set_title(
        "GLP-1 Pharmaceutical Risk Quotients by Drug and Adoption Scenario\n"
        "RQ = MEC$_{effluent}$ / PNEC  |  RQ > 1 indicates potential ecological risk",
        color="white", fontsize=11, fontweight="bold", pad=15
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"✓ RQ heatmap saved → {save_path}")


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    plot_rq_heatmap()
