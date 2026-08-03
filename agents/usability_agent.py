from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import USABILITY_SYSTEM_PROMPT


class UsabilityAgent(BaseAgent):
    """Identifies use errors and links to IEC 62366-1 usability tasks."""

    REQUIRED_FIELDS = (
        "intended_users",
        "use_environment",
        "intended_use_statement",
        "use_errors",
        "user_interface_considerations",
        "training_requirements",
    )

    @property
    def agent_name(self) -> str:
        return "UsabilityAgent"

    @property
    def system_prompt(self) -> str:
        return USABILITY_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Perform a use error analysis per IEC 62366-1 for the following medical device
software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASS: {ctx.iec_62304_class}
HAZARD: {ctx.hazard}
HARM: {ctx.harm}

Return ONLY a JSON object:
{{
  "intended_users": ["<user type>"],
  "use_environment": "<clinical environment>",
  "intended_use_statement": "<formal intended use>",
  "use_errors": [
    {{
      "id": "UE-001",
      "description": "<use error>",
      "error_type": "commission" | "omission" | "substitution",
      "contributing_factors": ["<factor>"],
      "potential_harm": "<harm>",
      "severity": "Negligible" | "Marginal" | "Critical" | "Catastrophic",
      "iec_62366_task": "<relevant IEC 62366-1 task reference>",
      "mitigation": "<usability mitigation>"
    }}
  ],
  "user_interface_considerations": ["<consideration>"],
  "training_requirements": ["<requirement>"]
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.use_error_analysis = data
