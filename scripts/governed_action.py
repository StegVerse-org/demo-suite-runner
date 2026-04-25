#!/usr/bin/env python3
"""GCAT/BCAT enforced action wrapper.

This is the commit-boundary gate for the demo runner.

Decision rule:
- ALLOW: delegate to the underlying SUT action command.
- DENY: do not call the SUT; emit a denial receipt.
- FAIL_CLOSED: do not call the SUT; emit a fail-closed receipt.

The wrapper exits 0 for all three governed outcomes because DENY and
FAIL_CLOSED are valid decisions, not runtime failures.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from admissibility import classify_action, receipt_id_for


def emit_receipt(action: str, decision: str, reason: str, admissibility: dict) -> None:
    rid = receipt_id_for(action, decision)
    if decision == "FAIL_CLOSED":
        print(f"Action fail_closed: {action}")
    elif decision == "DENY":
        print(f"Action denied: {action}")
    else:
        print(f"Action allowed: {action}")

    print(f"receipt_id: {rid}")
    print(f"decision: {decision}")
    print(f"reason: {reason}")
    print("admissibility:")
    print(json.dumps(admissibility, indent=2))


def main() -> int:
    if len(sys.argv) < 2:
        action = ""
    else:
        action = sys.argv[1]

    result = classify_action(action)
    decision = result.expected_decision

    if decision in {"DENY", "FAIL_CLOSED"}:
        emit_receipt(action, decision, result.reason, result.as_dict())
        return 0

    sut = Path("./stegverse")
    delegated = subprocess.run(
        [str(sut), "action", action],
        capture_output=True,
        text=True,
    )
    print(delegated.stdout, end="")
    if delegated.stderr:
        print(delegated.stderr, end="", file=sys.stderr)
    return delegated.returncode


if __name__ == "__main__":
    raise SystemExit(main())
