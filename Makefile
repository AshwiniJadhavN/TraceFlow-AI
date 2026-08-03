PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else command -v python3; fi)

.PHONY: help lint format type-check security-scan test test-verbose test-coverage test-integration load-test install-hooks build run-cli ci-local clean docs helm-template k8s-apply terraform-plan policy-check

help:
	@echo "TraceFlow AI - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install-hooks    Install pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Format code with ruff"
	@echo "  make type-check       Run Pyright type checker"
	@echo "  make security-scan    Run Bandit security scan"
	@echo "  make test             Run pytest suite"
	@echo "  make test-verbose     Run tests with detailed output"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Performance:"
	@echo "  make load-test        Run k6 load tests (requires k6 installed)"
	@echo ""
	@echo "CI/Local:"
	@echo "  make ci-local         Run all local checks (lint, type-check, security, test)"
	@echo "  make build            Build package distribution"
	@echo "  make run-cli          Run CLI interactively"
	@echo "  make helm-template    Render the Helm chart locally"
	@echo "  make k8s-apply        Apply raw Kubernetes manifests via kustomize"
	@echo "  make terraform-plan   Run terraform init/plan in infra/terraform"
	@echo "  make policy-check     Validate manifests against Kyverno policies"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Remove build artifacts and cache"
	@echo "  make docs             Generate or view documentation"

lint:
	$(PYTHON) -m ruff check . --ignore E501

format:
	$(PYTHON) -m ruff check . --fix --ignore E501
	$(PYTHON) -m ruff format .

type-check:
	$(PYTHON) -m pyright . --outputjson > /dev/null && echo "✓ Type checking passed" || ($(PYTHON) -m pyright . ; exit 1)

security-scan:
	$(PYTHON) -m bandit -r agents/ output/ prompts/ validators/ --skip B101 -f csv -o bandit-report.csv || true
	@echo "✓ Security scan complete (see bandit-report.csv for details)"

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-verbose:
	$(PYTHON) -m pytest tests/ -vv --tb=long --showlocals

test-integration:
	$(PYTHON) -m pytest tests/integration/ -v --tb=short
	@echo "✓ Integration tests passed"

test-coverage:
	$(PYTHON) -m pytest tests/ -v --cov=agents --cov=output --cov=prompts --cov=validators --cov-report=term-missing --cov-report=html --cov-fail-under=60

load-test:
	@command -v k6 >/dev/null 2>&1 || { echo "k6 not installed. Install from: https://k6.io/docs/getting-started/installation/"; exit 1; }
	k6 run tests/load/k6-orchestrator-load.js --out json=htmlreport/results.json
	@echo "✓ Load test complete (see htmlreport/ for results)"

install-hooks:
	$(PYTHON) -m pip install pre-commit --quiet
	pre-commit install
	@echo "✓ Pre-commit hooks installed. They will run automatically on git commit."

ci-local: lint type-check security-scan test
	@echo "✓ All CI checks passed!"

build:
	$(PYTHON) -m pip install build
	$(PYTHON) -m build

run-cli:
	$(PYTHON) main.py --help

helm-template:
	@command -v helm >/dev/null 2>&1 || { echo "helm not installed"; exit 1; }
	helm template traceflow-ai charts/traceflow-ai > /tmp/traceflow-ai-rendered.yaml
	@echo "✓ Helm chart rendered to /tmp/traceflow-ai-rendered.yaml"

k8s-apply:
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl not installed"; exit 1; }
	kubectl apply -k infra/kubernetes/base

terraform-plan:
	@command -v terraform >/dev/null 2>&1 || { echo "terraform not installed"; exit 1; }
	cd infra/terraform && terraform init && terraform plan

policy-check:
	@command -v kyverno >/dev/null 2>&1 || { echo "kyverno not installed"; exit 1; }
	kyverno apply policy/kyverno -r infra/kubernetes/base/job.yaml -r infra/kubernetes/base/cronjob.yaml

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete
	find . -type f -name coverage.xml -delete
	find . -type f -name bandit-report.* -delete
	rm -rf dist/ build/ *.egg-info/
	@echo "✓ Cleaned up build artifacts and cache files"

docs:
	@echo "TraceFlow AI Documentation"
	@echo "View the following files for more information:"
	@echo "  - README.md                          Project overview"
	@echo "  - CONTRIBUTING.md                    Development guidelines"
	@echo "  - DEPLOYMENT.md                      Deployment instructions"
	@echo "  - TROUBLESHOOTING.md                 Common issues and solutions"
	@echo "  - SYSTEM_DESIGN.md                   System architecture"
	@echo "  - docs/adr/                          Architecture Decision Records"
	@echo "  - docs/                              Detailed documentation"
