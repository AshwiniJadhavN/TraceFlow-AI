"""Orchestrator Agent - decomposes requirements and assembles the final risk report."""

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
from agents.mitigation_agent import MitigationAgent
from agents.review_agent import ReviewAgent
from agents.risk_benefit_agent import RiskBenefitAgent
from agents.security_agent import SecurityAgent
from agents.traceability_agent import TraceabilityAgent
from agents.usability_agent import UsabilityAgent
from context import RiskContext
from observability.tracing import get_tracer, mark_span_error

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

MAX_RETRIES = 3


class Orchestrator:
    """
    Central orchestrator.

    Dependency graph
    ----------------
    ClassificationAgent
        |-> HazardAgent
                |-> FMEAAgent       --+
                |-> FTAAgent        --+--> MitigationAgent
                |-> UsabilityAgent  --|        |--> RiskBenefitAgent
                |-> SecurityAgent   --+                   |--> TraceabilityAgent
                                                                      |--> ReviewAgent
    """

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)

    async def _run_agent_with_retry(self, agent: Any, ctx: RiskContext) -> None:
        """Run *agent* against *ctx*, retrying up to MAX_RETRIES times."""
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
            f"{agent.agent_name} failed after {MAX_RETRIES} attempts. " f"Last error: {last_exc}"
        )

    @staticmethod
    def _check_gather_results(results: Sequence[Any], stage: str) -> None:
        """Raise a consolidated RuntimeError if any gather result is an exception."""
        failures = [str(r) for r in results if isinstance(r, Exception)]
        if failures:
            raise RuntimeError(
                f"{stage} failed ({len(failures)}/{len(results)} agents): " + " | ".join(failures)
            )

    async def run(self, requirement: str | RiskContext) -> RiskContext:
        """Execute the full agentic pipeline and return the populated RiskContext.

        *requirement* can be either a plain requirement string (the typical CLI
        path) or a pre-populated :class:`RiskContext` (used in tests and when
        the caller wants to supply additional context upfront).
        """
        with tracer.start_as_current_span("traceflow.pipeline.software") as span:
            if isinstance(requirement, RiskContext):
                ctx = requirement
            else:
                ctx = RiskContext(requirement=requirement)
            span.set_attribute("traceflow.requirement_length", len(ctx.requirement))
            ctx.pipeline_name = "software"
            ctx.model_name = MODEL
            ctx.prepare_model_inputs()
            logger.info("TraceFlow AI starting: %s...", ctx.requirement[:80])

            logger.info("Stage 1: ClassificationAgent")
            await self._run_agent_with_retry(ClassificationAgent(self.client), ctx)

            logger.info("Stage 2: HazardAgent")
            await self._run_agent_with_retry(HazardAgent(self.client), ctx)

            logger.info("Stage 3: FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent [parallel]")
            stage3 = await asyncio.gather(
                self._run_agent_with_retry(FMEAAgent(self.client), ctx),
                self._run_agent_with_retry(FTAAgent(self.client), ctx),
                self._run_agent_with_retry(UsabilityAgent(self.client), ctx),
                self._run_agent_with_retry(SecurityAgent(self.client), ctx),
                return_exceptions=True,
            )
            self._check_gather_results(stage3, "Stage 3")

            logger.info("Stage 4: MitigationAgent")
            await self._run_agent_with_retry(MitigationAgent(self.client), ctx)

            logger.info("Stage 5: RiskBenefitAgent")
            await self._run_agent_with_retry(RiskBenefitAgent(self.client), ctx)

            logger.info("Stage 6: TraceabilityAgent")
            await self._run_agent_with_retry(TraceabilityAgent(self.client), ctx)

            logger.info("Stage 7: ReviewAgent [self-reflection]")
            await self._run_agent_with_retry(ReviewAgent(self.client), ctx)

            logger.info("TraceFlow AI pipeline complete")
            span.set_attribute("traceflow.audit_events", len(ctx.audit_trail))
            return ctx
