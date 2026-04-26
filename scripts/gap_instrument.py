#!/usr/bin/env python3
"""
gap_instrument.py -- Gap Instrumentation

Measures the active workspace between irreversibility and touching reality.
Tracks coherence budget, obscurity gradient, negotiation depth,
commitment latency, and entropy debt per transition.

The gap is where actionable reality exists between endpoints.
"""

import math
from datetime import datetime, timezone
from scalar_engine import compute_invariant, shannon_entropy, shannon_information


def compute_coherence_budget(state_before, projected_state):
    """
    Fidelity between before and projected states.
    Dot product of state vectors (already normalized by simplex constraint).
    """
    if not projected_state:
        return 0.0
    return sum(state_before[k] * projected_state[k] for k in state_before)


def compute_obscurity_gradient(state_before, projected_state):
    """Change in invariant across transition."""
    if not projected_state:
        return float('inf')
    return compute_invariant(projected_state) - compute_invariant(state_before)


def compute_entropy_debt(state_before, projected_state):
    """
    Entropy debt = information lost to obscurity in the gap.
    H(projected) - H(state_before), clamped to non-negative.
    """
    if not projected_state:
        return float('inf')
    return max(0.0, shannon_entropy(projected_state) - shannon_entropy(state_before))


def is_reversible(step):
    """
    A step is reversible if the simplex remains valid
    and the operation can be undone without information loss.
    """
    return step.get('simplex_valid', False) and step.get('information_loss', 0) < 1e-9


def compute_negotiation_depth(sequence):
    """Count reversible operations before first irreversible step."""
    depth = 0
    for step in sequence:
        if is_reversible(step):
            depth += 1
        else:
            break
    return depth


def compute_commitment_latency(sequence):
    """
    Time from last reversible step to irreversible contact.
    Returns 0 if no reversible steps or no contact.
    """
    reversible_times = [
        step['timestamp'] for step in sequence 
        if is_reversible(step) and 'timestamp' in step
    ]

    if not reversible_times or not sequence:
        return 0.0

    last_reversible = max(reversible_times)
    contact_time = sequence[-1].get('timestamp', last_reversible)

    if isinstance(last_reversible, str):
        last_reversible = datetime.fromisoformat(last_reversible.replace('Z', '+00:00'))
    if isinstance(contact_time, str):
        contact_time = datetime.fromisoformat(contact_time.replace('Z', '+00:00'))

    return (contact_time - last_reversible).total_seconds()


class GapLedger:
    """
    Maintains a sequence of gap operations for a single run.

    Rules:
      - Erased if FAIL_CLOSED (gap broken)
      - Committed if ALLOW (reality touched)
      - Suspended if DENY (negotiation incomplete)
    """

    def __init__(self):
        self.operations = []
        self.status = 'open'  # open, committed, suspended, erased

    def add_operation(self, operation, reversible, scalar, entropy_change, 
                      simplex_valid=True, information_loss=0.0):
        """Add an operation to the ledger."""
        self.operations.append({
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'operation': operation,
            'reversible': reversible,
            'scalar': scalar,
            'entropy_change': entropy_change,
            'simplex_valid': simplex_valid,
            'information_loss': information_loss
        })

    def commit(self, outcome):
        """Close the ledger with final outcome."""
        if outcome == 'ALLOW':
            self.status = 'committed'
        elif outcome == 'DENY':
            self.status = 'suspended'
        elif outcome == 'FAIL_CLOSED':
            self.status = 'erased'
            self.operations = []  # erase all

    def get_stats(self):
        """Compute gap statistics."""
        if not self.operations:
            return {
                'negotiation_depth': 0,
                'commitment_latency': 0.0,
                'total_entropy_change': 0.0,
                'mean_scalar': None,
                'status': self.status
            }

        reversible_steps = [op for op in self.operations if op['reversible']]

        return {
            'negotiation_depth': len(reversible_steps),
            'commitment_latency': compute_commitment_latency(self.operations),
            'total_entropy_change': sum(op['entropy_change'] for op in self.operations),
            'mean_scalar': sum(op['scalar'] for op in self.operations) / len(self.operations),
            'status': self.status
        }


if __name__ == '__main__':
    # Test gap ledger
    print("Gap Instrument Test")
    print("=" * 60)

    ledger = GapLedger()

    # Simulate a negotiation sequence
    ledger.add_operation('prepare', reversible=True, scalar=0.45, 
                         entropy_change=0.01, simplex_valid=True)
    ledger.add_operation('negotiate_1', reversible=True, scalar=0.48,
                         entropy_change=0.02, simplex_valid=True)
    ledger.add_operation('negotiate_2', reversible=True, scalar=0.52,
                         entropy_change=0.01, simplex_valid=True)
    ledger.add_operation('commit', reversible=False, scalar=0.50,
                         entropy_change=0.05, simplex_valid=True)

    ledger.commit('ALLOW')
    stats = ledger.get_stats()

    print(f"Status: {stats['status']}")
    print(f"Negotiation depth: {stats['negotiation_depth']}")
    print(f"Commitment latency: {stats['commitment_latency']:.6f} s")
    print(f"Total entropy change: {stats['total_entropy_change']:.4f}")
    print(f"Mean scalar: {stats['mean_scalar']:.4f}")
