"""Abstract base class shared by all TraceFlow sub-agents."""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import anthropic

from context import RiskContext
from observability.tracing import get_tracer, mark_span_error
from validators.output_validators import validate_required_fields

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
# Temperature 0 for deterministic, reproducible regulatory outputs.
TEMPERATURE = 0
tracer = get_tracer(__name__)


class BaseAgent(ABC):
    """Template for all sub-agents."""

    REQUIRED_FIELDS: tuple[str, ...] = ()

    def __init__(self, client: anthropic.Anthropic) -> None:
        self.client = client

    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def build_user_prompt(self, ctx: RiskContext) -> str: ...

    @abstractmethod
    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        """Write parsed output into the shared RiskContext."""
        ...

    def _call_api(self, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        """Extract the first valid JSON object from *text*.

        Handles plain JSON, markdown fenced blocks, and responses where
        the model prepends a short explanation before the JSON.
        """
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"(\{[\s\S]+\})", text)
        if match:
            return json.loads(match.group(1))

        raise ValueError(f"No valid JSON found in response: {text[:300]}")

    async def run(self, ctx: RiskContext) -> None:
        """Build prompt -> call API (in thread) -> parse -> apply to context."""
        prior_errors = [e for e in ctx.errors if self.agent_name in e]
        user_prompt = self.build_user_prompt(ctx)
        if prior_errors:
            user_prompt += "\n\n# ERROR FEEDBACK FROM PREVIOUS ATTEMPT (fix this):\n" + "\n".join(
                prior_errors
            )

        with tracer.start_as_current_span("traceflow.llm.request") as span:
            span.set_attributes(
                {
                    "traceflow.pipeline": ctx.pipeline_name,
                    "traceflow.agent": self.agent_name,
                    "traceflow.model": MODEL,
                    "traceflow.prompt_chars": len(user_prompt),
                    "traceflow.feedback_count": len(prior_errors),
                }
            )
            try:
                raw = await asyncio.to_thread(self._call_api, user_prompt)
                ctx.agent_logs[self.agent_name] = raw
                span.set_attribute("traceflow.response_chars", len(raw))

                data = self.extract_json(raw)
                validate_required_fields(data, self.REQUIRED_FIELDS, self.agent_name)
                self._apply_to_context(data, ctx)
            except Exception as exc:
                mark_span_error(span, exc)
                raise
