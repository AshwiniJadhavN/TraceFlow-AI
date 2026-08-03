# TraceFlow AI Quick Start

TraceFlow AI is a CLI-based engineering assistant for medical-device requirement analysis.
It produces structured, reviewable outputs for software-level and system-level risk workflows.

## 1. Read These First

Use this order if you are onboarding or re-orienting on the project:

1. [README.md](README.md) for the product overview and command surface.
2. [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) for product scope, users, and outcomes.
3. [docs/TECHNICAL_REQUIREMENTS.md](docs/TECHNICAL_REQUIREMENTS.md) for system constraints and engineering requirements.
4. [docs/DESIGN.md](docs/DESIGN.md) for the architecture and data flow.
5. [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for delivery priorities.
6. [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and [docs/adr/](docs/adr/) for the detailed architectural rationale.

## 2. Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env` before running either pipeline.

## 3. Run The Product

Software pipeline:

```bash
python main.py analyze "The system shall display real-time hemodynamic waveforms to the clinician during cardiac catheterization."
```

System pipeline:

```bash
python main.py system-analyze "The infusion pump shall deliver medication at a clinician-programmed rate accurate to ±5% of the set rate."
```

Input from file:

```bash
python main.py from-file examples/example_1_input.txt
```

## 4. Verify The Repo

```bash
make ci-local
```

Useful commands:

```bash
make lint
make format
make type-check
make test
make security-scan
```

## 5. Core Outputs

Each run can produce:

- JSON report
- CSV export
- Excel workbook
- Risk matrix image
- Audit metadata for agent sequence, validation, and privacy handling

Outputs are written to the `output/` directory by default.

## 6. Supporting Docs

- [DEPLOYMENT.md](DEPLOYMENT.md) for deployment and release steps.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for local and CI issues.
- [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.
- [SECURITY.md](SECURITY.md) for disclosure and handling expectations.
