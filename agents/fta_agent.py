from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import FTA_SYSTEM_PROMPT


class FTAAgent(BaseAgent):
    """Builds a fault tree: top event → OR/AND gates → basic events."""

    REQUIRED_FIELDS = ("top_event", "tree", "minimal_cut_sets", "critical_path")

    @property
    def agent_name(self) -> str:
        return "FTAAgent"

    @property
    def system_prompt(self) -> str:
        return FTA_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Construct a Fault Tree Analysis (FTA) for the following medical device software
requirement using top-down deductive decomposition.

REQUIREMENT:
{ctx.prompt_requirement}

TOP EVENT (HARM): {ctx.harm}
HAZARD: {ctx.hazard}
HAZARDOUS SITUATION: {ctx.hazardous_situation}

Decomposition rules:
1. Start with the harm as the top event
2. Use OR/AND gates to decompose into intermediate events
3. Continue until basic events (undeveloped root causes) are reached
4. Every gate must have ≥2 inputs
5. Assign failure probabilities (0.0-1.0) to basic events

Return ONLY a JSON object:
{{
  "top_event": "<ultimate harm description>",
  "tree": {{
    "id": "TE-001",
    "event": "<top event>",
    "gate_type": "OR",
    "type": "top",
    "children": [
      {{
        "id": "IE-001",
        "event": "<intermediate event>",
        "gate_type": "OR" | "AND",
        "type": "intermediate",
        "children": [
          {{
            "id": "BE-001",
            "event": "<basic event / root cause>",
            "gate_type": null,
            "type": "basic",
            "probability": 0.001,
            "children": []
          }}
        ]
      }}
    ]
  }},
  "minimal_cut_sets": ["<MCS1>", "<MCS2>"],
  "critical_path": "<most probable failure path>"
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.fta = data
