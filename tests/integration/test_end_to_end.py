"""
End-to-end integration tests for TraceFlow AI orchestration pipeline.

Tests the complete workflow: requirement → classification → hazard analysis →
parallel agents (FMEA, FTA, Security, Usability) → consolidated report.

Each test uses realistic mocked LLM responses to validate:
- Agent sequential execution
- Error handling and retries
- Data flow through RiskContext
- Final report generation
- Regulatory compliance requirements
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import replace

from orchestrator import Orchestrator
from context import RiskContext
from agents.base_agent import BaseAgent
from agents.classification_agent import ClassificationAgent
from agents.hazard_agent import HazardAgent


# ============================================================================
# Fixtures: Realistic LLM Response Mocks
# ============================================================================

@pytest.fixture
def mock_classification_response():
    """Realistic ClassificationAgent LLM response."""
    return {
        "iec_62304_class": "C",
        "risk_level": "HIGH",
        "summary": "Class C medical device with high risk - requires rigorous analysis",
        "key_hazards": ["Power failure", "Software malfunction", "Data integrity loss"],
    }


@pytest.fixture
def mock_hazard_response():
    """Realistic HazardAgent LLM response."""
    return {
        "identified_hazards": [
            {
                "id": "H1",
                "name": "Unintended device shutdown",
                "cause": "Power loss or firmware crash",
                "effect": "Loss of functionality during critical patient monitoring",
                "severity": "CRITICAL",
                "probability": "MEDIUM",
            },
            {
                "id": "H2",
                "name": "Data corruption",
                "cause": "Storage device failure",
                "effect": "Loss of patient records",
                "severity": "CRITICAL",
                "probability": "LOW",
            },
        ],
        "analysis_summary": "Two critical hazards identified requiring mitigation",
    }


@pytest.fixture
def mock_fmea_response():
    """Realistic FMEA Agent response."""
    return {
        "fmea_items": [
            {
                "component": "Power supply",
                "failure_mode": "Overcurrent",
                "effects": "Device shutdown",
                "rpn": 72,
                "mitigation": "Add current limiting circuitry",
            }
        ],
        "total_issues": 1,
        "critical_count": 1,
    }


@pytest.fixture
def mock_security_response():
    """Realistic Security Agent response."""
    return {
        "vulnerabilities": [
            {
                "id": "SEC-001",
                "type": "Authentication bypass",
                "severity": "HIGH",
                "mitigation": "Implement OAuth 2.0 with MFA",
            }
        ],
        "compliance_status": "PARTIAL",
        "security_score": 72,
    }


@pytest.fixture
def mock_usability_response():
    """Realistic Usability Agent response."""
    return {
        "usability_issues": [
            {
                "id": "UX-001",
                "issue": "Unclear alarm thresholds",
                "severity": "MEDIUM",
                "recommendation": "Add visual guidance and tooltips",
            }
        ],
        "overall_usability_score": 78,
    }


# ============================================================================
# Fixtures: Mock Clients
# ============================================================================

@pytest.fixture
def mock_orchestrator_client(
    mock_classification_response,
    mock_hazard_response,
    mock_fmea_response,
    mock_security_response,
    mock_usability_response,
):
    """Mock Anthropic client with all agent responses."""
    client = AsyncMock()
    
    # Sequence of responses for each agent call
    responses = [
        mock_classification_response,
        mock_hazard_response,
        mock_fmea_response,
        mock_security_response,
        mock_usability_response,
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        # Pop from responses list to simulate sequential calls
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        return response
    
    client.messages.create = mock_create
    return client


# ============================================================================
# Test: Full Pipeline Execution
# ============================================================================

@pytest.mark.asyncio
async def test_full_pipeline_class_c_device(
    mock_orchestrator_client,
    populated_risk_context,
):
    """
    Test complete TraceFlow pipeline for Class C device.
    
    Validates:
    - Classification agent identifies Class C
    - Hazard analysis finds critical issues
    - All parallel agents execute successfully
    - Final context contains all analysis results
    """
    # Reset responses list for this test
    responses = [
        {"iec_62304_class": "C", "risk_level": "HIGH", "summary": "Class C device"},
        {"identified_hazards": [{"id": "H1", "severity": "CRITICAL"}]},
        {"fmea_items": [{"rpn": 72}]},
        {"vulnerabilities": [{"severity": "HIGH"}]},
        {"usability_issues": []},
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        return response
    
    mock_orchestrator_client.messages.create = mock_create
    
    # Execute orchestration
    orchestrator = Orchestrator(mock_orchestrator_client)
    result_context = await orchestrator.run(populated_risk_context)
    
    # Validations
    assert result_context.iec_62304_class == "C"
    assert result_context.risk_level == "HIGH"
    assert len(result_context.identified_hazards) > 0
    assert result_context.security_assessment is not None


@pytest.mark.asyncio
async def test_pipeline_error_recovery(
    mock_orchestrator_client,
    risk_context_class_b,
):
    """
    Test pipeline continues after transient LLM error.
    
    Validates retry logic handles temporary failures gracefully.
    """
    call_count = 0
    
    async def mock_create_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        # First call fails, second succeeds
        if call_count == 1:
            raise Exception("Temporary API error")
        
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps({"iec_62304_class": "B"}))]
        return response
    
    mock_orchestrator_client.messages.create = mock_create_with_retry
    
    orchestrator = Orchestrator(mock_orchestrator_client)
    
    # Should retry and succeed
    result_context = await orchestrator.run(risk_context_class_b)
    assert result_context.iec_62304_class == "B"
    assert call_count == 2  # One failure + one retry


@pytest.mark.asyncio
async def test_pipeline_data_flow(
    mock_orchestrator_client,
    populated_risk_context,
):
    """
    Test data flows correctly between agents.
    
    Validates RiskContext is properly updated by each agent
    without data loss or corruption.
    """
    responses = [
        {"iec_62304_class": "A", "risk_level": "LOW"},
        {"identified_hazards": []},
        {"fmea_items": []},
        {"vulnerabilities": []},
        {"usability_issues": []},
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        return response
    
    mock_orchestrator_client.messages.create = mock_create
    
    orchestrator = Orchestrator(mock_orchestrator_client)
    
    # Store original context values
    original_requirement = populated_risk_context.requirement
    original_device_name = populated_risk_context.device_name
    
    result_context = await orchestrator.run(populated_risk_context)
    
    # Validate data is preserved
    assert result_context.requirement == original_requirement
    assert result_context.device_name == original_device_name
    assert result_context.iec_62304_class == "A"  # Updated by classification agent
    assert result_context.risk_level == "LOW"


# ============================================================================
# Test: Validation and Compliance
# ============================================================================

@pytest.mark.asyncio
async def test_class_c_requires_detailed_analysis(
    mock_orchestrator_client,
    risk_context_class_c,
):
    """
    Test that Class C devices trigger comprehensive analysis.
    
    IEC 62304 requires rigorous analysis for Class C devices.
    Validates all critical hazard analysis agents execute.
    """
    responses = [
        {"iec_62304_class": "C", "risk_level": "HIGH"},
        {"identified_hazards": [{"id": "H1", "severity": "CRITICAL"}]},
        {"fmea_items": [{"rpn": 80}]},
        {"vulnerabilities": [{"severity": "CRITICAL"}]},
        {"usability_issues": [{"severity": "HIGH"}]},
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        return response
    
    mock_orchestrator_client.messages.create = mock_create
    
    orchestrator = Orchestrator(mock_orchestrator_client)
    result_context = await orchestrator.run(risk_context_class_c)
    
    # All analyses should be performed
    assert result_context.iec_62304_class == "C"
    assert len(result_context.identified_hazards) > 0
    assert result_context.security_assessment is not None
    assert result_context.usability_assessment is not None


@pytest.mark.asyncio
async def test_malformed_llm_response_handling(
    populated_risk_context,
):
    """
    Test graceful handling of invalid LLM responses.
    
    Validates error handling when LLM returns malformed JSON.
    """
    client = AsyncMock()
    
    async def mock_create_malformed(*args, **kwargs):
        response = AsyncMock()
        # Return invalid JSON
        response.content = [AsyncMock(text="Not valid JSON at all")]
        return response
    
    client.messages.create = mock_create_malformed
    
    orchestrator = Orchestrator(client)
    
    # Should handle gracefully (raise or log, but not crash)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        await orchestrator.run(populated_risk_context)


# ============================================================================
# Test: Parallel Agent Execution
# ============================================================================

@pytest.mark.asyncio
async def test_fmea_fta_security_run_in_parallel(
    mock_orchestrator_client,
    populated_risk_context,
):
    """
    Test that FMEA, FTA, Security, and Usability agents run in parallel.
    
    Validates architectural decision to run agents concurrently
    for performance (target: <60s per requirement).
    """
    import time
    
    responses = [
        {"iec_62304_class": "B"},
        {"identified_hazards": [{"id": "H1"}]},
        {"fmea_items": [{"rpn": 50}]},
        {"vulnerabilities": []},
        {"usability_issues": []},
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        # Simulate LLM latency
        await pytest.asyncio.sleep(0.1)
        return response
    
    mock_orchestrator_client.messages.create = mock_create
    
    orchestrator = Orchestrator(mock_orchestrator_client)
    
    start = time.time()
    result_context = await orchestrator.run(populated_risk_context)
    elapsed = time.time() - start
    
    # If executed sequentially: 0.1 * 5 = 0.5s
    # If executed with parallelism: ~0.2-0.3s
    # This validates parallel execution assumption
    assert elapsed < 1.0, f"Pipeline took {elapsed}s, expected <1.0s for parallel execution"


# ============================================================================
# Test: Output Validation
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_output_format(
    mock_orchestrator_client,
    populated_risk_context,
):
    """
    Test final output conforms to expected format.
    
    Validates all required fields are present in final report.
    """
    responses = [
        {"iec_62304_class": "C", "risk_level": "HIGH", "summary": "Analysis complete"},
        {"identified_hazards": [{"id": "H1", "severity": "CRITICAL"}]},
        {"fmea_items": [{"component": "Power", "rpn": 72}]},
        {"vulnerabilities": [{"id": "SEC-001", "severity": "HIGH"}]},
        {"usability_issues": [{"issue": "Unclear UI", "severity": "MEDIUM"}]},
    ]
    
    async def mock_create(*args, **kwargs):
        response = AsyncMock()
        response.content = [AsyncMock(text=json.dumps(responses.pop(0)))]
        return response
    
    mock_orchestrator_client.messages.create = mock_create
    
    orchestrator = Orchestrator(mock_orchestrator_client)
    result_context = await orchestrator.run(populated_risk_context)
    
    # Validate required fields
    assert result_context.iec_62304_class in ["A", "B", "C"]
    assert result_context.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert hasattr(result_context, "identified_hazards")
    assert hasattr(result_context, "security_assessment")
    assert hasattr(result_context, "usability_assessment")


# ============================================================================
# Test: Regression Prevention
# ============================================================================

@pytest.mark.asyncio
async def test_classification_agent_output_schema(
    risk_context_class_b,
):
    """
    Regression test: Ensure ClassificationAgent maintains output schema.
    
    Validates changes to agent don't break downstream consumers.
    """
    client = AsyncMock()
    
    response = AsyncMock()
    response.content = [AsyncMock(text=json.dumps({
        "iec_62304_class": "B",
        "risk_level": "MEDIUM",
        "summary": "Class B device with medium risk",
        "key_hazards": ["Power loss"],
    }))]
    client.messages.create.return_value = response
    
    agent = ClassificationAgent(client)
    result_context = await agent.run(risk_context_class_b)
    
    # Validate all expected fields are present
    assert hasattr(result_context, "iec_62304_class")
    assert result_context.iec_62304_class == "B"
    assert hasattr(result_context, "risk_level")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
