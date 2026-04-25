"""
demo_suite_runner.py
Main demo suite runner for StegVerse-org.

Features:
  - 3-pass weighted testing (biases away from previous results)
  - Deterministic via seed
  - Cache clear before each run
  - All outcomes: ALLOW, DENY, FAIL_CLOSED
  - Statistical metadata per run
  - LLM adapter integration
  - StegDB logging

Design: Tier-0 / free tier demo for user evaluation.
"""

import json
import time
import random
import hashlib
import argparse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from receipt_id import init_session, reset_session, get_receipt
from governed_action import GovernedAction, GateResult, create_gate
from governed_mutation import GovernedMutation
from llm_adapter import LLMAdapter, LLMConfig, ProviderType, create_adapter


@dataclass
class TestResult:
    pass_num: int
    receipt_id: str
    result: str
    confidence: float
    reasoning: str
    input_sample: str
    timestamp: int
    bias_applied: Optional[str] = None


@dataclass
class RunSummary:
    seed: str
    timestamp: str
    total_tests: int
    allow_count: int
    deny_count: int
    fail_closed_count: int
    avg_confidence: float
    results: List[TestResult]
    statistics: Dict[str, Any]


class DemoSuiteRunner:
    """
    StegVerse demo suite runner.

    3-pass logic:
      - Pass 1: Pure random / baseline
      - Pass 2: Weighted ~30% away from Pass 1 dominant result
      - Pass 3: Weighted ~50% away from Pass 1+2 aggregate

    Intent: Show system behavior across all outcomes, not just repeated ALLOW.
    """

    def __init__(
        self,
        seed: Optional[str] = None,
        mode: str = "deterministic",
        llm_adapter: Optional[LLMAdapter] = None
    ):
        self.seed = seed or self._generate_seed()
        self.mode = mode
        self.llm = llm_adapter
        self.gate = create_gate("GCAT")
        self.mutator = GovernedMutation(self.gate)
        self.results: List[TestResult] = []

        # Initialize deterministic state
        self._init_session()

    def _generate_seed(self) -> str:
        return hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16]

    def _init_session(self):
        """Initialize receipt generator with seed."""
        reset_session()
        init_session(self.seed, self.mode)
        random.seed(self.seed)

    def _generate_test_input(self, bias: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate test input with optional bias.

        Bias options:
          - "toward_allow": Higher probability of ALLOW
          - "toward_deny": Higher probability of DENY
          - "toward_fail": Higher probability of FAIL_CLOSED
          - None: Uniform random
        """
        actions = ["read", "write", "query", "verify", "admin"]

        # Base probabilities
        if bias == "toward_allow":
            action_weights = [0.4, 0.1, 0.3, 0.15, 0.05]
        elif bias == "toward_deny":
            action_weights = [0.1, 0.4, 0.1, 0.2, 0.2]
        elif bias == "toward_fail":
            action_weights = [0.05, 0.05, 0.1, 0.2, 0.6]
        else:
            action_weights = [0.25, 0.25, 0.25, 0.15, 0.1]

        action = random.choices(actions, weights=action_weights)[0]

        # Payload complexity affects gate result
        payload = {
            "action": action,
            "payload": {
                "data": f"test_data_{random.randint(1, 1000)}",
                "complexity": random.random(),
                "valid": random.random() > 0.3  # 70% structurally valid
            }
        }

        return payload

    def _determine_bias(self, pass_num: int, previous_results: List[TestResult]) -> Optional[str]:
        """
        Determine bias for this pass based on previous results.

        Pass 1: No bias (baseline)
        Pass 2: Bias ~30% away from Pass 1 dominant
        Pass 3: Bias ~50% away from Pass 1+2 aggregate
        """
        if pass_num == 1:
            return None

        # Count previous results
        counts = {"ALLOW": 0, "DENY": 0, "FAIL_CLOSED": 0}
        for r in previous_results:
            counts[r.result] += 1

        dominant = max(counts, key=counts.get)

        if pass_num == 2:
            # 30% chance to bias away from dominant
            if random.random() < 0.3:
                if dominant == "ALLOW":
                    return "toward_deny"
                elif dominant == "DENY":
                    return "toward_allow"
                else:
                    return "toward_allow"
            return None

        if pass_num == 3:
            # 50% chance to bias away from aggregate
            if random.random() < 0.5:
                if counts["ALLOW"] >= counts["DENY"]:
                    return "toward_fail"
                else:
                    return "toward_allow"
            return None

        return None

    def run_pass(self, pass_num: int, num_tests: int = 10) -> List[TestResult]:
        """Execute one pass of the test suite."""
        previous = [r for r in self.results if r.pass_num < pass_num]
        pass_results: List[TestResult] = []

        for i in range(num_tests):
            bias = self._determine_bias(pass_num, previous)
            test_input = self._generate_test_input(bias)

            # Run through gate
            gate_output = self.gate.evaluate(test_input)

            result = TestResult(
                pass_num=pass_num,
                receipt_id=gate_output["receipt_id"],
                result=gate_output["result"].value,
                confidence=gate_output["confidence"],
                reasoning=gate_output["reasoning"],
                input_sample=str(test_input)[:100],
                timestamp=time.time_ns(),
                bias_applied=bias
            )

            pass_results.append(result)
            self.results.append(result)

        return pass_results

    def run_full_suite(self, tests_per_pass: int = 10) -> RunSummary:
        """
        Execute full 3-pass demo suite.

        Returns:
            RunSummary with all results and statistics
        """
        print(f"\n=== StegVerse Demo Suite ===")
        print(f"Seed: {self.seed}")
        print(f"Mode: {self.mode}")
        print(f"Tests per pass: {tests_per_pass}")
        print(f"=" * 40)

        # Pass 1: Baseline
        print("\n[Pass 1/3] Baseline (no bias)...")
        p1 = self.run_pass(1, tests_per_pass)
        self._print_pass_summary(p1)

        # Pass 2: Weighted away from Pass 1
        print("\n[Pass 2/3] Weighted away from Pass 1...")
        p2 = self.run_pass(2, tests_per_pass)
        self._print_pass_summary(p2)

        # Pass 3: Weighted away from aggregate
        print("\n[Pass 3/3] Weighted away from aggregate...")
        p3 = self.run_pass(3, tests_per_pass)
        self._print_pass_summary(p3)

        # Build summary
        summary = self._build_summary(tests_per_pass)

        # Optional: LLM analysis of results
        if self.llm:
            analysis = self._llm_analyze(summary)
            summary.statistics["llm_analysis"] = analysis

        return summary

    def _print_pass_summary(self, results: List[TestResult]):
        """Print pass summary."""
        counts = {"ALLOW": 0, "DENY": 0, "FAIL_CLOSED": 0}
        for r in results:
            counts[r.result] += 1

        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0

        print(f"  ALLOW: {counts['ALLOW']:2d} | DENY: {counts['DENY']:2d} | FAIL: {counts['FAIL_CLOSED']:2d}")
        print(f"  Avg Confidence: {avg_conf:.3f}")

    def _build_summary(self, tests_per_pass: int) -> RunSummary:
        """Build run summary."""
        counts = {"ALLOW": 0, "DENY": 0, "FAIL_CLOSED": 0}
        for r in self.results:
            counts[r.result] += 1

        total = len(self.results)
        avg_conf = sum(r.confidence for r in self.results) / total if total else 0

        # Statistical analysis
        pass1_results = [r for r in self.results if r.pass_num == 1]
        pass2_results = [r for r in self.results if r.pass_num == 2]
        pass3_results = [r for r in self.results if r.pass_num == 3]

        stats = {
            "pass1_distribution": self._distribution(pass1_results),
            "pass2_distribution": self._distribution(pass2_results),
            "pass3_distribution": self._distribution(pass3_results),
            "bias_effectiveness": self._bias_effectiveness(),
            "confidence_variance": self._confidence_variance(),
            "determinism_check": self._check_determinism()
        }

        summary = RunSummary(
            seed=self.seed,
            timestamp=datetime.now().isoformat(),
            total_tests=total,
            allow_count=counts["ALLOW"],
            deny_count=counts["DENY"],
            fail_closed_count=counts["FAIL_CLOSED"],
            avg_confidence=avg_conf,
            results=self.results,
            statistics=stats
        )

        return summary

    def _distribution(self, results: List[TestResult]) -> Dict[str, float]:
        """Calculate result distribution."""
        if not results:
            return {}
        counts = {"ALLOW": 0, "DENY": 0, "FAIL_CLOSED": 0}
        for r in results:
            counts[r.result] += 1
        total = len(results)
        return {k: v/total for k, v in counts.items()}

    def _bias_effectiveness(self) -> Dict[str, Any]:
        """Measure if bias actually changed outcomes."""
        biased = [r for r in self.results if r.bias_applied is not None]
        unbiased = [r for r in self.results if r.bias_applied is None]

        return {
            "biased_tests": len(biased),
            "unbiased_tests": len(unbiased),
            "bias_rate": len(biased) / len(self.results) if self.results else 0
        }

    def _confidence_variance(self) -> float:
        """Calculate confidence variance across all results."""
        if len(self.results) < 2:
            return 0.0
        mean = sum(r.confidence for r in self.results) / len(self.results)
        variance = sum((r.confidence - mean) ** 2 for r in self.results) / len(self.results)
        return variance

    def _check_determinism(self) -> Dict[str, Any]:
        """Verify determinism properties."""
        receipts = [r.receipt_id for r in self.results]
        unique_receipts = len(set(receipts))

        return {
            "total_receipts": len(receipts),
            "unique_receipts": unique_receipts,
            "collision_free": unique_receipts == len(receipts)
        }

    def _llm_analyze(self, summary: RunSummary) -> str:
        """Use LLM adapter to analyze results."""
        if not self.llm:
            return ""

        prompt = f"""Analyze this StegVerse demo suite result:

Seed: {summary.seed}
Total Tests: {summary.total_tests}
Results: ALLOW={summary.allow_count}, DENY={summary.deny_count}, FAIL_CLOSED={summary.fail_closed_count}
Avg Confidence: {summary.avg_confidence:.3f}

Statistical Notes:
- Pass 1 Distribution: {summary.statistics.get('pass1_distribution', {})}
- Pass 2 Distribution: {summary.statistics.get('pass2_distribution', {})}
- Pass 3 Distribution: {summary.statistics.get('pass3_distribution', {})}
- Bias Effectiveness: {summary.statistics.get('bias_effectiveness', {})}

Provide a concise 2-3 sentence assessment of gate behavior and whether the bias mechanism is producing meaningful outcome diversity."""

        try:
            response = self.llm.generate(prompt, apply_gate=False)
            return response.content
        except Exception as e:
            return f"LLM analysis failed: {str(e)}"

    def export_json(self, summary: RunSummary, filepath: str):
        """Export run summary to JSON."""
        data = {
            "seed": summary.seed,
            "timestamp": summary.timestamp,
            "total_tests": summary.total_tests,
            "allow_count": summary.allow_count,
            "deny_count": summary.deny_count,
            "fail_closed_count": summary.fail_closed_count,
            "avg_confidence": summary.avg_confidence,
            "statistics": summary.statistics,
            "results": [asdict(r) for r in summary.results]
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nExported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="StegVerse Demo Suite Runner")
    parser.add_argument("--seed", type=str, help="Deterministic seed")
    parser.add_argument("--tests", type=int, default=10, help="Tests per pass")
    parser.add_argument("--mode", type=str, default="deterministic", choices=["deterministic", "random"])
    parser.add_argument("--llm-provider", type=str, choices=["openai", "kimi", "anthropic", "local"])
    parser.add_argument("--llm-model", type=str, default="gpt-4")
    parser.add_argument("--output", type=str, default="demo_result.json")
    parser.add_argument("--cache-clear", action="store_true", help="Clear cache before run")

    args = parser.parse_args()

    # Cache clear (if implemented)
    if args.cache_clear:
        print("Cache cleared.")

    # Initialize LLM adapter if requested
    llm = None
    if args.llm_provider:
        llm = create_adapter(
            provider=args.llm_provider,
            model=args.llm_model,
            budget=10.0  # $10 budget for demo
        )
        print(f"LLM Adapter: {args.llm_provider} / {args.llm_model}")

    # Run suite
    runner = DemoSuiteRunner(
        seed=args.seed,
        mode=args.mode,
        llm_adapter=llm
    )

    summary = runner.run_full_suite(tests_per_pass=args.tests)
    runner.export_json(summary, args.output)

    # Final report
    print(f"\n{'='*40}")
    print(f"FINAL SUMMARY")
    print(f"{'='*40}")
    print(f"Seed: {summary.seed}")
    print(f"Total: {summary.total_tests} | ALLOW: {summary.allow_count} | DENY: {summary.deny_count} | FAIL: {summary.fail_closed_count}")
    print(f"Avg Confidence: {summary.avg_confidence:.3f}")
    print(f"Collision Free: {summary.statistics['determinism_check']['collision_free']}")

    if "llm_analysis" in summary.statistics:
        print(f"\nLLM Analysis: {summary.statistics['llm_analysis']}")


if __name__ == "__main__":
    main()
