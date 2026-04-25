"""
bcat_invariants.py
BCAT (Boundary Condition Admissibility Test) invariant implementations.

BCAT checks boundary conditions where GCAT invariants approach limits:
  B1: Boundary proximity (how close to α = 0 or α = 1)
  B2: Metric degeneracy (near-singular metric tensors)
  B3: Edge collapse (simplex edges approaching 0)
  B4: Confidence cliff (sudden confidence drops)
  B5: Irreversibility saturation (approaching maximum irreversibility)
  B6: Action replay resistance (same action, different context)

BCAT is the "safety net" — it catches cases where GCAT passes
but the system is near a dangerous boundary.
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from gcat_invariants import InvariantResult


class BCATInvariants:
    """
    BCAT boundary condition checker.

    Complements GCAT by checking "near-miss" conditions.
    """

    def __init__(self, warning_threshold: float = 0.1, danger_threshold: float = 0.01):
        self.warning_threshold = warning_threshold  # Yellow zone
        self.danger_threshold = danger_threshold    # Red zone
        self.history: List[InvariantResult] = []

    # ============================================
    # B1: Boundary Proximity
    # ============================================
    def check_boundary_proximity(
        self,
        alpha: float,
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B1: How close is α to boundaries [0, 1]?

        Formal: d(α, ∂[0,1]) < ε_warning → WARN, < ε_danger → DANGER

        Experimental: Determine optimal thresholds empirically.
        """
        dist_to_0 = abs(alpha - 0.0)
        dist_to_1 = abs(alpha - 1.0)
        min_dist = min(dist_to_0, dist_to_1)

        if min_dist < self.danger_threshold:
            status = "DANGER"
            passed = False
            confidence = 0.0
        elif min_dist < self.warning_threshold:
            status = "WARNING"
            passed = True
            confidence = min_dist / self.warning_threshold
        else:
            status = "SAFE"
            passed = True
            confidence = 1.0

        metadata = {
            "alpha": alpha,
            "dist_to_0": dist_to_0,
            "dist_to_1": dist_to_1,
            "min_dist": min_dist,
            "status": status,
            "threshold_warning": self.warning_threshold,
            "threshold_danger": self.danger_threshold
        }

        reasoning = f"α={alpha:.6f}, distance to boundary={min_dist:.6f} → {status}"

        result = InvariantResult(
            name="B1_BoundaryProximity",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # B2: Metric Degeneracy
    # ============================================
    def check_metric_degeneracy(
        self,
        metric_tensor: List[List[float]],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B2: Is the metric tensor approaching degeneracy?

        Formal: condition_number(G) > κ_max → DEGENERATE

        Experimental: Track condition number distributions
        to set κ_max empirically.
        """
        G = np.array(metric_tensor)

        try:
            eigenvalues = np.linalg.eigvalsh(G)
            min_eig = float(np.min(eigenvalues))
            max_eig = float(np.max(eigenvalues))
            cond_num = max_eig / min_eig if min_eig > 1e-12 else float('inf')
        except Exception:
            min_eig = 0
            max_eig = 0
            cond_num = float('inf')

        # Thresholds (empirical — adjust based on data)
        kappa_warn = 1e6
        kappa_danger = 1e12

        if cond_num == float('inf') or cond_num > kappa_danger:
            status = "DANGER"
            passed = False
            confidence = 0.0
        elif cond_num > kappa_warn:
            status = "WARNING"
            passed = True
            confidence = 1.0 - (cond_num - kappa_warn) / (kappa_danger - kappa_warn)
        else:
            status = "SAFE"
            passed = True
            confidence = 1.0

        metadata = {
            "dimensions": G.shape[0],
            "min_eigenvalue": min_eig,
            "max_eigenvalue": max_eig,
            "condition_number": cond_num if cond_num != float('inf') else None,
            "status": status,
            "threshold_warn": kappa_warn,
            "threshold_danger": kappa_danger
        }

        reasoning = (
            f"Condition number={cond_num:.2e if cond_num != float('inf') else 'INF'}, "
            f"min_eig={min_eig:.6f} → {status}"
        )

        result = InvariantResult(
            name="B2_MetricDegeneracy",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # B3: Edge Collapse
    # ============================================
    def check_edge_collapse(
        self,
        edge_lengths: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B3: Are simplex edges collapsing toward 0?

        Formal: ∃e ∈ E, e < ε_collapse → COLLAPSE IMMINENT

        Experimental: As edges → 0, simplex reduces to point.
        This is the "irreversibility point" where ALLOW is
        the only possible outcome (no freedom left).
        """
        if not edge_lengths:
            return InvariantResult(
                name="B3_EdgeCollapse",
                passed=False,
                confidence=0.0,
                reasoning="Empty edge set",
                metadata={}
            )

        collapse_threshold = 1e-6
        near_collapse = [e for e in edge_lengths if e < collapse_threshold]
        min_edge = min(edge_lengths)

        if min_edge < collapse_threshold / 10:
            status = "COLLAPSED"
            passed = False
            confidence = 0.0
        elif near_collapse:
            status = "IMMINENT"
            passed = True
            confidence = min_edge / collapse_threshold
        else:
            status = "SAFE"
            passed = True
            confidence = 1.0

        metadata = {
            "min_edge": min_edge,
            "collapse_threshold": collapse_threshold,
            "near_collapse_count": len(near_collapse),
            "status": status,
            "collapse_ratio": min_edge / max(edge_lengths) if max(edge_lengths) > 0 else 0
        }

        reasoning = (
            f"Min edge={min_edge:.6f}, "
            f"{len(near_collapse)} near-collapse edges → {status}"
        )

        result = InvariantResult(
            name="B3_EdgeCollapse",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # B4: Confidence Cliff
    # ============================================
    def check_confidence_cliff(
        self,
        confidence_sequence: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B4: Detect sudden confidence drops (cliffs).

        Formal: ∃i, c_{i+1} - c_i < -Δ_max → CLIFF DETECTED

        Experimental: Cliff frequency and magnitude reveal
        system stability. Frequent cliffs = unstable formalism.
        """
        if len(confidence_sequence) < 2:
            return InvariantResult(
                name="B4_ConfidenceCliff",
                passed=False,
                confidence=0.0,
                reasoning="Need ≥2 confidence values",
                metadata={}
            )

        delta_max = 0.3  # Threshold for "cliff"
        cliffs = []

        for i in range(len(confidence_sequence) - 1):
            delta = confidence_sequence[i + 1] - confidence_sequence[i]
            if delta < -delta_max:
                cliffs.append({
                    "index": i,
                    "delta": delta,
                    "from": confidence_sequence[i],
                    "to": confidence_sequence[i + 1]
                })

        if len(cliffs) > len(confidence_sequence) / 3:
            status = "UNSTABLE"
            passed = False
            confidence = 0.0
        elif cliffs:
            status = "WARNING"
            passed = True
            confidence = 1.0 - len(cliffs) / len(confidence_sequence)
        else:
            status = "STABLE"
            passed = True
            confidence = 1.0

        metadata = {
            "confidence_count": len(confidence_sequence),
            "cliff_count": len(cliffs),
            "cliff_rate": len(cliffs) / (len(confidence_sequence) - 1) if len(confidence_sequence) > 1 else 0,
            "max_cliff_magnitude": min(c["delta"] for c in cliffs) if cliffs else 0,
            "status": status,
            "cliffs": cliffs[:10]
        }

        reasoning = (
            f"{len(confidence_sequence)} confidence values, "
            f"{len(cliffs)} cliffs ({metadata['cliff_rate']:.1%}) → {status}"
        )

        result = InvariantResult(
            name="B4_ConfidenceCliff",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # B5: Irreversibility Saturation
    # ============================================
    def check_irreversibility_saturation(
        self,
        irreversibility_scores: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B5: Is irreversibility approaching maximum (saturation)?

        Formal: I_max - I_current < ε → SATURATED

        Experimental: Saturation indicates system has no
        "room" for further irreversible actions — all future
        actions must be reversible or the system locks.
        """
        if not irreversibility_scores:
            return InvariantResult(
                name="B5_IrreversibilitySaturation",
                passed=False,
                confidence=0.0,
                reasoning="Empty irreversibility data",
                metadata={}
            )

        max_possible = 1.0  # Normalized maximum
        current_max = max(irreversibility_scores)
        headroom = max_possible - current_max

        saturation_warn = 0.1
        saturation_danger = 0.01

        if headroom < saturation_danger:
            status = "SATURATED"
            passed = False
            confidence = 0.0
        elif headroom < saturation_warn:
            status = "WARNING"
            passed = True
            confidence = headroom / saturation_warn
        else:
            status = "SAFE"
            passed = True
            confidence = 1.0

        metadata = {
            "current_max": current_max,
            "max_possible": max_possible,
            "headroom": headroom,
            "status": status,
            "saturation_rate": current_max / max_possible,
            "score_count": len(irreversibility_scores),
            "mean_score": sum(irreversibility_scores) / len(irreversibility_scores)
        }

        reasoning = (
            f"Max irreversibility={current_max:.6f}, "
            f"headroom={headroom:.6f} → {status}"
        )

        result = InvariantResult(
            name="B5_IrreversibilitySaturation",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # B6: Action Replay Resistance
    # ============================================
    def check_action_replay_resistance(
        self,
        action: Dict[str, Any],
        history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        B6: Same action in different context must produce different receipts.

        Formal: A₁ = A₂ ∧ C₁ ≠ C₂ ⇒ Receipt(A₁,C₁) ≠ Receipt(A₂,C₂)

        Experimental: Measures context-sensitivity of the system.
        Low resistance = replay attacks possible.
        """
        if not history:
            return InvariantResult(
                name="B6_ActionReplayResistance",
                passed=True,
                confidence=1.0,
                reasoning="No history — replay impossible",
                metadata={"history_length": 0}
            )

        # Find similar actions in history
        similar = []
        for i, h in enumerate(history):
            if h.get("action") == action.get("action"):
                similar.append({"index": i, "context_diff": self._context_diff(h.get("context", {}), action.get("context", {}))})

        # Check if any identical action+context exists (replay)
        exact_replays = [s for s in similar if s["context_diff"] == 0]

        if exact_replays:
            status = "REPLAY_DETECTED"
            passed = False
            confidence = 0.0
        elif similar:
            status = "CONTEXT_DEPENDENT"
            passed = True
            confidence = 1.0 - (1.0 / (1 + min(s["context_diff"] for s in similar)))
        else:
            status = "UNIQUE"
            passed = True
            confidence = 1.0

        metadata = {
            "history_length": len(history),
            "similar_actions": len(similar),
            "exact_replays": len(exact_replays),
            "status": status
        }

        reasoning = (
            f"{len(history)} history items, "
            f"{len(similar)} similar, {len(exact_replays)} exact replays → {status}"
        )

        result = InvariantResult(
            name="B6_ActionReplayResistance",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    def _context_diff(self, c1: Dict, c2: Dict) -> float:
        """Measure context difference (0 = identical)."""
        all_keys = set(c1.keys()) | set(c2.keys())
        if not all_keys:
            return 0.0
        diffs = sum(1 for k in all_keys if c1.get(k) != c2.get(k))
        return diffs / len(all_keys)

    # ============================================
    # Composite: Run All BCAT Checks
    # ============================================
    def evaluate_all(
        self,
        test_data: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, InvariantResult]:
        """Run all BCAT boundary checks."""
        results = {}

        if "alpha" in test_data:
            results["B1"] = self.check_boundary_proximity(test_data["alpha"])

        if "metric_tensor" in test_data:
            results["B2"] = self.check_metric_degeneracy(test_data["metric_tensor"])

        if "edge_lengths" in test_data:
            results["B3"] = self.check_edge_collapse(test_data["edge_lengths"])

        if "confidence_sequence" in test_data:
            results["B4"] = self.check_confidence_cliff(test_data["confidence_sequence"])

        if "irreversibility_scores" in test_data:
            results["B5"] = self.check_irreversibility_saturation(test_data["irreversibility_scores"])

        if "action" in test_data and history:
            results["B6"] = self.check_action_replay_resistance(test_data["action"], history)

        return results

    def get_experimental_data(self) -> Dict[str, Any]:
        """Export all metadata for formalism refinement."""
        return {
            "total_checks": len(self.history),
            "by_invariant": self._group_by_name(),
            "boundary_violations": len([r for r in self.history if not r.passed]),
            "warning_count": len([r for r in self.history if r.metadata.get("status") == "WARNING"])
        }

    def _group_by_name(self) -> Dict[str, List[InvariantResult]]:
        groups = {}
        for r in self.history:
            groups.setdefault(r.name, []).append(r)
        return groups
