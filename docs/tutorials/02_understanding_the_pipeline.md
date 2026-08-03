# Tutorial 2 — Understanding the Agentic Pipeline

This tutorial explains how TraceFlow AI's multi-agent orchestration works
under the hood — the context object, dependency graph, and retry mechanism.

**Time to complete:** ~25 minutes  
**Prerequisites:** Completed Tutorial 1

---

## The shared context object

All agents communicate through a single `RiskContext` dataclass defined in `context.py`.
Think of it as a growing document that each agent reads from and writes to.

```python
# context.py (simplified)
@dataclass
class RiskContext:
    requirement: str = ""                        # Set by CLI before pipeline starts

    # Written by ClassificationAgent
    iec_62304_class: Optional[str] = None
    iec_62304_rationale: Optional[str] = None

    # Written by HazardAgent
    hazard: Optional[str] = None
    hazardous_situation: Optional[str] = None
    harm: Optional[str] = None
    probability_before_mitigation: Optional[str] = None
    severity: Optional[str] = None
    risk_level_before_mitigation: Optional[str] = None

    # Written by FMEAAgent
    fmea: Optional[dict] = None

    # ... and so on for every agent
```

### Why a dataclass?

- Fields are typed and explicit — you can see the entire data model in one file.
- All fields default to `None`, so agents can safely read upstream fields without `KeyError`.
- The `to_report_dict()` method assembles the final JSON output in a single place.

---

## Tracing a requirement through the pipeline

Let's trace what happens when you run:

```bash
python main.py analyze "The system shall display real-time hemodynamic waveforms..."
```

### Stage 1 — ClassificationAgent

**Reads:** `ctx.requirement`  
**Writes:** `ctx.iec_62304_class`, `ctx.iec_62304_rationale`

The agent receives this user prompt (built by `build_user_prompt`):
```
Analyze the following medical device software requirement and determine
its IEC 62304 software safety classification.

REQUIREMENT:
The system shall display real-time hemodynamic waveforms to the clinician
during cardiac catheterization.

Return ONLY a JSON object with this exact schema: ...
```

It returns:
```json
{
  "iec_62304_class": "C",
  "rationale": "Life-critical cardiac monitoring software...",
  "key_factors": ["cardiac procedure", "real-time display"],
  "potential_for_serious_injury": true
}
```

The orchestrator calls `_apply_to_context(data, ctx)`, which writes:
```python
ctx.iec_62304_class = "C"
ctx.iec_62304_rationale = "Life-critical cardiac monitoring software..."
```

---

### Stage 2 — HazardAgent

**Reads:** `ctx.requirement`, `ctx.iec_62304_class`, `ctx.iec_62304_rationale`  
**Writes:** `ctx.hazard`, `ctx.hazardous_situation`, `ctx.harm`, `ctx.probability_before_mitigation`, `ctx.severity`, `ctx.risk_level_before_mitigation`

Notice how the hazard agent's prompt *includes* the classification output:
```
IEC 62304 CLASSIFICATION: C
CLASSIFICATION RATIONALE: Life-critical cardiac monitoring software...
```

This is context passing in action — each agent builds on what came before.

---

### Stage 3 — Parallel execution (FMEA + FTA + Usability)

All three agents read from `ctx` but write to *different fields*:

```python
# orchestrator.py
await asyncio.gather(
    fmea_agent.run(ctx),       # writes ctx.fmea
    fta_agent.run(ctx),        # writes ctx.fta
    usability_agent.run(ctx),  # writes ctx.use_error_analysis
)
```

Because they write to non-overlapping fields, this is safe for concurrent execution.

**Why can they run in parallel?**
- FMEAAgent only needs `ctx.hazard`, `ctx.severity`, `ctx.probability_before_mitigation`.
- FTAAgent only needs `ctx.hazard`, `ctx.harm`, `ctx.hazardous_situation`.
- UsabilityAgent only needs `ctx.hazard`, `ctx.harm`.
- None of them need each other's output.

---

### Stage 4 — MitigationAgent

