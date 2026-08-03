# TraceFlow AI Technical Requirements

## 1. Runtime Model

- The system shall run as a Python 3.11 CLI application.
- The primary execution model shall remain batch-oriented, not request-response web serving.
- The runtime shall support local execution, containerized execution, and Kubernetes Job or CronJob deployment patterns.

## 2. Entry Points

- `python main.py analyze <requirement>` shall execute the software pipeline.
- `python main.py system-analyze <requirement>` shall execute the system pipeline.
- `python main.py from-file <path>` shall execute software analysis from file input.

## 3. Core Architecture Requirements

- The system shall use orchestrator classes to control pipeline order and retries.
- The system shall use a shared `RiskContext` dataclass as the contract between agent stages.
- Each agent shall read required context fields and write well-defined outputs back to the context.
- Parallel analysis stages shall use `asyncio.gather` with explicit failure handling.
- The model used by agents shall operate with deterministic settings suitable for structured output generation.

## 4. Pipeline Requirements

### Software Pipeline

- Classification must execute before hazard analysis.
- Hazard analysis must execute before FMEA, FTA, usability, and security.
- FMEA, FTA, usability, and security shall be allowed to run in parallel.
- Mitigation, benefit-risk, traceability, and review shall execute after the parallel stage completes successfully.

### System Pipeline

- Requirement decomposition shall execute before downstream analysis.
- HAZOP and interface hazard analysis shall run before the software-style hazard stage.
- Verification planning shall execute after traceability.

## 5. Data Handling Requirements

- Raw user input shall be retained for reporting.
- Model-facing input shall be sanitized before any LLM call.
- The system shall redact obvious emails, phone numbers, patient-style identifiers, and API-key-like strings.
- The system shall block processing when high-risk secret patterns are detected.
- Audit output shall record redaction counts and blocked findings when applicable.

## 6. Validation Requirements

- Agent responses shall be validated before they are applied to `RiskContext`.
- Validation shall include required-field checks and controlled-value checks where applicable.
- The system shall correct certain computable inconsistencies such as FMEA arithmetic and qualitative risk alignment when supported by validators.
- Agent failures caused by malformed output shall trigger bounded retries with feedback.

## 7. Output Requirements

- The system shall emit JSON as the canonical report structure.
- The system shall support CSV and Excel exports derived from the canonical report.
- The system shall generate a risk matrix image artifact.
- The report shall include audit metadata including timestamp, pipeline name, model name, successful agent sequence, correction notes, and human-review notice.

## 8. Observability Requirements

- The runtime shall initialize OpenTelemetry tracing when configured.
- CLI commands, pipeline runs, and agent executions shall be instrumented with spans.
- Errors shall be attached to spans for operational diagnosis.

## 9. Security And Privacy Requirements

- API keys shall be provided through environment variables or secret-backed deployment mechanisms.
- The runtime shall avoid embedding secrets in source-controlled configuration.
- Container execution shall support non-root operation.
- Production use shall assume approved model providers with retention and access controls outside the current codebase.

## 10. Quality Requirements

- The repository shall support automated linting, formatting, type checking, tests, and security scanning.
- The project shall maintain unit and integration coverage for orchestrators, validators, and representative agent flows.
- Documentation shall reflect the actual batch-first runtime instead of implying a web application.

## 11. Extensibility Requirements

- New agents shall be addable without redesigning the entire pipeline.
- Prompts and output validators shall remain isolated enough for targeted evolution.
- Output formatting shall remain decoupled from orchestration so additional export targets can be introduced later.