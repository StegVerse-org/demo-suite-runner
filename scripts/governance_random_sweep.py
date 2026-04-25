#!/usr/bin/env python3
"""Test 6: seeded random governance sweep with GCAT/BCAT enforcement."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys

from admissibility import classify_action, observed_decision_from_output


SEED = int(os.environ.get("SV_SEED", "42"))
SAMPLES = int(os.environ.get("SV_SAMPLES", "50"))

random.seed(SEED)

ALLOW_POOL = ["deploy_change"]
DENY_POOL = ["unauthorized_change", "invalid_access", "forbidden_deploy"]
FAIL_CLOSED_POOL = ["malformed_request", "", "!!!", "nonexistent_action_12345"]


def pick_action(target: str) -> str:
    if target == "DENY":
        return random.choice(DENY_POOL)
    if target == "FAIL_CLOSED":
        return random.choice(FAIL_CLOSED_POOL)
    return random.choice(ALLOW_POOL)


def run_action(action: str, sample: int, target: str) -> dict:
    formal = classify_action(action)
    result = subprocess.run(
        ["python3", "../../scripts/governed_action.py", action],
        capture_output=True,
        text=True,
    )
    actual = observed_decision_from_output(result.stdout)

    return {
        "sample": sample,
        "target": target,
        "action": action,
        "actual": actual,
        "formal_expected": formal.expected_decision,
        "alignment": actual == formal.expected_decision,
        "returncode": result.returncode,
    }


def run_phase(name: str, weights: list[float], samples: int) -> list[dict]:
    targets = random.choices(["ALLOW", "DENY", "FAIL_CLOSED"], weights=weights, k=samples)
    return [run_action(pick_action(target), i, target) for i, target in enumerate(targets)]


def summarize(results: list[dict], weights: list[float]) -> dict:
    return {
        "weights": weights,
        "distribution": {
            "ALLOW": sum(1 for item in results if item["actual"] == "ALLOW"),
            "DENY": sum(1 for item in results if item["actual"] == "DENY"),
            "FAIL_CLOSED": sum(1 for item in results if item["actual"] == "FAIL_CLOSED"),
        },
        "matches": sum(1 for item in results if item["alignment"]),
        "total": len(results),
    }


def main() -> int:
    phase1_weights = [0.50, 0.40, 0.10]
    phase2_weights = [0.10, 0.15, 0.75]

    phase1 = run_phase("Phase 1", phase1_weights, SAMPLES)
    phase2 = run_phase("Phase 2", phase2_weights, SAMPLES)

    all_results = phase1 + phase2
    aligned = sum(1 for item in all_results if item["alignment"])
    total = len(all_results)

    summary = {
        "test": "governance_random_sweep",
        "mode": "enforced",
        "seed": SEED,
        "samples_per_phase": SAMPLES,
        "total_samples": total,
        "correct_classifications": aligned,
        "alignment_rate": aligned / total if total else 0.0,
        "accuracy": aligned / total if total else 0.0,
        "phase1": summarize(phase1, phase1_weights),
        "phase2": summarize(phase2, phase2_weights),
        "results": all_results,
    }

    with open("sweep_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Random Sweep complete. GCAT/BCAT enforced at action boundary.")
    print(f"Alignment: {aligned}/{total}")

    return 0 if aligned == total else 1


if __name__ == "__main__":
    sys.exit(main())
