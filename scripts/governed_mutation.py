#!/usr/bin/env python3
"""
Governed Mutation Script

Validates any mutation against GCAT/BCAT admissibility.
Generates deterministic receipt IDs.

Usage:
    python3 governed_mutation.py <mutation_name>

    Examples:
        python3 governed_mutation.py deploy
"""

import json
import sys
import os

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from receipt_id import generate_receipt_id
from admissibility import classify_action


def main():
    # Accept mutation from command line
    mutation = sys.argv[1] if len(sys.argv) > 1 else "deploy"

    # Map mutation to action for admissibility check
    # deploy -> deploy_change is the known mapping
    action_map = {
        "deploy": "deploy_change",
    }
    mapped_action = action_map.get(mutation, mutation)

    # Use centralized classifier
    result = classify_action(mapped_action)
    admissibility = result.as_dict()

    expected_decision = admissibility["expected_decision"]

    if expected_decision == "FAIL_CLOSED":
        decision = "FAIL_CLOSED"
        reason = admissibility["reason"]
        status_line = f"Mutation fail_closed: {mutation}"
    elif expected_decision == "DENY":
        decision = "DENY"
        reason = admissibility["reason"]
        status_line = f"Mutation denied: {mutation}"
    else:
        decision = "ALLOW"
        reason = admissibility["reason"]
        status_line = f"Mutation allowed: {mutation}"

    # Generate deterministic receipt ID using the MUTATION name
    receipt_id = generate_receipt_id(
        action=mutation,
        previous_id="GENESIS",
        decision=decision,
        state_snapshot="state0"
    )

    print(status_line)
    print(f"receipt_id: {receipt_id}")
    print(f"decision: {decision}")
    print(f"mapped_action: {mapped_action}")
    print(f"reason: {reason}")
    print("admissibility:")
    print(json.dumps(admissibility, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
