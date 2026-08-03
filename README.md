# TraceFlow AI

> Agentic Medical Device Risk Traceability System powered by GenAI

TraceFlow AI is a multi-agent orchestration system that automates regulatory risk analysis
for medical device software and system requirements. It produces traceable, audit-ready
risk reports aligned with **IEC 62304**, **ISO 14971**, **IEC 62366-1**, **ISO 13485**,
**AAMI TIR57**, and **ISO/IEC/IEEE 29148**.

Two pipelines are available:

| Pipeline | Command | Use case |
|---|---|---|
| Software pipeline | `analyze` | Software requirement → 7-stage report (safety + security) |
| System pipeline | `system-analyze` | System requirement → 10-stage full system engineering report |

---

## Architecture

### Software pipeline (`analyze`)

```
Input: software requirement
       |
       v
+------------------------+
|      Orchestrator      |  task graph + retry-with-feedback
+----------+-------------+
           |
  Stage 1  v
+----------+------------------+
| ClassificationAgent         |  IEC 62304 Class A / B / C
+----------+------------------+
           |
  Stage 2  v
+----------+------------------+
| HazardAgent                 |  ISO 14971 hazard / situation / harm / severity
+----------+------------------+
           |
  Stage 3  v  (asyncio.gather — parallel)
+----------+----------+----------+----------+
|          |          |           |           |
v          v          v           v
FMEAAgent  FTAAgent   UsabilityAgent  SecurityAgent
(RPN)      (FTA/MCS)  (IEC 62366-1)  (AAMI TIR57 STRIDE)
|          |          |           |
+----------+----------+-----------+
           |
  Stage 4  v
+----------+------------------+
| MitigationAgent             |  risk controls + residual risk
+----------+------------------+
           |
  Stage 5  v
+----------+------------------+
| RiskBenefitAgent            |  ISO 14971 Clause 9
+----------+------------------+
           |
  Stage 6  v
+----------+------------------+
| TraceabilityAgent           |  REQ → HAZ → CTRL → VER → RISK
+----------+------------------+
           |
  Stage 7  v  (self-reflection)
+----------+------------------+
| ReviewAgent                 |  10-point consistency check (incl. cybersecurity)
+----------+------------------+
           |
           v
JSON + CSV + Excel (up to 7 sheets) + Risk Matrix PNG
```

### System pipeline (`system-analyze`)

```
Input: system requirement (+ optional system-context JSON)
       |
       v
+-------------------------------+
|      SystemOrchestrator       |  10-stage pipeline
+----------+--------------------+
           |
  Stage 0  v
+----------+----------------------------+
| RequirementDecompositionAgent         |  ISO/IEC/IEEE 29148: HW/SW/HF/IF allocation
+----------+----------------------------+
           |
  Stage 1  v
+----------+------------------+
| ClassificationAgent         |  IEC 62304 Class A / B / C
+----------+------------------+
           |
  Stage 2  v  (asyncio.gather — parallel)
+----------+---------------------------+
HAZOPAgent  +  InterfaceHazardAgent
           |
  Stage 3  v
+----------+------------------+
| HazardAgent                 |  ISO 14971 hazard / situation / harm
+----------+------------------+
           |
  Stage 4  v  (asyncio.gather — parallel)
FMEAAgent + FTAAgent + UsabilityAgent + SecurityAgent
           |
  Stage 5  v
+----------+------------------+
| MitigationAgent
  Stage 6  → RiskBenefitAgent
  Stage 7  → TraceabilityAgent
  Stage 8  → VerificationPlanAgent
  Stage 9  → ReviewAgent  (self-reflection)
           |
           v
JSON + CSV + Excel (up to 11 sheets) + Risk Matrix PNG
```

### Agentic behaviors

