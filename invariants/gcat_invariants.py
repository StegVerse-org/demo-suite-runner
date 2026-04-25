"""
gcat_invariants.py
GCAT (Global Canonical Admissibility Test) invariant implementations.

These are the formal mathematical checks derived from your GCAT/BCAT papers.
Each invariant returns:
  - passed: bool
  - confidence: float (0.0-1.0)
  - reasoning: str (concise mathematical explanation)
  - metadata: dict (experimental data for formalism refinement)

Invariants map to formalism components:
  I1: Simplex non-negativity (edge lengths ≥ 0)
  I2: Triangle inequality (1D edge closure)
  I3: Rigel metric positivity (metric tensor positive-definite)
  I4: Admissibility scalar bounds (0 ≤ α ≤ 1)
  I5: Confidence monotonicity (higher evidence → higher confidence)
  I6: Irreversibility preservation (action history non-decreasing)
"""

import math
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class InvariantResult:
    name: str
    passed: bool
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]


class GCATInvariants:
    """
    GCAT invariant checker.

    Each method implements one formal invariant from the GCAT/BCAT system.
    Metadata is collected for experimental formalism refinement.
    """

    def __init__(self, epsilon: float = 1e-9):
        self.epsilon = epsilon  # Numerical tolerance
        self.history: List[InvariantResult] = []

    # ============================================
    # I1: Simplex Non-Negativity
    # ============================================
    def check_simplex_non_negativity(
        self,
        edge_lengths: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I1: All simplex edge lengths must be non-negative.

        Formal: ∀e ∈ E, e ≥ 0

        Experimental: Track edge length distributions to refine
        the lower bound formalism (is 0 the correct floor?).
        """
        if not edge_lengths:
            return InvariantResult(
                name="I1_SimplexNonNegativity",
                passed=False,
                confidence=0.0,
                reasoning="Empty edge set — no simplex to evaluate",
                metadata={"edge_count": 0, "min_edge": None}
            )

        min_edge = min(edge_lengths)
        negative_edges = [e for e in edge_lengths if e < -self.epsilon]

        passed = len(negative_edges) == 0 and min_edge >= -self.epsilon

        # Confidence: how far above zero is the minimum?
        if passed:
            confidence = min(1.0, 1.0 - math.exp(-min_edge * 10)) if min_edge >= 0 else 0.5
        else:
            confidence = 0.0

        metadata = {
            "edge_count": len(edge_lengths),
            "min_edge": min_edge,
            "max_edge": max(edge_lengths),
            "mean_edge": sum(edge_lengths) / len(edge_lengths),
            "negative_count": len(negative_edges),
            "distribution": self._distribution_stats(edge_lengths)
        }

        reasoning = (
            f"Min edge={min_edge:.6f}, "
            f"{'all non-negative' if passed else f'{len(negative_edges)} negative edges'}"
        )

        result = InvariantResult(
            name="I1_SimplexNonNegativity",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # I2: Triangle Inequality (1D Edge Closure)
    # ============================================
    def check_triangle_inequality(
        self,
        edges: List[Tuple[float, float, float]],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I2: For every triangle (a, b, c): a + b ≥ c, a + c ≥ b, b + c ≥ a.

        Formal: ∀(a,b,c) ∈ T, a + b ≥ c ∧ a + c ≥ b ∧ b + c ≥ a

        Experimental: Track violation patterns to understand
        when the simplex "collapses" to a point (all edges → 0).
        """
        if not edges:
            return InvariantResult(
                name="I2_TriangleInequality",
                passed=False,
                confidence=0.0,
                reasoning="Empty triangle set",
                metadata={"triangle_count": 0}
            )

        violations = []
        closure_scores = []

        for i, (a, b, c) in enumerate(edges):
            checks = [
                (a + b >= c - self.epsilon, a + b - c, "a+b≥c"),
                (a + c >= b - self.epsilon, a + c - b, "a+c≥b"),
                (b + c >= a - self.epsilon, b + c - a, "b+c≥a")
            ]

            for passed, margin, desc in checks:
                if not passed:
                    violations.append({
                        "triangle": i,
                        "edge": desc,
                        "margin": margin,
                        "values": (a, b, c)
                    })
                closure_scores.append(margin)

        passed = len(violations) == 0

        # Confidence based on minimum closure margin
        if closure_scores:
            min_margin = min(closure_scores)
            confidence = min(1.0, max(0.0, 0.5 + min_margin * 5)) if min_margin >= 0 else 0.0
        else:
            confidence = 0.0

        metadata = {
            "triangle_count": len(edges),
            "violation_count": len(violations),
            "violations": violations[:10],  # Limit for size
            "min_closure_margin": min(closure_scores) if closure_scores else None,
            "mean_closure_margin": sum(closure_scores) / len(closure_scores) if closure_scores else None,
            "collapse_indicator": all(abs(e) < self.epsilon for tri in edges for e in tri)
        }

        reasoning = (
            f"{len(edges)} triangles, "
            f"{len(violations)} violations, "
            f"min_margin={metadata['min_closure_margin']:.6f if metadata['min_closure_margin'] else 'N/A'}"
        )

        result = InvariantResult(
            name="I2_TriangleInequality",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # I3: Rigel Metric Positivity
    # ============================================
    def check_rigel_metric_positivity(
        self,
        metric_tensor: List[List[float]],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I3: Rigel metric tensor must be positive-definite.

        Formal: ∀v ≠ 0, v^T G v > 0, where G is the Rigel metric.

        Experimental: Eigenvalue distributions reveal the "geometry"
        of the admissibility space. Near-zero eigenvalues indicate
        boundary proximity (irreversibility gap).
        """
        if not metric_tensor or not metric_tensor[0]:
            return InvariantResult(
                name="I3_RigelMetricPositivity",
                passed=False,
                confidence=0.0,
                reasoning="Empty metric tensor",
                metadata={"dimensions": 0}
            )

        G = np.array(metric_tensor)

        # Check symmetry
        is_symmetric = np.allclose(G, G.T, atol=self.epsilon)

        # Eigenvalues
        try:
            eigenvalues = np.linalg.eigvalsh(G)  # For symmetric matrices
        except Exception:
            eigenvalues = np.linalg.eigvals(G)

        min_eigenvalue = float(np.min(eigenvalues))
        max_eigenvalue = float(np.max(eigenvalues))
        condition_number = max_eigenvalue / min_eigenvalue if min_eigenvalue > self.epsilon else float('inf')

        passed = min_eigenvalue > self.epsilon and is_symmetric

        # Confidence: how positive-definite is it?
        if passed:
            confidence = min(1.0, 1.0 - math.exp(-min_eigenvalue * 100))
        else:
            confidence = 0.0

        metadata = {
            "dimensions": G.shape[0],
            "is_symmetric": is_symmetric,
            "eigenvalues": eigenvalues.tolist(),
            "min_eigenvalue": min_eigenvalue,
            "max_eigenvalue": max_eigenvalue,
            "condition_number": condition_number if condition_number != float('inf') else None,
            "positive_definite": passed,
            "near_singular": min_eigenvalue < 1e-6
        }

        reasoning = (
            f"{G.shape[0]}x{G.shape[0]} metric, "
            f"min_eigenvalue={min_eigenvalue:.6f}, "
            f"{'positive-definite' if passed else 'NOT positive-definite'}"
        )

        result = InvariantResult(
            name="I3_RigelMetricPositivity",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # I4: Admissibility Scalar Bounds
    # ============================================
    def check_admissibility_scalar_bounds(
        self,
        alpha: float,
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I4: Admissibility scalar α must satisfy 0 ≤ α ≤ 1.

        Formal: α ∈ [0, 1]

        Experimental: Track α distributions to determine if
        the bounds are correct or if α can exceed 1 in
        high-confidence scenarios (super-admissibility?).
        """
        passed = 0.0 - self.epsilon <= alpha <= 1.0 + self.epsilon

        # Confidence: how centered is α in [0,1]?
        if 0 <= alpha <= 1:
            # Peak confidence at α = 0.5, drops toward boundaries
            confidence = 1.0 - abs(alpha - 0.5) * 2
        else:
            confidence = 0.0

        metadata = {
            "alpha": alpha,
            "in_bounds": passed,
            "distance_to_lower": alpha - 0.0,
            "distance_to_upper": 1.0 - alpha,
            "is_boundary": abs(alpha) < self.epsilon or abs(alpha - 1.0) < self.epsilon,
            "quadrant": "LOW" if alpha < 0.25 else "MID-LOW" if alpha < 0.5 else "MID-HIGH" if alpha < 0.75 else "HIGH"
        }

        reasoning = (
            f"α={alpha:.6f}, "
            f"{'in bounds' if passed else f'OUT OF BOUNDS (α={alpha:.6f})'}"
        )

        result = InvariantResult(
            name="I4_AdmissibilityScalarBounds",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # I5: Confidence Monotonicity
    # ============================================
    def check_confidence_monotonicity(
        self,
        evidence_sequence: List[float],
        confidence_sequence: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I5: Higher evidence should yield monotonically non-decreasing confidence.

        Formal: e₁ ≤ e₂ ⇒ c₁ ≤ c₂

        Experimental: Track violations to understand when
        "more evidence reduces confidence" — indicates
        contradictory evidence or model misspecification.
        """
        if len(evidence_sequence) != len(confidence_sequence) or len(evidence_sequence) < 2:
            return InvariantResult(
                name="I5_ConfidenceMonotonicity",
                passed=False,
                confidence=0.0,
                reasoning="Insufficient paired data",
                metadata={"pairs": len(evidence_sequence)}
            )

        violations = []
        for i in range(len(evidence_sequence) - 1):
            e1, e2 = evidence_sequence[i], evidence_sequence[i + 1]
            c1, c2 = confidence_sequence[i], confidence_sequence[i + 1]

            if e2 > e1 and c2 < c1 - self.epsilon:
                violations.append({
                    "index": i,
                    "evidence_delta": e2 - e1,
                    "confidence_delta": c2 - c1,
                    "severity": abs(c2 - c1) / (c1 if c1 > 0 else 1)
                })

        passed = len(violations) == 0

        # Confidence: proportion of monotonic pairs
        total_pairs = len(evidence_sequence) - 1
        monotonic_pairs = total_pairs - len(violations)
        confidence = monotonic_pairs / total_pairs if total_pairs > 0 else 0.0

        metadata = {
            "total_pairs": total_pairs,
            "monotonic_pairs": monotonic_pairs,
            "violation_count": len(violations),
            "violations": violations[:10],
            "mean_evidence": sum(evidence_sequence) / len(evidence_sequence),
            "mean_confidence": sum(confidence_sequence) / len(confidence_sequence),
            "correlation": self._correlation(evidence_sequence, confidence_sequence)
        }

        reasoning = (
            f"{total_pairs} pairs, "
            f"{len(violations)} monotonicity violations, "
            f"correlation={metadata['correlation']:.3f}"
        )

        result = InvariantResult(
            name="I5_ConfidenceMonotonicity",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # I6: Irreversibility Preservation
    # ============================================
    def check_irreversibility_preservation(
        self,
        action_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> InvariantResult:
        """
        I6: Action history must be non-decreasing in irreversibility.

        Formal: ∀t, I(t+1) ≥ I(t), where I is irreversibility measure.

        Experimental: Track how irreversibility accumulates.
        The "gap between irreversibility and touching reality"
        is the safety margin.
        """
        if len(action_history) < 2:
            return InvariantResult(
                name="I6_IrreversibilityPreservation",
                passed=False,
                confidence=0.0,
                reasoning="Need ≥2 actions to check preservation",
                metadata={"action_count": len(action_history)}
            )

        irreversibility_scores = []
        for action in action_history:
            # Irreversibility = hash of action content (simplified)
            # In formalism: I(A) = entropy of state change
            action_str = str(sorted(action.items()))
            irreversibility = int(hashlib.sha256(action_str.encode()).hexdigest(), 16) % 10000 / 10000
            irreversibility_scores.append(irreversibility)

        violations = []
        for i in range(len(irreversibility_scores) - 1):
            if irreversibility_scores[i + 1] < irreversibility_scores[i] - self.epsilon:
                violations.append({
                    "index": i,
                    "delta": irreversibility_scores[i + 1] - irreversibility_scores[i]
                })

        passed = len(violations) == 0

        # Confidence: cumulative irreversibility growth rate
        if len(irreversibility_scores) > 1:
            growth = (irreversibility_scores[-1] - irreversibility_scores[0]) / len(irreversibility_scores)
            confidence = min(1.0, max(0.0, 0.5 + growth * 10))
        else:
            confidence = 0.0

        metadata = {
            "action_count": len(action_history),
            "irreversibility_scores": irreversibility_scores,
            "violations": violations,
            "total_irreversibility": sum(irreversibility_scores),
            "growth_rate": growth if len(irreversibility_scores) > 1 else None,
            "safety_margin": 1.0 - max(irreversibility_scores) if irreversibility_scores else None
        }

        reasoning = (
            f"{len(action_history)} actions, "
            f"total_irreversibility={metadata['total_irreversibility']:.6f}, "
            f"{len(violations)} preservation violations"
        )

        result = InvariantResult(
            name="I6_IrreversibilityPreservation",
            passed=passed,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata
        )
        self.history.append(result)
        return result

    # ============================================
    # Composite: Run All Invariants
    # ============================================
    def evaluate_all(
        self,
        test_data: Dict[str, Any]
    ) -> Dict[str, InvariantResult]:
        """Run all invariants against test data."""
        results = {}

        if "edge_lengths" in test_data:
            results["I1"] = self.check_simplex_non_negativity(test_data["edge_lengths"])

        if "triangles" in test_data:
            results["I2"] = self.check_triangle_inequality(test_data["triangles"])

        if "metric_tensor" in test_data:
            results["I3"] = self.check_rigel_metric_positivity(test_data["metric_tensor"])

        if "alpha" in test_data:
            results["I4"] = self.check_admissibility_scalar_bounds(test_data["alpha"])

        if "evidence_sequence" in test_data and "confidence_sequence" in test_data:
            results["I5"] = self.check_confidence_monotonicity(
                test_data["evidence_sequence"],
                test_data["confidence_sequence"]
            )

        if "action_history" in test_data:
            results["I6"] = self.check_irreversibility_preservation(test_data["action_history"])

        return results

    # ============================================
    # Utilities
    # ============================================
    def _distribution_stats(self, values: List[float]) -> Dict[str, float]:
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "mean": sum(values) / n,
            "median": sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2,
            "std": math.sqrt(sum((x - sum(values)/n)**2 for x in values) / n) if n > 1 else 0,
            "q25": sorted_vals[n // 4],
            "q75": sorted_vals[3 * n // 4]
        }

    def _correlation(self, x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den_x = math.sqrt(sum((xi - mean_x)**2 for xi in x))
        den_y = math.sqrt(sum((yi - mean_y)**2 for yi in y))

        if den_x == 0 or den_y == 0:
            return 0.0
        return num / (den_x * den_y)

    def get_experimental_data(self) -> Dict[str, Any]:
        """Export all metadata for formalism refinement."""
        return {
            "total_checks": len(self.history),
            "by_invariant": self._group_by_name(),
            "aggregate_confidence": self._aggregate_confidence(),
            "violation_patterns": self._violation_patterns()
        }

    def _group_by_name(self) -> Dict[str, List[InvariantResult]]:
        groups = {}
        for r in self.history:
            groups.setdefault(r.name, []).append(r)
        return groups

    def _aggregate_confidence(self) -> Dict[str, float]:
        if not self.history:
            return {}
        return {
            "mean": sum(r.confidence for r in self.history) / len(self.history),
            "min": min(r.confidence for r in self.history),
            "max": max(r.confidence for r in self.history)
        }

    def _violation_patterns(self) -> Dict[str, Any]:
        violations = [r for r in self.history if not r.passed]
        return {
            "total_violations": len(violations),
            "by_invariant": {name: len([v for v in violations if v.name == name]) 
                           for name in set(v.name for v in violations)}
        }
