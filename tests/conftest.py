"""Shared pytest fixtures for TraceFlow AI tests."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from context import RiskContext

# ============= Mock LLM Clients =============


@pytest.fixture
def mock_anthropic_client():
    """Basic mock Anthropic client for agent tests."""
    client = MagicMock()
    content = MagicMock()
    content.text = json.dumps({"result": "success", "status": "complete"})
    client.messages.create.return_value = MagicMock(content=[content])
    return client


@pytest.fixture
def mock_async_client():
    """Async mock Anthropic client for async agent tests."""
    client = AsyncMock()
    content = MagicMock()
    content.text = json.dumps({"result": "success", "status": "complete"})
    client.messages.create = AsyncMock(return_value=MagicMock(content=[content]))
    return client


@pytest.fixture
def mock_client_with_response():
    """Factory fixture: create mock client with custom response."""

    def _make_client(response_text: str) -> MagicMock:
        client = MagicMock()
        content = MagicMock()
        content.text = response_text
        client.messages.create.return_value = MagicMock(content=[content])
        return client

    return _make_client


@pytest.fixture
def mock_async_client_with_response():
    """Factory fixture: create async mock client with custom response."""

    def _make_client(response_text: str) -> AsyncMock:
        client = AsyncMock()
        content = MagicMock()
        content.text = response_text
        client.messages.create = AsyncMock(return_value=MagicMock(content=[content]))
        return client

    return _make_client


# ============= Risk Context Fixtures =============


@pytest.fixture
def risk_context():
    """Fresh RiskContext for each test."""
    return RiskContext(
        requirement="The system shall display real-time hemodynamic waveforms."
    )


@pytest.fixture
def risk_context_class_a():
    """RiskContext with Class A device."""
    ctx = RiskContext(requirement="Simple display of static data.")
    ctx.iec_62304_class = "A"
    return ctx


@pytest.fixture
def risk_context_class_b():
    """RiskContext with Class B device."""
    ctx = RiskContext(requirement="System shall process vital signs.")
    ctx.iec_62304_class = "B"
    return ctx


@pytest.fixture
def risk_context_class_c():
    """RiskContext with Class C device (most stringent)."""
    ctx = RiskContext(requirement="System shall control drug infusion.")
    ctx.iec_62304_class = "C"
    return ctx


@pytest.fixture
def populated_risk_context():
    """Pre-populated context for downstream agent tests."""
    ctx = RiskContext(requirement="System shall log all access attempts.")
    ctx.iec_62304_class = "C"
    ctx.hazard = "Unauthorized access to patient data"
    ctx.hazardous_situation = "Attacker gains system access via weak credentials"
    ctx.harm = "Patient privacy breach"
    ctx.intended_use = "cardiac monitoring system"
    ctx.potential_for_serious_injury = True
    return ctx


# ============= Parametrization Helpers =============


@pytest.fixture(params=["A", "B", "C"])
def device_class(request):
    """Parametrize tests across IEC 62304 device classes."""
    return request.param


@pytest.fixture(
    params=[
        ("Improbable", "Negligible", "Low"),
        ("Remote", "Minor", "Low"),
        ("Occasional", "Major", "Medium"),
        ("Frequent", "Critical", "High"),
        ("Frequent", "Catastrophic", "High"),
    ]
)
def probability_severity_risk(request):
    """Parametrize probability/severity/risk combinations (ISO 14971)."""
    probability, severity, risk_level = request.param
    return {
        "probability": probability,
        "severity": severity,
        "expected_risk_level": risk_level,
    }


@pytest.fixture(
    params=[
        "Tampering",
        "Repudiation",
        "Information Disclosure",
        "Denial of Service",
        "Elevation of Privilege",
    ]
)
def stride_threat_category(request):
    """Parametrize STRIDE threat categories."""
    return request.param


# ============= Output/Response Fixtures =============


@pytest.fixture
def classification_agent_response():
    """Typical ClassificationAgent output (valid JSON)."""
    return {
        "iec_62304_class": "C",
        "rationale": "Life-critical function: drug delivery control",
        "key_factors": ["active_control", "patient_connected", "harm_catastrophic"],
        "intended_use": "Automated infusion pump for ICU monitoring",
        "potential_for_serious_injury": True,
    }


@pytest.fixture
def hazard_agent_response():
    """Typical HazardAgent output."""
    return {
        "hazard": "Incorrect drug dosage calculation",
        "hazardous_situation": "Software error in dosage formula",
        "harm": "Patient overdose or underdose",
        "harm_type": "patient",
        "probability_before_mitigation": "Occasional",
        "probability_rationale": "Boundary conditions may trigger calculation error",
        "severity": "Catastrophic",
        "severity_rationale": "Patient can receive 10x incorrect dose",
        "risk_level": "High",
    }


@pytest.fixture
def security_agent_response():
    """Typical SecurityAgent output (AAMI TIR57 compliance)."""
    return {
        "assets": ["patient_data", "infusion_commands", "system_logs"],
        "threats": [
            {
                "id": "SEC-001",
                "stride_category": "Tampering",
                "threat_description": "Attacker modifies infusion rate via network injection",
                "attack_vector": "Network",
                "attack_complexity": "Low",
                "exploitability": "High",
                "impact_on_patient_safety": "Critical",
                "cybersecurity_risk_level": "High",
                "affected_asset": "infusion_commands",
                "aami_tir57_reference": "TIR57 §5.4.2",
            }
        ],
        "security_controls": [
            {
                "id": "SC-001",
                "addresses_threat": "SEC-001",
                "control_type": "technical",
                "description": "TLS 1.3 with mutual authentication on all network channels",
                "standard_reference": "AAMI TIR57 §6.3",
                "acceptance_criteria": "Penetration testing confirms no injection possible",
            }
        ],
        "residual_cybersecurity_risk": "Low",
        "sbom_required": True,
        "coordinated_vulnerability_disclosure_required": True,
    }
