"""Unit tests for SecurityAgent (API calls mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agents.security_agent import SecurityAgent
from context import RiskContext

REQ = (
    "The system shall display real-time hemodynamic waveforms to the "
    "clinician during cardiac catheterization."
)


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    content = MagicMock()
    content.text = response_text
    client.messages.create.return_value = MagicMock(content=[content])
    return client


def _valid_payload(stride_category: str = "Tampering", attack_vector: str = "Network") -> dict:
    return {
        "assets": ["patient waveform data", "network interface"],
        "threats": [
            {
                "id": "SEC-001",
                "stride_category": stride_category,
                "threat_description": "Attacker modifies waveform data in transit",
                "attack_vector": attack_vector,
                "attack_complexity": "Low",
                "exploitability": "High",
                "impact_on_patient_safety": "Critical",
                "cybersecurity_risk_level": "High",
                "affected_asset": "patient waveform data",
                "aami_tir57_reference": "TIR57 §5.4",
            }
        ],
        "security_controls": [
            {
                "id": "SC-001",
                "addresses_threat": "SEC-001",
                "control_type": "technical",
                "description": "TLS 1.3 with mutual authentication",
                "standard_reference": "AAMI TIR57 §6.3",
                "acceptance_criteria": "No plain-text transmission confirmed by penetration test",
            }
        ],
        "residual_cybersecurity_risk": "Low",
        "sbom_required": True,
        "coordinated_vulnerability_disclosure_required": True,
        "security_summary": {
            "total_threats": 1,
            "high_or_critical_threats": 1,
            "stride_categories_identified": [stride_category],
            "total_security_controls": 1,
        },
    }


class TestSecurityAgent:
    async def test_stores_cybersecurity_risks_in_context(self):
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Waveform data corruption"
        ctx.harm = "Incorrect clinical decision"
        agent = SecurityAgent(_mock_client(json.dumps(_valid_payload())))
        await agent.run(ctx)
        assert ctx.cybersecurity_risks is not None
        assert ctx.cybersecurity_risks["residual_cybersecurity_risk"] == "Low"
        assert len(ctx.cybersecurity_risks["threats"]) == 1
        assert ctx.cybersecurity_risks["security_summary"]["total_threats"] == 1

    async def test_all_stride_categories_accepted(self):
        from agents.security_agent import VALID_STRIDE

        for category in VALID_STRIDE:
            ctx = RiskContext(requirement=REQ)
            ctx.iec_62304_class = "C"
            agent = SecurityAgent(_mock_client(json.dumps(_valid_payload(stride_category=category))))
            await agent.run(ctx)
            assert ctx.cybersecurity_risks is not None

    async def test_invalid_stride_category_raises_value_error(self):
        payload = _valid_payload()
        payload["threats"][0]["stride_category"] = "PhishingAttack"  # not in STRIDE
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        agent = SecurityAgent(_mock_client(json.dumps(payload)))
        with pytest.raises(ValueError, match="stride_category"):
            await agent.run(ctx)

    async def test_invalid_attack_vector_raises_value_error(self):
        payload = _valid_payload()
        payload["threats"][0]["attack_vector"] = "Wireless"  # not a valid vector
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        agent = SecurityAgent(_mock_client(json.dumps(payload)))
        with pytest.raises(ValueError, match="attack_vector"):
            await agent.run(ctx)

    async def test_invalid_exploitability_raises_value_error(self):
        payload = _valid_payload()
        payload["threats"][0]["exploitability"] = "Critical"  # not Low/Medium/High
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        agent = SecurityAgent(_mock_client(json.dumps(payload)))
        with pytest.raises(ValueError, match="exploitability"):
            await agent.run(ctx)

    async def test_invalid_cyber_risk_level_raises_value_error(self):
        payload = _valid_payload()
        payload["threats"][0]["cybersecurity_risk_level"] = "Unacceptable"  # not in VALID_CYBER_RISK
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        agent = SecurityAgent(_mock_client(json.dumps(payload)))
        with pytest.raises(ValueError, match="cybersecurity_risk_level"):
            await agent.run(ctx)

    async def test_empty_threats_list_accepted(self):
        payload = _valid_payload()
        payload["threats"] = []
        payload["security_summary"]["total_threats"] = 0
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        agent = SecurityAgent(_mock_client(json.dumps(payload)))
        await agent.run(ctx)
        assert ctx.cybersecurity_risks["threats"] == []

    def test_prompt_contains_requirement_and_stride_reference(self):
        agent = SecurityAgent(MagicMock())
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Display error"
        ctx.harm = "Misdiagnosis"
        prompt = agent.build_user_prompt(ctx)
        assert REQ in prompt
        assert "STRIDE" in prompt
        assert "AAMI TIR57" in prompt

    def test_agent_name_property(self):
        agent = SecurityAgent(MagicMock())
        assert agent.agent_name == "SecurityAgent"

    def test_system_prompt_is_non_empty_string(self):
        agent = SecurityAgent(MagicMock())
        assert isinstance(agent.system_prompt, str)
        assert len(agent.system_prompt) > 100
        assert "STRIDE" in agent.system_prompt
        assert "AAMI TIR57" in agent.system_prompt
