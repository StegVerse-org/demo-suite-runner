#!/usr/bin/env python3
"""Test 6: seeded random governance sweep with GCAT/BCAT interpretation."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path

from admissibility import classify_action, observed_decision_from_output


SUT_DIR = Path(".")
STEGVERSE = SUT_DIR / "stegverse"

SEED = int(os.environ.get("SV_SEED", "42"))
SAMPLES = int(os.environ.get("SV_SAMPLES", "50"))

random.seed(SEED)

ALLOW_POOL = ["deploy_change", "release_secret", "write_config"]
DENY_POOL = ["unauthorized_change", "invalid_access", "forbidden_deploy"]
FAIL_CLOSED_POOL = ["malformed_request", "", "!!!", "nonexistent_action_12345"]


def pick_action(target: str) -> str:
    if target == "ALLOW":
        return random.choice(ALLOW_POOL)
    if target == "DENY":
        return random.choice(DENY_POOL)
    return random.choice(FAIL_CLOSED_POOL)


def run_action(action: str, sample: int, target: str) -> dict:
    result = subprocess.run(
        [str(STEGVERSE), "action", action],
        capture_output=True,
        text=True,
        cwd=SUT_DIR,
    )
    admissibility = classify_action(action)
    actual = observed_decision_from_output(result.stdout)

    return {
        "sample": sample,
        "target": target,
        "action": action,
        "expected": admissibility.expected_decision,
        "actual": actual,
        "match": actual == admissibility.expected_decision,
        "target_match": target == actual,
        "returncode": result.returncode,
        "admissibility": admissibility.as_dict(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_phase(name: str, weights: list[float], samples: int) -> list[dict]:
    targets = random.choices(["ALLOW", "DENY", "FAIL_CLOSED"], weights=weights, k=samples)
    results = []

    for index, target in enumerate(targets):
        action = pick_action(target)
        results.append(run_action(action, sample=index, target=target))

    return results


def summarize_phase(results: list[dict], weights: list[float]) -> dict:
    return {
        "weights": weights,
        "distribution": {
            "ALLOW": sum(1 for r in results if r["actual"] == "ALLOW"),
            "DENY": sum(1 for r in results if r["actual"] == "DENY"),
            "FAIL_CLOSED": sum(1 for r in results if r["actual"] == "FAIL_CLOSED"),
        },
        "matches": sum(1 for r in results if r["match"]),
        "target_matches": sum(1 for r in results if r["target_match"]),
    }


def main() -> int:
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True, text=True)

    phase1_weights = [0.50, 0.40, 0.10]
    phase1 = run_phase("Phase 1 (ALLOW/DENY weighted)", phase1_weights, SAMPLES)

    subprocess.run([str(STEGVERSE), "reset"], cwd=SUT_DIR, capture_output=True, text=True)
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True, text=True)

    phase2_weights = [0.10, 0.15, 0.75]
    phase2 = run_phase("Phase 2 (FAIL_CLOSED weighted)", phase2_weights, SAMPLES)

    all_results = phase1 + phase2
    total = len(all_results)
    matches = sum(1 for r in all_results if r["match"])

    summary = {
        "test": "governance_random_sweep",
        "formalism": "GCAT/BCAT minimal admissibility binding",
        "seed": SEED,
        "samples_per_phase": SAMPLES,
        "total_samples": total,
        "correct_classifications": matches,
        "accuracy": round(matches / total, 4) if total else 0.0,
        "phase1": summarize_phase(phase1, phase1_weights),
        "phase2": summarize_phase(phase2, phase2_weights),
        "details": all_results,
    }

    with open("sweep_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nRandom Sweep: {matches}/{total} correct ({summary['accuracy']:.1%})")
    print(f"  Phase 1: {summary['phase1']['matches']}/{SAMPLES} admissibility matches")
    print(f"  Phase 2: {summary['phase2']['matches']}/{SAMPLES} admissibility matches")

    return 0 if matches == total else 1


if __name__ == "__main__":
    sys.exit(main())
