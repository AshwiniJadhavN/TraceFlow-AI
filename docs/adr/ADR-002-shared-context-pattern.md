# ADR-002: Shared RiskContext Pattern for Data Flow

**Status**: Accepted  
**Date**: July 29, 2026  
**Supersedes**: None  
**Related**: ADR-001

---

## Problem

In a multi-agent pipeline, how should agents communicate and pass data?

### Options Evaluated

1. **Tight Coupling** - Agents call each other directly
   ```python
   classification = ClassificationAgent().run(requirement)
   hazard = HazardAgent(classification).run()  # Depends on prev
   ```
   ❌ Hard to test independently; breaks if one agent changes

2. **Message Queue** - Agents publish/subscribe to events
   ```python
   hazard_agent.subscribe("classification.complete")
   classification_agent.emit("classification.complete", data)
   ```
   ❌ Complex orchestration; harder to debug; overkill for linear pipeline

3. **Shared RiskContext** - All agents read/write shared data structure
   ```python
   context = RiskContext(requirement="...")
   await classification_agent.run(context)  # Updates context
   await hazard_agent.run(context)  # Reads from context
   ```
   ✅ Simple, explicit; easy to test; clear dependencies

---

## Decision

Use a **shared RiskContext dataclass** that:

- All agents read from and write to
- Contains full pipeline state (requirement → final report)
- Includes audit metadata (errors, timestamps, agent logs)
- Is validated at each stage

### RiskContext Schema

```python
@dataclass
class RiskContext:
    """Shared data structure for multi-agent pipeline."""
    
    # Input
    requirement: str
    intended_use: str = None
    user_profile: str = None
    
    # IEC 62304 Classification
    iec_62304_class: Optional[str] = None
    classification_rationale: Optional[str] = None
    
    # ISO 14971 Hazards
    hazard: Optional[str] = None
    hazardous_situation: Optional[str] = None
    harm: Optional[str] = None
    probability: Optional[str] = None
    severity: Optional[str] = None
    
    # FMEA Analysis
    fmea_results: Optional[dict] = None
    rpn_score: Optional[int] = None
    
    # AAMI TIR57 Security
    cybersecurity_risks: Optional[dict] = None
    security_controls: Optional[list] = None
    
    # Usability
    usability_hazards: Optional[list] = None
    
    # Audit metadata
    errors: list[str] = field(default_factory=list)
    agent_log: dict[str, dict] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def log_agent(self, agent_name: str, status: str, output: dict) -> None:
        """Track what each agent did."""
        self.agent_log[agent_name] = {
            "status": status,
            "output_keys": list(output.keys()),
            "timestamp": datetime.now(),
        }
```

---

## Consequences

### ✅ Advantages

| Benefit | Example |
|---------|---------|
| **Transparent Data Flow** | Read context to see what previous agents did |
| **Easy Testing** | Create context, run agent, verify fields updated |
| **No Side Effects** | Agents don't call each other; only read/write context |
| **Simple Debugging** | Print context at any point to see full state |
| **Audit Trail** | Log shows which agent set which field |

### ❌ Disadvantages

| Drawback | Mitigation |
|----------|-----------|
| **Accidental Cross-Dependencies** | Document which agents depend on which fields; use type hints |
| **Context Bloat** | Schema keeps growing; mitigate with composition (nested dataclasses) |
| **Implicit Ordering** | Agents must run in sequence; document in orchestrator |

---

## Agent Dependency Map

```
HazardAgent expects:
  ✓ context.requirement (from user input)
  ✓ context.iec_62304_class (from ClassificationAgent)
  
FMEAAgent expects:
  ✓ context.requirement
  ✓ context.hazard (from HazardAgent)
  ✓ context.severity (from HazardAgent)
  
SecurityAgent expects:
  ✓ context.requirement
  ✓ context.hazard (optional but preferred)
  
(No dependencies)
```

---

## Validation Strategy

Each agent must validate its inputs:

```python
class HazardAgent(BaseAgent):
    async def run(self, context: RiskContext) -> None:
        # Validate prerequisites
        if not context.requirement:
            raise ValueError("Requirement missing")
        if not context.iec_62304_class:
            raise ValueError("Must run ClassificationAgent first")
        
        # Process
        hazards = await self._analyze(context)
        
        # Validate output
        if not self._validate_hazard_output(hazards):
            context.errors.append("Invalid hazard output from LLM")
            return
        
        # Update context
        context.hazard = hazards["hazard"]
        context.harm = hazards["harm"]
        context.agent_log["HazardAgent"] = {"status": "success"}
```

---

## Comparison to Alternatives

| Pattern | Data Passing | Coupling | Testability | Complexity |
|---------|--------------|----------|------------|-----------|
| Tight coupling | Direct function calls | HIGH | Hard | Low |
| Message queue | Pub/sub events | MEDIUM | Medium | High |
| **Shared RiskContext** | Shared dataclass | LOW | Easy | Medium |

---

## Migration Path

If complexity grows, we can evolve to:
1. **Composition** - Separate dataclasses for each analysis type
2. **Event sourcing** - Log all state changes for audit trail
3. **Message queue** - If scaling to distributed agents

---

## Related

- **ADR-001**: Multi-agent architecture rationale
- **ADR-003**: Why async/await is compatible with this pattern
- **SYSTEM_DESIGN.md**: Full context definition

