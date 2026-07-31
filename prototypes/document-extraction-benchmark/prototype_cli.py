"""Interactive shell for the throwaway document-extraction benchmark."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from scoring import CandidateMetrics, score_candidate


BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_candidate(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("candidate must use NAME=PATH")
    return name, Path(path)


def load_metrics(truth_path: Path, candidates: list[tuple[str, Path]]) -> list[CandidateMetrics]:
    truths = read_jsonl(truth_path)
    return [score_candidate(name, truths, read_jsonl(path)) for name, path in candidates]


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render(metrics: list[CandidateMetrics], selected: int) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    current = metrics[selected]
    print(f"{BOLD}PROTOTYPE — document extraction benchmark{RESET}")
    print(f"{DIM}Candidate {selected + 1} of {len(metrics)}{RESET}\n")
    print(f"{BOLD}candidate{RESET}:              {current.name}")
    print(f"{BOLD}release gate{RESET}:           {'PASS' if current.release_gate_passed else 'FAIL'}")
    print(f"{BOLD}cases{RESET}:                  {current.total_cases}")
    print(f"{BOLD}accepted correct{RESET}:       {current.accepted_correct}")
    print(f"{BOLD}accepted wrong{RESET}:         {current.accepted_wrong}")
    print(f"{BOLD}straight-through rate{RESET}:  {percent(current.straight_through_rate)}")
    print(f"{BOLD}correction rate{RESET}:        {percent(current.correction_rate)}")
    print(f"{BOLD}blocked rate{RESET}:           {percent(current.blocked_rate)}")
    print(f"{BOLD}p50 latency{RESET}:            {current.p50_latency_ms:.0f} ms")
    print(f"{BOLD}p95 latency{RESET}:            {current.p95_latency_ms:.0f} ms")
    print(f"{BOLD}total cost{RESET}:             ₹{current.total_cost_inr:.2f}")
    print(f"{BOLD}cost / verified filing{RESET}: ₹{current.cost_per_verified_filing_inr:.2f}")
    print(f"{BOLD}wrong case IDs{RESET}:          {', '.join(current.wrong_case_ids) or 'none'}")
    print(f"\n{BOLD}[n]{RESET} next candidate  {BOLD}[r]{RESET} reload files  {BOLD}[q]{RESET} quit")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--candidate", required=True, action="append", type=parse_candidate)
    args = parser.parse_args()
    selected = 0

    while True:
        metrics = load_metrics(args.truth, args.candidate)
        selected %= len(metrics)
        render(metrics, selected)
        if not sys.stdin.isatty():
            return
        command = input().strip().lower()
        if command == "q":
            return
        if command == "n":
            selected += 1


if __name__ == "__main__":
    main()

