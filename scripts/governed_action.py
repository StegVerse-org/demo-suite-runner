#!/usr/bin/env python3
"""
Governed Action Script

Validates any action against GCAT/BCAT admissibility.
Generates deterministic receipt IDs.

Usage:
    python3 governed_action.py <action_name>

    Examples:
        python3 governed_action.py deploy_change
        python3 governed_action.py unauthorized_change
        python3 governed_action.py malformed_request
"""

import json
import sys
import os

# Add scripts directory to path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from receipt_id import generate_receipt_id
from admissibility import classify_action, observed_decision_from_output


def main():
    # Accept action from command line, default to deploy_change
    action = sys.argv[1] if len(sys.argv) > 1 else "deploy_change"

    # Use the centralized admissibility classifier
    result = classify_action(action)
    admissibility = result.as_dict()

    expected_decision = admissibility["expected_decision"]

    # Determine output format based on decision type
    if expected_decision == "FAIL_CLOSED":
        decision = "FAIL_CLOSED"
        reason = admissibility["reason"]
        status_line = f"Action fail_closed: {action}"
    elif expected_decision == "DENY":
        decision = "DENY"
        reason = admissibility["reason"]
        status_line = f"Action denied: {action}"
    else:  # ALLOW
        decision = "ALLOW"
        reason = admissibility["reason"]
        status_line = f"Action allowed: {action}"

    # Generate deterministic receipt ID using the ACTUAL action name
    receipt_id = generate_receipt_id(
        action=action,
        previous_id="GENESIS",  # Action receipts start fresh
        decision=decision,
        state_snapshot="state0"  # Matrix tests run from base state
    )

    # Output format (must match observed_decision_from_output expectations)
    print(status_line)
    print(f"receipt_id: {receipt_id}")
    print(f"decision: {decision}")
    print(f"reason: {reason}")
    print("admissibility:")
    print(json.dumps(admissibility, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
