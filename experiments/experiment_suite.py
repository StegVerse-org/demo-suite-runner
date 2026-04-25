"""
experiment_suite.py
Pre-built experiment suites for formalism exploration.

Each suite targets a specific theoretical question:
  Suite 1: "As edges → 0, does simplex always reduce to ALLOW?"
  Suite 2: "What is the optimal α boundary threshold?"
  Suite 3: "Does confidence monotonicity hold under contradiction?"
  Suite 4: "When does metric degeneracy trigger FAIL_CLOSED?"
  Suite 5: "Can we empirically derive the Rigel metric from data?"

All suites use the ephemeral sandbox — no persistence, full logging.
"""

import json
import numpy as np
from typing import Dict, Any, List
from sandbox.ephemeral_sandbox import EphemeralSandbox, ExperimentResult


class ExperimentSuites:
    """Collection of pre-built formalism experiments."""

    def __init__(self, base_seed: str = "formalism-exploration"):
        self.base_seed = base_seed
        self.all_results: List[ExperimentResult] = []

    # ============================================
    # Suite 1: Edge Collapse → ALLOW Convergence
    # ============================================
    def suite_edge_collapse_convergence(self, num_steps: int = 20) -> List[ExperimentResult]:
        """
        Q: As simplex edges shrink toward 0, does the system
           always converge to ALLOW (no freedom left)?

        Method: Gradually reduce edge lengths, measure gate results.
        """
        print("
[SUITE 1] Edge Collapse → ALLOW Convergence")
        print("-" * 40)

        results = []
        sandbox = EphemeralSandbox(seed=f"{self.base_seed}-collapse", experiment_name="collapse")

        for step in range(num_steps):
            scale = 10.0 * (0.5 ** step)  # Exponential decay

            result = sandbox.run_experiment({
                "test_simplex": True,
                "dimension": 3,
                "collapse_prob": 0.0,  # Controlled collapse via scale
                "test_admissibility": True,
                "alpha": 0.5  # Neutral alpha
            }, custom_data={
                "edge_lengths": [scale, scale * 1.1, scale * 0.9],
                "triangles": [(scale, scale * 1.1, scale * 0.9)],
                "alpha": 0.5
            })

            results.append(result)

            gcat_pass = result.aggregate.get("gcat_pass_rate", 0)
            bcat_pass = result.aggregate.get("bcat_pass_rate", 0)

            print(f"  Step {step:2d}: scale={scale:.6f} | GCAT={gcat_pass:.1%} | BCAT={bcat_pass:.1%}")

            # Stop if we've reached collapse
            if scale < 1e-9:
                print(f"  → Collapse threshold reached at step {step}")
                break

        self.all_results.extend(results)
        return results

    # ============================================
    # Suite 2: Alpha Boundary Threshold Optimization
    # ============================================
    def suite_alpha_threshold(self, num_samples: int = 100) -> List[ExperimentResult]:
        """
        Q: What is the empirical optimal boundary threshold for α?

        Method: Sample α across [0,1], measure BCAT B1 (boundary proximity)
        and GCAT I4 (bounds) failure rates.
        """
        print("
[SUITE 2] Alpha Boundary Threshold Optimization")
        print("-" * 40)

        results = []
        sandbox = EphemeralSandbox(seed=f"{self.base_seed}-alpha", experiment_name="alpha")

        alphas = np.linspace(0, 1, num_samples)

        for alpha in alphas:
            result = sandbox.run_experiment({
                "test_admissibility": True,
                "alpha": float(alpha),
                "test_simplex": True,
                "dimension": 3
            }, custom_data={
                "alpha": float(alpha),
                "edge_lengths": [1.0, 1.0, 1.0],
                "triangles": [(1.0, 1.0, 1.0)]
            })

            results.append(result)

        # Analyze: find where failures start
        failures = []
        for i, r in enumerate(results):
            b1 = r.bcat_results.get("B1")
            if b1 and not b1.passed:
                failures.append((alphas[i], b1.metadata.get("min_dist", 0)))

        if failures:
            max_safe = min(f[0] for f in failures)
            print(f"  Failures start at α ≈ {max_safe:.4f}")
            print(f"  Suggested threshold: {max_safe + 0.05:.4f}")
        else:
            print("  No failures detected — threshold may be too conservative")

        self.all_results.extend(results)
        return results

    # ============================================
    # Suite 3: Confidence Monotonicity Under Contradiction
    # ============================================
    def suite_monotonicity_contradiction(self, violation_rates: List[float] = None) -> List[ExperimentResult]:
        """
        Q: Does confidence monotonicity hold when evidence is contradictory?

        Method: Inject controlled violations at different rates,
        measure I5 pass rate and confidence degradation.
        """
        if violation_rates is None:
            violation_rates = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

        print("
[SUITE 3] Confidence Monotonicity Under Contradiction")
        print("-" * 40)

        results = []
        sandbox = EphemeralSandbox(seed=f"{self.base_seed}-mono", experiment_name="monotonicity")

        for rate in violation_rates:
            result = sandbox.run_experiment({
                "test_monotonicity": True,
                "sequence_length": 50,
                "violation_prob": rate
            })

            i5 = result.gcat_results.get("I5")
            b4 = result.bcat_results.get("B4")

            i5_pass = i5.passed if i5 else False
            i5_conf = i5.confidence if i5 else 0
            cliff_rate = b4.metadata.get("cliff_rate", 0) if b4 else 0

            print(f"  Violation rate {rate:.1%}: I5_pass={i5_pass} | I5_conf={i5_conf:.3f} | Cliff_rate={cliff_rate:.1%}")

            results.append(result)

        self.all_results.extend(results)
        return results

    # ============================================
    # Suite 4: Metric Degeneracy Trigger Points
    # ============================================
    def suite_metric_degeneracy(self, dimensions: List[int] = None) -> List[ExperimentResult]:
        """
        Q: At what condition number does the metric trigger FAIL_CLOSED?

        Method: Generate metrics with increasing condition numbers,
        measure I3 and B2 behavior.
        """
        if dimensions is None:
            dimensions = [2, 3, 4, 5, 10]

        print("
[SUITE 4] Metric Degeneracy Trigger Points")
        print("-" * 40)

        results = []
        sandbox = EphemeralSandbox(seed=f"{self.base_seed}-metric", experiment_name="metric")

        for dim in dimensions:
            # Generate metrics with controlled eigenvalue spread
            for spread in [1, 10, 100, 1000, 10000, 100000, 1000000]:
                # Create metric with eigenvalues 1 and 1/spread
                eigenvalues = [1.0] + [1.0 / spread] * (dim - 1)

                # Reconstruct metric from eigenvalues
                D = np.diag(eigenvalues)
                Q = np.linalg.qr(np.random.randn(dim, dim))[0]  # Random orthogonal
                G = Q @ D @ Q.T

                result = sandbox.run_experiment({
                    "test_metric": True,
                    "dimension": dim
                }, custom_data={
                    "metric_tensor": G.tolist()
                })

                i3 = result.gcat_results.get("I3")
                b2 = result.bcat_results.get("B2")

                cond = i3.metadata.get("condition_number", 0) if i3 else 0
                i3_pass = i3.passed if i3 else False
                b2_status = b2.metadata.get("status", "N/A") if b2 else "N/A"

                print(f"  Dim={dim:2d} spread={spread:8d} cond={cond:.2e} I3={i3_pass} B2={b2_status}")

                results.append(result)

        self.all_results.extend(results)
        return results

    # ============================================
    # Suite 5: Empirical Rigel Metric Derivation
    # ============================================
    def suite_rigel_derivation(self, num_samples: int = 500) -> List[ExperimentResult]:
        """
        Q: Can we empirically derive the Rigel metric from admissibility data?

        Method: Generate many (input, confidence) pairs, fit a metric
        that makes confident inputs "close" and unconfident inputs "far".
        """
        print("
[SUITE 5] Empirical Rigel Metric Derivation")
        print("-" * 40)

        results = []
        sandbox = EphemeralSandbox(seed=f"{self.base_seed}-rigel", experiment_name="rigel")

        # Collect data points
        data_points = []

        for i in range(num_samples):
            # Random simplex
            dim = random.choice([2, 3, 4, 5])
            edges = [random.uniform(0.1, 10.0) for _ in range(dim * (dim - 1) // 2)]

            result = sandbox.run_experiment({
                "test_simplex": True,
                "dimension": dim
            }, custom_data={
                "edge_lengths": edges,
                "triangles": [(edges[j], edges[j+1], edges[j+2]) for j in range(0, len(edges)-2, 3) if j+2 < len(edges)]
            })

            # Extract confidence as "admissibility score"
            mean_conf = result.aggregate.get("mean_confidence", 0)

            data_points.append({
                "edges": edges,
                "confidence": mean_conf,
                "passed": result.aggregate.get("pass_rate", 0) > 0.5
            })

            results.append(result)

        # Simple empirical metric: weighted edge lengths
        # In formalism: G_ij = ∂²α/∂e_i∂e_j (Hessian of admissibility)
        # Empirically: Fit linear model confidence = edges · weights

        from itertools import combinations

        # Aggregate edge length statistics by confidence bin
        bins = {"high": [], "mid": [], "low": []}
        for dp in data_points:
            if dp["confidence"] > 0.7:
                bins["high"].append(dp["edges"])
            elif dp["confidence"] > 0.3:
                bins["mid"].append(dp["edges"])
            else:
                bins["low"].append(dp["edges"])

        print(f"  Data collected: {len(data_points)} points")
        print(f"  High confidence: {len(bins['high'])} | Mid: {len(bins['mid'])} | Low: {len(bins['low'])}")

        if bins["high"] and bins["low"]:
            high_mean = np.mean([np.mean(e) for e in bins["high"]])
            low_mean = np.mean([np.mean(e) for e in bins["low"]])
            print(f"  Mean edge (high conf): {high_mean:.3f}")
            print(f"  Mean edge (low conf):  {low_mean:.3f}")
            print(f"  Suggested: larger edges → higher confidence")

        self.all_results.extend(results)
        return results

    # ============================================
    # Run All Suites
    # ============================================
    def run_all(self):
        """Execute all experiment suites."""
        print("=" * 50)
        print("STEGVERSE FORMALISM EXPLORATION — ALL SUITES")
        print("=" * 50)

        self.suite_edge_collapse_convergence()
        self.suite_alpha_threshold()
        self.suite_monotonicity_contradiction()
        self.suite_metric_degeneracy()
        self.suite_rigel_derivation()

        # Final analysis
        print("
" + "=" * 50)
        print("CROSS-SUITE ANALYSIS")
        print("=" * 50)

        analysis = self._cross_suite_analysis()
        print(f"Total experiments: {len(self.all_results)}")
        print(f"Overall pass rate: {analysis['overall_pass_rate']:.1%}")
        print(f"Critical findings: {len(analysis['critical_findings'])}")

        for finding in analysis["critical_findings"][:5]:
            print(f"  - {finding}")

        # Export
        self._export_all()

    def _cross_suite_analysis(self) -> Dict[str, Any]:
        """Analyze patterns across all suites."""
        total_checks = 0
        total_passed = 0
        critical = []

        for r in self.all_results:
            agg = r.aggregate
            total_checks += agg.get("total_invariants", 0)
            total_passed += agg.get("total_passed", 0)

            for cf in agg.get("critical_failures", []):
                critical.append(f"{r.experiment_id}: {cf}")

        return {
            "overall_pass_rate": total_passed / total_checks if total_checks else 0,
            "critical_findings": critical,
            "total_experiments": len(self.all_results)
        }

    def _export_all(self):
        """Export complete results."""
        data = []
        for r in self.all_results:
            data.append({
                "experiment_id": r.experiment_id,
                "timestamp": r.timestamp,
                "seed": r.seed,
                "parameters": r.parameters,
                "aggregate": r.aggregate
            })

        with open("formalism_exploration_results.json", "w") as f:
            json.dump(data, f, indent=2)

        print(f"
Exported to formalism_exploration_results.json")


if __name__ == "__main__":
    import random
    suites = ExperimentSuites()
    suites.run_all()


    def export_results(self, filepath: str = "formalism_exploration_results.json"):
        """Public export method for CI integration."""
        data = []
        for r in self.all_results:
            data.append({
                "experiment_id": r.experiment_id,
                "timestamp": r.timestamp,
                "seed": r.seed,
                "parameters": r.parameters,
                "aggregate": r.aggregate
            })

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nExported to {filepath}")
