"""
Pure metric calculation functions for Vaidya multi-agent clinical evaluation.
All functions are unit-testable and perform no I/O or network requests.
"""

from typing import List, Dict, Any, Tuple
import math

SEVERITY_LEVELS = ["EMERGENCY", "HIGH", "MODERATE", "LOW"]
SEVERITY_ORDER = {
    "LOW": 1,
    "MODERATE": 2,
    "HIGH": 3,
    "EMERGENCY": 4
}


def calculate_safety_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes critical clinical safety metrics including emergency sensitivity,
    under-triage / over-triage rates, and 4x4 confusion matrix.
    """
    if not results:
        return {}

    total = len(results)
    exact_match = 0
    under_triage_count = 0
    over_triage_count = 0
    missed_emergencies = []

    # Confusion matrix 4x4
    matrix: Dict[str, Dict[str, int]] = {
        exp: {pred: 0 for pred in SEVERITY_LEVELS}
        for exp in SEVERITY_LEVELS
    }

    tp_emg = 0
    fp_emg = 0
    fn_emg = 0
    tn_emg = 0
    safety_floor_count = 0

    for r in results:
        exp = r.get("expected_severity", "LOW").upper()
        pred = r.get("predicted_severity", "LOW").upper()

        if exp in matrix and pred in matrix[exp]:
            matrix[exp][pred] += 1

        exp_rank = SEVERITY_ORDER.get(exp, 1)
        pred_rank = SEVERITY_ORDER.get(pred, 1)

        if exp == pred:
            exact_match += 1
        elif pred_rank < exp_rank:
            under_triage_count += 1
        else:
            over_triage_count += 1

        # Emergency metrics
        if exp == "EMERGENCY" and pred == "EMERGENCY":
            tp_emg += 1
        elif exp == "EMERGENCY" and pred != "EMERGENCY":
            fn_emg += 1
            missed_emergencies.append({
                "id": r.get("id"),
                "text": r.get("text"),
                "expected": exp,
                "predicted": pred,
                "category": r.get("category"),
                "reason": r.get("predicted_reason")
            })
        elif exp != "EMERGENCY" and pred == "EMERGENCY":
            fp_emg += 1
        else:
            tn_emg += 1

        if r.get("safety_floor_activated"):
            safety_floor_count += 1

    emg_recall = tp_emg / (tp_emg + fn_emg) if (tp_emg + fn_emg) > 0 else 1.0
    emg_precision = tp_emg / (tp_emg + fp_emg) if (tp_emg + fp_emg) > 0 else 1.0
    emg_f1 = (
        2 * (emg_precision * emg_recall) / (emg_precision + emg_recall)
        if (emg_precision + emg_recall) > 0 else 0.0
    )

    return {
        "exact_match_accuracy": round(exact_match / total, 4),
        "emergency_recall": round(emg_recall, 4),
        "emergency_precision": round(emg_precision, 4),
        "emergency_f1": round(emg_f1, 4),
        "emergency_tp": tp_emg,
        "emergency_fn": fn_emg,
        "emergency_fp": fp_emg,
        "emergency_tn": tn_emg,
        "missed_emergencies": missed_emergencies,
        "under_triage_count": under_triage_count,
        "under_triage_rate": round(under_triage_count / total, 4),
        "over_triage_count": over_triage_count,
        "over_triage_rate": round(over_triage_count / total, 4),
        "safety_floor_activations": safety_floor_count,
        "confusion_matrix": matrix
    }


def calculate_routing_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes specialty routing accuracy and per-specialty precision / recall.
    """
    if not results:
        return {}

    total = len(results)
    matches = 0
    per_specialty: Dict[str, Dict[str, int]] = {}

    for r in results:
        exp = r.get("expected_specialty", "General Medicine").strip()
        pred = r.get("predicted_specialty", "General Medicine").strip()

        # Normalize casing / terminology
        if exp.lower() == pred.lower():
            matches += 1

        if exp not in per_specialty:
            per_specialty[exp] = {"tp": 0, "fn": 0, "fp": 0}
        if pred not in per_specialty:
            per_specialty[pred] = {"tp": 0, "fn": 0, "fp": 0}

        if exp.lower() == pred.lower():
            per_specialty[exp]["tp"] += 1
        else:
            per_specialty[exp]["fn"] += 1
            per_specialty[pred]["fp"] += 1

    breakdown = {}
    for spec, counts in per_specialty.items():
        tp = counts["tp"]
        fn = counts["fn"]
        fp = counts["fp"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        breakdown[spec] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn
        }

    return {
        "specialty_top1_accuracy": round(matches / total, 4),
        "per_specialty": breakdown
    }


