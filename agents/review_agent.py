from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import REVIEW_SYSTEM_PROMPT
from validators.output_validators import build_review_summary


class ReviewAgent(BaseAgent):
    """Final self-reflection pass: targeted consistency and completeness checks.

    Receives a condensed summary (not the full JSON dump) to avoid the
    'lost in the middle' attention problem and reduce token cost.
    """

    REQUIRED_FIELDS = (
        "consistent",
        "flags",
        "corrections",
        "completeness_score",
        "regulatory_gaps",
        "reviewed_by",
        "review_confidence",
        "summary",
    )

    @property
    def agent_name(self) -> str:
        return "ReviewAgent"

    @property
    def system_prompt(self) -> str:
        return REVIEW_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        summary = build_review_summary(ctx)
        return f"""Review the following medical device risk analysis for consistency and completeness.
Work through each numbered check in sequence.

ANALYSIS SUMMARY:
{json.dumps(summary, indent=2)}

Systematic checks:
1. RPN arithmetic: Is rpn_before = severity_score x occurrence_score x detectability_score?
2. Risk matrix (before): Is risk_level_before consistent with probability_before x severity per ISO 14971 Annex C?
3. Risk matrix (after): Is risk_level_after consistent with probability_after x severity_after per ISO 14971 Annex C?
4. Class vs severity: Is IEC 62304 Class consistent with severity (Class C expected for Critical/Catastrophic)?
5. Controls coverage: Does controls_count adequately address the identified hazard?
6. Risk-benefit alignment: Is benefit_outweighs_risk consistent with residual_risk_acceptable?
7. Traceability: Is traceability_complete=true with all requirements covered?

Return ONLY a JSON object:
{{
  "consistent": true | false,
  "flags": ["<specific inconsistency found>"],
  "corrections": [
    {{
      "field": "<field name>",
      "issue": "<what is wrong>",
      "suggested_correction": "<what it should be>"
    }}
  ],
  "completeness_score": <0-100>,
  "regulatory_gaps": ["<gap>"],
  "reviewed_by": "ReviewAgent",
  "review_confidence": "High" | "Medium" | "Low",
  "summary": "<2-sentence overall assessment>"
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.validation_summary = data
