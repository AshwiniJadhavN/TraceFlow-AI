"""Security Risk Agent — AAMI TIR57 STRIDE threat modeling and cybersecurity risk assessment."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import SECURITY_SYSTEM_PROMPT

VALID_STRIDE = {
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
}
VALID_ATTACK_VECTORS = {"Physical", "Local", "Adjacent", "Network"}
VALID_EXPLOITABILITY = {"Low", "Medium", "High"}
VALID_CYBER_RISK = {"Low", "Medium", "High", "Critical"}


class SecurityAgent(BaseAgent):
    """AAMI TIR57 STRIDE threat modeling and cybersecurity risk assessment."""

    REQUIRED_FIELDS = (
        "assets",
        "threats",
        "security_controls",
        "residual_cybersecurity_risk",
        "sbom_required",
        "coordinated_vulnerability_disclosure_required",
        "security_summary",
    )

    @property
    def agent_name(self) -> str:
        return "SecurityAgent"

    @property
    def system_prompt(self) -> str:
        return SECURITY_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Perform a cybersecurity risk assessment per AAMI TIR57 for the following medical device software.

Requirement: {ctx.prompt_requirement}

IEC 62304 Class: {ctx.iec_62304_class or 'Not yet classified'}
Identified Hazard: {ctx.hazard or 'Not yet identified'}
Harm: {ctx.harm or 'Not yet identified'}

Apply STRIDE threat modeling. For each STRIDE category, assess whether a realistic threat exists for this
specific software. Identify all digital assets, enumerate threats, specify security controls, and determine
residual cybersecurity risk.

Return ONLY this JSON structure:
{{
  "assets": ["asset1", "asset2"],
  "threats": [
    {{
      "id": "SEC-001",
      "stride_category": "Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege",
      "threat_description": "specific, concrete threat for this device",
      "attack_vector": "Physical|Local|Adjacent|Network",
      "attack_complexity": "Low|High",
      "exploitability": "Low|Medium|High",
      "impact_on_patient_safety": "Negligible|Marginal|Critical|Catastrophic",
      "cybersecurity_risk_level": "Low|Medium|High|Critical",
      "affected_asset": "asset name",
      "aami_tir57_reference": "TIR57 §section"
    }}
  ],
  "security_controls": [
    {{
      "id": "SC-001",
      "addresses_threat": "SEC-001",
      "control_type": "technical|operational|administrative",
      "description": "specific control",
      "standard_reference": "AAMI TIR57 §x.x or IEC 62443-x-x",
      "acceptance_criteria": "measurable pass/fail criterion"
    }}
  ],
  "residual_cybersecurity_risk": "Low|Medium|High|Critical",
  "sbom_required": true,
  "coordinated_vulnerability_disclosure_required": true,
  "security_summary": {{
    "total_threats": 0,
    "high_or_critical_threats": 0,
    "stride_categories_identified": [],
    "total_security_controls": 0
  }}
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        for threat in data.get("threats", []):
            cat = threat.get("stride_category", "")
            if cat not in VALID_STRIDE:
                raise ValueError(
                    f"SecurityAgent: invalid stride_category '{cat}'. "
                    f"Must be one of: {sorted(VALID_STRIDE)}"
                )
            vec = threat.get("attack_vector", "")
            if vec not in VALID_ATTACK_VECTORS:
                raise ValueError(
                    f"SecurityAgent: invalid attack_vector '{vec}'. "
                    f"Must be one of: {sorted(VALID_ATTACK_VECTORS)}"
                )
            exp = threat.get("exploitability", "")
            if exp not in VALID_EXPLOITABILITY:
                raise ValueError(
                    f"SecurityAgent: invalid exploitability '{exp}'. "
                    f"Must be one of: {sorted(VALID_EXPLOITABILITY)}"
                )
            risk = threat.get("cybersecurity_risk_level", "")
            if risk not in VALID_CYBER_RISK:
                raise ValueError(
                    f"SecurityAgent: invalid cybersecurity_risk_level '{risk}'. "
                    f"Must be one of: {sorted(VALID_CYBER_RISK)}"
                )
        ctx.cybersecurity_risks = data
