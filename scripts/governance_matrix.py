#!/usr/bin/env python3
"""
Test 5: Governance Matrix (Deterministic)
Fixed cases: safe_deploy → ALLOW, unauthorized_change → DENY, malformed_request → FAIL_CLOSED
"""

import subprocess
import sys
import json
from pathlib import Path

SUT_DIR = Path(".")
STEGVERSE = SUT_DIR / "stegverse"

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

def main():
    # Advance to state4 so ALLOW is possible
    subprocess.run([str(STEGVERSE), "demo"], cwd=SUT_DIR, capture_output=True)

    cases = [
        {"action": "deploy_change",   "expected": "ALLOW"},
        {"action": "unauthorized_change", "expected": "DENY"},
        {"action": "malformed_request",   "expected": "FAIL_CLOSED"},
    ]

    results = []
    all_pass = True
    for case in cases:
        result = run_action(case["action"])
        result["expected"] = case["expected"]
        result["pass"] = result["actual"] == case["expected"]
        if not result["pass"]:
            all_pass = False
        results.append(result)
        print(f"  {case['action']}: expected {case['expected']}, got {result['actual']} — {'PASS' if result['pass'] else 'FAIL'}")

    summary = {
        "test": "governance_matrix",
        "total": len(cases),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
        "all_pass": all_pass,
        "cases": results
    }

    with open("matrix_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nGovernance Matrix: {summary['passed']}/{summary['total']} passed")
    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()
