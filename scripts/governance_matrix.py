#!/usr/bin/env python3
"""Test 5: deterministic governance matrix with GCAT/BCAT interpretation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from admissibility import classify_action, observed_decision_from_output


SUT_DIR = Path(".")
STEGVERSE = SUT_DIR / "stegverse"


def run_action(action: str) -> dict:
    result = subprocess.run(
        [str(STEGVERSE), "action", action],
        capture_output=True,
        text=True,
        cwd=SUT_DIR,
    )
    admissibility = classify_action(action)
    actual = observed_decision_from_output(result.stdout)

    return {
        "action": action,
        "expected": admissibility.expected_decision,
        "actual": actual,
        "pass": actual == admissibility.expected_decision,
        "returncode": result.returncode,
        "admissibility": admissibility.as_dict(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    # Advance to a state where the allow path is possible in the demo SUT.
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True, text=True)

    cases = ["deploy_change", "unauthorized_change", "malformed_request"]

    results = []
    for action in cases:
        result = run_action(action)
        results.append(result)
        status = "PASS" if result["pass"] else "FAIL"
        print(
            f"{action}: expected {result['expected']}, "
            f"got {result['actual']} — {status}"
        )
        print(
            "  admissibility="
            f"{result['admissibility']['admissibility']} "
            f"I={result['admissibility']['invariant']} "
            f"basis={result['admissibility']['basis']}"
        )

    passed = sum(1 for result in results if result["pass"])
    summary = {
        "test": "governance_matrix",
        "formalism": "GCAT/BCAT minimal admissibility binding",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_pass": passed == len(results),
        "cases": results,
    }

    with open("matrix_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nGovernance Matrix: {passed}/{len(results)} passed")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
