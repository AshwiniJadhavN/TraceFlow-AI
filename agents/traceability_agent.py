from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import TRACEABILITY_SYSTEM_PROMPT


class TraceabilityAgent(BaseAgent):
    """Builds full traceability matrix: REQ → HAZARD → CONTROL → VER → RISK."""

    REQUIRED_FIELDS = (
        "requirement_id",
        "requirement_text",
        "matrix",
        "coverage_summary",
        "regulatory_references",
    )

    @property
    def agent_name(self) -> str:
        return "TraceabilityAgent"

    @property
    def system_prompt(self) -> str:
        return TRACEABILITY_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        controls_str = json.dumps(ctx.risk_controls, indent=2) if ctx.risk_controls else "None"
        req_snippet = ctx.prompt_requirement[:120] + (
            "..." if len(ctx.prompt_requirement) > 120 else ""
        )
        return f"""Build a complete regulatory traceability matrix for the following medical
device software requirement.

REQUIREMENT:
{ctx.prompt_requirement}

IEC 62304 CLASS: {ctx.iec_62304_class}
HAZARD: {ctx.hazard}
HARM: {ctx.harm}
SEVERITY: {ctx.severity}
RISK BEFORE: {ctx.risk_level_before_mitigation}
RISK AFTER: {ctx.risk_level_after_mitigation}
RESIDUAL RISK ACCEPTABLE: {ctx.residual_risk_acceptable}

RISK CONTROLS:
{controls_str}

Create one matrix row per risk control, linking REQ → HAZARD → CONTROL → VERIFICATION → RESIDUAL RISK.

Return ONLY a JSON object:
{{
  "requirement_id": "REQ-001",
  "requirement_text": "{req_snippet}",
  "matrix": [
    {{
      "row_id": "TR-001",
      "req_id": "REQ-001",
      "req_text": "<requirement>",
      "hazard_id": "HAZ-001",
      "hazard_description": "<hazard>",
      "hazardous_situation": "<situation>",
      "harm": "<harm>",
      "risk_level_before": "<risk before>",
      "control_id": "RC-001",
      "control_description": "<control>",
      "control_type": "design" | "protective" | "information",
      "verification_id": "VER-001",
      "verification_method": "<method>",
      "verification_acceptance_criteria": "<pass/fail criteria>",
      "residual_risk_level": "<risk after>",
      "residual_risk_acceptable": true | false,
      "iec_62304_activity": "<relevant IEC 62304 activity>",
      "iso_14971_clause": "<relevant ISO 14971 clause>"
    }}
  ],
  "coverage_summary": {{
    "total_requirements": 1,
    "requirements_with_hazards": 1,
    "requirements_with_controls": <N>,
    "requirements_verified": <N>,
    "traceability_complete": true | false
  }},
  "regulatory_references": ["IEC 62304", "ISO 14971", "IEC 62366-1", "ISO 13485"]
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.traceability = data
