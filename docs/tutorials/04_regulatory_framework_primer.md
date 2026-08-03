# Tutorial 4 — Medical Device Regulatory Framework Primer

This tutorial provides the regulatory context that TraceFlow AI automates.
Understanding the standards helps you evaluate the quality of AI-generated outputs.

**Time to complete:** ~35 minutes  
**Prerequisites:** None — this is conceptual content

---

## Why medical device software is heavily regulated

Medical device software can directly harm patients:

- A dosing algorithm with an integer overflow can recommend a lethal dose.
- A display bug in a cardiac monitor can hide a life-threatening arrhythmia.
- A race condition in an infusion pump can deliver a bolus instead of a continuous dose.

Regulatory frameworks exist to ensure systematic identification and control of these risks
before devices reach patients.

---

## The regulatory landscape

```
╔══════════════════════════════════════════════════════════════╗
║                     DEVICE-LEVEL STANDARDS                    ║
║                                                               ║
║  ISO 14971:2019         Risk Management for Medical Devices   ║
║  ISO 13485:2016         Quality Management System            ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║                    SOFTWARE-SPECIFIC STANDARDS                ║
║                                                               ║
║  IEC 62304:2015+AMD1    Software Lifecycle Processes         ║
║  IEC 62366-1:2015+AMD1  Usability Engineering                ║
║  IEC 81001-5-1:2021     Cybersecurity                        ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║                    REGULATORY AUTHORITY REQUIREMENTS          ║
║                                                               ║
║  FDA 21 CFR 820.30      Design Controls (US)                 ║
║  EU MDR 2017/745        Medical Device Regulation (EU)       ║
║  Health Canada MDSAP    Medical Device Single Audit Program  ║
╚══════════════════════════════════════════════════════════════╝
```

---

## ISO 14971 — The risk management framework

ISO 14971 is the foundation. It applies to the entire device, not just software.

### The risk management file

Every device must have a **Risk Management File** (RMF) containing:
- Risk management plan
- Hazard identification records
- Risk estimation records
- Risk control implementation records
- Residual risk evaluation
- Overall residual risk evaluation
- Post-market surveillance plan

### The risk estimation matrix

ISO 14971 Annex C provides a qualitative risk matrix:

```
              SEVERITY
              Negligible  Marginal  Critical  Catastrophic
          ┌───────────┬──────────┬─────────┬──────────────┐
Frequent  │   Medium  │   High   │ Unacc.  │   Unacc.     │
Probable  │    Low    │  Medium  │  High   │   Unacc.     │
Occasional│    Low    │  Medium  │  High   │   Unacc.     │
Remote    │    Low    │   Low    │  Medium │    High      │
Improbable│    Low    │   Low    │   Low   │   Medium     │
          └───────────┴──────────┴─────────┴──────────────┘
P
R
O
B
A
B
I
L
I
T
Y
```

This is exactly what `output/risk_matrix.py` visualizes.

### Risk acceptability

Each manufacturer must define their own risk policy (in the Risk Management Plan)
specifying what constitutes acceptable risk. Typical policy:
- **Low** — acceptable without further action
- **Medium** — acceptable if ALARP (As Low As Reasonably Practicable)
- **High** — not acceptable; risk controls required
- **Unacceptable** — not acceptable even with benefit-risk justification

---

## IEC 62304 — Software lifecycle

### The V-model

IEC 62304 follows a V-model structure:

```
Software requirements  ─────────────────────→  System testing
  specification                                       |
      |                                         Integration
  Software                                       testing
  architectural                                     |
  design         ─────────────────────→    Software unit
      |                                      testing
  Software
  detailed
  design         ─────→  Software unit
                           implementation
```

Left side = development activities. Right side = verification activities.
Each level verifies the corresponding development artifact.

### Software decomposition

IEC 62304 requires decomposing software into:

```
Software System
  └── Software Item
        └── Software Unit (smallest unit that can be independently tested)
```

Class C software requires verification at all three levels.

### The anomaly resolution process

IEC 62304 Section 9 requires a process for:
1. Tracking all known software anomalies (defects)
2. Evaluating each anomaly for safety impact
3. Resolving or documenting rationale for deferral
4. Ensuring no safety-critical anomalies exist in released software

---

## IEC 62366-1 — Usability engineering

### The usability engineering file

IEC 62366-1 requires a **Usability Engineering File** containing:
- User research (intended users, environments, tasks)
- User interface specification
- Use error risk analysis
- Formative evaluation records
- Summative evaluation protocol and results

### The three user populations

Usability engineering must consider three populations:
1. **Intended users** — the primary target (clinicians, patients)
2. **Lay users** — non-professional users if applicable (home use devices)
3. **Users with disabilities** — accessibility requirements

### Use error vs. abnormal use

| | Use Error | Abnormal Use |
|---|---|---|
| Definition | Foreseeable incorrect action | Intentional use contrary to intended use |
| Manufacturer's responsibility | Must design to prevent | Must assess and document |
| Example | Nurse accidentally selects wrong patient | Nurse deliberately bypasses safety check |

---

## How TraceFlow AI maps to the regulatory framework

| TraceFlow AI Agent | Standard | Regulatory Artifact |
|---|---|---|
| ClassificationAgent | IEC 62304 §4.3 | Software safety classification record |
| HazardAgent | ISO 14971 §5 | Hazard identification and risk estimation |
| FMEAAgent | ISO 14971 §5-7 | Risk analysis supporting record |
| FTAAgent | ISO 14971 §5 | Risk analysis supporting record |
| UsabilityAgent | IEC 62366-1 §5 | Use error risk analysis |
| MitigationAgent | ISO 14971 §7 | Risk control implementation record |
| RiskBenefitAgent | ISO 14971 §9 | Benefit-risk analysis |
| TraceabilityAgent | IEC 62304 §7.1, ISO 14971 §10.2 | Traceability matrix (DHF artifact) |
| ReviewAgent | ISO 14971 §10 | Risk management review record |

---

## What TraceFlow AI does NOT replace

> **Important:** TraceFlow AI generates a first-pass risk analysis to accelerate
> the regulatory workflow. It does **not** replace:

1. **Expert review** — A qualified regulatory affairs specialist, risk manager, or
   clinical safety officer must review and approve all outputs before they are
   included in the Risk Management File.

2. **Design verification and validation** — The V&V activities (testing, code review,
   static analysis) referenced in the traceability matrix must actually be performed.

3. **Clinical evaluation** — ISO 14971 Clause 9 benefit-risk analysis requires real
   clinical evidence; TraceFlow AI's output provides a structured framework, not
   clinical data.

4. **Change control** — When the software requirement changes, the risk analysis must
   be re-run and re-reviewed by a human.

5. **Post-market surveillance** — Risk management continues after device launch.
   Complaint data and adverse event reports must feed back into the RMF.

---

## Regulatory submission expectations

### FDA 510(k) / De Novo

The FDA expects to see in a software submission:
- Software description and device hazard analysis
- IEC 62304 software development lifecycle documentation
- Software hazard analysis (referencing ISO 14971)
- Testing documentation (unit, integration, system, regression)
- Traceability matrix from requirements through testing
- Cybersecurity documentation (per FDA 2023 cybersecurity guidance)

### EU MDR Technical Documentation

EU MDR Annex II requires:
- Design and manufacturing information
- Risk management documentation (ISO 14971)
- Clinical evaluation (ISO 14155, MEDDEV 2.7/1)
- Post-market surveillance plan
- Usability evaluation (IEC 62366-1)

TraceFlow AI generates content directly relevant to the risk management and
usability sections of both submission types.
