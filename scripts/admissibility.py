#!/usr/bin/env python3
"""Minimal GCAT/BCAT admissibility helpers for the demo runner.

This file intentionally keeps the formalism small and inspectable. It is not a
production policy engine. It provides a deterministic bridge between governance
test cases and the GCAT/BCAT admissibility language used by the SDK demos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose
from typing import Dict, Optional


@dataclass(frozen=True)
class GCATParameters:
    K: float = 1.0
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0


@dataclass(frozen=True)
class StateVector:
    g: float
    c: float
    a: float
    t: float

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class AdmissibilityResult:
    action: str
    expected_decision: str
    admissibility: str
    basis: str
    state_before: Optional[Dict[str, float]]
    projected_state: Optional[Dict[str, float]]
    lambda_capacity: Optional[float]
    invariant: Optional[float]
    delta_invariant: Optional[float]
    bcat_simplex_sum: Optional[float]
    bcat_simplex_valid: bool
    reason: str

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


PARAMS = GCATParameters()

# Current demo baseline. This is intentionally simple: the test is about making
# the admissibility basis explicit in reports, not pretending this is the full
# production state model.
BASE_STATE = StateVector(g=0.30, c=0.30, a=0.20, t=0.20)

ACTION_PROJECTIONS: Dict[str, Optional[StateVector]] = {
    # ADMISSIBLE: autonomy stays below capacity.
    "deploy_change": StateVector(g=0.30, c=0.30, a=0.08, t=0.32),
    "release_secret": StateVector(g=0.30, c=0.30, a=0.08, t=0.32),
    "write_config": StateVector(g=0.30, c=0.30, a=0.08, t=0.32),

    # INADMISSIBLE: autonomy exceeds legitimacy capacity.
    "unauthorized_change": StateVector(g=0.25, c=0.25, a=0.35, t=0.15),
    "invalid_access": StateVector(g=0.25, c=0.25, a=0.35, t=0.15),
    "forbidden_deploy": StateVector(g=0.25, c=0.25, a=0.35, t=0.15),

    # Invalid / undefined transition basis.
    "malformed_request": None,
    "": None,
    "!!!": None,
    "nonexistent_action_12345": None,
}


def legitimacy_capacity(x: StateVector, params: GCATParameters = PARAMS) -> float:
    return params.K * (x.g ** params.alpha) * (x.c ** params.beta) * (x.t ** params.gamma)


def invariant(x: StateVector, params: GCATParameters = PARAMS) -> float:
    return x.a - legitimacy_capacity(x, params)


def bcat_simplex_valid(x: StateVector, tolerance: float = 1e-9) -> bool:
    values_in_range = all(0.0 <= value <= 1.0 for value in (x.g, x.c, x.a, x.t))
    return values_in_range and isclose(x.g + x.c + x.a + x.t, 1.0, abs_tol=tolerance)


def classify_action(action: str) -> AdmissibilityResult:
    normalized = action if isinstance(action, str) else ""
    projected = ACTION_PROJECTIONS.get(normalized)

    before_i = invariant(BASE_STATE)

    if projected is None:
        return AdmissibilityResult(
            action=repr(action),
            expected_decision="FAIL_CLOSED",
            admissibility="UNKNOWN",
            basis="BCAT/GCAT projection unavailable",
            state_before=BASE_STATE.as_dict(),
            projected_state=None,
            lambda_capacity=None,
            invariant=None,
            delta_invariant=None,
            bcat_simplex_sum=None,
            bcat_simplex_valid=False,
            reason="Projected state is undefined or invalid; fail closed.",
        )

    lambda_x = legitimacy_capacity(projected)
    after_i = invariant(projected)
    simplex_sum = projected.g + projected.c + projected.a + projected.t
    simplex_valid = bcat_simplex_valid(projected)
    admissible = simplex_valid and after_i <= 0.0

    return AdmissibilityResult(
        action=normalized,
        expected_decision="ALLOW" if admissible else "DENY",
        admissibility="ADMISSIBLE" if admissible else "INADMISSIBLE",
        basis="I(x') <= 0 and BCAT simplex valid" if admissible else "I(x') > 0 or BCAT simplex invalid",
        state_before=BASE_STATE.as_dict(),
        projected_state=projected.as_dict(),
        lambda_capacity=round(lambda_x, 12),
        invariant=round(after_i, 12),
        delta_invariant=round(after_i - before_i, 12),
        bcat_simplex_sum=round(simplex_sum, 12),
        bcat_simplex_valid=simplex_valid,
        reason=(
            "Projected transition preserves admissibility."
            if admissible
            else "Projected transition violates admissibility."
        ),
    )


def observed_decision_from_output(stdout: str) -> str:
    if "Action allowed" in stdout:
        return "ALLOW"
    if "Action denied" in stdout:
        return "DENY"
    return "FAIL_CLOSED"
