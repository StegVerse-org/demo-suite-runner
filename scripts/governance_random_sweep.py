#!/usr/bin/env python3
"""
Test 6: Governance Random Sweep
Seeded bounded input sweep with weighted outcome phases.
Phase 1: weighted toward ALLOW + DENY
Phase 2: weighted toward FAIL_CLOSED
"""

import random
import subprocess
import json
import sys
import os
from pathlib import Path

SUT_DIR = Path(".")
STEGVERSE = SUT_DIR / "stegverse"

SEED = int(os.environ.get("SV_SEED", "42"))
SAMPLES = int(os.environ.get("SV_SAMPLES", "50"))

random.seed(SEED)

# Action pools derived from observed SUT behavior
ALLOW_POOL = ["deploy_change", "release_secret", "write_config"]
DENY_POOL = ["unauthorized_change", "invalid_access", "forbidden_deploy"]
FAIL_CLOSED_POOL = ["", "malformed\x00request", "!!!", "nonexistent_action_12345", "\n\t"]

def pick_action(target):
    if target == "ALLOW":
        return random.choice(ALLOW_POOL)
    elif target == "DENY":
        return random.choice(DENY_POOL)
    else:
        return random.choice(FAIL_CLOSED_POOL)

def run_action(action):
    result = subprocess.run(
        [str(STEGVERSE), "action", action],
        capture_output=True, text=True, cwd=SUT_DIR
    )
    stdout = result.stdout
    if "Action allowed" in stdout:
        actual = "ALLOW"
    elif "Action denied" in stdout:
        actual = "DENY"
    else:
        actual = "FAIL_CLOSED"
    return {
        "action": action,
        "actual": actual,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": result.stderr
    }

def run_phase(name, weights, samples):
    targets = random.choices(["ALLOW", "DENY", "FAIL_CLOSED"], weights=weights, k=samples)
    results = []
    for i, target in enumerate(targets):
        action = pick_action(target)
        result = run_action(action)
        result["sample"] = i
        result["target"] = target
        result["match"] = target == result["actual"]
        results.append(result)
    return results

def main():
    # Advance to state4 so ALLOW is possible
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True)

    # Phase 1: weighted toward ALLOW + DENY
    phase1 = run_phase("Phase 1 (ALLOW/DENY weighted)", [0.50, 0.40, 0.10], SAMPLES)

    # Reset and re-advance for Phase 2
    subprocess.run([str(STEGVERSE), "reset"], cwd=SUT_DIR, capture_output=True)
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True)

    # Phase 2: weighted toward FAIL_CLOSED
    phase2 = run_phase("Phase 2 (FAIL_CLOSED weighted)", [0.10, 0.15, 0.75], SAMPLES)

    all_results = phase1 + phase2
    total = len(all_results)
    matches = sum(1 for r in all_results if r["match"])

    summary = {
        "test": "governance_random_sweep",
        "seed": SEED,
        "samples_per_phase": SAMPLES,
        "total_samples": total,
        "correct_classifications": matches,
        "accuracy": round(matches / total, 4) if total else 0,
        "phase1": {
            "weights": [0.50, 0.40, 0.10],
            "distribution": {
                "ALLOW": sum(1 for r in phase1 if r["actual"] == "ALLOW"),
                "DENY": sum(1 for r in phase1 if r["actual"] == "DENY"),
                "FAIL_CLOSED": sum(1 for r in phase1 if r["actual"] == "FAIL_CLOSED"),
            },
            "matches": sum(1 for r in phase1 if r["match"])
        },
        "phase2": {
            "weights": [0.10, 0.15, 0.75],
            "distribution": {
                "ALLOW": sum(1 for r in phase2 if r["actual"] == "ALLOW"),
                "DENY": sum(1 for r in phase2 if r["actual"] == "DENY"),
                "FAIL_CLOSED": sum(1 for r in phase2 if r["actual"] == "FAIL_CLOSED"),
            },
            "matches": sum(1 for r in phase2 if r["match"])
        },
        "details": all_results
    }

    with open("sweep_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nRandom Sweep: {matches}/{total} correct ({summary['accuracy']:.1%})")
    print(f"  Phase 1 (50/40/10): {summary['phase1']['matches']}/{SAMPLES} correct")
    print(f"  Phase 2 (10/15/75): {summary['phase2']['matches']}/{SAMPLES} correct")

    sys.exit(0 if matches == total else 1)

if __name__ == "__main__":
    main()
