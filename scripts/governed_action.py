"""
governed_action.py
Gate action handler with FAIL_CLOSED fix.

CRITICAL FIX: malformed_request FAIL_CLOSED bug
  - OLD: Receipt generated AFTER evaluation → malformed requests got no receipt
  - NEW: Receipt generated BEFORE evaluation → EVERY request gets a receipt
  - If evaluation fails, receipt is logged as FAIL_CLOSED with reason

All actions pass through GCAT/BCAT gate before execution.
Confidence number + concise reasoning included for every output.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum
import logging

# Import receipt system
from receipt_id import get_receipt, init_session

logger = logging.getLogger("stegverse.gate")


class GateResult(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    FAIL_CLOSED = "FAIL_CLOSED"


class GovernedAction:
    """
    Wrapper for all gate-evaluated actions.
    Ensures: receipt first, evaluation second, logging third.
    """

    def __init__(self, gate_type: str = "GCAT"):
        self.gate_type = gate_type
        self.history: list = []

    def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate input through gate.

        Returns:
            {
                "receipt_id": str,
                "result": GateResult,
                "confidence": float,  # 0.0 - 1.0
                "reasoning": str,     # concise explanation
                "output": Any,        # result data if ALLOW
                "error": Optional[str] # error if FAIL_CLOSED
            }
        """
        # STEP 1: Generate receipt BEFORE any evaluation
        # FIX: This was previously done after evaluation, causing malformed
        #      requests to slip through without tracking
        receipt_id = get_receipt(input_data, self.gate_type)

        result = {
            "receipt_id": receipt_id,
            "result": None,
            "confidence": 0.0,
            "reasoning": "",
            "output": None,
            "error": None
        }

        try:
            # STEP 2: Validate input structure
            if not self._validate_input(input_data):
                result["result"] = GateResult.FAIL_CLOSED
                result["confidence"] = 1.0
                result["reasoning"] = "Input failed structural validation"
                self._log(result)
                return result

            # STEP 3: Run gate evaluation
            gate_output = self._run_gate(input_data, context or {})

            # STEP 4: Package result
            result["result"] = gate_output["decision"]
            result["confidence"] = gate_output["confidence"]
            result["reasoning"] = gate_output["reasoning"]

            if result["result"] == GateResult.ALLOW:
                result["output"] = gate_output.get("data", {})

            self._log(result)
            return result

        except Exception as e:
            # CRITICAL: Any exception = FAIL_CLOSED, but receipt already exists
            result["result"] = GateResult.FAIL_CLOSED
            result["confidence"] = 1.0
            result["reasoning"] = f"Exception during evaluation: {str(e)}"
            result["error"] = str(e)
            self._log(result)
            return result

    def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Structural validation before gate logic."""
        if not isinstance(input_data, dict):
            return False
        required_keys = ["action", "payload"]
        return all(k in input_data for k in required_keys)

    def _run_gate(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core gate evaluation logic.

        This is where GCAT/BCAT invariants are checked.
        For demo purposes, this is a simplified version.
        """
        action = input_data.get("action", "")
        payload = input_data.get("payload", {})

        # Example invariant checks (replace with actual GCAT/BCAT logic)
        checks = [
            ("payload_not_empty", len(payload) > 0),
            ("action_allowed", action in {"read", "write", "query", "verify"}),
            ("context_valid", isinstance(context, dict)),
        ]

        passed = sum(1 for _, check in checks if check)
        total = len(checks)
        confidence = passed / total

        if confidence >= 0.75:
            return {
                "decision": GateResult.ALLOW,
                "confidence": confidence,
                "reasoning": f"Passed {passed}/{total} invariant checks: {[n for n, c in checks if c]}",
                "data": {"action": action, "processed": True}
            }
        elif confidence >= 0.5:
            return {
                "decision": GateResult.DENY,
                "confidence": confidence,
                "reasoning": f"Partial pass {passed}/{total}: failed {[n for n, c in checks if not c]}",
                "data": None
            }
        else:
            return {
                "decision": GateResult.FAIL_CLOSED,
                "confidence": confidence,
                "reasoning": f"Failed {total - passed}/{total} critical checks: {[n for n, c in checks if not c]}",
                "data": None
            }

    def _log(self, result: Dict[str, Any]):
        """Log to StegDB (placeholder — wire to actual StegDB)."""
        self.history.append(result)
        logger.info(f"RECEIPT={result['receipt_id']} RESULT={result['result'].value} CONF={result['confidence']:.3f}")


def create_gate(gate_type: str = "GCAT") -> GovernedAction:
    """Factory for gate instances."""
    return GovernedAction(gate_type)
