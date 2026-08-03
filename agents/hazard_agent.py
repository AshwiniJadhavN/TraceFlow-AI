from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import HAZARD_SYSTEM_PROMPT
from validators.output_validators import (
    VALID_PROBABILITIES,
    VALID_RISK_LEVELS,
    VALID_SEVERITIES,
    check_enum,
    correct_risk_level,
)


class HazardAgent(BaseAgent):
    """Identifies hazards, hazardous situations, and harms per ISO 14971."""

    REQUIRED_FIELDS = (
        "hazard",
        "hazardous_situation",
        "harm",
        "probability_before_mitigation",
        "severity",
        "risk_level_before_mitigation",
    )

    @property
    def agent_name(self) -> str:
        return "HazardAgent"

    @property
    def system_prompt(self) -> str:
        return HAZARD_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Perform an ISO 14971 hazard analysis for the following medical device software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASSIFICATION: {ctx.iec_62304_class}
CLASSIFICATION RATIONALE: {ctx.iec_62304_rationale}

Reasoning chain:
1. Intended use -> clinical purpose
2. Failure modes -> what can go wrong
3. Hazardous situation -> exposure sequence
4. Harm pathway -> what harm, to whom
5. Probability (Frequent / Probable / Occasional / Remote / Improbable)
6. Severity (Negligible / Marginal / Critical / Catastrophic)
7. Risk level (Low / Medium / High / Unacceptable) per ISO 14971 Table C.3

Return ONLY a JSON object:
{{
  "hazard": "<root hazard>",
  "hazardous_situation": "<sequence leading to harm>",
  "harm": "<specific patient/user harm>",
  "harm_type": "patient" | "user" | "third_party" | "environment",
  "probability_before_mitigation": "Frequent" | "Probable" | "Occasional" | "Remote" | "Improbable",
  "probability_rationale": "<rationale>",
  "severity": "Negligible" | "Marginal" | "Critical" | "Catastrophic",
  "severity_rationale": "<rationale>",
  "risk_level_before_mitigation": "Low" | "Medium" | "High" | "Unacceptable",
  "additional_hazards": ["<other hazard>"]
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        prob = check_enum(
            data["probability_before_mitigation"],
            VALID_PROBABILITIES,
            "probability_before_mitigation",
        )
        sev = check_enum(data["severity"], VALID_SEVERITIES, "severity")
        risk = check_enum(
            data["risk_level_before_mitigation"],
            VALID_RISK_LEVELS,
            "risk_level_before_mitigation",
        )
        risk, corrected = correct_risk_level(prob, sev, risk)
        if corrected:
            ctx.errors.append(
                f"HazardAgent: risk_level_before_mitigation auto-corrected to '{risk}' "
                f"per ISO 14971 matrix ({prob} x {sev})."
            )

        ctx.hazard = data["hazard"]
        ctx.hazardous_situation = data["hazardous_situation"]
        ctx.harm = data["harm"]
        ctx.probability_before_mitigation = prob
        ctx.severity = sev
        ctx.risk_level_before_mitigation = risk
