#!/usr/bin/env python3
"""TraceFlow AI - CLI entry point."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from observability.tracing import configure_telemetry, get_tracer, mark_span_error
from orchestrator import Orchestrator
from output.formatter import ReportFormatter
from output.risk_matrix import RiskMatrixPlotter
from system_orchestrator import SystemOrchestrator

load_dotenv()

APP_VERSION = "0.1.0"
configure_telemetry(service_name="traceflow-ai", service_version=APP_VERSION)

app = typer.Typer(
    name="traceflow",
    help="TraceFlow AI - Agentic Medical Device Risk Traceability powered by GenAI",
    add_completion=False,
)
console = Console()
tracer = get_tracer(__name__)


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Check your .env file.[/red]")
        raise typer.Exit(1)
    return key


def _save_and_print(report: dict, output_dir: Path, console: Console) -> None:
    formatter = ReportFormatter(report, output_dir)
    json_path = formatter.save_json()
    csv_path = formatter.save_csv()
    excel_path = formatter.save_excel()
    plotter = RiskMatrixPlotter(report, output_dir)
    matrix_path = plotter.save()
    _print_summary_table(console, report)
    console.print("\n[dim]Outputs saved to:[/dim]")
    for p in [json_path, csv_path, excel_path, matrix_path]:
        console.print(f"  [cyan]{p}[/cyan]")


@app.command()
def analyze(
    requirement: str = typer.Argument(..., help="Software requirement to analyze"),
    output_dir: Path = typer.Option(
        Path("output"), "--output", "-o", help="Directory for output reports"
    ),
    json_only: bool = typer.Option(False, "--json-only", help="Print JSON to stdout only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Software-level risk analysis: IEC 62304, ISO 14971, FMEA, FTA, usability, security, traceability."""
    with tracer.start_as_current_span("traceflow.cli.analyze") as span:
        span.set_attributes(
            {
                "traceflow.pipeline": "software",
                "traceflow.json_only": json_only,
                "traceflow.verbose": verbose,
                "traceflow.requirement_length": len(requirement),
            }
        )
        try:
            if verbose:
                logging.basicConfig(level=logging.INFO, stream=sys.stderr)
            api_key = _get_api_key()
            output_dir.mkdir(parents=True, exist_ok=True)
            span.set_attribute("traceflow.output_dir", str(output_dir))

            if not json_only:
                console.print(
                    Panel.fit(
                        f"[bold cyan]TraceFlow AI[/bold cyan] — Software Analysis\n\n"
                        f"[yellow]Requirement:[/yellow] {requirement[:100]}"
                        f"{'...' if len(requirement) > 100 else ''}",
                        border_style="cyan",
                    )
                )

            orch = Orchestrator(api_key=api_key)
            if json_only:
                report = asyncio.run(orch.run(requirement))
                print(json.dumps(report.to_report_dict(), indent=2))
                return

            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
                t = p.add_task("Running software pipeline...", total=None)
                result = asyncio.run(orch.run(requirement))
                p.update(t, completed=True)

            console.print("\n[bold green]Analysis complete![/bold green]")
            _save_and_print(result.to_report_dict(), output_dir, console)
        except Exception as exc:
            mark_span_error(span, exc)
            raise


