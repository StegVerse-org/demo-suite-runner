"""
governed_mutation.py
State mutation with deterministic logging.

All state changes are:
  1. Pre-approved by GCAT/BCAT gate
  2. Receipt-tagged before execution
  3. Logged to StegDB after execution
  4. Reversible where possible

This prevents "silent mutations" — every change is tracked.
"""

from typing import Dict, Any, Optional, Callable
from copy import deepcopy
from governed_action import GovernedAction, GateResult, get_receipt


class GovernedMutation:
    """
    Wrapper for state mutations.
    Ensures no state change happens without gate approval and receipt.
    """

    def __init__(self, gate: GovernedAction, state_store: Optional[Dict[str, Any]] = None):
        self.gate = gate
        self.state = state_store or {}
        self.mutation_log: list = []
        self.rollback_stack: list = []

    def mutate(
        self,
        mutation_type: str,
        target_key: str,
        new_value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a governed mutation.

        Flow:
          1. Build gate input from mutation request
          2. Get gate approval (receipt generated here)
          3. If ALLOW: execute mutation, log to StegDB
          4. If DENY/FAIL_CLOSED: reject, log attempt

        Returns:
            {
                "receipt_id": str,
                "result": GateResult,
                "confidence": float,
                "reasoning": str,
                "previous_value": Any,
                "new_value": Any,
                "rolled_back": bool
            }
        """
        # Build gate input
        gate_input = {
            "action": "write",
            "payload": {
                "mutation_type": mutation_type,
                "target_key": target_key,
                "new_value_hash": hash(str(new_value)) & 0xFFFFFFFF,
                "context": context or {}
            }
        }

        # Evaluate through gate (receipt generated inside)
        gate_result = self.gate.evaluate(gate_input, context)

        mutation_record = {
            "receipt_id": gate_result["receipt_id"],
            "result": gate_result["result"],
            "confidence": gate_result["confidence"],
            "reasoning": gate_result["reasoning"],
            "previous_value": None,
            "new_value": None,
            "rolled_back": False
        }

        if gate_result["result"] == GateResult.ALLOW:
            # Save for rollback
            previous = deepcopy(self.state.get(target_key))
            self.rollback_stack.append({
                "target_key": target_key,
                "previous_value": previous,
                "receipt_id": gate_result["receipt_id"]
            })

            # Execute mutation
            mutation_record["previous_value"] = previous
            self.state[target_key] = new_value
            mutation_record["new_value"] = new_value

            # Log to StegDB (placeholder)
            self._log_mutation(mutation_record)

        self.mutation_log.append(mutation_record)
        return mutation_record

    def rollback(self, receipt_id: Optional[str] = None) -> bool:
        """
        Rollback last mutation (or specific receipt).
        Only rolls back ALLOW mutations.
        """
        if not self.rollback_stack:
            return False

        if receipt_id:
            # Find specific mutation
            for i, entry in enumerate(self.rollback_stack):
                if entry["receipt_id"] == receipt_id:
                    self.state[entry["target_key"]] = entry["previous_value"]
                    self.rollback_stack.pop(i)
                    return True
            return False
        else:
            # Rollback most recent
            entry = self.rollback_stack.pop()
            self.state[entry["target_key"]] = entry["previous_value"]
            return True

    def query(self, key: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Governed read operation."""
        gate_input = {
            "action": "read",
            "payload": {"target_key": key}
        }
        return self.gate.evaluate(gate_input, context)

    def _log_mutation(self, record: Dict[str, Any]):
        """Log to StegDB (wire to actual StegDB implementation)."""
        # Placeholder: In production, this writes to StegDB
        pass

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Return immutable snapshot of current state."""
        return deepcopy(self.state)
