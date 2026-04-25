"""
StegVerse Receipt ID Generator

All receipt IDs are content-addressable and deterministic.
This ensures cross-run reproducibility for StegDB canonical monitoring.

Usage:
    from receipt_id import generate_receipt_id

    rid = generate_receipt_id(
        action="deploy",
        previous_id="GENESIS",
        decision="DENIED",
        state_snapshot="state4"
    )

Environment:
    STEGVERSE_DETERMINISTIC_IDS: true/false (default: true)
    STEGVERSE_SALT: optional per-deployment secret
"""

import hashlib
import os
import uuid


def make_receipt_id(action: str, previous_id: str, decision: str, state_snapshot: str) -> str:
    """
    Generate a deterministic receipt ID from semantic content.

    Algorithm:
        SHA256(salt:action:previous_id:decision:state_snapshot)[:16].upper()

    Args:
        action: The action/mutation name (e.g., "deploy", "deploy_change")
        previous_id: Previous receipt ID or "GENESIS"
        decision: "ALLOWED", "DENIED", or "FAIL_CLOSED"
        state_snapshot: Current state identifier (e.g., "state4")

    Returns:
        16-character uppercase hexadecimal string
    """
    salt = os.environ.get('STEGVERSE_SALT', '')
    content = f"{salt}:{action}:{previous_id}:{decision}:{state_snapshot}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16].upper()


def make_receipt_id_legacy() -> str:
    """Legacy non-deterministic generator for backward compatibility."""
    return uuid.uuid4().hex[:16].upper()


def should_use_deterministic() -> bool:
    """Check if deterministic IDs are enabled."""
    return os.environ.get('STEGVERSE_DETERMINISTIC_IDS', 'true').lower() == 'true'


def generate_receipt_id(action: str, previous_id: str, decision: str, state_snapshot: str) -> str:
    """
    Main entry point. Uses deterministic or legacy based on env flag.
    """
    if should_use_deterministic():
        return make_receipt_id(action, previous_id, decision, state_snapshot)
    return make_receipt_id_legacy()
