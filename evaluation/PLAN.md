# Evaluation Harness Implementation Plan

## Objective
Provide an isolated, comprehensive, offline evaluation framework for the Vaidya clinical multi-agent triage system without modifying any existing project files, touching the production PostgreSQL database, or requiring external network access.

## Architecture & Design
1. **Isolated Database Sandbox**:
   - Set `DATABASE_URL=sqlite:///:memory:` (or temp SQLite file) before importing application modules (`data.database`, `agents.orchestrator`).
   - Create schema tables via `Base.metadata.create_all()` on the SQLite test engine.
   - Provide clean session isolation per case evaluation run.

2. **Network Decoupling & PubMed Mocking**:
   - Default to mocking NCBI PubMed HTTP requests (`requests.get`) returning realistic mock JSON payloads (`esearch` and `esummary`).
   - Provide a `--live-pubmed` CLI flag to disable the mock for live integration tests when needed.

3. **50-Vignette Benchmark Dataset (`evaluation/dataset/cases.json`)**:
   - Rigorously covers all single red flags (10 conditions).
   - Covers all multi-symptom red flag combinations (7 combinations).
   - Covers age extremes (<2, >65) and sub-day durations ("2 hours", "30 minutes", "this morning").
   - Covers all 6 canonical specialists (Cardiology, Pulmonology, Neurology, Gastroenterology, Dermatology, General Medicine) with >=4 cases each.
   - Covers >=5 adversarial, negation, typo, and edge-case vignettes.

4. **Metrics Module (`evaluation/metrics.py`)**:
   - Pure, unit-testable evaluation metrics.
   - Safety: Emergency Recall/Precision, Missed Emergency cases, Under-triage & Over-triage rates, 4x4 Confusion Matrix, Safety-floor activations.
   - Routing: Specialty top-1 accuracy and per-specialty metrics.
   - Intake Extraction: Symptom set P/R/F1, Age exact match, Duration tolerance (±20%), Silent default rate (age=40, symptom=["fever"]).
   - Robustness & Determinism: Fallback rate, N-repeat determinism check, Fallback vs LLM severity agreement.
   - Operational: Latency percentiles (mean, p50, p95), trace row count, citation presence.

5. **CLI Runner (`evaluation/run_eval.py`)**:
   - CLI flags: `--mode fallback|llm|both`, `--repeat N`, `--live-pubmed`, `--fail-on-missed-emergency`, `--output-dir`.
   - Generates `per_case.csv`, `summary.json`, `report.md`, and optional confusion matrix PNG.
   - Prints formatted summary table to console.

6. **Smoke Test (`evaluation/test_eval_smoke.py`)**:
   - Quick pytest test running 3 cases through the evaluation pipeline.

7. **Documentation (`evaluation/README.md`)**:
   - Instructions for running evaluation, metric definitions, and findings.
