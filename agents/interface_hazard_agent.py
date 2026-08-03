from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import INTERFACE_HAZARD_SYSTEM_PROMPT


class InterfaceHazardAgent(BaseAgent):
    """Interface Hazard Analysis: failure modes at HW-SW, User-SW, and external boundaries."""

    REQUIRED_FIELDS = ("interfaces", "interface_summary")

    @property
    def agent_name(self) -> str:
        return "InterfaceHazardAgent"

    @property
    def system_prompt(self) -> str:
        return INTERFACE_HAZARD_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        iface_reqs = ""
        if ctx.decomposed_requirements:
            reqs = ctx.decomposed_requirements.get("interface_requirements", [])
            if reqs:
                iface_reqs = f"\nINTERFACE REQUIREMENTS:\n{json.dumps(reqs, indent=2)}"

        hazard_ctx = ""
        if ctx.hazard:
            hazard_ctx = f"\nPRIMARY HAZARD: {ctx.hazard}\nHARM: {ctx.harm}"

        return f"""Perform an Interface Hazard Analysis (IHA) for the following medical device system.

SYSTEM REQUIREMENT:
{ctx.prompt_requirement}
{hazard_ctx}
{iface_reqs}

Identify all significant system interfaces and their failure modes. Consider:
- HW-SW: sensor data paths, actuator command paths
- SW-User: display outputs, alert mechanisms, user inputs
- System-External: network connections, other medical devices, hospital systems
- SW-SW: internal software component boundaries

Return ONLY a JSON object:
{{
  "interfaces": [
    {{
      "id": "INT-001",
      "name": "<interface name>",
      "type": "HW-SW" | "SW-User" | "System-External" | "SW-SW",
      "from_component": "<sender>",
      "to_component": "<receiver>",
      "data_or_signal": "<what is transferred>",
      "failure_modes": [
        {{
          "id": "IFM-001",
          "description": "<how this interface fails>",
          "effect": "<impact on system and patient>",
          "severity": "Negligible" | "Marginal" | "Critical" | "Catastrophic",
          "probability": "Frequent" | "Probable" | "Occasional" | "Remote" | "Improbable",
          "existing_controls": ["<control>"],
          "recommended_controls": ["<control>"]
        }}
      ]
    }}
  ],
  "interface_summary": {{
    "total_interfaces": <n>,
    "critical_interfaces": <n>,
    "key_risks": ["<risk>"]
  }}
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.interface_hazards = data
