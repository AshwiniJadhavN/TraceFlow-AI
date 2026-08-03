# Tutorial 1 — Getting Started with TraceFlow AI

This tutorial walks you through installing TraceFlow AI, running your first analysis,
and understanding the output.

**Time to complete:** ~20 minutes  
**Prerequisites:** Python 3.10+, an Anthropic API key

---

## Step 1 — Clone and install

```bash
git clone https://github.com/ashwinijadhavn/traceflow-ai.git
cd traceflow-ai

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate.bat     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2 — Configure your API key

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

You can get an API key at [console.anthropic.com](https://console.anthropic.com).

---

## Step 3 — Run your first analysis

Let's analyze the example requirement that ships with the project:

```bash
python main.py from-file examples/example_1_input.txt --verbose
```

You will see the pipeline stages executing in real time:

```
╭─────────────────────────────────────────────╮
│ TraceFlow AI                                │
│ Agentic Medical Device Risk Traceability    │
│                                             │
│ Requirement: The system shall display       │
│ real-time hemodynamic waveforms...          │
╰─────────────────────────────────────────────╯

⠋ Running agentic pipeline...
  ✓ ClassificationAgent completed (attempt 1)
  ✓ HazardAgent completed (attempt 1)
  ✓ FMEAAgent completed (attempt 1)
  ✓ FTAAgent completed (attempt 1)
  ✓ UsabilityAgent completed (attempt 1)
  ✓ MitigationAgent completed (attempt 1)
  ✓ RiskBenefitAgent completed (attempt 1)
  ✓ TraceabilityAgent completed (attempt 1)
  ✓ ReviewAgent completed (attempt 1)

Analysis complete!
┌──────────────────────────────────────────────────┐
│ Risk Analysis Summary                            │
│ IEC 62304 Class          │ C                     │
│ Hazard                   │ Inaccurate waveform.. │
│ Risk Before              │ Unacceptable          │
│ Risk After               │ Medium                │
│ Residual Risk Acceptable │ True                  │
│ Review Consistent        │ True                  │
└──────────────────────────────────────────────────┘

Outputs saved to:
  output/The_system_shall_display_real_time_risk_report.json
  output/The_system_shall_display_real_time_traceability.csv
  output/The_system_shall_display_real_time_risk_report.xlsx
  output/risk_matrix.png
```

---

## Step 4 — Explore the outputs

### JSON report

```bash
# Pretty-print the full report
cat output/*_risk_report.json | python -m json.tool

# Extract specific fields with jq
cat output/*_risk_report.json | jq '{
  class: .iec_62304_class,
  hazard: .hazard,
  risk_before: .risk_level_before_mitigation,
  risk_after: .risk_level_after_mitigation
}'
```

Expected output:
```json
{
  "class": "C",
  "hazard": "Inaccurate or missing hemodynamic waveform data",
  "risk_before": "Unacceptable",
  "risk_after": "Medium"
}
```

### Traceability CSV

Open `*_traceability.csv` in Excel or Google Sheets. Each row represents one
`Requirement → Hazard → Control → Verification` chain.

### Risk matrix PNG

Open `risk_matrix.png`. You will see a 5×4 ISO 14971 risk matrix with:
- **Left panel:** Before mitigation (star marker at the risk position)
- **Right panel:** After mitigation (star marker shifted to lower risk)

---

## Step 5 — Analyze your own requirement

Try a requirement from your own project:

```bash
python main.py analyze "The software shall alert the clinician when the patient's \
SpO2 reading falls below a configurable threshold."
```

Or write it to a file:

```bash
echo "The software shall alert the clinician when the patient's SpO2 reading falls below a configurable threshold." \
  > my_requirement.txt

python main.py from-file my_requirement.txt --output ./my_reports
```

---

## Step 6 — JSON-only mode (for scripting)

If you want to pipe the output to another tool:

```bash
python main.py analyze "<requirement>" --json-only > report.json

# Check residual risk acceptability
python main.py analyze "<requirement>" --json-only | jq '.residual_risk_acceptable'
```

---

## Understanding the report structure

| Field | Source agent | Description |
|---|---|---|
| `iec_62304_class` | ClassificationAgent | A, B, or C |
| `iec_62304_rationale` | ClassificationAgent | Justification for classification |
| `hazard` | HazardAgent | Root hazard (ISO 14971) |
| `hazardous_situation` | HazardAgent | Exposure sequence |
| `harm` | HazardAgent | Specific patient/user harm |
| `probability_before_mitigation` | HazardAgent | Frequent/Probable/Occasional/Remote/Improbable |
| `severity` | HazardAgent | Negligible/Marginal/Critical/Catastrophic |
| `risk_level_before_mitigation` | HazardAgent | Low/Medium/High/Unacceptable |
| `fmea` | FMEAAgent | Full FMEA entry with RPN before/after |
| `fta` | FTAAgent | Fault tree with minimal cut sets |
| `use_error_analysis` | UsabilityAgent | IEC 62366-1 use errors |
| `risk_controls` | MitigationAgent | List of risk controls with type and verification |
| `probability_after_mitigation` | MitigationAgent | Probability after controls |
| `risk_level_after_mitigation` | MitigationAgent | Risk level after controls |
| `residual_risk_acceptable` | MitigationAgent | true / false |
| `risk_benefit_analysis` | RiskBenefitAgent | ISO 14971 Cl. 9 benefit-risk analysis |
| `traceability` | TraceabilityAgent | Traceability matrix with coverage summary |
| `validation_summary` | ReviewAgent | Consistency check results |

---

## Troubleshooting

**`ANTHROPIC_API_KEY not set`**  
Make sure you created a `.env` file and set the key. The `.env` file must be in the
project root (same directory as `main.py`).

**`ModuleNotFoundError: No module named 'anthropic'`**  
Make sure your virtual environment is activated (`source .venv/bin/activate`) and
you ran `pip install -r requirements.txt`.

**Agent fails after 3 attempts**  
This is rare but can happen if the model returns unusually formatted output. Try running
again — the retry mechanism handles transient failures. If it persists, run with `--verbose`
to see the raw API responses.

**Output directory not created**  
TraceFlow AI creates the output directory automatically. If you get a permission error,
check that you have write access to the specified path.