| Behavior | Implementation |
|---|---|
| Task decomposition | Orchestrator decomposes input into sequential/parallel agent tasks |
| Context passing | `RiskContext` dataclass grows as each agent writes its output |
| Validation + retry | Agents raise `ValueError` on enum violation; orchestrator retries up to 3× with error injected into next prompt |
| Async parallelism | FMEA + FTA + Usability + Security run concurrently via `asyncio.gather(return_exceptions=True)` |
| Auto-correction | Risk level corrected against ISO 14971 Annex C; RPN recomputed when S×O×D is wrong |
| Self-reflection | ReviewAgent runs a 10-point checklist including cybersecurity coverage |
| Deterministic outputs | `temperature=0` on every API call |
| Data minimization | Inputs are sanitized before model calls; obvious patient IDs, emails, phone numbers, and API keys are redacted |
| Leakage guardrails | High-risk secrets such as private keys or access tokens block execution before any model call |
| Auditability | Reports include model, pipeline, agent sequence, validation notes, privacy redaction counts, and human-review notice |

---

## Data protection posture

TraceFlow AI is designed as a decision-support prototype, not a consumer chatbot
for confidential company data. For enterprise use, deploy it only through an
approved LLM environment with contractual no-training guarantees, retention
controls, SSO/RBAC, encryption in transit and at rest, and internal audit
policies.

The current implementation includes prototype guardrails:

- model-facing prompts use sanitized inputs (`ctx.prompt_requirement` and
  `ctx.prompt_system_description`);
- obvious emails, phone numbers, patient identifiers, and API keys are redacted
  before model calls;
- private-key or access-token-like content blocks the pipeline before any model
  call;
- final reports include privacy redaction counts and a human-review-required
  notice in `audit_metadata`.

Do not submit PHI, patient records, trade secrets, source code, credentials, or
restricted design history to a public model endpoint. In regulated environments,
use company-approved providers and keep human review inside the quality process.

---

## Regulatory context

| Standard | Role in TraceFlow AI |
|---|---|
| **IEC 62304:2015+AMD1** | Software safety classification (Class A/B/C), software lifecycle activities |
| **ISO 14971:2019** | Hazard identification, risk estimation, Annex C risk matrix, Clause 9 benefit-risk |
| **IEC 62366-1:2015+AMD1** | Use error analysis, intended users, usability engineering |
| **ISO 13485:2016** | Design and development documentation traceability |
| **AAMI TIR57:2016** | STRIDE cybersecurity threat modeling, cybersecurity risk management |
| **AAMI TIR97:2019** | Postmarket cybersecurity, coordinated vulnerability disclosure |
| **ISO/IEC/IEEE 29148:2018** | Requirement decomposition — HW / SW / HF / interface allocation |
| **IEC 61025** | Fault tree analysis (FTA), minimal cut sets |
| **IEC 62443-4-2** | Security controls for medical device software components |
| **FDA 21 CFR 820.30** | Design controls traceability matrix |
| **FDA Cybersecurity Guidance 2023** | SBOM, coordinated vulnerability disclosure |

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/ashwinijadhavn/traceflow-ai.git
cd traceflow-ai
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API key

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run analysis

**Software pipeline:**

```bash
# Analyze a requirement (includes STRIDE security analysis automatically)
python main.py analyze "The system shall display real-time hemodynamic waveforms to the clinician during cardiac catheterization."

# Read requirement from file
python main.py from-file examples/example_1_input.txt

# JSON-only output (pipe-friendly)
python main.py analyze "<requirement>" --json-only | jq '.cybersecurity_risks.security_summary'

# Verbose logging
python main.py analyze "<requirement>" --verbose
```

**System pipeline:**

```bash
# System requirement with optional system context
python main.py system-analyze "The infusion pump shall deliver medication at a clinician-programmed rate accurate to ±5% of the set rate."
python main.py system-analyze "<requirement>" --system-context system_context.json
```

---

## Platform hardening (Tier 3)

Optional production-oriented assets are included for teams that want to push the prototype toward a more audit-ready platform posture:

- `infra/kubernetes/base/`: raw Kubernetes Job/CronJob manifests, PVC, NetworkPolicy, and secret/config templates for batch execution.
- `charts/traceflow-ai/`: Helm chart for parameterized cluster deployment of the CLI workload.
- `infra/terraform/`: Terraform that provisions a namespace, deploys the Helm chart, and can install an OpenTelemetry Collector.
- `observability/`: OpenTelemetry bootstrap used by the CLI and orchestrators to emit spans for pipeline, agent, and model-call execution.
- `policy/`: Policy-as-code examples for Kyverno and OPA to enforce non-root execution, pinned images, and secret-backed API keys.

