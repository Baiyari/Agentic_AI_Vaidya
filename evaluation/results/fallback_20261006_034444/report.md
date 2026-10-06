# Vaidya Multi-Agent Health-Triage Evaluation Report

**Generated At:** 2026-10-06T03:44:44.260497+00:00 (UTC)
**Total Benchmark Cases:** 50 | **Mode:** `fallback` | **Repeats:** 3

## 1. Executive Summary & Safety Dashboard
| Safety Metric | Result | Target / Standard |
| :--- | :--- | :--- |
| **Emergency Recall (Sensitivity)** | **`94.4%`** | 100.0% (Zero missed emergencies) |
| **Emergency Precision** | `94.4%` | >= 85.0% |
| **Missed Emergency Count** | `1` | 0 |
| **Severity Exact-Match Accuracy** | `78.0%` | >= 80.0% |
| **Under-Triage Rate** | `16.0%` | <= 5.0% |
| **Over-Triage Rate** | `6.0%` | <= 20.0% |
| **Safety Floor Activations** | `1` | N/A (Rule enforcement) |

### ⚠️ CRITICAL SAFETY ALERT: Missed Emergencies
- **Case `case_018`** (`red_flag`): Expected `EMERGENCY` but got `LOW`.
  *Text:* "I am 68 years old and have had pressure in my chest for 3 days."
### Severity 4x4 Confusion Matrix
| Expected \ Predicted | EMERGENCY | HIGH | MODERATE | LOW |
| :--- | :---: | :---: | :---: | :---: |
| **EMERGENCY** | 17 | 0 | 0 | 1 |
| **HIGH** | 0 | 1 | 3 | 0 |
| **MODERATE** | 0 | 0 | 3 | 4 |
| **LOW** | 1 | 2 | 0 | 18 |

## 2. Routing & Entity Extraction Performance
| Subsystem Metric | Score |
| :--- | :--- |
| **Specialty Top-1 Routing Accuracy** | `90.0%` |
| **Symptom Extraction Macro F1** | `89.9%` |
| **Age Exact-Match Rate** | `100.0%` |
| **Duration (±20% Tolerance) Match** | `96.0%` |
| **Silent Default Symptom Rate** | `4.0%` |

## 3. Robustness & Operational Latency
| Metric | Value |
| :--- | :--- |
| **Determinism Rate (N-repeats)** | `100.0%` |
| **Fallback Execution Rate** | `100.0%` |
| **Mean Latency per Case** | `8.91 ms` |
| **P50 Latency / P95 Latency** | `7.92 ms / 14.01 ms` |
| **Evidence Citation Rate (Non-Emergency)** | `100.0%` |

## 4. Performance Breakdown by Vignette Category
| Category | Cases | Severity Accuracy | Top-1 Routing Accuracy |
| :--- | :---: | :---: | :---: |
| **`ambiguous`** | 2 | `50.0%` | `50.0%` |
| **`edge_case`** | 3 | `33.3%` | `100.0%` |
| **`multi_symptom`** | 3 | `66.7%` | `66.7%` |
| **`negation`** | 1 | `0.0%` | `0.0%` |
| **`red_flag`** | 18 | `94.4%` | `94.4%` |
| **`routine`** | 22 | `77.3%` | `95.5%` |
| **`typo`** | 1 | `100.0%` | `100.0%` |

