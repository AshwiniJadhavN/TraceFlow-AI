# TraceFlow AI Design

## 1. System Context

TraceFlow AI is a batch-oriented engineering tool that accepts a requirement, orchestrates a sequence of specialist AI agents, validates their structured outputs, and produces a reviewable risk-analysis package.

The design centers on three concerns:

- keep the reasoning workflow close to how regulated engineering teams work;
- keep intermediate outputs structured and inspectable;
- keep privacy, validation, and auditability explicit.

## 2. Major Components

### CLI Layer

`main.py` exposes the user-facing commands:

- `analyze`
- `system-analyze`
- `from-file`

The CLI is responsible for input loading, environment setup, progress display, and output persistence.

### Orchestration Layer

`orchestrator.py` and `system_orchestrator.py` coordinate the agent graph, retries, and final report assembly.

Responsibilities:

- instantiate the shared context;
- prepare model-safe inputs;
- execute stages in order;
- execute selected stages concurrently;
- capture audit events;
- return a canonical report dictionary.

### Shared Context Layer

`context.py` defines `RiskContext`, the mutable contract shared by all stages.

This design keeps the state model explicit and avoids fragile ad hoc dictionaries. It also gives each stage a predictable place to read inputs and write outputs.

### Agent Layer

The `agents/` package contains specialized analysis units such as classification, hazard, FMEA, FTA, usability, security, mitigation, traceability, review, HAZOP, interface hazards, requirement decomposition, and verification planning.

Each agent is designed to perform one focused analysis step.

### Validation And Privacy Layer

The `validators/` package and `RiskContext.prepare_model_inputs()` provide:

- schema and required-field enforcement;
- correction logic for selected calculated values;
- data sanitization before model calls;
- blocking for obvious secret leakage patterns.

### Output Layer

The `output/` package converts the canonical report into JSON, CSV, Excel, and a risk matrix visualization.

### Observability Layer

The `observability/` package wires OpenTelemetry spans across CLI, pipeline, and agent execution.

## 3. Pipeline Design

### Software Pipeline

```text
Requirement
  -> ClassificationAgent
  -> HazardAgent
  -> FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent
  -> MitigationAgent
  -> RiskBenefitAgent
  -> TraceabilityAgent
  -> ReviewAgent
  -> Report Outputs
```

### System Pipeline

```text
Requirement + Optional System Context
  -> RequirementDecompositionAgent
  -> ClassificationAgent
  -> HAZOPAgent + InterfaceHazardAgent
  -> HazardAgent
  -> FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent
  -> MitigationAgent
  -> RiskBenefitAgent
  -> TraceabilityAgent
  -> VerificationPlanAgent
  -> ReviewAgent
  -> Report Outputs
```

Parallel stages are intentionally limited to analyses that share prerequisites but do not depend on one another.

## 4. Data Flow

1. The CLI captures the raw requirement and optional system context.
2. `RiskContext` stores the original inputs and generates sanitized model-facing equivalents.
3. Orchestrators execute specialist agents against the shared context.
4. Agents write structured results back to the context.
5. Validation and corrections happen before results are considered final.
6. `RiskContext.to_report_dict()` assembles the canonical output.
7. Output formatters persist user-facing artifacts.

## 5. Error Handling Design

- Bounded retries are used for malformed or incomplete LLM outputs.
- Retry context captures the prior failure so the next attempt is better constrained.
- Parallel-stage failures are consolidated before the pipeline proceeds.
- Audit metadata records retries, failures, and successful agent completions.

## 6. Privacy And Safety Design

- The model never needs the unsanitized requirement when a sanitized equivalent is available.
- Blocking patterns are treated as hard stops rather than warnings.
- Final reports include a human-review-required notice to prevent misuse as an autonomous compliance artifact.

## 7. Deployment Design

The preferred operational shape is a local CLI or a containerized batch workload. The repository includes Docker, Compose, Helm, Terraform, and policy assets that support controlled execution without changing the product into a long-running web service.

## 8. Design Constraints

- Keep the runtime simple enough for local demonstrations and engineering experiments.
- Preserve deterministic, structured output behavior.
- Avoid coupling the product to a single deployment environment.
- Optimize for inspectability and traceability over raw throughput.