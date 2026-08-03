# Interview Questions — Medical Device Regulatory Fundamentals

These questions cover IEC 62304, ISO 14971, IEC 62366-1, and ISO 13485 as they apply to
medical device software and risk management. Expect these in regulatory affairs, software
QA, and clinical systems engineering roles.

---

## IEC 62304 — Software Lifecycle

### Q1. What are the three IEC 62304 software safety classes and how do you determine which applies?

**Answer:**

| Class | Condition | Example |
|---|---|---|
| **A** | Software failure cannot contribute to a hazardous situation, or contributes only negligible risk | Patient scheduling system |
| **B** | Software failure can contribute to a hazardous situation but will not result in serious injury | Blood pressure trend display (non-critical alarm) |
| **C** | Software failure can contribute to a hazardous situation that could result in death or serious injury | Insulin dose calculator, ventilator control |

**Determination process:**
1. Identify the software item's function in the device.
2. Ask: *can this software item fail in a way that contributes to a hazardous situation?*
3. If yes: ask *what is the worst-case severity of the harm?*
4. Apply IEC 62304 Table 2 decision logic.

**Key point:** You classify the *software item*, not the device. A single device can contain Class A, B, and C items simultaneously.

---

### Q2. What additional activities does IEC 62304 require for Class C software versus Class B?

**Answer:**

Class C requires everything in Class B plus:

- **Software architecture** must be documented and evaluated against software requirements.
- **Unit-level testing** is mandatory (Class B only requires integration and system testing).
- **Additional verification** of software design against software architecture.
- **Traceability** from system requirements → software requirements → software design → unit implementation → unit tests.

In practice, Class C software needs a complete V-model trace from requirements through unit tests, whereas Class B can stop at integration testing.

---

### Q3. What is a SOUP and what does IEC 62304 require you to do with it?

**Answer:**

**SOUP** = Software of Unknown Provenance — pre-existing software (libraries, OS, frameworks) not developed to IEC 62304.

Required activities:
1. **Identify** all SOUP items with version and manufacturer.
2. **Document** the known anomalies in the SOUP that could affect safety.
3. **Establish requirements** the SOUP must meet.
4. **Assess risk** introduced by SOUP anomalies.
5. **Monitor** for SOUP updates and assess impact on the device.

*Example:* If your Class C software uses NumPy for signal processing, NumPy is SOUP. You must document its version, known bugs relevant to your use, and have a plan for updating it.

---

### Q4. What is the relationship between IEC 62304 and ISO 14971?

**Answer:**

They are complementary standards that must be applied together:

- **ISO 14971** is the overarching risk management framework for medical devices. It applies to the whole device system.
- **IEC 62304** is the software-specific lifecycle standard. It references ISO 14971 for risk management activities.

IEC 62304 Section 7.1 requires software risk management to be performed as part of the ISO 14971 process. Practically:
- ISO 14971 identifies system-level hazards.
- IEC 62304 traces those hazards to specific software items and requires software-level mitigations.
- IEC 62304 Section 7.4 requires evaluation of risk control measures implemented in software.

---

## ISO 14971 — Risk Management

### Q5. Walk through the ISO 14971 risk management process.

**Answer:**

ISO 14971:2019 defines a closed-loop process:

```
1. Risk Management Planning
      |
2. Risk Analysis
   a. Intended use + reasonably foreseeable misuse
   b. Hazard identification
   c. Risk estimation (probability x severity)
      |
3. Risk Evaluation
   -> Is risk acceptable per risk policy?
      |
4. Risk Control (if not acceptable)
   a. Inherent safety by design
   b. Protective measures
   c. Information for safety
      |
5. Residual Risk Evaluation
   -> Is residual risk acceptable?
      |
6. Risk-Benefit Analysis (Clause 9)
   -> If residual risk still high: do benefits outweigh risks?
      |
7. Overall Residual Risk Evaluation
      |
8. Risk Management Review
      |
9. Production and Post-Production
   (post-market surveillance, feedback loop)
```

---

### Q6. What is the difference between a hazard, a hazardous situation, and harm?

