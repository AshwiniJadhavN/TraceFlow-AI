from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from validators.data_privacy import sanitize_for_model


@dataclass
class RiskContext:
    """Shared mutable context passed through the agent pipeline."""

    requirement: str = ""
    model_requirement: str = ""

    # System-level (populated by system engineering pipeline)
    system_description: str | None = None
    model_system_description: str | None = None
    decomposed_requirements: dict[str, Any] | None = None
    hazop_analysis: dict[str, Any] | None = None
    interface_hazards: dict[str, Any] | None = None
    verification_plan: dict[str, Any] | None = None

    # ClassificationAgent
    iec_62304_class: str | None = None
    iec_62304_rationale: str | None = None

    # HazardAgent
    hazard: str | None = None
    hazardous_situation: str | None = None
    harm: str | None = None
    probability_before_mitigation: str | None = None
    severity: str | None = None
    risk_level_before_mitigation: str | None = None

    # FMEAAgent
    fmea: dict[str, Any] | None = None

    # FTAAgent
    fta: dict[str, Any] | None = None

    # UsabilityAgent
    use_error_analysis: dict[str, Any] | None = None

    # SecurityAgent
    cybersecurity_risks: dict[str, Any] | None = None

    # MitigationAgent
    risk_controls: list[dict[str, Any]] | None = None
    probability_after_mitigation: str | None = None
    severity_after_mitigation: str | None = None
    risk_level_after_mitigation: str | None = None
    residual_risk_acceptable: bool | None = None

    # RiskBenefitAgent
    risk_benefit_analysis: dict[str, Any] | None = None

    # TraceabilityAgent
    traceability: dict[str, Any] | None = None

    # ReviewAgent
    validation_summary: dict[str, Any] | None = None

    # ISO 14971 Clause 8 — overall residual risk
    overall_residual_risk: str | None = None
    overall_residual_risk_acceptable: bool | None = None

    # Internal
    errors: list[str] = field(default_factory=list)
    agent_logs: dict[str, Any] = field(default_factory=dict)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    privacy_redactions: dict[str, int] = field(default_factory=dict)
    privacy_blocked_findings: list[str] = field(default_factory=list)
    pipeline_name: str = "software"
    model_name: str | None = None
    generated_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def prepare_model_inputs(self, *, block_sensitive: bool = True) -> None:
        """Create sanitized model-facing inputs and record privacy findings."""
        req_scan = sanitize_for_model(self.requirement, block_sensitive=block_sensitive)
        self.model_requirement = req_scan.sanitized_text
        self.privacy_redactions.update(req_scan.redactions)
        self.privacy_blocked_findings.extend(req_scan.blocked_findings)

        if self.system_description:
            sys_scan = sanitize_for_model(
                self.system_description,
                block_sensitive=block_sensitive,
            )
            self.model_system_description = sys_scan.sanitized_text
            for key, count in sys_scan.redactions.items():
                self.privacy_redactions[key] = self.privacy_redactions.get(key, 0) + count
            self.privacy_blocked_findings.extend(sys_scan.blocked_findings)

        if self.privacy_blocked_findings:
            raise ValueError(
                "Input blocked by data privacy guardrail: "
                + ", ".join(sorted(set(self.privacy_blocked_findings)))
            )

    @property
    def prompt_requirement(self) -> str:
        return self.model_requirement or self.requirement

    @property
    def prompt_system_description(self) -> str | None:
        return self.model_system_description or self.system_description

    def to_report_dict(self) -> dict[str, Any]:
        report = {
            "requirement": self.requirement,
            "iec_62304_class": self.iec_62304_class,
            "iec_62304_rationale": self.iec_62304_rationale,
            "hazard": self.hazard,
            "hazardous_situation": self.hazardous_situation,
            "harm": self.harm,
            "probability_before_mitigation": self.probability_before_mitigation,
            "severity": self.severity,
            "risk_level_before_mitigation": self.risk_level_before_mitigation,
            "fmea": self.fmea,
            "fta": self.fta,
            "use_error_analysis": self.use_error_analysis,
            "risk_controls": self.risk_controls,
            "probability_after_mitigation": self.probability_after_mitigation,
            "risk_level_after_mitigation": self.risk_level_after_mitigation,
            "residual_risk_acceptable": self.residual_risk_acceptable,
            "overall_residual_risk": self.overall_residual_risk,
            "overall_residual_risk_acceptable": self.overall_residual_risk_acceptable,
            "risk_benefit_analysis": self.risk_benefit_analysis,
            "traceability": self.traceability,
            "validation_summary": self.validation_summary,
        }
        # Optional fields — only included when populated
        if self.cybersecurity_risks is not None:
            report["cybersecurity_risks"] = self.cybersecurity_risks
        if self.decomposed_requirements is not None:
            report["decomposed_requirements"] = self.decomposed_requirements
        if self.hazop_analysis is not None:
            report["hazop_analysis"] = self.hazop_analysis
        if self.interface_hazards is not None:
            report["interface_hazards"] = self.interface_hazards
        if self.verification_plan is not None:
            report["verification_plan"] = self.verification_plan
        report["audit_metadata"] = {
            "generated_at_utc": self.generated_at_utc,
            "pipeline": self.pipeline_name,
            "model": self.model_name,
            "agent_sequence": [
                event["agent"] for event in self.audit_trail if event.get("status") == "success"
            ],
            "validation_or_correction_notes": self.errors,
            "audit_trail": self.audit_trail,
            "privacy": {
                "model_inputs_sanitized": bool(self.privacy_redactions),
                "redactions": self.privacy_redactions,
                "blocked_findings": self.privacy_blocked_findings,
                "data_minimization_notice": (
                    "Prompt inputs are sanitized before model calls. Enterprise "
                    "deployment should use approved providers, contractual "
                    "no-training guarantees, retention controls, SSO/RBAC, "
                    "encryption, and internal audit policies."
                ),
            },
            "human_review_required": True,
            "intended_use_notice": (
                "AI-generated first-draft risk analysis; requires qualified "
                "human review before quality-system or regulatory use."
            ),
        }
        return report
