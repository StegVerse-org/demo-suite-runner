"""
StegVerse Receipt ID Generator

All receipt IDs are content-addressable and deterministic.
This ensures cross-run reproducibility for StegDB canonical monitoring.
"""

import hashlib
import os


def make_receipt_id(action: str, previous_id: str, decision: str, state_snapshot: str) -> str:
    """
    Generate a deterministic receipt ID from semantic content.

    The ID is computed as:
        SHA256(salt:action:previous_id:decision:state_snapshot)[:16].upper()

    Args:
        action: The action name (e.g., "deploy", "deploy_change")
        previous_id: Previous receipt ID or "GENESIS"
        decision: "ALLOWED", "DENIED", or "FAIL_CLOSED"
        state_snapshot: Current state identifier (e.g., "state4")

    Returns:
        16-character uppercase hexadecimal string

    Examples:
        >>> make_receipt_id("deploy", "GENESIS", "DENIED", "state4")
        'A1B2C3D4E5F67890'  # deterministic for these inputs

    Environment:
        STEGVERSE_SALT: Optional per-deployment secret. If set, adds
        unpredictability to IDs while maintaining cross-run stability
        within the same deployment.
    """
    salt = os.environ.get('STEGVERSE_SALT', '')
    content = f"{salt}:{action}:{previous_id}:{decision}:{state_snapshot}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16].upper()


def make_receipt_id_legacy() -> str:
    """
    Legacy non-deterministic receipt ID generator.

    Used for backward compatibility or when STEGVERSE_DETERMINISTIC_IDS
    is set to false. Not recommended for production StegDB integration.
    """
    import uuid
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
