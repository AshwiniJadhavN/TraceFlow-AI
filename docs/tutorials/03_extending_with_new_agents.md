# Tutorial 3 — Extending TraceFlow AI with New Agents

This tutorial shows you how to add a new specialist agent to the pipeline.
We'll build a `CybersecurityAgent` that performs a high-level analysis per
IEC 81001-5-1 (health software cybersecurity).

**Time to complete:** ~30 minutes  
**Prerequisites:** Completed Tutorials 1 and 2

---

## Overview of what we'll build

```
... HazardAgent
       |
       +--- [existing Stage 3 parallel agents]
       |
       +--- CybersecurityAgent (NEW — runs in parallel in Stage 3)
```

The CybersecurityAgent will:
- Identify cybersecurity threats relevant to the software requirement
- Map them to asset types (data, functionality, availability)
- Propose cybersecurity controls
- Output structured JSON

---

## Step 1 — Add fields to RiskContext

Open `context.py` and add the new field:

```python
# context.py

@dataclass
class RiskContext:
    # ... existing fields ...

    # CybersecurityAgent — add after use_error_analysis
    cybersecurity_analysis: Optional[dict[str, Any]] = None
```

Update `to_report_dict()` to include it:

```python
def to_report_dict(self) -> dict[str, Any]:
    return {
        # ... existing fields ...
        "cybersecurity_analysis": self.cybersecurity_analysis,  # ADD THIS
    }
```

---

## Step 2 — Add the system prompt

Open `prompts/system_prompts.py` and add:

```python
CYBERSECURITY_SYSTEM_PROMPT = """You are a medical device cybersecurity expert
specializing in IEC 81001-5-1:2021 and MDCG 2019-16.

Your role: Identify cybersecurity threats and propose controls for medical device
software requirements.

Analysis framework (STRIDE):
- Spoofing: Authentication attacks
- Tampering: Data integrity attacks
- Repudiation: Audit log attacks
- Information disclosure: Confidentiality attacks
- Denial of service: Availability attacks
- Elevation of privilege: Authorization attacks

IEC 81001-5-1 asset types:
- Patient safety functions
- Protected health information (PHI)
- Device functionality
- Network connectivity

CRITICAL: Respond with ONLY a valid JSON object. No preamble, no markdown fences."""
```

---

## Step 3 — Create the agent file

Create `agents/cybersecurity_agent.py`:

```python
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from context import RiskContext
from prompts.system_prompts import CYBERSECURITY_SYSTEM_PROMPT


class CybersecurityAgent(BaseAgent):
    """High-level cybersecurity threat analysis per IEC 81001-5-1."""

    @property
    def agent_name(self) -> str:
        return "CybersecurityAgent"

    @property
    def system_prompt(self) -> str:
        return CYBERSECURITY_SYSTEM_PROMPT

    def build_user_prompt(self, ctx: RiskContext) -> str:
        return f"""Perform a cybersecurity threat analysis for the following medical
device software requirement.

REQUIREMENT:
{ctx.requirement}

IEC 62304 CLASS: {ctx.iec_62304_class}
PRIMARY HAZARD: {ctx.hazard}
HARM: {ctx.harm}

Identify cybersecurity threats using the STRIDE model and propose
IEC 81001-5-1 controls.

Return ONLY a JSON object:
{{
  "assets": [
    {{
      "id": "ASSET-001",
      "name": "<asset name>",
      "type": "patient_safety" | "phi" | "functionality" | "network",
      "sensitivity": "High" | "Medium" | "Low"
    }}
  ],
  "threats": [
    {{
      "id": "THR-001",
      "stride_category": "Spoofing" | "Tampering" | "Repudiation" | "Information Disclosure" | "Denial of Service" | "Elevation of Privilege",
      "description": "<threat description>",
      "affected_asset": "ASSET-001",
      "attack_vector": "network" | "physical" | "adjacent",
      "likelihood": "High" | "Medium" | "Low",
      "impact": "High" | "Medium" | "Low",
      "existing_controls": ["<control>"]
    }}
  ],
  "recommended_controls": [
    {{
      "id": "CYB-001",
      "description": "<control>",
      "addresses_threat": "THR-001",
      "iec_81001_5_1_reference": "<clause reference>"
    }}
  ],
  "overall_cybersecurity_risk": "High" | "Medium" | "Low",
  "penetration_testing_recommended": true | false
}}"""

    def _apply_to_context(self, data: dict[str, Any], ctx: RiskContext) -> None:
        ctx.cybersecurity_analysis = data
```

