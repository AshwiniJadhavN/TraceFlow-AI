from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import HAZOP_SYSTEM_PROMPT


class HAZOPAgent(BaseAgent):
    """HAZOP analysis: guide-word deviation study across system nodes."""

    REQUIRED_FIELDS = ("system_nodes", "hazop_summary")

    @property
    def agent_name(self) -> str:
        return "HAZOPAgent"

    @property
    def system_prompt(self) -> str:
        return HAZOP_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        sys_desc = ctx.prompt_system_description or "Not provided"
        subsystems = ""
        if ctx.decomposed_requirements:
            names = ctx.decomposed_requirements.get("subsystems_identified", [])
            if names:
                subsystems = f"\nIDENTIFIED SUBSYSTEMS: {', '.join(names)}"

        return f"""Perform a HAZOP analysis for the following medical device system requirement.

SYSTEM REQUIREMENT:
{ctx.prompt_requirement}

SYSTEM DESCRIPTION:
{sys_desc}
{subsystems}

Apply HAZOP guide words to key system parameters.
Guide words: No / Less / More / Reverse / Part of / As well as / Other than / Early / Late
Parameters for medical software systems: Signal, Data, Display, Command, Timing,
Communication, Power, Control, Sequence.

Identify at least 2 system nodes and at least 2 deviations per node.

Return ONLY a JSON object:
{{
  "system_nodes": [
    {{
      "id": "NODE-001",
      "name": "<node name>",
      "description": "<what this node does>",
      "deviations": [
        {{
          "id": "DEV-001",
          "guide_word": "<guide word>",
          "parameter": "<parameter>",
          "deviation": "<guide word + parameter>",
          "causes": ["<cause1>", "<cause2>"],
          "consequences": ["<consequence>"],
          "severity": "Negligible" | "Marginal" | "Critical" | "Catastrophic",
          "probability": "Frequent" | "Probable" | "Occasional" | "Remote" | "Improbable",
          "risk_ranking": "Low" | "Medium" | "High" | "Unacceptable",
          "existing_safeguards": ["<safeguard>"],
          "recommended_actions": ["<action>"]
        }}
      ]
    }}
  ],
  "hazop_summary": {{
    "total_nodes": <n>,
    "total_deviations": <n>,
    "high_risk_deviations": <n>,
    "key_findings": ["<finding>"]
  }}
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.hazop_analysis = data
