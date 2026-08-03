# Troubleshooting Guide

Solutions for common issues in development, testing, and deployment of TraceFlow AI.

---

## CI/CD Pipeline Issues

### ❌ "Test Coverage Dropped Below 60%"

**Symptoms:**
- CI fails at coverage gate
- Error: `coverage.xml: TOTAL 45% < 60%`

**Root Cause:**
- New code added without tests
- Existing tests deleted or disabled
- Coverage thresholds changed

**Solution:**

```bash
# Generate detailed coverage report
make test-coverage

# Open HTML report to see uncovered lines
open htmlcov/index.html

# Add tests for uncovered code
pytest tests/ -k "new_feature" -v

# Verify coverage improved
make test-coverage

# If only temporarily needed, verify coverage with:
pytest tests/ --cov=agents --cov-report=term-missing | grep -A5 "TOTAL"
```

**Prevention:**
- Add tests for new code simultaneously
- Review coverage in PRs before merging
- Set coverage thresholds appropriately per module

---

### ❌ "Pyright Type Errors in CI but not locally"

**Symptoms:**
- Local: `make type-check` passes
- CI: Type checking fails
- Error mentions `3.11 vs 3.10` or cache issues

**Root Causes:**
1. Different Python versions locally vs CI (3.11 vs 3.10)
2. Stale type cache
3. Missing type stubs for dependencies

**Solution:**

```bash
# 1. Verify Python version (must be 3.11)
python --version
# Expected: Python 3.11.x

# 2. Clear type checking cache
rm -rf .pyright_cache .ruff_cache .mypy_cache

# 3. Reinstall with clean environment
deactivate
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Re-run type check
make type-check

# 5. If still failing, check specific file
pyright --outputjson agents/your_agent.py | jq '.generalDiagnostics'
```

**Manual type checking:**

```python
# pyright: ignore[reportMissingImports]
# Add to top of file if external library lacks stubs

from agents.base_agent import BaseAgent  # Will check types for this

# Check specific symbol
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from agents.classification_agent import ClassificationAgent
```

---

### ❌ "Docker Build Fails: 'pip install' timeout"

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all
the packages that are installed (x more).
TimeoutError: The read operation timed out
```

**Root Causes:**
- Network connectivity issues
- PyPI rate limiting
- Large dependency tree

**Solution:**

```bash
# 1. Build with longer timeout and verbose output
docker build \
  --progress=plain \
  --no-cache \
  --build-arg PIP_DEFAULT_TIMEOUT=1000 \
  -t traceflow-ai:debug .

# 2. If PyPI is slow, use different mirror
docker build \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  -t traceflow-ai:test .

# 3. Test locally first (bypasses Docker)
make ci-local

# 4. Rebuild with cache from previous successful build
docker build --progress=plain -t traceflow-ai:v2 .
```

**Long-term fix:**
```dockerfile
# In Dockerfile, add timeout for pip
RUN pip install --default-timeout=1000 -r requirements.txt
```

---

### ❌ "Pre-commit Hook Blocks Commit"

**Symptoms:**
```
Ruff found errors
E501 line too long (120 > 100 characters)
❌ git commit fails
```

**Solution:**

```bash
# 1. Auto-fix style issues
make format

# 2. Re-run type checks
make type-check

# 3. Run tests locally to pass pre-commit hook
make test

# 4. Try commit again
git add .
git commit -m "Your message"

# If hook still blocks (and you're 100% sure it's safe):
# ⚠️ Use with caution:
git commit --no-verify

# Document why you skipped hooks:
git log --oneline | head -1  # Shows your commit
git commit --amend -m "Original message

[skip-hooks-reason: Pre-commit took too long, verified locally]"
```

**Prevent long lines:**

```python
# Instead of:
result = some_function(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10)

# Do:
result = some_function(
    arg1, arg2, arg3, arg4, arg5,
    arg6, arg7, arg8, arg9, arg10,
)
```

---

### ❌ "Workflow Cancelled: 'cancel-in-progress: true' timed out"

**Symptoms:**
- Previous CI run still in progress
- New push cancels old run mid-way
- Workflow shows "cancelled" status

**Solution:**

```bash
# This is intentional behavior (see concurrency in ci.yml)
# To avoid it, wait for previous CI to complete before pushing

# View in-progress runs
gh run list --workflow=ci.yml --status in_progress

# Check specific run
gh run view <RUN_ID> --log

# If you need to force a rerun
gh run rerun <RUN_ID>
```

---

## Development Issues

### ❌ "ModuleNotFoundError: No module named 'agents'"

**Symptoms:**
```python
Traceback (most recent call last):
  File "main.py", line 10, in <module>
    from agents.classification_agent import ClassificationAgent
ModuleNotFoundError: No module named 'agents'
```

**Root Causes:**
- Virtual environment not activated
- Python path not set correctly
- Running from wrong directory

**Solution:**

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Verify you're in repository root
pwd  # Should end with /TraceFlow-AI
ls agents/  # Should show agent files

# 3. Run from repo root
cd /Users/ashwinijadhav/GenAI/TraceFlow-AI
python main.py --help

# 4. If still failing, reinstall package in development mode
pip install -e .
```

---

### ❌ "Test Hangs or Times Out (pytest-asyncio)"

**Symptoms:**
```
FAILED tests/test_agents.py::test_hazard_agent - 
timeout: test did not complete within 60s
```

**Root Causes:**
- Async function not awaited
- Mock not configured for async
- Infinite loop in agent logic

