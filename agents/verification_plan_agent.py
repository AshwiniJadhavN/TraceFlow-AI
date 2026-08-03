from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import VERIFICATION_PLAN_SYSTEM_PROMPT


class VerificationPlanAgent(BaseAgent):
    """Generates a system V&V plan mapping requirements and controls to test activities."""

    REQUIRED_FIELDS = (
        "verification_activities",
        "validation_activities",
        "verification_summary",
    )

    @property
    def agent_name(self) -> str:
        return "VerificationPlanAgent"

    @property
    def system_prompt(self) -> str:
        return VERIFICATION_PLAN_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        controls_str = (
            json.dumps(ctx.risk_controls, indent=2) if ctx.risk_controls else "Not available"
        )
        sw_reqs_str = "Not available"
        if ctx.decomposed_requirements:
            sw_reqs = ctx.decomposed_requirements.get("software_requirements", [])
            hw_reqs = ctx.decomposed_requirements.get("hardware_requirements", [])
            all_reqs = sw_reqs + hw_reqs
            if all_reqs:
                sw_reqs_str = json.dumps(all_reqs, indent=2)

        return f"""Generate a system verification and validation plan for the following medical device.

SYSTEM REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASS: {ctx.iec_62304_class or 'Not classified'}
RISK LEVEL AFTER MITIGATION: {ctx.risk_level_after_mitigation or 'Not assessed'}
RESIDUAL RISK ACCEPTABLE: {ctx.residual_risk_acceptable}

DERIVED REQUIREMENTS TO VERIFY:
{sw_reqs_str}

RISK CONTROLS TO VERIFY:
{controls_str}

Test methods: test | analysis | inspection | demonstration
Test levels: unit | integration | system | acceptance
Test types: functional | safety | performance | usability | regression

Return ONLY a JSON object:
{{
  "verification_activities": [
    {{
      "id": "VER-001",
      "verifies": "<requirement ID or control ID>",
      "description": "<what is being verified>",
      "test_level": "unit" | "integration" | "system" | "acceptance",
      "test_type": "functional" | "safety" | "performance" | "usability" | "regression",
      "method": "test" | "analysis" | "inspection" | "demonstration",
      "acceptance_criteria": "<measurable pass/fail criteria>",
      "test_environment": "<bench|simulation|lab|clinical>",
      "iec_62304_activity": "<relevant IEC 62304 activity reference>",
      "responsible_party": "<engineering role>"
    }}
  ],
  "validation_activities": [
    {{
      "id": "VAL-001",
      "description": "<what is being validated>",
      "method": "clinical simulation" | "usability study" | "alpha testing" | "beta testing",
      "acceptance_criteria": "<criteria>",
      "participants": "<who performs validation>"
    }}
  ],
  "verification_summary": {{
    "total_verification": <n>,
    "total_validation": <n>,
    "by_level": {{"unit": <n>, "integration": <n>, "system": <n>, "acceptance": <n>}},
    "by_method": {{"test": <n>, "analysis": <n>, "inspection": <n>, "demonstration": <n>}}
  }}
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.verification_plan = data