@app.command(name="system-analyze")
def system_analyze(
    requirement: str = typer.Argument(..., help="System-level requirement to analyze"),
    system_context: Path | None = typer.Option(
        None,
        "--system-context",
        "-s",
        help="Path to a text file describing the system architecture and context",
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output", "-o", help="Directory for output reports"
    ),
    json_only: bool = typer.Option(False, "--json-only"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Full system engineering analysis: HAZOP, interface hazards, requirement decomposition, security, V&V plan.

    Includes everything from the software pipeline plus:
    - Requirement decomposition into HW / SW / HF / interface sub-requirements
    - HAZOP deviation study across system nodes
    - Interface Hazard Analysis at all system boundaries
    - STRIDE cybersecurity threat modeling (AAMI TIR57)
    - System V&V plan mapping requirements and controls to test activities
    """
    with tracer.start_as_current_span("traceflow.cli.system_analyze") as span:
        span.set_attributes(
            {
                "traceflow.pipeline": "system",
                "traceflow.json_only": json_only,
                "traceflow.verbose": verbose,
                "traceflow.requirement_length": len(requirement),
            }
        )
        try:
            if verbose:
                logging.basicConfig(level=logging.INFO, stream=sys.stderr)
            api_key = _get_api_key()
            output_dir.mkdir(parents=True, exist_ok=True)
            span.set_attribute("traceflow.output_dir", str(output_dir))

            system_description = ""
            if system_context:
                if not system_context.exists():
                    console.print(f"[red]System context file not found: {system_context}[/red]")
                    raise typer.Exit(1)
                system_description = system_context.read_text().strip()
                span.set_attribute("traceflow.system_context_path", str(system_context))

            if not json_only:
                console.print(
                    Panel.fit(
                        f"[bold cyan]TraceFlow AI[/bold cyan] — System Engineering Analysis\n\n"
                        f"[yellow]Requirement:[/yellow] {requirement[:100]}"
                        f"{'...' if len(requirement) > 100 else ''}\n"
                        f"[dim]System context: {'provided' if system_description else 'not provided'}[/dim]",
                        border_style="blue",
                    )
                )

            orch = SystemOrchestrator(api_key=api_key)
            if json_only:
                report = asyncio.run(orch.run(requirement, system_description))
                print(json.dumps(report, indent=2))
                return

            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
                t = p.add_task("Running system engineering pipeline...", total=None)
                report = asyncio.run(orch.run(requirement, system_description))
                p.update(t, completed=True)

            console.print("\n[bold green]System analysis complete![/bold green]")
            _save_and_print(report, output_dir, console)
            _print_system_summary(console, report)
        except Exception as exc:
            mark_span_error(span, exc)
            raise


@app.command(name="from-file")
def from_file(
    input_file: Path = typer.Argument(..., help="File containing the requirement"),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o"),
    json_only: bool = typer.Option(False, "--json-only"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Read a requirement from a text file and run software-level analysis."""
    with tracer.start_as_current_span("traceflow.cli.from_file") as span:
        span.set_attribute("traceflow.input_file", str(input_file))
        if not input_file.exists():
            console.print(f"[red]File not found: {input_file}[/red]")
            raise typer.Exit(1)
        requirement = input_file.read_text().strip()
        span.set_attribute("traceflow.requirement_length", len(requirement))
        analyze(
            requirement=requirement,
            output_dir=output_dir,
            json_only=json_only,
            verbose=verbose,
        )


def _print_summary_table(console: Console, report: dict) -> None:
    table = Table(title="Risk Analysis Summary", border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for label, val in [
        ("IEC 62304 Class", report.get("iec_62304_class")),
        ("Hazard", report.get("hazard")),
        ("Harm", report.get("harm")),
        ("Severity", report.get("severity")),
        ("Risk Before", report.get("risk_level_before_mitigation")),
        ("Risk After", report.get("risk_level_after_mitigation")),
        ("Residual Risk Acceptable", str(report.get("residual_risk_acceptable"))),
    ]:
        table.add_row(label, val or "N/A")
    sec = report.get("cybersecurity_risks") or {}
    sec_summary = sec.get("security_summary", {})
    if sec_summary:
        table.add_row("Security Threats", str(sec_summary.get("total_threats", "N/A")))
        table.add_row(
            "High/Critical Threats",
            str(sec_summary.get("high_or_critical_threats", "N/A")),
        )
        table.add_row(
            "Residual Cyber Risk",
            sec.get("residual_cybersecurity_risk") or "N/A",
        )
    vs = report.get("validation_summary") or {}
    table.add_row("Review Consistent", str(vs.get("consistent", "N/A")))
    flags = vs.get("flags", [])
    if flags:
        table.add_row("Review Flags", "; ".join(flags))
    console.print(table)


def _print_system_summary(console: Console, report: dict) -> None:
    """Print additional system engineering summary rows."""
    decomp = report.get("decomposed_requirements") or {}
    hazop = report.get("hazop_analysis") or {}
    iface = report.get("interface_hazards") or {}
    vplan = report.get("verification_plan") or {}

    if not any([decomp, hazop, iface, vplan]):
        return

    table = Table(title="System Engineering Summary", border_style="blue")
    table.add_column("Area", style="bold")
    table.add_column("Count / Finding")

    alloc = decomp.get("allocation_summary", {})
    if alloc:
        table.add_row("HW requirements", str(alloc.get("hardware_count", "N/A")))
        table.add_row("SW requirements", str(alloc.get("software_count", "N/A")))
        table.add_row("HF requirements", str(alloc.get("human_factors_count", "N/A")))
        table.add_row("Interface requirements", str(alloc.get("interface_count", "N/A")))

    hazop_summary = hazop.get("hazop_summary", {})
    if hazop_summary:
        table.add_row("HAZOP nodes", str(hazop_summary.get("total_nodes", "N/A")))
        table.add_row("HAZOP deviations", str(hazop_summary.get("total_deviations", "N/A")))
        table.add_row("High-risk deviations", str(hazop_summary.get("high_risk_deviations", "N/A")))

    iface_summary = iface.get("interface_summary", {})
    if iface_summary:
        table.add_row("Interfaces analysed", str(iface_summary.get("total_interfaces", "N/A")))
        table.add_row("Critical interfaces", str(iface_summary.get("critical_interfaces", "N/A")))

    vplan_summary = vplan.get("verification_summary", {})
    if vplan_summary:
        table.add_row(
            "Verification activities", str(vplan_summary.get("total_verification", "N/A"))
        )
        table.add_row("Validation activities", str(vplan_summary.get("total_validation", "N/A")))

    console.print(table)


if __name__ == "__main__":
    app()
