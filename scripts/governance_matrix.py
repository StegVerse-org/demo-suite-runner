#!/usr/bin/env python3
"""Test 5: deterministic governance matrix with GCAT/BCAT enforcement."""

from __future__ import annotations

import json
import subprocess
import sys

from admissibility import classify_action, observed_decision_from_output


CASES = ["deploy_change", "unauthorized_change", "malformed_request"]


def run_case(action: str) -> dict:
    formal = classify_action(action)

    result = subprocess.run(
        ["python3", "../../scripts/governed_action.py", action],
        capture_output=True,
        text=True,
    )

    actual = observed_decision_from_output(result.stdout)
    alignment = actual == formal.expected_decision

    return {
        "action": action,
        "actual": actual,
        "formal_expected": formal.expected_decision,
        "alignment": alignment,
        "returncode": result.returncode,
        "admissibility": formal.as_dict(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    results = [run_case(action) for action in CASES]
    aligned = sum(1 for item in results if item["alignment"])
    total = len(results)

    summary = {
        "test": "governance_matrix",
        "mode": "enforced",
        "alignment_pass_rate": aligned / total if total else 0.0,
        "all_aligned": aligned == total,
        "cases": results,
    }

    with open("matrix_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Governance Matrix complete. GCAT/BCAT enforced at action boundary.")
    for item in results:
        status = "PASS" if item["alignment"] else "FAIL"
        print(
            f"{item['action']}: expected {item['formal_expected']}, "
            f"got {item['actual']} — {status}"
        )

    return 0 if summary["all_aligned"] else 1


if __name__ == "__main__":
    sys.exit(main())
