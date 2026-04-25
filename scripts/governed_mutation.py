#!/usr/bin/env python3
"""GCAT/BCAT enforced mutation wrapper.

This closes the mutation bypass.

Previous behavior:
    ./stegverse mutate deploy

New governed behavior:
    python3 ../../scripts/governed_mutation.py deploy

Decision rule:
- ALLOW: delegate to ./stegverse mutate <mutation>
- DENY: do not call the SUT mutation command; emit a denial receipt
- FAIL_CLOSED: do not call the SUT mutation command; emit a fail-closed receipt

DENY and FAIL_CLOSED exit 0 because they are valid governed outcomes, not
runtime failures. The pipeline should fail only when the wrapper itself breaks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from admissibility import classify_action


# Map mutation names to the action-equivalent transition they represent.
# This lets the formalism evaluate the state transition even when the SUT exposes
# the operation through a mutation command instead of an action command.
MUTATION_TO_ACTION = {
    "deploy": "deploy_change",
}


def receipt_id_for_mutation(mutation: str, decision: str) -> str:
    material = f"gcat-bcat-mutation:{mutation}:{decision}".encode("utf-8")
    return sha256(material).hexdigest()[:16].upper()


def emit_mutation_receipt(mutation: str, mapped_action: str, decision: str, reason: str, admissibility: dict) -> None:
    rid = receipt_id_for_mutation(mutation, decision)

    if decision == "FAIL_CLOSED":
        print(f"Mutation fail_closed: {mutation}")
    elif decision == "DENY":
        print(f"Mutation denied: {mutation}")
    else:
        print(f"Mutation allowed: {mutation}")

    print(f"receipt_id: {rid}")
    print(f"decision: {decision}")
    print(f"mapped_action: {mapped_action}")
    print(f"reason: {reason}")
    print("admissibility:")
    print(json.dumps(admissibility, indent=2))


def main() -> int:
    mutation = sys.argv[1] if len(sys.argv) >= 2 else ""
    mapped_action = MUTATION_TO_ACTION.get(mutation)

    if mapped_action is None:
        synthetic = classify_action("malformed_request")
        emit_mutation_receipt(
            mutation=mutation,
            mapped_action="",
            decision="FAIL_CLOSED",
            reason=f"No GCAT/BCAT projection mapping exists for mutation: {mutation!r}",
            admissibility=synthetic.as_dict(),
        )
        return 0

    result = classify_action(mapped_action)
    decision = result.expected_decision

    if decision in {"DENY", "FAIL_CLOSED"}:
        emit_mutation_receipt(
            mutation=mutation,
            mapped_action=mapped_action,
            decision=decision,
            reason=result.reason,
            admissibility=result.as_dict(),
        )
        return 0

    delegated = subprocess.run(
        ["./stegverse", "mutate", mutation],
        capture_output=True,
        text=True,
        cwd=Path("."),
    )

    print(delegated.stdout, end="")
    if delegated.stderr:
        print(delegated.stderr, end="", file=sys.stderr)

    return delegated.returncode


if __name__ == "__main__":
    raise SystemExit(main())
