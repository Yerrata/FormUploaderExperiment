"""Pure scoring logic for the throwaway document-extraction benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import median
from typing import Any, Iterable


ID_FIELDS = {"passport_number", "visa_number", "oci_number"}


@dataclass(frozen=True)
class CandidateMetrics:
    name: str
    total_cases: int
    accepted_correct: int
    accepted_wrong: int
    correction_requests: int
    blocked: int
    wrong_case_ids: tuple[str, ...]
    straight_through_rate: float
    correction_rate: float
    blocked_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_cost_inr: float
    cost_per_verified_filing_inr: float
    release_gate_passed: bool


def normalize(field: str, value: Any) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().upper().split())
    if field in ID_FIELDS:
        return text.replace(" ", "").replace("-", "")
    return text


def percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, ceil(proportion * len(ordered)) - 1)
    return ordered[index]


def score_candidate(
    name: str,
    truths: Iterable[dict[str, Any]],
    predictions: Iterable[dict[str, Any]],
    minimum_straight_through_rate: float = 0.90,
) -> CandidateMetrics:
    truth_rows = list(truths)
    predictions_by_id = {row["case_id"]: row for row in predictions}
    accepted_correct = 0
    accepted_wrong = 0
    correction_requests = 0
    blocked = 0
    wrong_case_ids: list[str] = []
    latencies: list[float] = []
    costs: list[float] = []

    for truth in truth_rows:
        prediction = predictions_by_id.get(truth["case_id"])
        if prediction is None:
            blocked += 1
            continue

        latencies.append(float(prediction.get("latency_ms", 0.0)))
        costs.append(float(prediction.get("cost_inr", 0.0)))
        decision = prediction.get("decision", "block")

        if decision == "correct":
            correction_requests += 1
            continue
        if decision != "accept":
            blocked += 1
            continue

        expected = truth.get("critical_fields", {})
        actual = prediction.get("critical_fields", {})
        wrong_fields = [
            field
            for field, expected_value in expected.items()
            if normalize(field, actual.get(field)) != normalize(field, expected_value)
        ]
        mrz_failed = truth.get("mrz_expected", False) and prediction.get("mrz_valid") is not True

        if wrong_fields or mrz_failed:
            accepted_wrong += 1
            wrong_case_ids.append(truth["case_id"])
        else:
            accepted_correct += 1

    total_cases = len(truth_rows)
    denominator = total_cases or 1
    straight_through_rate = accepted_correct / denominator
    total_cost = sum(costs)
    verified_denominator = accepted_correct or 1
    release_gate_passed = accepted_wrong == 0 and straight_through_rate >= minimum_straight_through_rate

    return CandidateMetrics(
        name=name,
        total_cases=total_cases,
        accepted_correct=accepted_correct,
        accepted_wrong=accepted_wrong,
        correction_requests=correction_requests,
        blocked=blocked,
        wrong_case_ids=tuple(wrong_case_ids),
        straight_through_rate=straight_through_rate,
        correction_rate=correction_requests / denominator,
        blocked_rate=blocked / denominator,
        p50_latency_ms=median(latencies) if latencies else 0.0,
        p95_latency_ms=percentile(latencies, 0.95),
        total_cost_inr=total_cost,
        cost_per_verified_filing_inr=total_cost / verified_denominator,
        release_gate_passed=release_gate_passed,
    )