**Answer:**

| Term | ISO 14971 Definition | Example |
|---|---|---|
| **Hazard** | Potential source of harm | Software displays incorrect blood pressure value |
| **Hazardous situation** | Circumstance in which people/property/environment are exposed to a hazard | Clinician administers wrong medication dose based on incorrect value during emergency |
| **Harm** | Physical injury or damage to health | Patient death from overdose |

The sequence is: **Hazard → Hazardous Situation → Harm**. Each step requires a trigger event (foreseeable sequence of events).

**Why the distinction matters:** Risk controls can interrupt the chain at any step — you can eliminate the hazard, prevent the hazardous situation from occurring, or mitigate the severity of harm.

---

### Q7. What is the ISO 14971 risk control hierarchy and why does the order matter?

**Answer:**

ISO 14971 Clause 7.4 requires considering risk controls in this priority order:

1. **Inherent safety by design** — eliminate the hazard or reduce risk through design choices (e.g., removing a dangerous feature, using fail-safe architecture).
2. **Protective measures** — guards, alarms, interlocks, software watchdogs, redundancy.
3. **Information for safety** — labels, warnings, Instructions for Use, training requirements.

**Why the order matters:**
- Design controls are more reliable because they do not depend on human behaviour.
- Information for safety is least reliable — it depends on users reading, understanding, and acting on warnings.
- Regulatory reviewers will question why you chose a label (Level 3) over a design change (Level 1) for a high-severity hazard.

---

### Q8. What is ISO 14971 Clause 9 (risk-benefit analysis) and when is it triggered?

**Answer:**

Clause 9 applies when residual risk is **not broadly acceptable** under the manufacturer's risk policy after all feasible risk controls have been applied.

**Process:**
1. Review available clinical data on the medical benefits of the device.
2. Compare residual risks against expected clinical benefits.
3. Consider state of the art and available alternatives.
4. If benefits outweigh risks → document the justification and accept the residual risk.
5. If risks outweigh benefits → the device or feature cannot proceed to market.

**Key point:** Clause 9 is not a way to avoid risk reduction — you must first apply all feasible risk controls. Only then can you invoke benefit-risk analysis for remaining risk.

---

### Q9. What is overall residual risk and how does it differ from individual residual risks?

**Answer:**

- **Individual residual risk**: the risk remaining after controls for each specific hazard.
- **Overall residual risk** (ISO 14971 Clause 8): the combined effect of all individual residual risks considered together.

A device could have many individually acceptable residual risks that together create an unacceptable overall risk burden. The risk management file must include an explicit evaluation of overall residual risk.

---

## IEC 62366-1 — Usability Engineering

### Q10. What is the difference between a use error and a device malfunction in the context of IEC 62366-1?

**Answer:**

| | Use Error | Device Malfunction |
|---|---|---|
| **Cause** | User action (or inaction) produces unintended result | Device hardware or software fails |
| **Standard** | IEC 62366-1 (usability) | IEC 62304 (software) / ISO 14971 (risk) |
| **Example** | Nurse selects wrong patient from dropdown under time pressure | Dropdown list crashes due to null pointer exception |

IEC 62366-1 specifically addresses **abnormal use** (use errors that are reasonably foreseeable even if unintended) and distinguishes from **abnormal use by intent** (deliberate misuse, which is not covered).

**Why it matters in TraceFlow AI:** The UsabilityAgent identifies use errors that ISO 14971 hazard analysis might miss — e.g., a clinician misreading a correctly-displayed value.

---

### Q11. What is summative usability testing and when must it be performed?

**Answer:**

Summative usability testing is the **final, formal human factors validation** performed with representative users, tasks, and environments. It answers: *does this device's user interface support safe and effective use by the intended users?*

Required for Class B and Class C software items, and for any device with a user interface that could contribute to a hazardous situation.

**Key requirements:**
- Representative users (not engineers or developers)
- Simulated or actual use environment
- Defined test protocol with pass/fail criteria
- Focus on use errors that could lead to serious harm
- Documented results in the usability engineering file

