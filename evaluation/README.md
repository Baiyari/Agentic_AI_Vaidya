# Vaidya Clinical Evaluation Harness

An offline, zero-network, isolated evaluation framework for the Vaidya Multi-Agent Health-Triage Advisor.

---

## 1. Overview & Core Philosophy

The evaluation harness measures the safety, clinical routing accuracy, and entity extraction performance of the Vaidya multi-agent pipeline against 50 standardized clinical vignettes.

### Key Guarantees:
- **Zero Production Database Contamination:** Evaluation runs against an in-memory SQLite database (`sqlite:///:memory:`) completely separate from the PostgreSQL database.
- **Offline & Mocked by Default:** NCBI PubMed API calls (`requests.get`) are mocked with realistic clinical responses, allowing full offline execution without network dependencies.
- **Strict Safety Prioritization:** Focuses on Emergency Sensitivity (Recall), missed emergency identification, and under-triage detection.

---

## 2. Quickstart & CLI Usage

### Running Evaluation in Fallback Mode (Deterministic Rules)
```bash
python evaluation/run_eval.py --mode fallback --repeat 3
```

### Running Evaluation with Gemini LLM Integration
```bash
python evaluation/run_eval.py --mode llm --repeat 3
```

### Running Both Modes for Head-to-Head Comparison
```bash
python evaluation/run_eval.py --mode both --repeat 3
```

### CI / Automated Safety Gate Flag
```bash
# Returns non-zero exit code if any critical emergency is missed
python evaluation/run_eval.py --mode fallback --fail-on-missed-emergency
```

### Running with Live PubMed Requests (Optional)
```bash
python evaluation/run_eval.py --mode fallback --live-pubmed
```

### Running the Smoke Test
```bash
pytest evaluation/test_eval_smoke.py -v
```

---

## 3. Command Line Options

| Argument | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--mode` | `str` | `fallback` | Execution mode: `fallback`, `llm`, or `both`. |
| `--repeat` | `int` | `3` | Number of test repetitions to verify determinism. |
| `--dataset` | `str` | `evaluation/dataset/cases.json` | Path to benchmark JSON dataset. |
| `--output-dir` | `str` | `evaluation/results/` | Output directory for CSV, JSON, and Markdown reports. |
| `--live-pubmed` | `flag` | `False` | Disables PubMed mocking and queries live NCBI E-Utilities. |
| `--fail-on-missed-emergency` | `flag` | `False` | Exits with status code 1 if Emergency Recall < 100%. |

---

## 4. Evaluated Metrics

### Clinical Safety Metrics (Highest Priority)
- **Emergency Recall (Sensitivity):** $\frac{\text{TP}_{\text{Emergency}}}{\text{TP}_{\text{Emergency}} + \text{FN}_{\text{Emergency}}}$. The system must maintain 100% sensitivity for life-threatening conditions.
- **Emergency Precision:** $\frac{\text{TP}_{\text{Emergency}}}{\text{TP}_{\text{Emergency}} + \text{FP}_{\text{Emergency}}}$. Measures how reliably emergency escalations reflect true acute risk.
- **Missed Emergencies:** Complete forensic listing of any false negatives.
- **Under-Triage Rate:** Share of cases where assigned severity was lower than ground-truth clinical acuity.
- **Over-Triage Rate:** Share of cases where assigned severity was higher than ground-truth clinical acuity.
- **Severity 4x4 Confusion Matrix:** Breakdown across `EMERGENCY`, `HIGH`, `MODERATE`, and `LOW`.
- **Safety Floor Activations:** Count of cases where the autonomous Safety Floor Agent escalated severity to HIGH upon detecting critical specialist diagnoses (e.g. ACS, aortic dissection).

### Specialist Routing Metrics
- **Specialty Top-1 Accuracy:** Proportion of cases correctly assigned to the canonical specialist agent (Cardiology, Pulmonology, Neurology, Gastroenterology, Dermatology, General Medicine, or Emergency Medicine).
- **Per-Specialty Precision, Recall, and F1-Score.**

### Intake Extraction Metrics
- **Symptom Extraction Macro F1:** Overlap between expected symptoms and extracted snake_case symptom entities.
- **Age Exact-Match Rate:** Accuracy of natural language age parser.
- **Duration Tolerance Match Rate:** Extracted duration within $\pm 20\%$ tolerance.
- **Silent Default Rates:** Frequency of fallback defaults (`["fever"]` or age `40`).

### Robustness & Operational Metrics
- **Determinism Rate:** Percentage of test cases returning 100% identical severity scores across $N$ repeats.
- **Fallback Rate:** Proportion of cases executing on deterministic templates versus Gemini generation.
- **Latency Percentiles:** Mean, P50, and P95 execution times per case in milliseconds.
- **Citation Presence Rate:** Percentage of non-emergency cases successfully embedding peer-reviewed PubMed citations.

---

## 5. Benchmark Dataset Structure (`evaluation/dataset/cases.json`)

The benchmark includes 50 curated clinical vignettes covering:
1. **10 Single Red Flags:** Severe bleeding, stridor, hemoptysis, seizures, slurred speech, facial drooping, unilateral weakness, sudden numbness, suicidal ideation, syncope.
2. **7 Red Flag Combinations:** Chest pain + shortness of breath, chest pain + difficulty breathing, severe headache + vision loss, anaphylaxis, meningitis signs, cardiogenic shock.
3. **Acute Chest Pain Presentations:** Age $\ge 50$ or duration $< 2$ days.
4. **All 6 Canonical Specialists:** $\ge 4$ non-emergency vignettes per specialty.
5. **Age Extremes & Sub-Day Durations:** Infant (1 y/o), geriatric ($>65$ y/o), and hour/minute durations ("2 hours", "30 minutes", "this morning").
6. **Adversarial / Ambiguous Cases:** Negations ("I do not have chest pain"), family history distractors, typos, and multi-symptom presentations.

---

## 6. Output Artifacts (`evaluation/results/`)

Each evaluation run outputs:
- `summary.json`: Machine-readable summary of all metrics.
- `per_case.csv`: Case-by-case outputs and predictions for spreadsheet analysis.
- `report.md`: Markdown clinical evaluation report with tables and error analysis.
- `confusion_matrix.png`: Graphical confusion matrix (generated if `matplotlib` is installed).
