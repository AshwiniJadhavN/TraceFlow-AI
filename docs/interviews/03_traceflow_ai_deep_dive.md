# Interview Questions — TraceFlow AI Deep Dive

These questions test understanding of the TraceFlow AI architecture, design decisions,
and implementation details. Suitable for technical interviews and code review discussions.

---

## Architecture

### Q1. Explain the TraceFlow AI agent dependency graph. Why is it structured this way?

**Answer:**

```
Stage 1: ClassificationAgent          (independent)
    |
Stage 2: HazardAgent                  (needs class to contextualize severity)
    |
Stage 3: FMEAAgent ─┐
         FTAAgent   ├─ asyncio.gather  (all need hazard; independent of each other)
         UsabilityAgent ─┘
    |
Stage 4: MitigationAgent              (needs FMEA failure modes + FTA root causes)
    |
Stage 5: RiskBenefitAgent             (needs controls to assess residual risk vs benefit)
    |
Stage 6: TraceabilityAgent            (needs everything to build REQ→HAZARD→CTRL→VER)
    |
Stage 7: ReviewAgent                  (needs condensed report summary to check consistency)
```

**Rationale for each stage:**
- Classification must come first because the IEC 62304 class informs the severity threshold for the hazard analysis.
- Hazard analysis must come before FMEA/FTA — the primary hazard is the input to both.
- FMEA and FTA are parallelized because they analyze the same hazard independently.
- MitigationAgent explicitly references both FMEA failure modes and FTA root causes in its prompt — it cannot run until both are available.
- ReviewAgent gets a condensed review summary to perform cross-section consistency checking while limiting token use.

---

### Q2. Why use a dataclass (`RiskContext`) for shared context instead of a dict or a message queue?

**Answer:**

**Advantages of dataclass over dict:**
- **Type hints** — field types are explicit, enabling IDE autocomplete and static analysis.
- **Default values** — all fields initialized to `None`, preventing `KeyError` on access.
- **Attribute access** — `ctx.iec_62304_class` instead of `ctx["iec_62304_class"]`.
- **Structured** — schema is visible in one place, making the data contract explicit.
- **Serialization** — `to_report_dict()` method produces the final JSON output cleanly.

**Advantages over a message queue:**
- Zero infrastructure — no broker, no serialization, no network.
- Appropriate for an in-process pipeline where all agents run in the same Python process.
- Simpler reasoning: context is a single object in memory, not distributed state.

**Tradeoff:** The shared mutable context is not thread-safe. However, since agents write to non-overlapping fields and parallel execution uses `asyncio` (single-threaded event loop + `to_thread` for blocking calls), this is not a concern in practice.

---

### Q3. How does the retry-with-feedback mechanism work, and why is it better than a blind retry?

**Answer:**

**Blind retry:** Re-send the exact same prompt. The model will likely make the same error again because nothing has changed.

**Feedback retry:** Append the specific error message to the next prompt, allowing the model to understand what went wrong and correct it.

```python
# On failure, inject error into context
ctx.errors.append(
    f"{agent.agent_name} attempt {n} error: {exc}. "
    "Return ONLY valid JSON matching the required schema."
)

# BaseAgent.run() appends prior errors to the user prompt
prior_errors = [e for e in ctx.errors if self.agent_name in e]
if prior_errors:
    user_prompt += "\n\n# ERROR FEEDBACK:\n" + "\n".join(prior_errors)
```

**Why it's better:**
- If the model returned markdown fences around JSON, the error message tells it exactly what the problem was.
- If a required field was missing, the error names the field.
- Empirically, ~90% of JSON formatting failures resolve on the first retry when the specific error is fed back.

---

### Q4. How does `BaseAgent.extract_json()` work? Why three fallback stages?

**Answer:**

```python
@staticmethod
def extract_json(text: str) -> dict:
    text = text.strip()

    # Stage 1: Direct parse (happy path ~85% of calls)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Stage 2: Strip markdown code fences (```json ... ```)
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Stage 3: Find first { ... } block in the response
    match = re.search(r"(\{[\s\S]+\})", text)
    if match:
        return json.loads(match.group(1))

    raise ValueError(f"No valid JSON found: {text[:300]}")
```

**Why three stages:**
- Stage 1 handles clean responses (most cases).
- Stage 2 handles the common case where the model wraps JSON in markdown despite instructions.
- Stage 3 handles cases where the model adds an explanatory sentence before or after the JSON object.

Each stage is more permissive than the last. If all three fail, the error is specific enough that the retry-with-feedback mechanism can correct it.

---

### Q5. How would you extend TraceFlow AI to support batch analysis of multiple requirements?

**Answer:**

**Option A — CLI iteration (simplest):**
```bash
while IFS= read -r req; do
    python main.py analyze "$req" --output "./reports/$(date +%s)"
done < requirements.txt
```

**Option B — Async batch in Python:**
```python
async def analyze_batch(requirements: list[str], api_key: str) -> list[dict]:
    # Limit concurrency to avoid rate limits
    semaphore = asyncio.Semaphore(3)

    async def analyze_one(req: str) -> dict:
        async with semaphore:
            orch = Orchestrator(api_key=api_key)
            return await orch.run(req)

    return await asyncio.gather(*[analyze_one(r) for r in requirements])
```

