
# ============================================================================
# STEGVERSE CLI PATCH: mutation-receipts command
# ============================================================================
# 
# Location: In the main stegverse script, find the section that handles
# the "mutation-receipts" argument/command.
#
# Replace the existing receipt ID generation with the code below.
#
# Prerequisites:
#   1. receipt_id.py must be in the same directory or in PYTHONPATH
#   2. Or copy the generate_receipt_id function directly into stegverse
# ============================================================================

import os
import sys

# Add scripts directory to path if needed
scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from receipt_id import generate_receipt_id

# ... inside the mutation-receipts handler ...

def handle_mutation_receipts():
    """
    Generate and display mutation receipts with deterministic IDs.
    """
    # Get current state from runtime
    state = get_current_state()  # Your existing function

    # Receipt 1: Initial denial from GENESIS
    receipt_1_id = generate_receipt_id(
        action="deploy",
        previous_id="GENESIS",
        decision="DENIED",
        state_snapshot=state
    )

    # Receipt 2: Allowed, chained to receipt 1
    receipt_2_id = generate_receipt_id(
        action="deploy",
        previous_id=receipt_1_id,
        decision="ALLOWED",
        state_snapshot=state
    )

    # Output format must match existing expectations
    print(f"1. deploy | {receipt_1_id} | prev=GENESIS | decision=denied")
    print(f"2. deploy | {receipt_2_id} | prev={receipt_1_id} | decision=allowed")

    return [receipt_1_id, receipt_2_id]
