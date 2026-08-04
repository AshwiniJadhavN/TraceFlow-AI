"""System-level orchestrator for system engineers.

Runs the full system engineering pipeline:
  Stage 0 : RequirementDecompositionAgent  (HW/SW/HF/IF allocation)
  Stage 1 : ClassificationAgent            (IEC 62304 class)
  Stage 2 : HAZOPAgent + InterfaceHazardAgent  [parallel]
  Stage 3 : HazardAgent                   (ISO 14971 software hazard)
  Stage 4 : FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent  [parallel]
  Stage 5 : MitigationAgent
  Stage 6 : RiskBenefitAgent
  Stage 7 : TraceabilityAgent
  Stage 8 : VerificationPlanAgent
  Stage 9 : ReviewAgent                   (self-reflection)
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import anthropic

from agents.base_agent import MODEL
from agents.classification_agent import ClassificationAgent
from agents.fmea_agent import FMEAAgent
from agents.fta_agent import FTAAgent
from agents.hazard_agent import HazardAgent
from agents.hazop_agent import HAZOPAgent
from agents.interface_hazard_agent import InterfaceHazardAgent
from agents.mitigation_agent import MitigationAgent
from agents.requirement_decomposition_agent import RequirementDecompositionAgent
from agents.review_agent import ReviewAgent
from agents.risk_benefit_agent import RiskBenefitAgent
from agents.security_agent import SecurityAgent
from agents.traceability_agent import TraceabilityAgent
from agents.usability_agent import UsabilityAgent
from agents.verification_plan_agent import VerificationPlanAgent
from context import RiskContext
from observability.tracing import get_tracer, mark_span_error

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

MAX_RETRIES = 3


class SystemOrchestrator:
    """Full system engineering pipeline for system engineers."""

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)

    async def _run_agent_with_retry(self, agent: Any, ctx: RiskContext) -> None:
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            with tracer.start_as_current_span("traceflow.agent.run") as span:
                span.set_attributes(
                    {
                        "traceflow.pipeline": ctx.pipeline_name,
                        "traceflow.agent": agent.agent_name,
                        "traceflow.attempt": attempt,
                    }
                )
                try:
                    await agent.run(ctx)
                    logger.info("  + %s completed (attempt %d)", agent.agent_name, attempt)
                    ctx.audit_trail.append(
                        {
                            "agent": agent.agent_name,
                            "status": "success",
                            "attempt": attempt,
                            "model": MODEL,
                            "timestamp_utc": datetime.now(UTC).isoformat(),
                        }
                    )
                    return
                except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
                    last_exc = exc
                    mark_span_error(span, exc)
                    logger.warning(
                        "  ! %s attempt %d/%d failed: %s",
                        agent.agent_name,
                        attempt,
                        MAX_RETRIES,
                        exc,
                    )
                    if attempt < MAX_RETRIES:
                        ctx.errors.append(
                            f"{agent.agent_name} attempt {attempt} error: {exc}. "
                            "Return ONLY valid JSON matching the required schema."
                        )
                    ctx.audit_trail.append(
                        {
                            "agent": agent.agent_name,
                            "status": "retry" if attempt < MAX_RETRIES else "failed",
                            "attempt": attempt,
                            "model": MODEL,
                            "error": str(exc),
                            "timestamp_utc": datetime.now(UTC).isoformat(),
                        }
                    )
        raise RuntimeError(
            f"{agent.agent_name} failed after {MAX_RETRIES} attempts. Last error: {last_exc}"
        )

    @staticmethod
    def _check_gather(results: Sequence[Any], stage: str) -> None:
        failures = [str(r) for r in results if isinstance(r, Exception)]
        if failures:
            raise RuntimeError(
                f"{stage} failed ({len(failures)}/{len(results)} agents): " + " | ".join(failures)
            )

    async def run(self, requirement: str, system_description: str = "") -> dict[str, Any]:
        """Execute the system engineering pipeline and return the assembled report."""
        with tracer.start_as_current_span("traceflow.pipeline.system") as span:
            span.set_attributes(
                {
                    "traceflow.requirement_length": len(requirement),
                    "traceflow.system_context_length": len(system_description),
                }
            )
            ctx = RiskContext(requirement=requirement)
            ctx.pipeline_name = "system"
            ctx.model_name = MODEL
            ctx.system_description = system_description or None
            ctx.prepare_model_inputs()
            logger.info("SystemOrchestrator starting: %s...", requirement[:80])

            logger.info("Stage 0: RequirementDecompositionAgent")
            await self._run_agent_with_retry(RequirementDecompositionAgent(self.client), ctx)

            logger.info("Stage 1: ClassificationAgent")
            await self._run_agent_with_retry(ClassificationAgent(self.client), ctx)

            logger.info("Stage 2: HAZOPAgent + InterfaceHazardAgent [parallel]")
            stage2 = await asyncio.gather(
                self._run_agent_with_retry(HAZOPAgent(self.client), ctx),
                self._run_agent_with_retry(InterfaceHazardAgent(self.client), ctx),
                return_exceptions=True,
            )
            self._check_gather(stage2, "Stage 2")

            logger.info("Stage 3: HazardAgent")
            await self._run_agent_with_retry(HazardAgent(self.client), ctx)

            logger.info("Stage 4: FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent [parallel]")
            stage4 = await asyncio.gather(
                self._run_agent_with_retry(FMEAAgent(self.client), ctx),
                self._run_agent_with_retry(FTAAgent(self.client), ctx),
                self._run_agent_with_retry(UsabilityAgent(self.client), ctx),
                self._run_agent_with_retry(SecurityAgent(self.client), ctx),
                return_exceptions=True,
            )
            self._check_gather(stage4, "Stage 4")

            logger.info("Stage 5: MitigationAgent")
            await self._run_agent_with_retry(MitigationAgent(self.client), ctx)

            logger.info("Stage 6: RiskBenefitAgent")
            await self._run_agent_with_retry(RiskBenefitAgent(self.client), ctx)

            logger.info("Stage 7: TraceabilityAgent")
            await self._run_agent_with_retry(TraceabilityAgent(self.client), ctx)

            logger.info("Stage 8: VerificationPlanAgent")
            await self._run_agent_with_retry(VerificationPlanAgent(self.client), ctx)

            logger.info("Stage 9: ReviewAgent [self-reflection]")
            await self._run_agent_with_retry(ReviewAgent(self.client), ctx)

            logger.info("SystemOrchestrator pipeline complete")
            span.set_attribute("traceflow.audit_events", len(ctx.audit_trail))
            return ctx.to_report_dict()