---

## ISO 13485 — Quality Management

### Q12. What is a Design History File (DHF) and what must it contain?

**Answer:**

The DHF (ISO 13485 Section 7.3, FDA 21 CFR 820.30) is the collection of records describing the design and development history of a finished device.

It must contain:
- Design and development plan
- Design inputs (requirements)
- Design outputs (specifications, software code)
- Design reviews
- Design verification records
- Design validation records
- Design transfer records
- Design changes
- Risk management file (ISO 14971)
- Usability engineering file (IEC 62366-1)

**TraceFlow AI connection:** The traceability matrix output directly supports DHF requirements by linking requirements → hazards → controls → verification.

---

### Q13. What is the difference between design verification and design validation?

**Answer:**

| | Verification | Validation |
|---|---|---|
| **Question** | Did we build the device right? | Did we build the right device? |
| **Tests against** | Design specifications (outputs) | User needs and intended uses (inputs) |
| **Examples** | Unit tests, code review, static analysis | Clinical evaluation, usability testing, simulated use |
| **ISO 13485** | Section 7.3.6 | Section 7.3.7 |

*Mnemonic:* Verification = inspect the artifact. Validation = confirm it works for the user.

---

## Traceability

### Q14. What is a requirements traceability matrix (RTM) and what must it trace?

**Answer:**

An RTM is a document that maps and traces user requirements through the design, implementation, testing, and risk management lifecycle.

For medical device software (per IEC 62304 + ISO 14971) the RTM must trace:

```
User Need
  -> System Requirement
     -> Software Requirement
        -> Software Architecture/Design
           -> Software Implementation (code module)
              -> Verification Test
                 -> Test Result
                    -> Hazard (ISO 14971)
                       -> Risk Control
                          -> Control Verification
                             -> Residual Risk
```

TraceFlow AI's TraceabilityAgent generates the hazard → control → verification → residual risk columns of this matrix automatically.

---

### Q15. During an FDA inspection, what are the most common traceability deficiencies cited?

**Answer:**

1. **Orphaned requirements** — software requirements with no corresponding test.
2. **Orphaned hazards** — hazards identified in risk analysis with no risk control.
3. **Unverified controls** — risk controls with no verification activity or acceptance criteria.
4. **Missing residual risk** — controls documented but residual risk not re-evaluated after control.
5. **Design changes not traced** — change control records not reflected in RTM update.
6. **SOUP not in RTM** — third-party libraries not identified as contributing to requirements.

---

## Scenario questions

### Q16. Your software displays a drug dose recommendation. During testing you discover the display rounds 2.45 mg to 2 mg instead of 2.5 mg. How do you handle this?

**Answer:**

1. **Raise a software defect** (IEC 62304 Section 9 — software problem resolution process).
2. **Assess safety impact**: Is this within the therapeutic window? Could the rounding cause harm?
3. **ISO 14971 hazard evaluation**: Does this constitute a new hazard or a known hazard with changed probability/severity?
4. **Risk management file update**: Document the defect, its safety impact assessment, and disposition.
5. **If safety-significant**: classify as a safety-critical defect requiring immediate fix before release. Update risk analysis and re-verify.
6. **CAPA**: If the defect escaped testing, investigate the test coverage gap and update the test suite.

---

### Q17. A risk control you implemented is an alarm. Under what conditions is an alarm NOT an acceptable risk control per ISO 14971?

**Answer:**

An alarm is a **Level 2 protective measure**. It is not acceptable as the *primary* risk control when:

1. The alarm depends on user response in a time frame shorter than human reaction time.
2. The clinical environment has documented high alarm fatigue (e.g., ICU with dozens of simultaneous alarms).
3. The alarm could itself create a hazardous situation (e.g., startling a surgeon).
4. A Level 1 (design) control is feasible but was not evaluated first.
5. The residual risk after the alarm (assuming alarm fatigue / non-response) is still unacceptable.

The key question: *what is the residual risk if the user ignores the alarm?* If ignoring it leads to Catastrophic severity, the alarm alone is insufficient.
