# ADR-003: Async/Await with Exponential Backoff Retries

**Status**: Accepted  
**Date**: July 29, 2026  
**Related**: ADR-001, ADR-002

---

## Problem

TraceFlow AI makes external API calls to Anthropic's LLM API. These calls can:

- **Timeout** - API temporarily slow
- **Rate limit** - Too many requests too fast
- **Transient errors** - 5xx server errors (usually recover within seconds)

How should TraceFlow AI handle these failures without losing the entire analysis?

---

## Decision

Use **Python async/await** with **exponential backoff retries**:

### Async/Await for I/O

```python
class Orchestrator:
    async def run(self, context: RiskContext):
        # Non-blocking I/O - can call multiple agents concurrently
        await asyncio.gather(
            FMEAAgent().run(context),
            FTAAgent().run(context),
            SecurityAgent().run(context),
            timeout=60.0,  # 60s max for all three in parallel
        )
```

### Exponential Backoff for Retries

```python
class BaseAgent(ABC):
    async def _call_llm_with_retry(self, prompt: str) -> str:
        max_retries = 3
        base_wait = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                response = await self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30.0,
                )
                return response.content[0].text
                
            except APIError as e:
                wait_time = base_wait * (2 ** attempt)  # Exponential: 1s, 2s, 4s
                if attempt < max_retries - 1:
                    logger.warning(
                        f"API error (attempt {attempt+1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"Failed after {max_retries} attempts: {e}")
```

---

## Why Async/Await?

### ✅ Advantages

| Benefit | Example |
|---------|---------|
| **Non-blocking I/O** | While waiting for LLM API, CPU can handle other agents |
| **Concurrency** | Run 5 independent agents in parallel with single thread (not multithreading complexity) |
| **Cleaner Code** | `await` reads naturally vs callbacks or Futures |
| **Testable** | Use `pytest-asyncio` to test async code easily |
| **Standard Python** | Built-in since Python 3.5; mature ecosystem |

### Concurrency Model

```python
# SEQUENTIAL (slower): ~45 seconds
classification = await ClassificationAgent().run(context)  # ~5s
hazard = await HazardAgent().run(context)                   # ~5s
await asyncio.gather(
    FMEAAgent().run(context),      # ~10s
    FTAAgent().run(context),       # ~10s
    SecurityAgent().run(context),  # ~10s
)  # Total: ~50s

# PARALLEL (faster): ~20 seconds
await ClassificationAgent().run(context)  # ~5s (prerequisite)
await HazardAgent().run(context)          # ~5s (prerequisite)
await asyncio.gather(
    FMEAAgent().run(context),      # ~10s
    FTAAgent().run(context),       # ~10s (runs in parallel)
    SecurityAgent().run(context),  # ~10s (runs in parallel)
)  # Total: ~20s (3 agents in parallel)
```

---

## Why Exponential Backoff?

### ❌ Without Retries
```python
# First call to API fails
await client.messages.create(...)  # TimeoutError
# Entire analysis fails, user gets error
```

### ❌ Naive Retry (No Backoff)
```python
for _ in range(3):
    try:
        return await client.messages.create(...)
    except APIError:
        pass  # Retry immediately
# Hammers API with 3 requests in rapid succession
# API might still be recovering; increases load
```

### ✅ Exponential Backoff
```python
# First attempt: immediate
await client.messages.create(...)  # Fails

# Second attempt: wait 1 second (API recovering)
await asyncio.sleep(1.0)
await client.messages.create(...)  # Succeeds!

# If still failing:
# Third attempt: wait 2 seconds (give API more time)
# Fourth attempt: wait 4 seconds
# (Follows 2^n pattern: gives system time to recover)
```

### Benefits

| Scenario | Result |
|----------|--------|
| **Transient timeout** | Retry succeeds; analysis completes ✓ |
| **Temporary rate limit** | Exponential backoff prevents hammer; API recovers ✓ |
| **API down (long-term)** | Fails after 3 retries; user knows quickly (not slow hang) ✓ |

---

## Implementation

### In pytest

```python
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Auto-mark async tests

# tests/test_agents.py
@pytest.mark.asyncio
async def test_agent_with_retry():
    mock_client = AsyncMock()
    
    # Simulate: first call fails, second succeeds
    mock_client.messages.create.side_effect = [
        APIError("timeout"),
        MagicMock(content=[MagicMock(text='{"result": "success"}')])
    ]
    
    agent = ClassificationAgent(mock_client)
    context = RiskContext(requirement="Test")
    await agent.run(context)  # Should retry and succeed
    
    assert context.iec_62304_class is not None
    assert mock_client.messages.create.call_count == 2
```

### Production Usage

```python
# main.py
async def main():
    orchestrator = Orchestrator(api_key=os.getenv("ANTHROPIC_API_KEY"))
    context = RiskContext(requirement=args.requirement)
    
    try:
        await orchestrator.run(context)
        print_report(context)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

# Run with asyncio
if __name__ == "__main__":
    asyncio.run(main())
```

---

## Jitter (Optional Enhancement)

For high-concurrency scenarios, add random jitter to prevent thundering herd:

```python
import random

wait_time = base_wait * (2 ** attempt)
jitter = random.uniform(0, wait_time * 0.1)  # ±10% randomness
await asyncio.sleep(wait_time + jitter)
```

---

## Monitoring & Observability

Track retry metrics for debugging:

```python
class Agent:
    def __init__(self):
        self.retry_count = 0
        self.api_calls = 0
    
    async def _call_llm_with_retry(self, prompt):
        for attempt in range(3):
            self.api_calls += 1
            try:
                return await self.client.messages.create(...)
            except APIError:
                self.retry_count += 1
                # Log for analysis
                logger.info(
                    f"{self.__class__.__name__}: "
                    f"retry_count={self.retry_count}, "
                    f"api_calls={self.api_calls}"
                )
```

---

## Alternatives Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Sync + No Retries** | Simple | Fails on any API error; slow sequential execution |
| **Multithreading** | Parallel execution | Complex; GIL limits concurrency; harder to debug |
| **Async + No Retries** | Non-blocking; concurrent | Still fails on transient errors |
| **Async + Exponential Backoff** | ✅ Resilient; efficient; concurrent | Requires async/await knowledge |

---

## Related Decisions

- **ADR-001**: Multi-agent pipeline means independent retries per agent
- **ADR-002**: RiskContext + Shared state compatible with async
- **SYSTEM_DESIGN.md**: Full error handling strategy

