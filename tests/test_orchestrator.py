"""Tests for the Orchestrator retry logic and context assembly."""

from __future__ import annotations

import pytest

from context import RiskContext
from orchestrator import Orchestrator

REQ = (
    "The system shall display real-time hemodynamic waveforms to the "
    "clinician during cardiac catheterization."
)


class TestRiskContext:
    def test_initial_state(self):
        ctx = RiskContext(requirement=REQ)
        assert ctx.requirement == REQ
        assert ctx.iec_62304_class is None
        assert ctx.errors == []

    def test_to_report_dict_keys(self):
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Stale waveform"
        report = ctx.to_report_dict()
        assert report["iec_62304_class"] == "C"
        assert report["hazard"] == "Stale waveform"
        assert "traceability" in report
        assert "validation_summary" in report
        assert report["audit_metadata"]["human_review_required"] is True


class TestOrchestratorRetry:
    @pytest.mark.asyncio
    async def test_succeeds_after_two_failures(self):
        orch = Orchestrator(api_key="test-key")
        orch_ctx = RiskContext(requirement=REQ)
        call_count = 0

        class FlakyAgent:
            agent_name = "FlakyAgent"

            async def run(self, ctx: RiskContext) -> None:
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ValueError("Simulated malformed JSON")

        await orch._run_agent_with_retry(FlakyAgent(), orch_ctx)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries_raise_runtime_error(self):
        orch = Orchestrator(api_key="test-key")
        orch_ctx = RiskContext(requirement=REQ)

        class AlwaysFailAgent:
            agent_name = "AlwaysFailAgent"

            async def run(self, ctx: RiskContext) -> None:
                raise ValueError("Always fails")

        with pytest.raises(RuntimeError, match="AlwaysFailAgent failed after"):
            await orch._run_agent_with_retry(AlwaysFailAgent(), orch_ctx)

    @pytest.mark.asyncio
    async def test_error_feedback_injected_into_context(self):
        orch = Orchestrator(api_key="test-key")
        orch_ctx = RiskContext(requirement=REQ)
        attempt = 0

        class ErrorInspectAgent:
            agent_name = "ErrorInspectAgent"

            async def run(self, ctx: RiskContext) -> None:
                nonlocal attempt
                attempt += 1
                if attempt == 1:
                    raise ValueError("bad JSON")
                # On 2nd attempt the error should be in ctx.errors
                assert any("ErrorInspectAgent" in e for e in ctx.errors)

        await orch._run_agent_with_retry(ErrorInspectAgent(), orch_ctx)
        assert attempt == 2
