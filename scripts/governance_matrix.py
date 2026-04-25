#!/usr/bin/env python3
import json, subprocess
from admissibility import classify_action, observed_decision_from_output

CASES = ["deploy_change", "unauthorized_change", "malformed_request"]

def run():
    results = []
    for action in CASES:
        r = subprocess.run(["./stegverse", "action", action], capture_output=True, text=True)
        actual = observed_decision_from_output(r.stdout)
        formal = classify_action(action)

        results.append({
            "action": action,
            "actual": actual,
            "formal_expected": formal.expected_decision,
            "alignment": actual == formal.expected_decision,
            "admissibility": formal.as_dict()
        })

    summary = {
        "test": "governance_matrix",
        "alignment_pass_rate": sum(1 for r in results if r["alignment"]) / len(results),
        "cases": results
    }

    with open("matrix_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("Matrix complete. Alignment recorded (no hard fail).")

if __name__ == "__main__":
    run()
