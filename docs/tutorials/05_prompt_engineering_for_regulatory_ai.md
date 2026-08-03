# Tutorial 5 — Prompt Engineering for Regulatory AI Agents

This tutorial explains the prompt engineering decisions in TraceFlow AI
and teaches you how to improve or customize the agents for your specific context.

**Time to complete:** ~30 minutes  
**Prerequisites:** Completed Tutorials 1 and 2

---

## Principles of regulatory prompt engineering

Regulatory analysis has unique requirements compared to creative or open-ended AI tasks:

| Requirement | Implication for prompts |
|---|---|
| **Accuracy** | Ground the model in specific standards; avoid vague instructions |
| **Consistency** | Same input should produce same output; use temperature 0 |
| **Structured output** | JSON with validated schema; strict output contract |
| **Traceability** | Each output field should reference a specific standard clause |
| **Auditability** | Reasoning must be reproducible and inspectable |

---

## Anatomy of a TraceFlow AI system prompt

Let's dissect the `HazardAgent` system prompt:

```python
HAZARD_SYSTEM_PROMPT = """
You are a medical device risk management expert          # 1. Persona
specializing in ISO 14971:2019 hazard analysis.         # 2. Domain specificity

Your role: Identify hazards, hazardous situations,       # 3. Task definition
and harms for medical device software.                   #

ISO 14971 definitions:                                   # 4. Reference framework
- Hazard: Potential source of harm...                    #
- Hazardous situation: Circumstance...                   #
- Harm: Physical injury...                               #

Probability categories: Frequent, Probable...            # 5. Controlled vocabulary
Severity categories: Negligible, Marginal...             # 5. Controlled vocabulary

Reasoning chain: intended use → failure mode →           # 6. Explicit reasoning steps
hazardous situation → harm pathway →                     #
probability/severity estimation.                         #

CRITICAL: Respond with ONLY a valid JSON object.         # 7. Output contract
No preamble, no markdown fences, no text outside JSON.   #
"""
```

**Seven components every specialist agent system prompt should have.**

---

## Technique 1 — Controlled vocabulary

For enumerations (probability levels, severity classes), always provide the exact
permitted values in the system prompt:

```python
# Bad: model may invent its own terms
"Estimate the probability of the hazard occurring."

# Good: controlled vocabulary enforced in prompt
"Probability categories: Frequent (>1:100), Probable (1:100-1:1000), "
"Occasional (1:1000-1:10000), Remote (1:10000-1:100000), Improbable (<1:100000)."
```

Then validate the output:
```python
VALID_PROBABILITIES = {"Frequent", "Probable", "Occasional", "Remote", "Improbable"}
assert data["probability_before_mitigation"] in VALID_PROBABILITIES
```

---

## Technique 2 — Reasoning chains in user prompts

For complex multi-step reasoning tasks, provide an explicit reasoning chain in the
**user prompt** (not the system prompt). This elicits chain-of-thought behavior:

```python
# HazardAgent user prompt
def build_user_prompt(self, ctx):
    return f"""...

Reasoning chain:
1. Intended use → clinical purpose
2. Failure modes → what can go wrong
3. Hazardous situation → exposure sequence
4. Harm pathway → what harm, to whom
5. Probability estimation
6. Severity estimation
7. Risk level determination

..."""
```

**Why in the user prompt, not the system prompt?**  
The reasoning chain references the specific requirement being analyzed. System prompts
should be general (and cacheable). User prompts contain the task-specific instructions.

---

## Technique 3 — Inline schema specification

Always specify the exact JSON schema in the user prompt, not just "return JSON":

```python
# Weak:
"Return a JSON object with the hazard analysis."

# Strong: exact schema with types and permitted values
"""Return ONLY a JSON object:
{{
  "hazard": "<root hazard>",
  "hazardous_situation": "<sequence leading to harm>",
  "harm": "<specific patient/user harm>",
  "harm_type": "patient" | "user" | "third_party" | "environment",
  "probability_before_mitigation": "Frequent" | "Probable" | "Occasional" | "Remote" | "Improbable",
  ...
}}"""
```

**Note the double braces `{{` and `}}`** — in Python f-strings, single braces are
interpreted as format placeholders, so literal braces must be doubled.

---

## Technique 4 — Context injection with clear labeling

When passing upstream context to downstream agents, label sections clearly:

```python
# MitigationAgent user prompt
def build_user_prompt(self, ctx):
    return f"""...

FMEA OUTPUT:
{json.dumps(ctx.fmea, indent=2)}

FTA OUTPUT:
{json.dumps(ctx.fta, indent=2)}

..."""
```

