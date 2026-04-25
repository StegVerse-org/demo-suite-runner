#!/usr/bin/env python3
"""
Governed Action Script

Validates deploy_change action against GCAT/BCAT admissibility.
Generates deterministic receipt IDs.
"""

import json
import sys
import os

# Add scripts directory to path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from receipt_id import generate_receipt_id


def main():
    action = "deploy_change"
    state = "state0"  # Or get from runtime

    # GCAT/BCAT admissibility check (your existing logic)
    admissibility = check_admissibility(action, state)

    if admissibility["expected_decision"] == "DENY":
        decision = "DENY"
        reason = "Projected transition violates admissibility."
    else:
        decision = "ALLOW"
        reason = "Admissible transition."

    # Generate deterministic receipt ID
    receipt_id = generate_receipt_id(
        action=action,
        previous_id="GENESIS",  # Action receipts start fresh
        decision=decision,
        state_snapshot=state
    )

    # Output format (must match existing expectations)
    print(f"Action denied: {action}")
    print(f"receipt_id: {receipt_id}")
    print(f"decision: {decision}")
    print(f"reason: {reason}")
    print("admissibility:")
    print(json.dumps(admissibility, indent=2))

    return 0


def check_admissibility(action, state):
    """Your existing GCAT/BCAT logic."""
    # ... existing implementation ...
    return {
        "action": action,
        "expected_decision": "DENY",
        "admissibility": "INADMISSIBLE",
        "basis": "I(x') > 0 or BCAT simplex invalid",
        "state_before": {"g": 0.3, "c": 0.3, "a": 0.2, "t": 0.2},
        "projected_state": {"g": 0.3, "c": 0.3, "a": 0.08, "t": 0.32},
        "lambda_capacity": 0.0288,
        "invariant": 0.0512,
        "delta_invariant": -0.1308,
        "bcat_simplex_sum": 1.0,
        "bcat_simplex_valid": True,
        "reason": "Projected transition violates admissibility."
    }


if __name__ == "__main__":
    sys.exit(main())
