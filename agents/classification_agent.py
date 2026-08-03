from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import CLASSIFICATION_SYSTEM_PROMPT
from validators.output_validators import VALID_CLASSES, check_enum


class ClassificationAgent(BaseAgent):
    """Determines IEC 62304 software safety class (A / B / C)."""

    REQUIRED_FIELDS = (
        "iec_62304_class",
        "rationale",
        "key_factors",
        "intended_use",
        "potential_for_serious_injury",
    )

    @property
    def agent_name(self) -> str:
        return "ClassificationAgent"

    @property
    def system_prompt(self) -> str:
        return CLASSIFICATION_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Analyze the following medical device software requirement and determine its
IEC 62304 software safety classification.

REQUIREMENT:
{ctx.prompt_requirement}

Return ONLY a JSON object with this exact schema:
{{
  "iec_62304_class": "A" | "B" | "C",
  "rationale": "<detailed reasoning referencing IEC 62304 Table 2>",
  "key_factors": ["<factor1>", "<factor2>"],
  "intended_use": "<brief clinical intended use>",
  "potential_for_serious_injury": true | false
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.iec_62304_class = check_enum(data["iec_62304_class"], VALID_CLASSES, "iec_62304_class")
        ctx.iec_62304_rationale = data["rationale"]
