"""Unit tests for individual sub-agents (all API calls are mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agents.base_agent import BaseAgent
from agents.classification_agent import ClassificationAgent
from agents.fmea_agent import FMEAAgent
from agents.hazard_agent import HazardAgent
from agents.review_agent import ReviewAgent
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


class TestBaseAgentExtractJson:
    def test_plain_json(self):
        assert BaseAgent.extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced(self):
        assert BaseAgent.extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_embedded_in_text(self):
        result = BaseAgent.extract_json('Here is the answer: {"a": 1} done.')
        assert result == {"a": 1}

    def test_invalid_raises(self):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            BaseAgent.extract_json("no braces here at all")


class TestClassificationAgent:
    @pytest.mark.asyncio
    async def test_applies_class_to_context(self):
        payload = {
            "iec_62304_class": "C",
            "rationale": "Life-critical display",
            "key_factors": ["cardiac monitoring"],
            "intended_use": "cardiac catheterization",
            "potential_for_serious_injury": True,
        }
        agent = ClassificationAgent(_mock_client(json.dumps(payload)))
        ctx = RiskContext(requirement=REQ)
        await agent.run(ctx)
        assert ctx.iec_62304_class == "C"
        assert "Life-critical" in (ctx.iec_62304_rationale or "")

    def test_builds_prompt_with_requirement(self):
        agent = ClassificationAgent(MagicMock())
        prompt = agent.build_user_prompt(RiskContext(requirement=REQ))
        assert REQ in prompt
        assert "IEC 62304" in prompt


class TestHazardAgent:
    @pytest.mark.asyncio
    async def test_applies_hazard_to_context(self):
        payload = {
            "hazard": "Incorrect waveform data",
            "hazardous_situation": "Clinician sees erroneous waveform",
            "harm": "Incorrect treatment decision",
            "harm_type": "patient",
            "probability_before_mitigation": "Occasional",
            "probability_rationale": "Software bugs possible",
            "severity": "Critical",
            "severity_rationale": "Severe injury possible",
            "risk_level_before_mitigation": "High",
            "additional_hazards": [],
        }
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.iec_62304_rationale = "Life-critical"
        agent = HazardAgent(_mock_client(json.dumps(payload)))
        await agent.run(ctx)
        assert ctx.hazard == "Incorrect waveform data"
        assert ctx.severity == "Critical"
        assert ctx.risk_level_before_mitigation == "High"


class TestFMEAAgent:
    @pytest.mark.asyncio
    async def test_rpn_stored_in_context(self):
        payload = {
            "item": "Waveform Display Module",
            "function": "Render real-time waveforms",
            "failure_mode": "Display freezes",
            "local_effect": "Waveform stops updating",
            "system_effect": "Clinician sees stale data",
            "end_effect": "Incorrect decision",
            "severity_score": 8,
            "occurrence_score": 4,
            "detectability_score": 6,
            "rpn_before": 192,
            "current_controls": ["watchdog"],
            "recommended_action": "Add data freshness indicator",
            "responsible_party": "Software Engineer",
            "severity_score_after": 8,
            "occurrence_score_after": 2,
            "detectability_score_after": 2,
            "rpn_after": 32,
        }
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Stale waveform"
        ctx.hazardous_situation = "Clinician sees outdated data"
        ctx.harm = "Incorrect treatment"
        ctx.severity = "Critical"
        ctx.probability_before_mitigation = "Occasional"
        agent = FMEAAgent(_mock_client(json.dumps(payload)))
        await agent.run(ctx)
        assert ctx.fmea is not None
        assert ctx.fmea["rpn_before"] == 192
        assert ctx.fmea["rpn_after"] == 32


class TestReviewAgent:
    @pytest.mark.asyncio
    async def test_validation_summary_stored(self):
        payload = {
            "consistent": True,
            "flags": [],
            "corrections": [],
            "completeness_score": 95,
            "regulatory_gaps": [],
            "reviewed_by": "ReviewAgent",
            "review_confidence": "High",
            "summary": "Report is consistent and complete.",
        }
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Stale waveform"
        ctx.harm = "Misdiagnosis"
        ctx.severity = "Critical"
        ctx.risk_level_before_mitigation = "High"
        ctx.risk_level_after_mitigation = "Low"
        ctx.residual_risk_acceptable = True
        agent = ReviewAgent(_mock_client(json.dumps(payload)))
        await agent.run(ctx)
        assert ctx.validation_summary is not None
        assert ctx.validation_summary["consistent"] is True
        assert ctx.validation_summary["reviewed_by"] == "ReviewAgent"
