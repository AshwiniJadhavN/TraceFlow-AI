from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import FMEA_SYSTEM_PROMPT
from validators.output_validators import correct_fmea_rpn


class FMEAAgent(BaseAgent):
    """Generates an FMEA table entry with RPN before and after mitigation."""

    REQUIRED_FIELDS = (
        "item",
        "function",
        "failure_mode",
        "severity_score",
        "occurrence_score",
        "detectability_score",
        "rpn_before",
        "severity_score_after",
        "occurrence_score_after",
        "detectability_score_after",
        "rpn_after",
    )

    @property
    def agent_name(self) -> str:
        return "FMEAAgent"

    @property
    def system_prompt(self) -> str:
        return FMEA_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Generate an FMEA table entry for the following medical device software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASS: {ctx.iec_62304_class}
PRIMARY HAZARD: {ctx.hazard}
HAZARDOUS SITUATION: {ctx.hazardous_situation}
HARM: {ctx.harm}
SEVERITY: {ctx.severity}
PROBABILITY: {ctx.probability_before_mitigation}

Scoring scales (1-10):
- Severity: 1=Negligible, 2-3=Marginal, 4-6=Critical, 7-10=Catastrophic
- Occurrence: 1=Improbable, 2-3=Remote, 4-6=Occasional, 7-8=Probable, 9-10=Frequent
- Detectability: 1-2=Almost certain detect, 9-10=Almost impossible to detect
- RPN = Severity x Occurrence x Detectability (must equal the product exactly)

Return ONLY a JSON object:
{{
  "item": "<system/component name>",
  "function": "<intended function>",
  "failure_mode": "<how it fails>",
  "local_effect": "<immediate effect>",
  "system_effect": "<effect on overall system>",
  "end_effect": "<effect on patient/user>",
  "severity_score": <1-10>,
  "occurrence_score": <1-10>,
  "detectability_score": <1-10>,
  "rpn_before": <S x O x D>,
  "current_controls": ["<control1>"],
  "recommended_action": "<mitigation>",
  "responsible_party": "<role>",
  "severity_score_after": <1-10>,
  "occurrence_score_after": <1-10>,
  "detectability_score_after": <1-10>,
  "rpn_after": <S_after x O_after x D_after>
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        data, corrections = correct_fmea_rpn(data)
        if corrections:
            ctx.errors.append(f"FMEAAgent: RPN auto-corrections applied: {'; '.join(corrections)}")
        ctx.fmea = data
