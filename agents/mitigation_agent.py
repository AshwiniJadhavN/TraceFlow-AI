from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import MITIGATION_SYSTEM_PROMPT
from validators.output_validators import (
    VALID_PROBABILITIES,
    VALID_RISK_LEVELS,
    VALID_SEVERITIES,
    check_enum,
    correct_risk_level,
)


class MitigationAgent(BaseAgent):
    """Proposes risk controls and recalculates residual risk."""

    REQUIRED_FIELDS = (
        "risk_controls",
        "probability_after_mitigation",
        "risk_level_after_mitigation",
        "residual_risk_acceptable",
    )

    @property
    def agent_name(self) -> str:
        return "MitigationAgent"

    @property
    def system_prompt(self) -> str:
        return MITIGATION_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        fmea_str = json.dumps(ctx.fmea, indent=2) if ctx.fmea else "Not available"
        fta_str = json.dumps(ctx.fta, indent=2) if ctx.fta else "Not available"
        return f"""Propose ISO 14971 risk controls and calculate residual risk for the following
medical device software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

HAZARD: {ctx.hazard}
HAZARDOUS SITUATION: {ctx.hazardous_situation}
HARM: {ctx.harm}
SEVERITY: {ctx.severity}
PROBABILITY BEFORE: {ctx.probability_before_mitigation}
RISK LEVEL BEFORE: {ctx.risk_level_before_mitigation}

FMEA OUTPUT:
{fmea_str}

FTA OUTPUT:
{fta_str}

Apply ISO 14971 risk control hierarchy:
1. Inherent safety by design
2. Protective measures
3. Information for safety (labeling / IFU)

Return ONLY a JSON object:
{{
  "risk_controls": [
    {{
      "id": "RC-001",
      "type": "design" | "protective" | "information",
      "description": "<control>",
      "addresses": "<hazard or failure mode addressed>",
      "implementation": "<how to implement>",
      "verification_method": "<how to verify effectiveness>",
      "effectiveness": "High" | "Medium" | "Low"
    }}
  ],
  "probability_after_mitigation": "Frequent" | "Probable" | "Occasional" | "Remote" | "Improbable",
  "severity_after_mitigation": "Negligible" | "Marginal" | "Critical" | "Catastrophic",
  "risk_level_after_mitigation": "Low" | "Medium" | "High" | "Unacceptable",
  "residual_risk_acceptable": true | false,
  "residual_risk_justification": "<rationale>",
  "new_risks_introduced": ["<new risk from control>"]
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        prob_after = check_enum(
            data["probability_after_mitigation"],
            VALID_PROBABILITIES,
            "probability_after_mitigation",
        )
        sev_after = check_enum(
            data.get("severity_after_mitigation", ctx.severity),
            VALID_SEVERITIES,
            "severity_after_mitigation",
        )
        risk_after = check_enum(
            data["risk_level_after_mitigation"],
            VALID_RISK_LEVELS,
            "risk_level_after_mitigation",
        )
        risk_after, corrected = correct_risk_level(prob_after, sev_after, risk_after)
        if corrected:
            ctx.errors.append(
                f"MitigationAgent: risk_level_after_mitigation auto-corrected to '{risk_after}' "
                f"per ISO 14971 matrix ({prob_after} x {sev_after})."
            )

        ctx.risk_controls = data["risk_controls"]
        ctx.probability_after_mitigation = prob_after
        ctx.severity_after_mitigation = sev_after
        ctx.risk_level_after_mitigation = risk_after
        ctx.residual_risk_acceptable = data["residual_risk_acceptable"]