### OpenTelemetry configuration

TraceFlow AI now emits spans when OpenTelemetry is configured. The runtime stays functional when no collector is present.

```bash
# Optional: export traces to an OTLP HTTP collector
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"

# Optional: useful for local verification without a collector
export TRACEFLOW_OTEL_CONSOLE=true

python main.py analyze "The system shall alarm on occlusion within 5 seconds."
```

### Kubernetes and Helm

The workload is modeled as a batch pipeline, not a web service, so the cluster artifacts use `Job` and optional `CronJob` resources rather than a long-running `Deployment`.

```bash
# Render the default Helm chart
helm template traceflow-ai charts/traceflow-ai

# Apply the raw manifests with kustomize
kubectl apply -k infra/kubernetes/base
```

### Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

---

## Output files

### Software pipeline output (up to 7 Excel sheets)

| Excel sheet | Content |
|---|---|
| Summary | IEC 62304 class, hazard, risk levels, security threat count, review score |
| Traceability | REQ → HAZ → CTRL → VER → RISK mapping |
| FMEA | Failure modes with RPN before/after |
| Risk Controls | Safety control type, description, residual risk impact |
| Use Errors | IEC 62366-1 use error analysis |
| Security Threats | STRIDE threats with exploitability, patient safety impact, risk level |
| Security Controls | Security mitigations with AAMI TIR57/IEC 62443 references |

### System pipeline output (up to 11 Excel sheets)

All software sheets plus: Decomposition, HAZOP, Interface Hazards, Verification, Validation.

### JSON report — cybersecurity fields

```json
{
  "cybersecurity_risks": {
    "assets": ["patient waveform data", "display rendering engine", "network interface"],
    "threats": [
      {
        "id": "SEC-001",
        "stride_category": "Tampering",
        "threat_description": "Attacker modifies waveform data in transit via MITM attack",
        "attack_vector": "Network",
        "attack_complexity": "Low",
        "exploitability": "High",
        "impact_on_patient_safety": "Critical",
        "cybersecurity_risk_level": "High",
        "affected_asset": "patient waveform data",
        "aami_tir57_reference": "TIR57 §5.4"
      }
    ],
    "security_controls": [
      {
        "id": "SC-001",
        "addresses_threat": "SEC-001",
        "control_type": "technical",
        "description": "Implement TLS 1.3 with mutual authentication for all waveform data transmission",
        "standard_reference": "AAMI TIR57 §6.3, IEC 62443-4-2",
        "acceptance_criteria": "Penetration test confirms no plain-text transmission; TLS 1.3 enforced"
      }
    ],
    "residual_cybersecurity_risk": "Low",
    "sbom_required": true,
    "coordinated_vulnerability_disclosure_required": true,
    "security_summary": {
      "total_threats": 4,
      "high_or_critical_threats": 1,
      "stride_categories_identified": ["Spoofing", "Tampering", "Denial of Service", "Information Disclosure"],
      "total_security_controls": 4
    }
  }
}
```

---

## Agent reference

### Software agents

| Agent | Standard | Input | Output |
|---|---|---|---|
| `ClassificationAgent` | IEC 62304 | requirement | Class A/B/C + rationale |
| `HazardAgent` | ISO 14971 | requirement + class | hazard, situation, harm, probability, severity, risk level |
| `FMEAAgent` | AIAG/VDA FMEA | requirement + hazard | FMEA entry with RPN before/after (auto-corrected) |
| `FTAAgent` | IEC 61025 | requirement + hazard | Fault tree with MCS and critical path |
| `UsabilityAgent` | IEC 62366-1 | requirement + hazard | Use errors with task references |
| `SecurityAgent` | AAMI TIR57 | requirement + hazard | STRIDE threats + security controls + residual cyber risk |
| `MitigationAgent` | ISO 14971 | requirement + FMEA + FTA | Risk controls + residual risk |
| `RiskBenefitAgent` | ISO 14971 Cl. 9 | requirement + controls | Benefit-risk analysis + conclusion |
| `TraceabilityAgent` | IEC 62304 + ISO 14971 | all above | Full traceability matrix |
| `ReviewAgent` | All | condensed summary | 10-point consistency check incl. cybersecurity |