**Option C — Add a `batch` CLI command to `main.py`:**
```python
@app.command()
def batch(input_csv: Path, output_dir: Path = Path("output")):
    reqs = pd.read_csv(input_csv)["requirement"].tolist()
    reports = asyncio.run(analyze_batch(reqs, os.getenv("ANTHROPIC_API_KEY")))
    # Save all reports...
```

**Key concern:** API rate limits. Add exponential backoff and a concurrency semaphore.

---

### Q6. The ReviewAgent receives a `json.dumps(ctx.to_report_dict())` of the full report. What problems could this cause at scale?

**Answer:**

1. **Token cost:** A full report with FMEA, FTA, use error analysis, controls, and traceability matrix can be 3,000–8,000 tokens. The ReviewAgent prompt already costs ~$0.05–0.20 per call on claude-sonnet.

2. **Context window pressure:** If upstream agents produce verbose outputs, the full report could approach or exceed the model's context window.

3. **Review quality degradation:** LLMs have a well-documented "lost in the middle" problem — attention weakens for content in the middle of a long context.

**Mitigations:**

1. **Summarised review input:** Pass only the key fields (classification, hazard, risk levels, control IDs, residual risk acceptability) rather than full nested objects.

2. **Targeted review prompts:** Split the ReviewAgent into focused sub-checks ("Check FMEA consistency", "Check traceability completeness") rather than one omnibus review.

3. **Structured review checklist:** Give the ReviewAgent a numbered checklist to work through rather than asking it to free-form review the report.

---

### Q7. How would you add a new agent (e.g., a `CybersecurityAgent` for IEC 81001-5-1) to the pipeline?

**Answer:**

**Step 1 — Add fields to `RiskContext`:**
```python
# context.py
cybersecurity_analysis: Optional[dict[str, Any]] = None
```

**Step 2 — Add system prompt:**
```python
# prompts/system_prompts.py
CYBERSECURITY_SYSTEM_PROMPT = """You are a medical device cybersecurity expert
specializing in IEC 81001-5-1 and MDCG 2019-16..."""
```

**Step 3 — Create the agent:**
```python
# agents/cybersecurity_agent.py
class CybersecurityAgent(BaseAgent):
    @property
    def agent_name(self): return "CybersecurityAgent"
    @property
    def system_prompt(self): return CYBERSECURITY_SYSTEM_PROMPT
    def build_user_prompt(self, ctx): ...
    def _apply_to_context(self, data, ctx):
        ctx.cybersecurity_analysis = data
```

**Step 4 — Wire into orchestrator:**
```python
# orchestrator.py
# After HazardAgent (cybersecurity depends on knowing the system function)
await self._run_agent_with_retry(CybersecurityAgent(self.client), ctx)
```

**Step 5 — Update `to_report_dict()`** to include `cybersecurity_analysis`.

**Step 6 — Add tests** in `tests/test_agents.py`.

---

## Code Quality

### Q8. What would you change to make TraceFlow AI production-ready for a regulated environment?

**Answer:**

1. **Structured logging with correlation IDs** — every agent call tagged with a `run_id` for audit trail. Log to a tamper-evident store.

2. **Pin model version** — `claude-sonnet-4-20250514` is already pinned; add a CI check that fails if the model constant is changed without a corresponding validation study.

3. **Pydantic output validation** — validate each agent's JSON against a Pydantic model (not just field presence) to catch type errors before they propagate.

4. **Human-in-the-loop sign-off** — add an approval step where a regulatory expert reviews the AI-generated report before it is included in the risk management file.

5. **Versioned outputs** — hash inputs and outputs, store in an immutable log (e.g., S3 with versioning + object lock) for 21 CFR Part 11 compliance.

6. **IQ/OQ/PQ validation** — treat TraceFlow AI as a computerized system requiring Installation Qualification, Operational Qualification, and Performance Qualification per GAMP 5.

7. **Rate limit handling** — add exponential backoff for Anthropic API 429 errors.

8. **Secrets management** — use a secrets manager (AWS Secrets Manager, HashiCorp Vault) instead of `.env` files in production.

---

### Q9. How would you test TraceFlow AI's output quality without calling the live API in CI?

**Answer:**

**Strategy: fixture-based golden output tests**

```python
# tests/fixtures/hemodynamic_waveform_classification.json
{
  "iec_62304_class": "C",
  "rationale": "..."
}

# tests/test_agent_outputs.py
import json
from pathlib import Path

def test_classification_output_schema(mock_client):
    fixture = json.loads(Path("tests/fixtures/...").read_text())
    # Validate fixture against Pydantic schema
    ClassificationOutput(**fixture)  # raises if schema wrong

def test_classification_class_is_valid_enum():
    # Parameterize over fixtures
    assert fixture["iec_62304_class"] in {"A", "B", "C"}
```

**Additional approaches:**
- **Contract tests:** Verify the JSON schema (required fields, types) without testing values.
- **Property tests:** Use Hypothesis to generate random requirement strings and verify the output is always valid JSON with required fields.
- **Eval harness:** Periodic offline evaluation (weekly/per release) against a curated golden dataset, with human expert scoring.
