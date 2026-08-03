"""Utility helpers for building structured user prompts from RiskContext."""

from __future__ import annotations

import json

from context import RiskContext


def format_upstream_context(ctx: RiskContext) -> str:
    """Return a formatted summary of everything known so far.

    Used by downstream agents that need the full upstream picture.
    """
    sections: list[str] = []

    if ctx.iec_62304_class:
        sections.append(
            f"IEC 62304 CLASS: {ctx.iec_62304_class}\n" f"RATIONALE: {ctx.iec_62304_rationale}"
        )

    if ctx.hazard:
        sections.append(
            f"HAZARD: {ctx.hazard}\n"
            f"HAZARDOUS SITUATION: {ctx.hazardous_situation}\n"
            f"HARM: {ctx.harm}\n"
            f"SEVERITY: {ctx.severity}\n"
            f"PROBABILITY BEFORE: {ctx.probability_before_mitigation}\n"
            f"RISK LEVEL BEFORE: {ctx.risk_level_before_mitigation}"
        )

    if ctx.fmea:
        sections.append(f"FMEA:\n{json.dumps(ctx.fmea, indent=2)}")

    if ctx.fta:
        sections.append(f"FTA:\n{json.dumps(ctx.fta, indent=2)}")

    if ctx.risk_controls:
        sections.append(f"RISK CONTROLS:\n{json.dumps(ctx.risk_controls, indent=2)}")

    return "\n\n---\n\n".join(sections)


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate long text for safe inclusion in prompts."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"