def calculate_intake_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates intake entity extraction: symptoms set F1, age exact match,
    duration within ±20% tolerance, and silent default detection.
    """
    if not results:
        return {}

    total = len(results)
    age_matches = 0
    duration_matches = 0
    silent_symptom_defaults = 0
    silent_age_defaults = 0

    precisions = []
    recalls = []
    f1s = []

    for r in results:
        exp_s = set(r.get("expected_symptoms", []))
        pred_s = set(r.get("predicted_symptoms", []))

        # Precision & Recall
        if not exp_s and not pred_s:
            p, rec, f = 1.0, 1.0, 1.0
        elif not pred_s:
            p, rec, f = 0.0, 0.0, 0.0
        else:
            intersection = exp_s.intersection(pred_s)
            p = len(intersection) / len(pred_s) if pred_s else 0.0
            rec = len(intersection) / len(exp_s) if exp_s else 0.0
            f = 2 * p * rec / (p + rec) if (p + rec) > 0 else 0.0

        precisions.append(p)
        recalls.append(rec)
        f1s.append(f)

        # Age match
        if r.get("expected_age") == r.get("predicted_age"):
            age_matches += 1

        # Duration match (within ±20% tolerance, min 0.1 day window)
        exp_d = float(r.get("expected_duration_days", 1.0))
        pred_d = float(r.get("predicted_duration_days", 1.0))
        tolerance = max(0.20 * exp_d, 0.1)
        if abs(exp_d - pred_d) <= tolerance:
            duration_matches += 1

        # Silent defaults
        if r.get("predicted_symptoms") == ["fever"] and exp_s != {"fever"}:
            silent_symptom_defaults += 1
        if r.get("predicted_age") == 40 and r.get("expected_age") != 40:
            silent_age_defaults += 1

    return {
        "symptom_precision_macro": round(sum(precisions) / total, 4),
        "symptom_recall_macro": round(sum(recalls) / total, 4),
        "symptom_f1_macro": round(sum(f1s) / total, 4),
        "age_exact_match_rate": round(age_matches / total, 4),
        "duration_tolerance_match_rate": round(duration_matches / total, 4),
        "silent_symptom_default_rate": round(silent_symptom_defaults / total, 4),
        "silent_age_default_rate": round(silent_age_defaults / total, 4)
    }


def calculate_robustness_metrics(results: List[Dict[str, Any]], repeat_runs: List[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Computes fallback rates and determinism across multiple repetitions.
    """
    if not results:
        return {}

    total = len(results)
    fallback_count = sum(1 for r in results if r.get("is_fallback", True))

    determinism_score = 1.0
    if repeat_runs and len(repeat_runs) > 1:
        deterministic_cases = 0
        num_cases = len(results)
        for i in range(num_cases):
            severities = [run[i].get("predicted_severity") for run in repeat_runs]
            scores = [run[i].get("predicted_score") for run in repeat_runs]
            specialties = [run[i].get("predicted_specialty") for run in repeat_runs]

            if len(set(severities)) == 1 and len(set(scores)) == 1 and len(set(specialties)) == 1:
                deterministic_cases += 1
        determinism_score = round(deterministic_cases / num_cases, 4) if num_cases > 0 else 1.0

    return {
        "fallback_rate": round(fallback_count / total, 4),
        "determinism_rate": determinism_score
    }


def calculate_operational_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates operational latency and citation / trace densities.
    """
    if not results:
        return {}

    latencies = [float(r.get("latency_ms", 0)) for r in results]
    latencies.sort()
    n = len(latencies)

    mean_lat = sum(latencies) / n if n > 0 else 0
    p50_lat = latencies[int(n * 0.50)] if n > 0 else 0
    p95_lat = latencies[min(int(n * 0.95), n - 1)] if n > 0 else 0

    trace_counts = [r.get("trace_count", 0) for r in results]
    citation_counts = [r.get("citation_count", 0) for r in results]
    non_emg_citations = [
        r.get("citation_count", 0) for r in results
        if r.get("predicted_severity") != "EMERGENCY"
    ]

    has_citations = sum(1 for c in non_emg_citations if c > 0)
    citation_rate = round(has_citations / len(non_emg_citations), 4) if non_emg_citations else 1.0

    return {
        "latency_mean_ms": round(mean_lat, 2),
        "latency_p50_ms": round(p50_lat, 2),
        "latency_p95_ms": round(p95_lat, 2),
        "mean_trace_count": round(sum(trace_counts) / n, 2) if n > 0 else 0,
        "mean_citation_count": round(sum(citation_counts) / n, 2) if n > 0 else 0,
        "citation_presence_rate": citation_rate
    }
