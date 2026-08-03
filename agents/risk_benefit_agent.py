from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import RISK_BENEFIT_SYSTEM_PROMPT


class RiskBenefitAgent(BaseAgent):
    """Performs ISO 14971 Clause 9 risk-benefit analysis."""

    REQUIRED_FIELDS = (
        "clinical_context",
        "patient_population",
        "clinical_benefits",
        "residual_risks_summary",
        "benefit_outweighs_risk",
        "overall_benefit_risk_conclusion",
        "justification",
    )

    @property
    def agent_name(self) -> str:
        return "RiskBenefitAgent"

    @property
    def system_prompt(self) -> str:
        return RISK_BENEFIT_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        controls_str = json.dumps(ctx.risk_controls, indent=2) if ctx.risk_controls else "None"
        return f"""Perform an ISO 14971 Clause 9 Risk-Benefit Analysis for the following medical
device software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASS: {ctx.iec_62304_class}
HAZARD: {ctx.hazard}
HARM: {ctx.harm}
SEVERITY: {ctx.severity}
RESIDUAL RISK LEVEL: {ctx.risk_level_after_mitigation}
RESIDUAL RISK ACCEPTABLE: {ctx.residual_risk_acceptable}

RISK CONTROLS APPLIED:
{controls_str}

Reason through:
1. Clinical context and patient population
2. Available alternatives (including no treatment)
3. Specific clinical benefits
4. Residual risks vs expected benefits
5. ISO 14971 Clause 9 conclusion

Return ONLY a JSON object:
{{
  "clinical_context": "<description>",
  "patient_population": "<target population>",
  "clinical_benefits": [
    {{
      "benefit": "<specific benefit>",
      "significance": "High" | "Medium" | "Low",
      "evidence_basis": "<rationale>"
    }}
  ],
  "treatment_alternatives": ["<alternative>"],
  "residual_risks_summary": [
    {{
      "risk": "<residual risk>",
      "level": "<level>",
      "acceptable": true | false
    }}
  ],
  "benefit_outweighs_risk": true | false,
  "overall_benefit_risk_conclusion": "<ISO 14971 Cl. 9 conclusion>",
  "justification": "<detailed reasoning>",
  "state_of_the_art_comparison": "<comparison with current practice>",
  "post_market_surveillance_needed": true | false
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.risk_benefit_analysis = data