**Solution:**

```python
# ✅ CORRECT: Use @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_agent_runs():
    result = await agent.run(context)  # await is required
    assert result.status == "success"

# ❌ WRONG: Missing @pytest.mark.asyncio
async def test_agent_runs():  # Won't run as async
    result = agent.run(context)  # Missing await

# ❌ WRONG: Async mock not configured
mock_client = MagicMock()  # Not an AsyncMock
result = await agent.run(context)  # Hangs

# ✅ CORRECT: Use AsyncMock for async functions
from unittest.mock import AsyncMock
mock_client = AsyncMock()
mock_client.messages.create = AsyncMock(return_value=...)
```

**Debug timeouts:**

```bash
# Run with verbose output and timeout
pytest tests/test_agents.py -vv -s --timeout=30

# If specific test hangs, isolate it
pytest tests/test_agents.py::test_hazard_agent -vv -s --pdb
# Use (Pdb) commands to step through
```

---

### ❌ "LLM Agent Returns Malformed JSON"

**Symptoms:**
```python
JSONDecodeError: Expecting value: line 1 column 1
Agent returned: "I can't determine the classification..."
```

**Root Causes:**
- LLM hallucination or rate limiting
- Invalid prompt template
- Anthropic API returning error message

**Solution:**

```python
# In agent or orchestrator, add validation:
import json
from typing import Any

def extract_json_safely(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response with fallback."""
    try:
        # Try direct parse first
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON from markdown code block
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Log for debugging
        print(f"Warning: Could not parse: {text[:100]}")
        return {"error": "parse_failed", "raw_response": text}

# In your agent:
response = client.messages.create(...)
try:
    payload = extract_json_safely(response.content[0].text)
    if "error" in payload:
        raise ValueError(f"LLM error: {payload}")
except Exception as e:
    # Retry logic here
    logger.error(f"Agent failed: {e}, retrying...")
```

**Testing with realistic LLM responses:**

```bash
# Create tests/fixtures/llm_responses.json
{
  "classification": {
    "success": "{\"iec_62304_class\": \"C\", ...}",
    "malformed": "I think this is Class C but...",
    "timeout": "API rate limit exceeded"
  }
}

# Use in tests
@pytest.fixture
def llm_response():
    with open("tests/fixtures/llm_responses.json") as f:
        return json.load(f)

def test_malformed_response(llm_response):
    agent = ClassificationAgent(mock_client)
    result = agent.extract_json_safely(llm_response["classification"]["malformed"])
    assert result.get("error") == "parse_failed"
```

---

### ❌ "Coverage Report Shows 0% for New Module"

**Symptoms:**
```
agents/new_agent.py   0%  (no coverage)
```

**Root Cause:**
- New module exists but has no tests
- New module imported but not executed

**Solution:**

```bash
# 1. Create test file
touch tests/test_new_agent.py

# 2. Add minimal test
cat > tests/test_new_agent.py << 'EOF'
import pytest
from agents.new_agent import NewAgent

def test_new_agent_initializes():
    agent = NewAgent()
    assert agent is not None
EOF

# 3. Run coverage again
make test-coverage

# 4. Verify coverage for your module
pytest tests/test_new_agent.py --cov=agents.new_agent
```

---

## Docker Issues

### ❌ "Docker: 'command not found' or Permission denied"

**Solution:**

```bash
# Install Docker (if not installed)
# On macOS:
brew install docker

# Start Docker daemon
# Launch Docker Desktop or run:
docker run hello-world

# If permission denied:
sudo usermod -aG docker $USER
# Log out and back in
```

---

### ❌ "Container Exits Immediately"

**Symptoms:**
```
docker run traceflow-ai
# Container exits with code 1, no output
```

**Debugging:**

```bash
# 1. Check container logs
docker logs <container_id>

# 2. Run with interactive terminal to see errors
docker run -it traceflow-ai bash
# Then manually run: python main.py --help

# 3. Check Dockerfile for issues
docker build --progress=plain -t traceflow-ai:debug .
```

---

## Performance Issues

### ⚠️ "Agents Running Slow (>60 seconds per requirement)"

**Diagnosis:**

```bash
# Profile orchestrator execution
python -m cProfile -s cumulative main.py analyze \
  --requirement "Test" \
  --output /tmp/profile.txt

# Identify slowest stages
grep -A10 "cumulative" /tmp/profile.txt
```

**Optimizations:**

```python
# 1. Parallelize independent agents
import asyncio

async def run_parallel_agents(context):
    # These don't depend on each other
    results = await asyncio.gather(
        fmea_agent.run(context),
        security_agent.run(context),
        usability_agent.run(context),
    )
    return results

# 2. Cache LLM responses for identical inputs
from functools import lru_cache

@lru_cache(maxsize=128)
async def cached_llm_call(prompt_hash):
    return await client.messages.create(...)
```

---

## Getting Help

1. **Check documentation first:**
   - [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
   - [SECURITY.md](SECURITY.md) - Security guidelines
   - [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) - Architecture

2. **Search existing issues:**
   ```bash
   gh issue list --search "your error message"
   ```

3. **Create detailed issue:**
   ```bash
   gh issue create --title "Error X" --body "$(cat debug-log.txt)"
   ```

4. **Run diagnostics:**
   ```bash
   make ci-local  # Full local check
   docker compose up  # Test in container
   ```

---

**Last Updated**: July 29, 2026
