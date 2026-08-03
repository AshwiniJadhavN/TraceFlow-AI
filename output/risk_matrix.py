"""5x4 ISO 14971 risk matrix visualisation - before and after mitigation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

# ISO 14971 axes
PROBABILITY_LEVELS = ["Improbable", "Remote", "Occasional", "Probable", "Frequent"]
SEVERITY_LEVELS = ["Negligible", "Marginal", "Critical", "Catastrophic"]

# Colour map aligned to ISO 14971 Annex D risk acceptability regions
RISK_COLORS: np.ndarray = np.array(
    [
        # Negligible    Marginal      Critical      Catastrophic
        ["#00b050", "#00b050", "#ffff00", "#ff9900"],  # Improbable
        ["#00b050", "#ffff00", "#ffff00", "#ff9900"],  # Remote
        ["#00b050", "#ffff00", "#ff9900", "#ff0000"],  # Occasional
        ["#ffff00", "#ff9900", "#ff0000", "#ff0000"],  # Probable
        ["#ffff00", "#ff9900", "#ff0000", "#ff0000"],  # Frequent
    ]
)

PROB_IDX = {p: i for i, p in enumerate(PROBABILITY_LEVELS)}
SEV_IDX = {s: i for i, s in enumerate(SEVERITY_LEVELS)}


class RiskMatrixPlotter:
    def __init__(self, report: dict[str, Any], output_dir: Path) -> None:
        self.report = report
        self.output_dir = output_dir

    def save(self) -> Path:
        path = self.output_dir / "risk_matrix.png"
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("ISO 14971 Risk Matrix — TraceFlow AI", fontsize=14, fontweight="bold")

        prob_before = self.report.get("probability_before_mitigation", "Occasional")
        sev = self.report.get("severity", "Critical")
        prob_after = self.report.get("probability_after_mitigation", "Remote")

        self._draw(axes[0], prob_before, sev, "Before Mitigation")
        self._draw(axes[1], prob_after, sev, "After Mitigation")

        plt.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def _draw(self, ax: plt.Axes, probability: str, severity: str, title: str) -> None:
        n_prob = len(PROBABILITY_LEVELS)
        n_sev = len(SEVERITY_LEVELS)

        for i in range(n_prob):
            for j in range(n_sev):
                rect = patches.FancyBboxPatch(
                    (j, i),
                    1,
                    1,
                    boxstyle="round,pad=0.03",
                    facecolor=RISK_COLORS[i][j],
                    edgecolor="white",
                    linewidth=2,
                )
                ax.add_patch(rect)

        # Star marker for current risk position
        prob_i = PROB_IDX.get(probability, 2)
        sev_j = SEV_IDX.get(severity, 2)
        ax.plot(
            sev_j + 0.5,
            prob_i + 0.5,
            marker="*",
            markersize=22,
            color="navy",
            markeredgecolor="white",
            markeredgewidth=1.5,
            zorder=5,
        )
        ax.text(
            sev_j + 0.5,
            prob_i + 0.5 - 0.35,
            f"{probability[:3]} / {severity[:3]}",
            ha="center",
            va="top",
            fontsize=7,
            color="navy",
            fontweight="bold",
        )

        ax.set_xlim(0, n_sev)
        ax.set_ylim(0, n_prob)
        ax.set_xticks([i + 0.5 for i in range(n_sev)])
        ax.set_yticks([i + 0.5 for i in range(n_prob)])
        ax.set_xticklabels(SEVERITY_LEVELS, fontsize=9)
        ax.set_yticklabels(PROBABILITY_LEVELS, fontsize=9)
        ax.set_xlabel("Severity →", fontsize=11)
        ax.set_ylabel("Probability →", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

        legend_elements = [
            patches.Patch(facecolor="#00b050", label="Low"),
            patches.Patch(facecolor="#ffff00", label="Medium"),
            patches.Patch(facecolor="#ff9900", label="High"),
            patches.Patch(facecolor="#ff0000", label="Unacceptable"),
        ]
        ax.legend(handles=legend_elements, loc="lower right", fontsize=7, title="Risk Level")
