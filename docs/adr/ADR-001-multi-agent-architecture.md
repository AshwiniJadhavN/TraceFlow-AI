# ADR-001: Multi-Agent Architecture for Risk Analysis

**Status**: Accepted  
**Date**: July 29, 2026  
**Context**: Medical device risk analysis (IEC 62304, ISO 14971, AAMI TIR57)

---

## Problem

TraceFlow AI must produce traceable, audit-ready risk reports for regulated medical devices. The analysis pipeline involves:

- **IEC 62304 Classification** (Class A/B/C)
- **Hazard Identification** (ISO 14971)
- **FMEA/FTA Analysis** (risk prioritization)
- **Cybersecurity Threats** (AAMI TIR57, STRIDE)
- **Usability Hazards** (IEC 62366-1)
- **Traceability Verification** (requirements → controls)

A monolithic LLM prompt would:
- ❌ Make validation & error detection difficult
- ❌ Obscure which stage introduced errors/hallucinations
- ❌ Prevent independent testing of each analysis type
- ❌ Reduce auditability for regulatory submissions

---

## Decision

Implement a **multi-agent pipeline** where:

1. **Each agent has a single responsibility** (classification, hazard detection, etc.)
2. **Shared RiskContext** passes data between agents (no tight coupling)
3. **Independent validation** at each stage (reject malformed outputs)
4. **Automatic retry logic** for transient LLM failures
5. **Async/await pattern** for non-blocking I/O

### Agent Sequence

```
Requirement
    ↓
ClassificationAgent (IEC 62304 class)
    ↓
HazardAgent (ISO 14971 hazards)
    ↓
┌───────┬──────────┬─────────────┬─────────────┐
│       │          │             │             │
v       v          v             v             v
FMEA    FTA    Usability    Security      Mitigation
Agent   Agent   Agent         Agent         Agent
│       │       │             │             │
└───────┴──────────┴─────────────┴─────────────┘
        ↓
    VerificationAgent (trace to controls)
        ↓
    Output: Full audit-ready report
```

---

## Consequences

### ✅ Advantages

| Benefit | Impact |
|---------|--------|
| **Independent Testing** | Each agent testable with mocked LLM responses; no need for full pipeline in tests |
| **Error Isolation** | If agent fails, we know exactly which analysis stage broke |
| **Audit Trail** | Each agent's input/output can be logged and reviewed independently |
| **Regulatory Compliance** | FDA/CE reviewers can trace each stage; supports traceability requirements |
| **Easier Debugging** | Developers can test/debug each agent in isolation |
| **Flexible Retry Logic** | Retry individual agents if LLM is flaky, not entire pipeline |

### ❌ Disadvantages

| Drawback | Mitigation |
|----------|-----------|
| **Higher Latency** | Sequential agent calls; ~3-5s per agent (mitigate with parallelization for independent agents) |
| **More Complex Context** | Must maintain shared RiskContext schema; risk of accidental cross-dependencies |
| **More Test Code** | Need fixtures, mocks, parametrization for each agent (worth it for correctness) |

---

## Alternatives Considered

### 1. ❌ Single Monolithic Prompt
```
"Analyze this requirement for IEC 62304, ISO 14971, AAMI TIR57, 
and usability. Provide classification, hazards, FMEA, FTA, 
security threats, controls, and traceability."
```
**Problems**: LLM struggles with complex multi-part requests; hard to validate individual sections; auditors can't trace reasoning per analysis type.

### 2. ❌ Tree-of-Thoughts with Branching
```
Requirement → [Multiple parallel thought chains] → Consensus output
```
**Problems**: Complex state management; expensive (many LLM calls); hard to debug which branch introduced error.

### 3. ✅ **Multi-Agent (Selected)**
Clear separation of concerns; each agent optimized for its task; independently testable.

---

## Implementation Details

### RiskContext as Data Bus

```python
@dataclass
class RiskContext:
    requirement: str
    
    # Classification (IEC 62304)
    iec_62304_class: str = None
    
    # Hazards (ISO 14971)
    hazard: str = None
    hazardous_situation: str = None
    harm: str = None
    severity: str = None
    
    # FMEA (RPN)
    rpn_score: int = None
    
    # Security (AAMI TIR57)
    cybersecurity_risks: dict = None
    
    # Audit metadata
    errors: list[str] = field(default_factory=list)
    agent_log: dict = field(default_factory=dict)
```

### Agent Interface

```python
class BaseAgent(ABC):
    @abstractmethod
    async def run(self, context: RiskContext) -> None:
        """Validate input, process, update context."""
        pass
    
    def validate_output(self, result: dict) -> bool:
        """Ensure output matches schema."""
        pass
```

### Orchestrator Pattern

```python
class Orchestrator:
    async def run(self, context: RiskContext):
        # Sequential pipeline
        await ClassificationAgent().run(context)
        await HazardAgent().run(context)
        
        # Parallel agents (don't depend on each other)
        await asyncio.gather(
            FMEAAgent().run(context),
            FTAAgent().run(context),
            SecurityAgent().run(context),
        )
        
        await VerificationAgent().run(context)
        return context
```

---

## Related Decisions

- **ADR-002**: Shared RiskContext pattern for decoupling
- **ADR-003**: Async/await with exponential backoff
- **ADR-004**: Retry logic at agent level
- **SYSTEM_DESIGN.md**: Full architecture documentation

---

## References

- IEC 62304 - Software development for medical devices
- ISO 14971 - Risk management for medical devices
- AAMI TIR57 - Cybersecurity for medical devices
- [12-Factor App](https://12factor.net/) - Separation of concerns