### System engineering agents

| Agent | Standard | Input | Output |
|---|---|---|---|
| `RequirementDecompositionAgent` | ISO/IEC/IEEE 29148 | system requirement | HW / SW / HF / interface derived requirements |
| `HAZOPAgent` | IEC 61882 | system nodes | Guide-word deviation table per node |
| `InterfaceHazardAgent` | MIL-STD-882E | interfaces | Failure modes per interface with severity |
| `VerificationPlanAgent` | IEC 62304 + ISO 13485 | all risk outputs | V&V activity plan with methods and acceptance criteria |

---

## Validation and auto-correction

| Validator | Logic |
|---|---|
| `check_enum(value, valid_set, field)` | Raises `ValueError` — triggers agent retry |
| `correct_risk_level(prob, sev, reported)` | ISO 14971 Annex C lookup; silently replaces wrong risk level |
| `correct_fmea_rpn(data)` | Recomputes `rpn = S × O × D`; clamps scores to 1–10 |
| SecurityAgent enum checks | Validates STRIDE category, attack vector, exploitability, cyber risk level |

**Controlled vocabularies:**

| Field | Valid values |
|---|---|
| `iec_62304_class` | `A`, `B`, `C` |
| `probability_*` | `Frequent`, `Probable`, `Occasional`, `Remote`, `Improbable` |
| `severity` | `Negligible`, `Marginal`, `Critical`, `Catastrophic` |
| `risk_level_*` | `Low`, `Medium`, `High`, `Unacceptable` |
| `stride_category` | `Spoofing`, `Tampering`, `Repudiation`, `Information Disclosure`, `Denial of Service`, `Elevation of Privilege` |
| `attack_vector` | `Physical`, `Local`, `Adjacent`, `Network` |
| `exploitability` | `Low`, `Medium`, `High` |
| `cybersecurity_risk_level` | `Low`, `Medium`, `High`, `Critical` |

---

## Development

```bash
pytest tests/ -v          # all tests, API mocked
ruff check .              # lint
```

CI runs lint + tests on every push to `main` and `claude/**` branches.

---

## Project structure

```
traceflow-ai/
├── main.py                              # CLI — analyze / system-analyze / from-file
├── orchestrator.py                      # Software pipeline: 7-stage task graph
├── system_orchestrator.py               # System pipeline: 9-stage task graph
├── context.py                           # Shared RiskContext dataclass
├── agents/
│   ├── base_agent.py                    # Abstract base: temperature=0, JSON extraction
│   ├── classification_agent.py
│   ├── hazard_agent.py
│   ├── fmea_agent.py
│   ├── fta_agent.py
│   ├── usability_agent.py
│   ├── security_agent.py                # AAMI TIR57 STRIDE threat modeling
│   ├── mitigation_agent.py
│   ├── risk_benefit_agent.py
│   ├── traceability_agent.py
│   ├── review_agent.py
│   ├── requirement_decomposition_agent.py
│   ├── hazop_agent.py
│   ├── interface_hazard_agent.py
│   └── verification_plan_agent.py
├── prompts/
│   ├── system_prompts.py                # 14 system prompts (one per agent)
│   └── user_prompt_builder.py
├── validators/
│   └── output_validators.py             # Enum checks, risk matrix, RPN, security enums
├── output/
│   ├── formatter.py                     # JSON + CSV + Excel (up to 11 sheets)
│   └── risk_matrix.py                   # 5×4 ISO 14971 risk matrix PNG
├── tests/
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   └── test_validators.py               # 32 validator unit tests
├── examples/
├── docs/
│   ├── interviews/                      # Regulatory + AI + TraceFlow Q&A
│   └── tutorials/                       # 5 step-by-step tutorials
├── .github/workflows/ci.yml
├── requirements.txt
└── .env.example
```

---

## Requirements

- Python 3.10+
- Anthropic API key (`claude-sonnet-4-20250514`)

Key dependencies: `anthropic`, `typer`, `python-dotenv`, `pandas`, `openpyxl`, `matplotlib`, `pytest`, `pytest-asyncio`, `rich`.

---

## License

MIT