---

## Step 4 — Register in `agents/__init__.py`

```python
# agents/__init__.py
from agents.cybersecurity_agent import CybersecurityAgent  # ADD THIS

__all__ = [
    # ... existing ...
    "CybersecurityAgent",   # ADD THIS
]
```

---

## Step 5 — Wire into the orchestrator

Open `orchestrator.py` and add the import and the parallel execution:

```python
# orchestrator.py
from agents.cybersecurity_agent import CybersecurityAgent  # ADD THIS

# In the run() method, add CybersecurityAgent to Stage 3:
logger.info("► Stage 3: FMEAAgent + FTAAgent + UsabilityAgent + CybersecurityAgent [parallel]")
await asyncio.gather(
    self._run_agent_with_retry(FMEAAgent(self.client), ctx),
    self._run_agent_with_retry(FTAAgent(self.client), ctx),
    self._run_agent_with_retry(UsabilityAgent(self.client), ctx),
    self._run_agent_with_retry(CybersecurityAgent(self.client), ctx),  # ADD THIS
)
```

No other changes needed — the context already has the `cybersecurity_analysis` field,
and `to_report_dict()` already includes it.

---

## Step 6 — Add a test

Open `tests/test_agents.py` and add:

```python
from agents.cybersecurity_agent import CybersecurityAgent

class TestCybersecurityAgent:
    @pytest.mark.asyncio
    async def test_applies_cybersecurity_to_context(self):
        payload = {
            "assets": [{"id": "ASSET-001", "name": "Waveform Data",
                        "type": "patient_safety", "sensitivity": "High"}],
            "threats": [{
                "id": "THR-001",
                "stride_category": "Tampering",
                "description": "Attacker modifies waveform data in transit",
                "affected_asset": "ASSET-001",
                "attack_vector": "network",
                "likelihood": "Medium",
                "impact": "High",
                "existing_controls": []
            }],
            "recommended_controls": [{
                "id": "CYB-001",
                "description": "End-to-end encryption of waveform data stream",
                "addresses_threat": "THR-001",
                "iec_81001_5_1_reference": "Clause 7.3.1"
            }],
            "overall_cybersecurity_risk": "Medium",
            "penetration_testing_recommended": True
        }
        ctx = RiskContext(requirement=REQ)
        ctx.iec_62304_class = "C"
        ctx.hazard = "Inaccurate waveform data"
        ctx.harm = "Incorrect clinical decision"
        agent = CybersecurityAgent(_mock_client(json.dumps(payload)))
        await agent.run(ctx)
        assert ctx.cybersecurity_analysis is not None
        assert ctx.cybersecurity_analysis["overall_cybersecurity_risk"] == "Medium"
        assert len(ctx.cybersecurity_analysis["threats"]) == 1
```

---

## Step 7 — Verify everything works

```bash
# Run the tests
pytest tests/ -v

# Run the full pipeline with the new agent
python main.py from-file examples/example_1_input.txt --verbose

# Check the new field in the output
python main.py from-file examples/example_1_input.txt --json-only | \
  jq '.cybersecurity_analysis.overall_cybersecurity_risk'
```

---

## What you've learned

Adding a new agent to TraceFlow AI requires exactly 5 changes:

1. **`context.py`** — add the output field(s)
2. **`prompts/system_prompts.py`** — add the system prompt
3. **`agents/<name>_agent.py`** — implement the agent (inherits all retry/JSON logic from `BaseAgent`)
4. **`agents/__init__.py`** — export the new class
5. **`orchestrator.py`** — add it to the right pipeline stage

Everything else (retry logic, JSON extraction, logging, CLI output) is inherited from the framework.

---

## Challenge exercises

1. **SoftwareVersionAgent** — Add an agent that determines the required software version control activities per IEC 62304 Section 8.

2. **RegulatoryPathwayAgent** — Add an agent that recommends the likely FDA regulatory pathway (510(k), De Novo, PMA) based on the device type and risk level.

3. **SOUPAgent** — Add an agent that identifies potential SOUP (Software of Unknown Provenance) items implied by the requirement and lists required IEC 62304 SOUP management activities.