## 5. Detailed Case Discrepancies (13 cases)
### Case `case_018` [red_flag]
- **Patient Prose:** "I am 68 years old and have had pressure in my chest for 3 days."
- **Expected:** Severity=`EMERGENCY`, Specialty=`Emergency Medicine`, Symptoms=`['chest_pain']`
- **Actual:** Severity=`LOW`, Specialty=`General Medicine`, Symptoms=`['fever']`
- **Triage Reason:** Low risk score (7). Routine care recommended.
### Case `case_021` [routine]
- **Patient Prose:** "I am 29 years old and have occasional heart palpitations after drinking coffee for 2 weeks."
- **Expected:** Severity=`MODERATE`, Specialty=`Cardiology`, Symptoms=`['palpitations']`
- **Actual:** Severity=`LOW`, Specialty=`Cardiology`, Symptoms=`['palpitations']`
- **Triage Reason:** Low risk score (3). Routine care recommended.
### Case `case_029` [routine]
- **Patient Prose:** "I am 46 years old and have felt dizziness and lightheadedness for 3 days."
- **Expected:** Severity=`LOW`, Specialty=`Neurology`, Symptoms=`['dizziness']`
- **Actual:** Severity=`HIGH`, Specialty=`Neurology`, Symptoms=`['dizziness']`
- **Triage Reason:** Safety Floor Enforcement: Escalated to HIGH due to specialist identification of STROKE. (Low risk score (2). Routine care recommended.)
### Case `case_030` [routine]
- **Patient Prose:** "I am 63 years old and have had a mild tremor in my hands for 2 weeks."
- **Expected:** Severity=`MODERATE`, Specialty=`Neurology`, Symptoms=`['tremor']`
- **Actual:** Severity=`LOW`, Specialty=`Neurology`, Symptoms=`['tremor']`
- **Triage Reason:** Low risk score (5). Routine care recommended.
### Case `case_031` [multi_symptom]
- **Patient Prose:** "I am 39 years old and have had vertigo and mild nausea for 3 days."
- **Expected:** Severity=`LOW`, Specialty=`Neurology`, Symptoms=`['vertigo', 'nausea']`
- **Actual:** Severity=`LOW`, Specialty=`Gastroenterology`, Symptoms=`['nausea', 'vertigo']`
- **Triage Reason:** Low risk score (4). Routine care recommended.
### Case `case_032` [routine]
- **Patient Prose:** "I am 27 years old and have felt mild nausea for 1 day after eating."
- **Expected:** Severity=`LOW`, Specialty=`Gastroenterologist`, Symptoms=`['nausea']`
- **Actual:** Severity=`LOW`, Specialty=`Gastroenterology`, Symptoms=`['nausea']`
- **Triage Reason:** Low risk score (2). Routine care recommended.
### Case `case_039` [routine]
- **Patient Prose:** "I am 40 years old and have an itchy eczema patch on my elbow for 3 weeks."
- **Expected:** Severity=`MODERATE`, Specialty=`Dermatology`, Symptoms=`['eczema', 'itching']`
- **Actual:** Severity=`LOW`, Specialty=`Dermatology`, Symptoms=`['itching', 'eczema']`
- **Triage Reason:** Low risk score (7). Routine care recommended.
### Case `case_042` [edge_case]
- **Patient Prose:** "I am 72 years old and have been experiencing general fatigue and tiredness for 3 weeks."
- **Expected:** Severity=`HIGH`, Specialty=`General Medicine`, Symptoms=`['fatigue']`
- **Actual:** Severity=`MODERATE`, Specialty=`General Medicine`, Symptoms=`['fatigue']`
- **Triage Reason:** Moderate risk score (10).
### Case `case_044` [edge_case]
- **Patient Prose:** "I am 66 years old and have had dull knee pain and joint pain for 1 month."
- **Expected:** Severity=`HIGH`, Specialty=`General Medicine`, Symptoms=`['knee_pain', 'joint_pain']`
- **Actual:** Severity=`MODERATE`, Specialty=`General Medicine`, Symptoms=`['joint_pain', 'knee_pain']`
- **Triage Reason:** Moderate risk score (12).
### Case `case_045` [routine]
- **Patient Prose:** "I am 47 years old and have joint pain and morning stiffness in both hands for 3 weeks."
- **Expected:** Severity=`MODERATE`, Specialty=`General Medicine`, Symptoms=`['joint_pain', 'morning_stiffness']`
- **Actual:** Severity=`LOW`, Specialty=`General Medicine`, Symptoms=`['joint_pain', 'morning_stiffness']`
- **Triage Reason:** Low risk score (7). Routine care recommended.
### Case `case_046` [negation]
- **Patient Prose:** "I do not have any chest pain or breathing issues, but I have had a mild runny cough for 3 days."
- **Expected:** Severity=`LOW`, Specialty=`General Medicine`, Symptoms=`['cough']`
- **Actual:** Severity=`HIGH`, Specialty=`Cardiology`, Symptoms=`['chest_pain', 'cough']`
- **Triage Reason:** High risk score (19) based on presenting symptoms, clinical risk factors, and duration.
### Case `case_047` [ambiguous]
- **Patient Prose:** "My mother had a severe stroke last week, but I am 30 years old and just have a mild headache since yesterday."
- **Expected:** Severity=`LOW`, Specialty=`Neurology`, Symptoms=`['headache']`
- **Actual:** Severity=`EMERGENCY`, Specialty=`Emergency Medicine`, Symptoms=`['headache', 'slurred_speech']`
- **Triage Reason:** Acute stroke / focal neurological deficit: Slurred speech requires immediate stroke code activation.
### Case `case_050` [multi_symptom]
- **Patient Prose:** "I am 21 years old and have multiple symptoms: headache, nausea, joint pain, fatigue, and slight cough for 4 days."
- **Expected:** Severity=`HIGH`, Specialty=`General Medicine`, Symptoms=`['headache', 'nausea', 'joint_pain', 'fatigue', 'cough']`
- **Actual:** Severity=`MODERATE`, Specialty=`General Medicine`, Symptoms=`['joint_pain', 'headache', 'fatigue', 'nausea', 'cough']`
- **Triage Reason:** Moderate risk score (10).

## 6. Clinical & System Findings
1. **Deterministic Rule Safety:** The rule-based MCP and deterministic safety triage layers enforce a solid safety floor.
2. **Sub-Day Durations:** Duration parsing accurately captures acute presentations ('two hours', '30 minutes') without quantizing to 0 days.
3. **Negation & Conversational Disclaimers:** Rule-based synonym matching on natural language prose can trigger keyword matches on negated sentences (e.g. 'I do not have chest pain').