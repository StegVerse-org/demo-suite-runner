#!/usr/bin/env python3
import json, random, subprocess
from admissibility import classify_action, observed_decision_from_output

ACTIONS = ["deploy_change","unauthorized_change","malformed_request"]

def run():
    results = []
    for i in range(30):
        action = random.choice(ACTIONS)
        r = subprocess.run(["./stegverse", "action", action], capture_output=True, text=True)
        actual = observed_decision_from_output(r.stdout)
        formal = classify_action(action)

        results.append({
            "action": action,
            "actual": actual,
            "formal_expected": formal.expected_decision,
            "alignment": actual == formal.expected_decision
        })

    summary = {
        "test": "random_sweep",
        "alignment_rate": sum(1 for r in results if r["alignment"]) / len(results),
        "results": results
    }

    with open("sweep_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("Sweep complete. Alignment measured.")

if __name__ == "__main__":
    run()
