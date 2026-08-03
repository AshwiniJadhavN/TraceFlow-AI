"""Export risk reports to JSON, CSV, and Excel."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd


class ReportFormatter:
    def __init__(self, report: dict[str, Any], output_dir: Path) -> None:
        self.report = report
        self.output_dir = output_dir
        raw = report.get("requirement", "report")[:40]
        self.slug = "".join(c if c.isalnum() else "_" for c in raw).strip("_")

    def save_json(self) -> Path:
        path = self.output_dir / f"{self.slug}_risk_report.json"
        path.write_text(json.dumps(self.report, indent=2, default=str))
        return path

    def save_csv(self) -> Path:
        path = self.output_dir / f"{self.slug}_traceability.csv"
        rows = self._traceability_rows()
        if rows:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        return path

    def save_excel(self) -> Path:
        path = self.output_dir / f"{self.slug}_risk_report.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            self._summary_df().to_excel(writer, sheet_name="Summary", index=False)

            rows = self._traceability_rows()
            if rows:
                pd.DataFrame(rows).to_excel(writer, sheet_name="Traceability", index=False)

            if self.report.get("fmea"):
                pd.DataFrame([self.report["fmea"]]).to_excel(writer, sheet_name="FMEA", index=False)

            controls = self.report.get("risk_controls")
            if controls:
                pd.DataFrame(controls).to_excel(writer, sheet_name="Risk Controls", index=False)

            ue = self.report.get("use_error_analysis") or {}
            if ue.get("use_errors"):
                pd.DataFrame(ue["use_errors"]).to_excel(
                    writer, sheet_name="Use Errors", index=False
                )

            # Optional sheets — written only when data is present
            self._write_security_sheet(writer)
            self._write_decomposition_sheet(writer)
            self._write_hazop_sheet(writer)
            self._write_interface_hazard_sheet(writer)
            self._write_verification_plan_sheet(writer)

        return path

    # ------------------------------------------------------------------
    # Private helpers — core
    # ------------------------------------------------------------------

    def _summary_df(self) -> pd.DataFrame:
        r = self.report
        rows = [
            {"Field": "Requirement", "Value": r.get("requirement", "")},
            {"Field": "IEC 62304 Class", "Value": r.get("iec_62304_class", "")},
            {"Field": "IEC 62304 Rationale", "Value": r.get("iec_62304_rationale", "")},
            {"Field": "Hazard", "Value": r.get("hazard", "")},
            {"Field": "Hazardous Situation", "Value": r.get("hazardous_situation", "")},
            {"Field": "Harm", "Value": r.get("harm", "")},
            {"Field": "Severity", "Value": r.get("severity", "")},
            {"Field": "Probability Before", "Value": r.get("probability_before_mitigation", "")},
            {"Field": "Risk Level Before", "Value": r.get("risk_level_before_mitigation", "")},
            {"Field": "Probability After", "Value": r.get("probability_after_mitigation", "")},
            {"Field": "Risk Level After", "Value": r.get("risk_level_after_mitigation", "")},
            {
                "Field": "Residual Risk Acceptable",
                "Value": str(r.get("residual_risk_acceptable", "")),
            },
        ]
        sec = r.get("cybersecurity_risks") or {}
        sec_summary = sec.get("security_summary", {})
        if sec_summary:
            rows.append(
                {
                    "Field": "Total Security Threats",
                    "Value": str(sec_summary.get("total_threats", "")),
                }
            )
            rows.append(
                {
                    "Field": "High/Critical Threats",
                    "Value": str(sec_summary.get("high_or_critical_threats", "")),
                }
            )
            rows.append(
                {
                    "Field": "Residual Cyber Risk",
                    "Value": sec.get("residual_cybersecurity_risk", ""),
                }
            )
        vs = r.get("validation_summary") or {}
        rows.append({"Field": "Review Consistent", "Value": str(vs.get("consistent", ""))})
        rows.append({"Field": "Completeness Score", "Value": str(vs.get("completeness_score", ""))})
        flags = vs.get("flags", [])
        if flags:
            rows.append({"Field": "Review Flags", "Value": "; ".join(flags)})
        audit = r.get("audit_metadata") or {}
        if audit:
            rows.append({"Field": "Pipeline", "Value": audit.get("pipeline", "")})
            rows.append({"Field": "Model", "Value": audit.get("model", "")})
            rows.append({"Field": "Generated At UTC", "Value": audit.get("generated_at_utc", "")})
            rows.append(
                {
                    "Field": "Human Review Required",
                    "Value": str(audit.get("human_review_required", True)),
                }
            )
        return pd.DataFrame(rows)

    def _traceability_rows(self) -> list[dict[str, Any]]:
        traceability = self.report.get("traceability")
        if not traceability:
            return []
        matrix = traceability.get("matrix", [])
        if matrix:
            return matrix
        return [
            {
                "req_id": "REQ-001",
                "req_text": self.report.get("requirement", ""),
                "hazard": self.report.get("hazard", ""),
                "harm": self.report.get("harm", ""),
                "risk_before": self.report.get("risk_level_before_mitigation", ""),
                "controls": "; ".join(
                    c.get("description", "") for c in (self.report.get("risk_controls") or [])
                ),
                "risk_after": self.report.get("risk_level_after_mitigation", ""),
                "acceptable": str(self.report.get("residual_risk_acceptable", "")),
            }
        ]

    # ------------------------------------------------------------------
    # Private helpers — security sheets
    # ------------------------------------------------------------------

    def _write_security_sheet(self, writer: pd.ExcelWriter) -> None:
        sec = self.report.get("cybersecurity_risks")
        if not sec:
            return
        threats = sec.get("threats", [])
        controls = sec.get("security_controls", [])
        if threats:
            pd.DataFrame(threats).to_excel(writer, sheet_name="Security Threats", index=False)
        if controls:
            pd.DataFrame(controls).to_excel(writer, sheet_name="Security Controls", index=False)

    # ------------------------------------------------------------------
    # Private helpers — system engineering sheets
    # ------------------------------------------------------------------

    def _write_decomposition_sheet(self, writer: pd.ExcelWriter) -> None:
        decomp = self.report.get("decomposed_requirements")
        if not decomp:
            return
        rows: list[dict] = []
        for domain, key in [
            ("Hardware", "hardware_requirements"),
            ("Software", "software_requirements"),
            ("Human Factors", "human_factors_requirements"),
            ("Interface", "interface_requirements"),
        ]:
            for req in decomp.get(key, []):
                rows.append({"Domain": domain, **req})
        if rows:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Decomposition", index=False)

    def _write_hazop_sheet(self, writer: pd.ExcelWriter) -> None:
        hazop = self.report.get("hazop_analysis")
        if not hazop:
            return
        rows: list[dict] = []
        for node in hazop.get("system_nodes", []):
            for dev in node.get("deviations", []):
                rows.append(
                    {
                        "node_id": node.get("id"),
                        "node_name": node.get("name"),
                        **{
                            k: (" | ".join(v) if isinstance(v, list) else v) for k, v in dev.items()
                        },
                    }
                )
        if rows:
            pd.DataFrame(rows).to_excel(writer, sheet_name="HAZOP", index=False)

    def _write_interface_hazard_sheet(self, writer: pd.ExcelWriter) -> None:
        iface_data = self.report.get("interface_hazards")
        if not iface_data:
            return
        rows: list[dict] = []
        for iface in iface_data.get("interfaces", []):
            for fm in iface.get("failure_modes", []):
                rows.append(
                    {
                        "interface_id": iface.get("id"),
                        "interface_name": iface.get("name"),
                        "interface_type": iface.get("type"),
                        "from": iface.get("from_component"),
                        "to": iface.get("to_component"),
                        **{k: (" | ".join(v) if isinstance(v, list) else v) for k, v in fm.items()},
                    }
                )
        if rows:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Interface Hazards", index=False)

    def _write_verification_plan_sheet(self, writer: pd.ExcelWriter) -> None:
        vplan = self.report.get("verification_plan")
        if not vplan:
            return
        ver = vplan.get("verification_activities", [])
        val = vplan.get("validation_activities", [])
        if ver:
            pd.DataFrame(ver).to_excel(writer, sheet_name="Verification", index=False)
        if val:
            pd.DataFrame(val).to_excel(writer, sheet_name="Validation", index=False)
