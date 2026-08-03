from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import REQUIREMENT_DECOMPOSITION_SYSTEM_PROMPT


class RequirementDecompositionAgent(BaseAgent):
    """Decomposes a system requirement into HW / SW / HF / interface sub-requirements."""

    REQUIRED_FIELDS = (
        "system_requirement",
        "subsystems_identified",
        "hardware_requirements",
        "software_requirements",
        "human_factors_requirements",
        "interface_requirements",
        "allocation_summary",
    )

    @property
    def agent_name(self) -> str:
        return "RequirementDecompositionAgent"

    @property
    def system_prompt(self) -> str:
        return REQUIREMENT_DECOMPOSITION_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        sys_desc = (
            f"\nSYSTEM DESCRIPTION:\n{ctx.prompt_system_description}\n"
            if ctx.prompt_system_description
            else ""
        )
        return f"""Decompose the following system-level requirement into derived subsystem requirements.

SYSTEM REQUIREMENT:
{ctx.prompt_requirement}
{sys_desc}
Allocate derived requirements to four engineering domains:
1. Hardware  (sensors, displays, processors, power, mechanical)
2. Software  (algorithms, UI, communication, data storage)
3. Human factors  (workflow, training, ergonomics, labeling)
4. Interfaces  (HW-SW data contracts, user-facing APIs, external system connections)

Return ONLY a JSON object:
{{
  "system_requirement": "<original requirement>",
  "subsystems_identified": ["<Subsystem A>", "<Subsystem B>"],
  "hardware_requirements": [
    {{"id": "HW-001", "requirement": "<shall statement>", "subsystem": "<name>", "rationale": "<why>"}}
  ],
  "software_requirements": [
    {{"id": "SW-001", "requirement": "<shall statement>", "subsystem": "<name>", "rationale": "<why>"}}
  ],
  "human_factors_requirements": [
    {{"id": "HF-001", "requirement": "<shall statement>", "rationale": "<why>"}}
  ],
  "interface_requirements": [
    {{"id": "IF-001", "requirement": "<shall statement>",
      "interface_type": "HW-SW" | "SW-User" | "System-External" | "SW-SW",
      "rationale": "<why>"}}
  ],
  "allocation_summary": {{
    "hardware_count": <n>, "software_count": <n>,
    "human_factors_count": <n>, "interface_count": <n>
  }}
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.decomposed_requirements = data