**Clear section labels** (`FMEA OUTPUT:`, `FTA OUTPUT:`) help the model understand
which part of the prompt contains what type of information.

---

## Technique 5 — Error feedback injection

When retrying a failed agent, tell the model specifically what went wrong:

```python
# Generic (less effective)
"Your previous response was invalid. Try again."

# Specific (more effective)
"ERROR FEEDBACK FROM PREVIOUS ATTEMPT:
  ClassificationAgent attempt 1 error: json.JSONDecodeError: 
  Expecting value: line 1 column 1 (char 0). 
  Return ONLY valid JSON matching the required schema."
```

The model can then understand: *I returned markdown fences, and I need to return
plain JSON instead.*

---

## Customizing prompts for your context

### Adding a company-specific risk policy

If your organization has a specific risk acceptability matrix, inject it into the
hazard agent's system prompt:

```python
# prompts/system_prompts.py
HAZARD_SYSTEM_PROMPT = """
...

This manufacturer's risk policy:
- Low risk: acceptable without further action
- Medium risk: acceptable if ALARP documented
- High risk: requires at least 2 risk controls before residual evaluation
- Unacceptable: requires Clause 9 benefit-risk analysis

CRITICAL: Respond with ONLY a valid JSON object.
"""
```

### Adding device-type context

For a domain-specific deployment, add device category context to the system prompt:

```python
# For a cardiology-focused deployment
CLASSIFICATION_SYSTEM_PROMPT = """
You are a medical device regulatory expert specializing in IEC 62304,
with deep expertise in cardiovascular medical devices.

For cardiovascular software, common Class C indicators:
- Any software that controls or displays cardiac rhythm data
- Hemodynamic monitoring during invasive procedures
- Calculation of cardiac output or derived hemodynamic parameters
...
"""
```

### Injecting regulatory guidance documents

For higher quality outputs, you can inject relevant regulatory text via RAG:

```python
def build_user_prompt(self, ctx, retrieved_guidance: str = "") -> str:
    base_prompt = f"""...{ctx.requirement}..."""
    if retrieved_guidance:
        base_prompt = (
            f"""RELEVANT REGULATORY GUIDANCE:\n{retrieved_guidance}\n\n"""
            + base_prompt
        )
    return base_prompt
```

---

## Evaluating prompt quality

### Quick sanity checks

Run these checks on agent outputs to catch prompt failures:

```python
# Check controlled vocabulary compliance
def validate_hazard_output(data: dict) -> list[str]:
    errors = []
    valid_probs = {"Frequent", "Probable", "Occasional", "Remote", "Improbable"}
    valid_sevs = {"Negligible", "Marginal", "Critical", "Catastrophic"}
    valid_risks = {"Low", "Medium", "High", "Unacceptable"}

    if data.get("probability_before_mitigation") not in valid_probs:
        errors.append(f"Invalid probability: {data.get('probability_before_mitigation')}")
    if data.get("severity") not in valid_sevs:
        errors.append(f"Invalid severity: {data.get('severity')}")
    if data.get("risk_level_before_mitigation") not in valid_risks:
        errors.append(f"Invalid risk level: {data.get('risk_level_before_mitigation')}")
    return errors
```

### Cross-field consistency check

```python
# Simple ISO 14971 risk matrix consistency check
RISK_MATRIX = {
    ("Frequent",   "Catastrophic"): "Unacceptable",
    ("Frequent",   "Critical"):     "Unacceptable",
    ("Occasional", "Catastrophic"): "Unacceptable",
    ("Occasional", "Critical"):     "High",
    ("Remote",     "Critical"):     "Medium",
    # ... etc
}

def check_risk_level_consistency(data: dict) -> bool:
    expected = RISK_MATRIX.get(
        (data["probability_before_mitigation"], data["severity"])
    )
    return expected is None or expected == data["risk_level_before_mitigation"]
```

---

## Common prompt failure modes and fixes

| Failure | Symptom | Fix |
|---|---|---|
| Model invents enum values | `probability: "Sometimes"` | Add explicit list to system prompt |
| Missing required fields | `KeyError` on `ctx.hazard` | Repeat required fields in JSON schema spec |
| Inconsistent risk level | Risk level doesn't match probability × severity | Add consistency check note to system prompt |
| Over-verbose rationale | Rationale field is 5 paragraphs | Add `max 2 sentences` constraint |
| Markdown fences in output | `json.JSONDecodeError` | Already handled by `extract_json()`; add to error feedback |
| Hallucinated standard clauses | `"per ISO 14971 Clause 42"` | Instruct model to only cite clauses from the list provided |
