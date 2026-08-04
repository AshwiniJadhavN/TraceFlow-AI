"""Output validators for TraceFlow AI agents.

All public functions either:
- Return the (possibly auto-corrected) value, or
- Raise ValueError so the orchestrator retry-with-feedback loop fires.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import RiskContext

VALID_CLASSES = {"A", "B", "C"}
VALID_PROBABILITIES = {"Frequent", "Probable", "Occasional", "Remote", "Improbable"}
VALID_SEVERITIES = {"Negligible", "Marginal", "Critical", "Catastrophic"}
VALID_RISK_LEVELS = {"Low", "Medium", "High", "Unacceptable"}

# ISO 14971 Annex C qualitative risk matrix
# Key: (probability, severity) -> expected risk level
RISK_MATRIX: dict[tuple[str, str], str] = {
    ("Frequent", "Negligible"): "Medium",
    ("Frequent", "Marginal"): "High",
    ("Frequent", "Critical"): "Unacceptable",
    ("Frequent", "Catastrophic"): "Unacceptable",
    ("Probable", "Negligible"): "Low",
    ("Probable", "Marginal"): "Medium",
    ("Probable", "Critical"): "High",
    ("Probable", "Catastrophic"): "Unacceptable",
    ("Occasional", "Negligible"): "Low",
    ("Occasional", "Marginal"): "Medium",
    ("Occasional", "Critical"): "High",
    ("Occasional", "Catastrophic"): "Unacceptable",
    ("Remote", "Negligible"): "Low",
    ("Remote", "Marginal"): "Low",
    ("Remote", "Critical"): "Medium",
    ("Remote", "Catastrophic"): "High",
    ("Improbable", "Negligible"): "Low",
    ("Improbable", "Marginal"): "Low",
    ("Improbable", "Critical"): "Low",
    ("Improbable", "Catastrophic"): "Medium",
}


def check_enum(value: str, valid: set[str], field: str) -> str:
    """Raise ValueError if *value* is not in *valid*."""
    if value not in valid:
        raise ValueError(f"{field} value '{value}' is invalid. " f"Must be one of: {sorted(valid)}")
    return value


def validate_required_fields(
    data: dict,
    required_fields: Iterable[str],
    agent_name: str,
) -> None:
    """Raise ValueError when an agent response omits required top-level fields."""
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        raise ValueError(f"{agent_name}: missing required field(s): {', '.join(missing)}")


def correct_risk_level(probability: str, severity: str, reported: str) -> tuple[str, bool]:
    """Return (correct_risk_level, was_corrected) using the ISO 14971 matrix.

    If the combination is not in the matrix the reported value is returned
    unchanged so unknown enums don't cause silent failures.
    """
    expected = RISK_MATRIX.get((probability, severity))
    if expected is None or expected == reported:
        return reported, False
    return expected, True


def correct_fmea_rpn(data: dict) -> tuple[dict, list[str]]:
    """Validate FMEA RPN arithmetic and auto-correct wrong products.

    Returns (corrected_data, list_of_corrections_made).
    """
    corrections: list[str] = []

    for suffix, rpn_key in (("before", "rpn_before"), ("after", "rpn_after")):
        s_key = "severity_score" + ("" if suffix == "before" else "_after")
        o_key = "occurrence_score" + ("" if suffix == "before" else "_after")
        d_key = "detectability_score" + ("" if suffix == "before" else "_after")

        if not all(k in data for k in (s_key, o_key, d_key, rpn_key)):
            continue

        # Clamp scores to valid 1-10 range
        for k in (s_key, o_key, d_key):
            clamped = max(1, min(10, int(data[k])))
            if clamped != data[k]:
                corrections.append(f"{k} clamped {data[k]} -> {clamped}")
                data[k] = clamped

        expected_rpn = data[s_key] * data[o_key] * data[d_key]
        if data[rpn_key] != expected_rpn:
            corrections.append(
                f"{rpn_key} corrected {data[rpn_key]} -> {expected_rpn} "
                f"({data[s_key]}x{data[o_key]}x{data[d_key]})"
            )
            data[rpn_key] = expected_rpn

    return data, corrections


def build_review_summary(ctx: RiskContext) -> dict:
    """Extract the minimal fields needed by ReviewAgent.

    Avoids passing the full nested JSON (reduces tokens and 'lost in the
    middle' attention degradation).
    """
    fmea = ctx.fmea or {}
    traceability = ctx.traceability or {}
    rb = ctx.risk_benefit_analysis or {}
    controls = ctx.risk_controls or []
    sec = ctx.cybersecurity_risks or {}
    sec_summary = sec.get("security_summary", {})

    summary = {
        "requirement": (ctx.prompt_requirement or "")[:200],
        "iec_62304_class": ctx.iec_62304_class,
        "hazard": ctx.hazard,
        "severity": ctx.severity,
        "probability_before": ctx.probability_before_mitigation,
        "risk_level_before": ctx.risk_level_before_mitigation,
        "fmea": {
            "failure_mode": fmea.get("failure_mode"),
            "severity_score": fmea.get("severity_score"),
            "occurrence_score": fmea.get("occurrence_score"),
            "detectability_score": fmea.get("detectability_score"),
            "rpn_before": fmea.get("rpn_before"),
            "rpn_after": fmea.get("rpn_after"),
        },
        "probability_after": ctx.probability_after_mitigation,
        "severity_after": ctx.severity_after_mitigation,
        "risk_level_after": ctx.risk_level_after_mitigation,
        "residual_risk_acceptable": ctx.residual_risk_acceptable,
        "controls_count": len(controls),
        "controls": [
            {"id": c.get("id"), "type": c.get("type"), "addresses": c.get("addresses")}
            for c in controls
        ],
        "risk_benefit_conclusion": {
            "benefit_outweighs_risk": rb.get("benefit_outweighs_risk"),
            "conclusion": rb.get("overall_benefit_risk_conclusion", "")[:200],
        },
        "traceability_coverage": traceability.get("coverage_summary", {}),
    }
    if sec_summary:
        summary["cybersecurity"] = {
            "total_threats": sec_summary.get("total_threats"),
            "high_or_critical_threats": sec_summary.get("high_or_critical_threats"),
            "residual_cybersecurity_risk": sec.get("residual_cybersecurity_risk"),
            "stride_categories": sec_summary.get("stride_categories_identified", []),
        }
    return summary
