# TraceFlow AI System Design

## 1. Problem We Wanted To Solve

Medical-device teams need to connect requirements to hazards, risks, controls,
verification activities, and traceability evidence. This is important for
systems engineering, safety engineering, QA/RA, and design-control workflows.

The manual process is often slow because engineers must repeatedly ask:

- What can go wrong if this requirement fails?
- Is the concern software, hardware, human factors, interface, or cybersecurity?
- What hazard and harm could result?
- What controls reduce the risk?
- How do we verify the control?
- Is the traceability from requirement to risk control complete?

TraceFlow AI was designed as a prototype decision-support tool that creates a
structured first draft for this workflow.

It is not intended to certify compliance or replace expert review. The goal is
to accelerate early analysis while keeping qualified human review in control.

## 2. Design Principles

The system design followed these principles:

1. Keep the workflow close to how regulated engineering teams think.
2. Split complex reasoning into focused specialist agents.
3. Preserve traceability from input requirement to final report.
4. Validate structured model outputs before using them.
5. Record audit metadata for transparency.
6. Add data-minimization guardrails before model calls.
7. Provide an offline demo path for reliable interviews and presentations.

## 3. Why We Chose A Multi-Agent Design

A single large prompt could generate a risk report, but it would be harder to
validate, debug, explain, and audit.

The work naturally decomposes into specialist tasks:

- classification
- hazard analysis
- FMEA
- FTA
- usability analysis
- cybersecurity threat modeling
- mitigation planning
- benefit-risk analysis
- traceability
- review

So the project uses a multi-agent pipeline where each agent has one clear job.
This makes the system easier to reason about because each stage reads specific
context and writes specific outputs.

## 4. High-Level Architecture

```text
CLI / Demo Input
      |
      v
Orchestrator
      |
      v
RiskContext
      |
      v
Specialist Agents
      |
      v
Validation + Retry
      |
      v
Report Formatter
      |
      v
JSON / CSV / Excel / Risk Matrix / Offline Demo
```

The main files are:

```text
main.py                 CLI entry point
orchestrator.py         software pipeline orchestration
system_orchestrator.py  system pipeline orchestration
context.py              shared RiskContext data model
agents/                 specialist agent implementations
validators/             validation and privacy helpers
output/                 JSON, CSV, Excel, and risk matrix output
offline_demo/           no-internet demo app
```

## 5. Shared Context Design

The project uses a shared dataclass called `RiskContext`.

Each agent reads from the context and writes its result back to it. This keeps
the data flow simple and visible.

Example:

```text
ClassificationAgent writes:
  iec_62304_class
  iec_62304_rationale

HazardAgent reads:
  requirement
  iec_62304_class
  iec_62304_rationale

HazardAgent writes:
  hazard
  hazardous_situation
  harm
  severity
  risk_level_before_mitigation
```

We chose a dataclass instead of an unstructured dictionary because it makes the
expected fields easier to see, document, and test.

## 6. Software Pipeline Design

The software pipeline is used for software-level requirements.

```text
ClassificationAgent
  -> HazardAgent
  -> FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent
  -> MitigationAgent
  -> RiskBenefitAgent
  -> TraceabilityAgent
  -> ReviewAgent
```

The parallel stage exists because FMEA, FTA, usability, and cybersecurity all
need the hazard context, but they do not depend on each other.

This improves runtime and keeps each analysis independent.

## 7. System Pipeline Design

The system pipeline is used for broader system-level requirements.

It adds system-engineering steps before and after the software-style risk
analysis:

```text
RequirementDecompositionAgent
  -> ClassificationAgent
  -> HAZOPAgent + InterfaceHazardAgent
  -> HazardAgent
  -> FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent
  -> MitigationAgent
  -> RiskBenefitAgent
  -> TraceabilityAgent
  -> VerificationPlanAgent
  -> ReviewAgent
```

This design supports systems engineers because it includes:

- requirement allocation across hardware, software, human factors, and interfaces
- HAZOP-style deviation thinking
- interface hazard analysis
- verification and validation planning

## 8. Standards Mapping

The project maps each analysis area to relevant standards:

| Area | Standard |
|---|---|
| Requirements | ISO/IEC/IEEE 29148 |
| Software lifecycle | IEC 62304 |
| Risk management | ISO 14971 |
| Usability / use error | IEC 62366-1 |
| Quality system / documentation | ISO 13485 |
| Cybersecurity risk | AAMI TIR57 |
| Postmarket cybersecurity | AAMI TIR97 |
| Fault tree analysis | IEC 61025 |
| Security controls | IEC 62443-4-2 |
| FDA design controls | FDA 21 CFR 820.30 |
| FDA cybersecurity expectations | FDA cybersecurity guidance |

The wording should be "aligned with" or "mapped to" these standards. The tool
should not be described as certified, validated, or compliance-guaranteeing.

## 9. Validation And Retry Design

LLM outputs can be malformed, incomplete, or inconsistent. To reduce this risk,
the system uses:

- JSON extraction from model output
- required-field validation
- enum checks for controlled values
- RPN correction for FMEA arithmetic
- risk-level correction against the qualitative risk matrix
- retry-with-feedback when validation fails

Each agent declares required fields. The shared `BaseAgent` validates the output
before applying it to the context.

If validation fails, the orchestrator records the error and retries the same
agent with feedback.

## 10. Auditability Design

Regulated workflows need transparency. The project records audit metadata in the
final report:

- generated timestamp
- pipeline name
- model name
- successful agent sequence
- retry/failure events
- validation or correction notes
- privacy redaction counts
- human-review-required notice

This helps explain how the report was created and why human review remains
necessary.

## 11. Data Privacy Design

The model should not receive unnecessary sensitive information.

We added a data-minimization layer before model calls:

```text
raw requirement
      |
      v
privacy scanner
      |
      v
sanitized model-facing requirement
```

The scanner redacts obvious:

- emails
- phone numbers
- patient/MRN-style identifiers
- API-key-like strings

It blocks high-risk secrets such as:

- private keys
- access-token/client-secret patterns

Agents use:

```python
ctx.prompt_requirement
ctx.prompt_system_description
```

instead of raw input fields.

This is a prototype guardrail, not a full enterprise DLP system. In production,
the system should run only through approved enterprise LLM infrastructure with:

- contractual no-training guarantees
- retention controls
- encryption in transit and at rest
- SSO and role-based access control
- audit logging
- company-approved data classification rules

## 12. Output Design

The project generates multiple output formats because different stakeholders
consume risk information differently:

- JSON for structured downstream use
- CSV for traceability export
- Excel for QA/RA and systems-engineering review
- PNG risk matrix for visual communication
- offline demo UI for interviews and presentations

This makes the prototype easier to demonstrate and easier to connect to real
engineering workflows later.

## 13. Offline Demo Design

The offline demo exists because interviews may not have internet access, API
keys, or stable model latency.

The demo uses bundled deterministic examples and simulates the agent pipeline.

This allows a live walkthrough of:

- requirement input
- pipeline stages
- hazard and harm
- risk before and after controls
- traceability
- standards coverage
- human-review checklist

The interview explanation is:

```text
This is the offline deterministic demo mode. It uses pre-generated reports so I
can show the workflow reliably without internet or live API access. In
production, the same interface would connect to the TraceFlow AI backend and an
approved enterprise LLM provider.
```

## 14. Production Evolution

To move from prototype to production, the next improvements would be:

1. Replace lightweight validation with full Pydantic or JSON Schema models.
2. Add source-backed retrieval from approved internal SOPs and standards.
3. Add SSO, RBAC, project-level permissions, and review workflows.
4. Store versioned prompts, model versions, and reviewer decisions.
5. Integrate with a document management or quality management system.
6. Add stronger enterprise DLP and data-classification enforcement.
7. Add export templates for controlled design-history-file artifacts.

## 15. Final Positioning

TraceFlow AI should be described as:

```text
An agentic GenAI prototype for medical-device risk traceability that supports
first-draft safety, usability, cybersecurity, verification, and traceability
analysis while keeping human review and auditability in the loop.
```

It should not be described as:

```text
A certified compliance automation tool.
```

The value of the system design is that it shows both AI engineering ability and
regulated-domain awareness.
