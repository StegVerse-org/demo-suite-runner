"""
ephemeral_sandbox.py
Ephemeral sandbox for experimental formalism exploration.

Design:
  - Each run creates an isolated, temporary environment
  - All state is discarded after run (ephemeral)
  - Data is collected and exported for formalism refinement
  - No persistence = no contamination between experiments
  - Deterministic when seeded, random when unseeded

Use cases:
  1. Parameter sweep: Test invariant thresholds empirically
  2. Edge case discovery: Find where formalism breaks
  3. Statistical validation: Confirm theoretical predictions
  4. Benchmark generation: Produce paper-ready tables
"""

import os
import json
import time
import random
import tempfile
import shutil
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

from gcat_invariants import GCATInvariants, InvariantResult
from bcat_invariants import BCATInvariants


@dataclass
class ExperimentResult:
    experiment_id: str
    timestamp: str
    seed: str
    parameters: Dict[str, Any]
    gcat_results: Dict[str, InvariantResult]
    bcat_results: Dict[str, InvariantResult]
    aggregate: Dict[str, Any]
    artifacts: Dict[str, Any]


class EphemeralSandbox:
    """
    Ephemeral sandbox for safe, isolated experimentation.

    Each experiment:
      1. Creates temp directory
      2. Runs GCAT + BCAT invariants
      3. Collects metadata
      4. Exports results
      5. Destroys temp directory

    Nothing persists. Everything is logged.
    """

    def __init__(
        self,
        seed: Optional[str] = None,
        experiment_name: str = "unnamed",
        collect_artifacts: bool = True
    ):
        self.seed = seed or self._generate_seed()
        self.experiment_name = experiment_name
        self.collect_artifacts = collect_artifacts
        self.gcat = GCATInvariants()
        self.bcat = BCATInvariants()
        self.results: List[ExperimentResult] = []

        # Set deterministic state
        random.seed(self.seed)
        np.random.seed(int(self.seed[:8], 16) % (2**32))

    def _generate_seed(self) -> str:
        return hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16]

    def create_isolated_env(self) -> str:
        """Create temporary isolated directory."""
        temp_dir = tempfile.mkdtemp(prefix=f"stegverse_sandbox_{self.experiment_name}_")

        # Create substructure
        os.makedirs(os.path.join(temp_dir, "inputs"))
        os.makedirs(os.path.join(temp_dir, "outputs"))
        os.makedirs(os.path.join(temp_dir, "logs"))

        return temp_dir

    def destroy_env(self, temp_dir: str):
        """Destroy temporary environment."""
        shutil.rmtree(temp_dir, ignore_errors=True)

    # ============================================
    # Experiment Generators
    # ============================================
    def generate_simplex_data(
        self,
        dimension: int = 3,
        edge_range: Tuple[float, float] = (0.001, 10.0),
        collapse_probability: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate random simplex data for I1/I2/B3 testing.

        Args:
            dimension: Simplex dimension (3 = triangle, 4 = tetrahedron)
            edge_range: (min, max) edge lengths
            collapse_probability: Chance of near-zero edges
        """
        num_edges = dimension * (dimension - 1) // 2

        edges = []
        for _ in range(num_edges):
            if random.random() < collapse_probability:
                # Near-collapse edge
                edge = random.uniform(0.0, 0.0001)
            else:
                edge = random.uniform(*edge_range)
            edges.append(edge)

        # Generate triangles (combinations of 3 edges)
        triangles = []
        for i in range(0, len(edges) - 2, 3):
            if i + 2 < len(edges):
                triangles.append((edges[i], edges[i+1], edges[i+2]))

        return {
            "edge_lengths": edges,
            "triangles": triangles,
            "dimension": dimension
        }

    def generate_metric_data(
        self,
        dimension: int = 3,
        positive_definite: bool = True,
        near_singular: bool = False
    ) -> Dict[str, Any]:
        """
        Generate metric tensor for I3/B2 testing.

        Args:
            positive_definite: Force positive-definite
            near_singular: Make near-degenerate
        """
        if positive_definite:
            # Generate random positive-definite matrix
            A = np.random.randn(dimension, dimension)
            G = A @ A.T  # Always positive semi-definite

            if near_singular:
                # Make one eigenvalue very small
                eigenvalues, eigenvectors = np.linalg.eigh(G)
                eigenvalues[0] = 1e-12  # Near-zero
                G = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
        else:
            # Random matrix (may not be positive-definite)
            G = np.random.randn(dimension, dimension)

        return {"metric_tensor": G.tolist()}

    def generate_admissibility_data(
        self,
        alpha: Optional[float] = None,
        boundary_proximity: Optional[str] = None  # "none", "warning", "danger"
    ) -> Dict[str, Any]:
        """
        Generate admissibility scalar for I4/B1 testing.

        Args:
            alpha: Fixed value, or None for random
            boundary_proximity: Force near-boundary
        """
        if alpha is not None:
            return {"alpha": alpha}

        if boundary_proximity == "danger":
            alpha = random.choice([0.0, 1.0]) + random.uniform(-1e-6, 1e-6)
        elif boundary_proximity == "warning":
            alpha = random.choice([0.0, 1.0]) + random.uniform(0.01, 0.1)
        else:
            alpha = random.uniform(0.1, 0.9)

        return {"alpha": alpha}

    def generate_monotonicity_data(
        self,
        length: int = 10,
        violation_probability: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate evidence/confidence sequences for I5/B4 testing.

        Args:
            length: Sequence length
            violation_probability: Chance of monotonicity violation
        """
        evidence = [random.uniform(0, 1) for _ in range(length)]
        evidence.sort()  # Monotonic by default

        confidence = []
        for i, e in enumerate(evidence):
            base_conf = e * 0.8 + 0.1  # Linear-ish mapping

            if random.random() < violation_probability and i > 0:
                # Inject violation: lower confidence despite higher evidence
                base_conf = confidence[-1] - random.uniform(0.1, 0.3)
                base_conf = max(0, base_conf)

            confidence.append(base_conf)

        return {
            "evidence_sequence": evidence,
            "confidence_sequence": confidence
        }

    def generate_irreversibility_data(
        self,
        num_actions: int = 10,
        saturation_probability: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate action history for I6/B5 testing.

        Args:
            num_actions: Number of actions
            saturation_probability: Chance of near-max irreversibility
        """
        actions = []
        scores = []

        for i in range(num_actions):
            action = {
                "id": i,
                "type": random.choice(["read", "write", "delete", "admin"]),
                "timestamp": time.time_ns(),
                "context": {"session": random.randint(1, 5)}
            }

            if random.random() < saturation_probability:
                score = 0.99 + random.uniform(0, 0.01)
            else:
                score = random.uniform(0.1, 0.8)

            actions.append(action)
            scores.append(score)

        return {
            "action_history": actions,
            "irreversibility_scores": scores
        }

    # ============================================
    # Run Experiment
    # ============================================
    def run_experiment(
        self,
        parameters: Dict[str, Any],
        custom_data: Optional[Dict[str, Any]] = None
    ) -> ExperimentResult:
        """
        Run single ephemeral experiment.

        Args:
            parameters: Experiment configuration
            custom_data: Override generated data

        Returns:
            ExperimentResult with all invariant checks
        """
        temp_dir = self.create_isolated_env()
        experiment_id = f"EXP-{self.experiment_name}-{int(time.time())}"

        try:
            # Generate or use custom test data
            if custom_data:
                test_data = custom_data
            else:
                test_data = self._generate_test_data(parameters)

            # Save inputs (ephemeral — will be destroyed)
            with open(os.path.join(temp_dir, "inputs", "test_data.json"), "w") as f:
                json.dump(test_data, f, indent=2)

            # Run GCAT invariants
            gcat_results = self.gcat.evaluate_all(test_data)

            # Run BCAT invariants (needs history for B6)
            history = test_data.get("action_history", [])
            bcat_results = self.bcat.evaluate_all(test_data, history)

            # Aggregate
            aggregate = self._aggregate_results(gcat_results, bcat_results)

            # Collect artifacts
            artifacts = {}
            if self.collect_artifacts:
                artifacts = {
                    "gcat_metadata": {k: v.metadata for k, v in gcat_results.items()},
                    "bcat_metadata": {k: v.metadata for k, v in bcat_results.items()},
                    "parameter_hash": hashlib.sha256(str(parameters).encode()).hexdigest()[:16]
                }

            result = ExperimentResult(
                experiment_id=experiment_id,
                timestamp=datetime.now().isoformat(),
                seed=self.seed,
                parameters=parameters,
                gcat_results=gcat_results,
                bcat_results=bcat_results,
                aggregate=aggregate,
                artifacts=artifacts
            )

            self.results.append(result)
            return result

        finally:
            # ALWAYS destroy — ephemeral guarantee
            self.destroy_env(temp_dir)

    def _generate_test_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test data based on experiment parameters."""
        data = {}

        if parameters.get("test_simplex", False):
            data.update(self.generate_simplex_data(
                dimension=parameters.get("dimension", 3),
                collapse_probability=parameters.get("collapse_prob", 0.1)
            ))

        if parameters.get("test_metric", False):
            data.update(self.generate_metric_data(
                dimension=parameters.get("dimension", 3),
                positive_definite=parameters.get("positive_definite", True),
                near_singular=parameters.get("near_singular", False)
            ))

        if parameters.get("test_admissibility", False):
            data.update(self.generate_admissibility_data(
                boundary_proximity=parameters.get("boundary_proximity", "none")
            ))

        if parameters.get("test_monotonicity", False):
            data.update(self.generate_monotonicity_data(
                length=parameters.get("sequence_length", 10),
                violation_probability=parameters.get("violation_prob", 0.0)
            ))

        if parameters.get("test_irreversibility", False):
            data.update(self.generate_irreversibility_data(
                num_actions=parameters.get("num_actions", 10),
                saturation_probability=parameters.get("saturation_prob", 0.0)
            ))

        return data

    def _aggregate_results(
        self,
        gcat: Dict[str, InvariantResult],
        bcat: Dict[str, InvariantResult]
    ) -> Dict[str, Any]:
        """Aggregate GCAT + BCAT results."""
        all_results = list(gcat.values()) + list(bcat.values())

        passed = sum(1 for r in all_results if r.passed)
        total = len(all_results)

        gcat_passed = sum(1 for r in gcat.values() if r.passed)
        bcat_passed = sum(1 for r in bcat.values() if r.passed)

        return {
            "total_invariants": total,
            "total_passed": passed,
            "total_failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "gcat_pass_rate": gcat_passed / len(gcat) if gcat else 0,
            "bcat_pass_rate": bcat_passed / len(bcat) if bcat else 0,
            "mean_confidence": sum(r.confidence for r in all_results) / len(all_results) if all_results else 0,
            "min_confidence": min(r.confidence for r in all_results) if all_results else 0,
            "critical_failures": [
                r.name for r in all_results 
                if not r.passed and r.name.startswith(("I3", "I6", "B2", "B5"))
            ]
        }

    # ============================================
    # Batch Experiments
    # ============================================
    def run_parameter_sweep(
        self,
        parameter_grid: Dict[str, List[Any]],
        num_runs_per_config: int = 5
    ) -> List[ExperimentResult]:
        """
        Run parameter sweep across configuration grid.

        Args:
            parameter_grid: {param_name: [values]}
            num_runs_per_config: Replicates per configuration

        Returns:
            All experiment results
        """
        from itertools import product

        keys = list(parameter_grid.keys())
        values = list(parameter_grid.values())

        all_results = []

        for config_values in product(*values):
            config = dict(zip(keys, config_values))

            for run in range(num_runs_per_config):
                # New seed per run
                self.seed = self._generate_seed()
                random.seed(self.seed)
                np.random.seed(int(self.seed[:8], 16) % (2**32))

                result = self.run_experiment(config)
                all_results.append(result)

        return all_results

    # ============================================
    # Export & Analysis
    # ============================================
    def export_results(self, filepath: str):
        """Export all experiment results to JSON."""
        data = []
        for r in self.results:
            data.append({
                "experiment_id": r.experiment_id,
                "timestamp": r.timestamp,
                "seed": r.seed,
                "parameters": r.parameters,
                "gcat_summary": {k: {"passed": v.passed, "confidence": v.confidence, "reasoning": v.reasoning} 
                                for k, v in r.gcat_results.items()},
                "bcat_summary": {k: {"passed": v.passed, "confidence": v.confidence, "reasoning": v.reasoning}
                                for k, v in r.bcat_results.items()},
                "aggregate": r.aggregate,
                "artifacts": r.artifacts
            })

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Exported {len(self.results)} experiments to {filepath}")

    def analyze_for_formalism(self) -> Dict[str, Any]:
        """
        Analyze all experimental data for formalism refinement.

        Returns insights for paper writing:
          - Optimal thresholds
          - Edge case patterns
          - Statistical validation of theoretical claims
        """
        if not self.results:
            return {}

        # Collect all metadata
        all_metadata = []
        for r in self.results:
            for inv in r.gcat_results.values():
                all_metadata.append({
                    "experiment_id": r.experiment_id,
                    "invariant": inv.name,
                    "passed": inv.passed,
                    "confidence": inv.confidence,
                    **inv.metadata
                })
            for inv in r.bcat_results.values():
                all_metadata.append({
                    "experiment_id": r.experiment_id,
                    "invariant": inv.name,
                    "passed": inv.passed,
                    "confidence": inv.confidence,
                    **inv.metadata
                })

        # Analysis
        analysis = {
            "total_experiments": len(self.results),
            "total_invariant_checks": len(all_metadata),
            "pass_rate_by_invariant": self._pass_rate_by_invariant(all_metadata),
            "threshold_optimization": self._optimize_thresholds(all_metadata),
            "edge_case_summary": self._find_edge_cases(all_metadata),
            "confidence_distributions": self._confidence_distributions(all_metadata),
            "recommended_formalism_changes": self._recommend_changes(all_metadata)
        }

        return analysis

    def _pass_rate_by_invariant(self, metadata: List[Dict]) -> Dict[str, float]:
        from collections import defaultdict
        counts = defaultdict(lambda: {"passed": 0, "total": 0})
        for m in metadata:
            counts[m["invariant"]]["total"] += 1
            if m["passed"]:
                counts[m["invariant"]]["passed"] += 1
        return {k: v["passed"] / v["total"] for k, v in counts.items()}

    def _optimize_thresholds(self, metadata: List[Dict]) -> Dict[str, Any]:
        """Suggest optimal thresholds based on data."""
        # Example: Find alpha boundary that maximizes safety
        alpha_data = [m for m in metadata if "alpha" in m]
        if not alpha_data:
            return {}

        alphas = [m["alpha"] for m in alpha_data]
        failures = [m for m in alpha_data if not m["passed"]]

        if failures:
            failure_alphas = [m["alpha"] for m in failures]
            suggested_boundary = max(failure_alphas) + 0.05
        else:
            suggested_boundary = 0.1

        return {
            "alpha_boundary_suggestion": suggested_boundary,
            "alpha_range_observed": (min(alphas), max(alphas)),
            "alpha_failure_rate": len(failures) / len(alpha_data)
        }

    def _find_edge_cases(self, metadata: List[Dict]) -> List[Dict[str, Any]]:
        """Identify edge cases where formalism breaks."""
        edge_cases = []

        for m in metadata:
            if not m["passed"]:
                # Check if it's a "near miss" (high confidence but failed)
                if m.get("confidence", 0) > 0.5:
                    edge_cases.append({
                        "invariant": m["invariant"],
                        "confidence": m["confidence"],
                        "parameters": {k: v for k, v in m.items() if k not in ["experiment_id", "invariant", "passed", "confidence"]},
                        "type": "near_miss"
                    })

        return edge_cases[:20]  # Limit output

    def _confidence_distributions(self, metadata: List[Dict]) -> Dict[str, Any]:
        by_invariant = {}
        for m in metadata:
            inv = m["invariant"]
            by_invariant.setdefault(inv, []).append(m["confidence"])

        return {
            inv: {
                "mean": sum(vals) / len(vals),
                "min": min(vals),
                "max": max(vals),
                "count": len(vals)
            }
            for inv, vals in by_invariant.items()
        }

    def _recommend_changes(self, metadata: List[Dict]) -> List[str]:
        """Generate recommendations for formalism refinement."""
        recommendations = []

        # Check if any invariant is always passing or always failing
        pass_rates = self._pass_rate_by_invariant(metadata)
        for inv, rate in pass_rates.items():
            if rate == 1.0:
                recommendations.append(f"{inv}: Always passes — may be too lenient or test data too easy")
            elif rate == 0.0:
                recommendations.append(f"{inv}: Always fails — may be too strict or test data too hard")
            elif rate < 0.3:
                recommendations.append(f"{inv}: Low pass rate ({rate:.1%}) — review threshold or formal definition")

        return recommendations


def main():
    """Example usage of ephemeral sandbox."""

    # Experiment 1: Simple edge collapse exploration
    print("=" * 50)
    print("EXPERIMENT 1: Edge Collapse Formalism")
    print("=" * 50)

    sandbox = EphemeralSandbox(
        seed="edge-collapse-test-001",
        experiment_name="edge_collapse"
    )

    result = sandbox.run_experiment({
        "test_simplex": True,
        "dimension": 3,
        "collapse_prob": 0.3,
        "test_metric": True,
        "near_singular": True
    })

    print(f"Experiment: {result.experiment_id}")
    print(f"Pass rate: {result.aggregate['pass_rate']:.1%}")
    print(f"Critical failures: {result.aggregate['critical_failures']}")

    # Experiment 2: Parameter sweep for alpha boundaries
    print("
" + "=" * 50)
    print("EXPERIMENT 2: Alpha Boundary Sweep")
    print("=" * 50)

    sweep_results = sandbox.run_parameter_sweep({
        "test_admissibility": [True],
        "boundary_proximity": ["none", "warning", "danger"],
        "test_simplex": [True],
        "dimension": [3, 4, 5]
    }, num_runs_per_config=3)

    print(f"Sweep completed: {len(sweep_results)} total experiments")

    # Analysis
    analysis = sandbox.analyze_for_formalism()
    print(f"
Formalism Analysis:")
    print(f"  Total experiments: {analysis['total_experiments']}")
    print(f"  Pass rates: {analysis.get('pass_rate_by_invariant', {})}")
    print(f"  Recommendations: {analysis.get('recommended_formalism_changes', [])}")

    # Export
    sandbox.export_results("sandbox_results.json")


if __name__ == "__main__":
    main()
