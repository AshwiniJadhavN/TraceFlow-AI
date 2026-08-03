# Contributing to TraceFlow AI

Thank you for your interest in contributing to TraceFlow AI! This document provides guidelines and instructions for developing features, fixes, and improvements.

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone and navigate to repository
cd TraceFlow-AI

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install ruff pyright pre-commit pytest pytest-asyncio pytest-cov
```

### 2. Install Pre-commit Hooks

```bash
make install-hooks
```

This ensures code quality checks run automatically before each commit.

### 3. Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test locally
make lint          # Run code style checks
make format        # Auto-format code
make type-check    # Run type checker
make test          # Run test suite
make ci-local      # Run all checks together
```

## Code Quality Standards

### Linting & Formatting

- **Ruff** is used for linting and formatting
- Run `make format` to auto-fix code style issues
- The CI pipeline enforces code style checks

### Type Checking

- **Pyright** performs static type analysis
- Type hints are required for public APIs
- Run `make type-check` locally before submitting PRs
- Type checking must pass in CI

### Testing

- All changes must include tests
- Maintain **60%+ code coverage** on core modules:
  - `agents/` - Core agent implementations
  - `output/` - Output formatting and analysis
  - `prompts/` - Prompt construction
  - `validators/` - Data validation

```bash
make test                 # Run all tests
make test-verbose         # Detailed output
make test-coverage        # Generate coverage report (htmlcov/index.html)
```

### Pre-commit Hooks

The following checks run automatically before commits:

- **Ruff** code style and import safety (auto-fixes where possible)
- **Unit tests** with 60%+ coverage requirement (fast offline tests)

To bypass hooks (not recommended):
```bash
git commit --no-verify
```

## Pull Request Process

1. **Branch naming**: Use `feature/`, `fix/`, `docs/`, or `chore/` prefixes
   ```bash
   git checkout -b feature/risk-matrix-improvements
   git checkout -b fix/hazard-classification-bug
   ```

2. **Commit messages**: Write clear, descriptive commit messages
   ```
   Fix: Correct FMEA RPN calculation for Class B devices
   
   - Updated scoring logic to match IEC 62304 section 5.2
   - Added test cases for edge conditions
   - Verified against reference implementations
   ```

3. **Local validation** before opening a PR:
   ```bash
   make ci-local    # All checks must pass
   ```

4. **Pull request expectations**:
   - Clear description of the change and its rationale
   - Link related issues: "Closes #123"
   - Ensure CI passes (lint, type-check, test, coverage)
   - Maintain or improve code coverage
   - Add/update tests for behavioral changes
   - Update documentation if needed

5. **Code review**: Address feedback and maintain conversation with reviewers

## Project Structure

```
TraceFlow-AI/
├── agents/              # Core agent implementations
│   ├── base_agent.py   # Abstract base class
│   ├── classification_agent.py  # IEC 62304 classification
│   ├── hazard_agent.py          # ISO 14971 hazard analysis
│   ├── fmea_agent.py            # FMEA (RPN) analysis
│   ├── fta_agent.py             # FTA/MCS analysis
│   └── ...
├── output/             # Report generation & formatting
│   ├── formatter.py    # JSON/CSV/Excel output
│   └── risk_matrix.py  # Risk matrix visualization
├── prompts/            # LLM prompt templates
│   └── system_prompts.py
├── validators/         # Input/output validation
│   ├── data_privacy.py
│   └── output_validators.py
├── tests/              # Test suite
│   ├── test_agents.py
│   ├── test_orchestrator.py
│   └── ...
├── main.py            # CLI entry point
├── orchestrator.py    # Pipeline orchestration
└── system_orchestrator.py # System-level analysis
```

## Adding New Agents

See [docs/tutorials/03_extending_with_new_agents.md](../docs/tutorials/03_extending_with_new_agents.md) for detailed instructions on creating new analysis agents.

## Regulatory & Compliance

TraceFlow AI produces outputs for regulated medical devices. When contributing:

- Maintain alignment with IEC 62304, ISO 14971, and other regulatory standards
- Document assumptions and methodologies clearly
- Include traceability references in outputs
- Ensure backward compatibility for existing analyses

## Issues & Discussions

- **Bug reports**: Use GitHub Issues with "bug" label
- **Feature requests**: Use GitHub Issues with "enhancement" label
- **Discussions**: Use GitHub Discussions for design questions

## Questions?

- Check existing documentation in `/docs`
- Review system design: [SYSTEM_DESIGN.md](../SYSTEM_DESIGN.md)
- Open an issue for guidance

Thank you for contributing to TraceFlow AI! 🚀