**Reads:** `ctx.fmea`, `ctx.fta`, `ctx.hazard`, `ctx.severity`, plus all hazard fields  
**Writes:** `ctx.risk_controls`, `ctx.probability_after_mitigation`, `ctx.risk_level_after_mitigation`, `ctx.residual_risk_acceptable`

This agent's prompt explicitly includes the FMEA and FTA outputs as JSON:
```
FMEA OUTPUT:
{
  "failure_mode": "Waveform display freezes",
  "rpn_before": 216,
  ...
}

FTA OUTPUT:
{
  "minimal_cut_sets": ["BE-001", "BE-002", ...]
  ...
}
```

This is why it cannot run until Stages 1–3 are complete.

---

### Stage 7 — ReviewAgent (self-reflection)

The ReviewAgent is special — it receives a condensed review summary instead of the full nested report. This keeps token use lower and focuses the review on fields that affect consistency, traceability, and risk acceptability:

```python
# agents/review_agent.py
def build_user_prompt(self, ctx: RiskContext) -> str:
    summary = build_review_summary(ctx)
    return f"""Review the following medical device risk analysis for consistency and completeness.

ANALYSIS SUMMARY:
{json.dumps(summary, indent=2)}
..."""
```

It then checks:
- Is the FMEA RPN consistent with the probability/severity ratings?
- Does the residual risk level match the controls applied?
- Is the traceability matrix complete?
- Are any regulatory references missing or incorrect?

If inconsistencies are found, they appear in `validation_summary.flags`.

---

## The retry mechanism

### What can go wrong

Even with a "return ONLY JSON" instruction, models occasionally:
- Wrap the JSON in markdown code fences (` ```json ... ``` `)
- Add an explanatory sentence before the JSON
- Omit a required field
- Return truncated JSON if the response is very long

### How TraceFlow AI handles it

```python
# orchestrator.py
async def _run_agent_with_retry(self, agent, ctx: RiskContext) -> None:
    for attempt in range(1, MAX_RETRIES + 1):   # MAX_RETRIES = 3
        try:
            await agent.run(ctx)
            return  # success
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            if attempt < MAX_RETRIES:
                # Inject the specific error into context
                ctx.errors.append(
                    f"{agent.agent_name} attempt {attempt} error: {exc}. "
                    "Return ONLY valid JSON matching the required schema."
                )
    raise RuntimeError(f"{agent.agent_name} failed after {MAX_RETRIES} attempts")
```

```python
# base_agent.py — the error is appended to the next prompt
async def run(self, ctx: RiskContext) -> None:
    prior_errors = [e for e in ctx.errors if self.agent_name in e]
    user_prompt = self.build_user_prompt(ctx)
    if prior_errors:
        user_prompt += "\n\n# ERROR FEEDBACK FROM PREVIOUS ATTEMPT:\n" + "\n".join(prior_errors)
    ...
```

### Example retry cycle

```
Attempt 1:
  Agent returns: ```json\n{"iec_62304_class": "C", ...}\n```
  json.loads() fails on the markdown fences
  Error injected: "ClassificationAgent attempt 1 error: ..."

Attempt 2:
  Prompt includes: "# ERROR FEEDBACK: ClassificationAgent attempt 1 error: ..."
  Agent returns: {"iec_62304_class": "C", ...}   <-- plain JSON
  json.loads() succeeds
  Context updated
```

---

## Reading the agent logs

Every raw API response is stored in `ctx.agent_logs`:

```python
ctx.agent_logs["ClassificationAgent"]  # raw string from API
ctx.agent_logs["HazardAgent"]
# ...
```

This is useful for debugging. After running the pipeline, you can access logs through
the orchestrator:

```python
orch = Orchestrator(api_key=api_key)
report = asyncio.run(orch.run(requirement))
# Access raw logs
for agent_name, raw_response in orch.ctx.agent_logs.items():
    print(f"=== {agent_name} ===")
    print(raw_response[:500])
```

---

## Modifying verbosity

All orchestrator stages use Python's `logging` module:

```bash
# See all INFO logs (stage progress)
python main.py analyze "<req>" --verbose

# Capture logs to file
python main.py analyze "<req>" --verbose 2> pipeline.log
```

To add DEBUG logging in your own scripts:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
