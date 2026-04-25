#!/usr/bin/env python3
"""Reconstruction engine with confidence and optional GCAT/BCAT alignment."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def parse_stdout_log(stdout_path: Path) -> List[Dict[str, Any]]:
    if not stdout_path.exists():
        return []

    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\$ ", text)
    parsed = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        if not lines:
            continue

        parsed.append({"command": lines[0].strip(), "output": "\n".join(lines[1:])})

    return parsed


def extract_state_transitions(blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    transitions = []

    for block in blocks:
        matches = re.findall(r"State transition:\s*(\w+)\s*->\s*(\w+)", block["output"])
        for start, end in matches:
            transitions.append({"from": start, "to": end, "source": block["command"]})

    return transitions


def extract_receipts(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    receipts = []
    seen_ids = set()

    for block in blocks:
        action_match = re.search(
            r"Action (allowed|denied):\s*(\w+).*?receipt_id['\"]?\s*:\s*['\"]?([A-F0-9]{16})",
            block["output"],
            re.DOTALL | re.IGNORECASE,
        )
        if action_match:
            rid = action_match.group(3)
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append(
                    {
                        "type": "action",
                        "decision": action_match.group(1).upper(),
                        "action": action_match.group(2),
                        "receipt_id": rid,
                        "source": block["command"],
                    }
                )
            continue

        mut_match = re.search(
            r"Mutation (allowed|denied):\s*(\w+).*?receipt_id['\"]?\s*:\s*['\"]?([A-F0-9]{16})",
            block["output"],
            re.DOTALL | re.IGNORECASE,
        )
        if mut_match:
            rid = mut_match.group(3)
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append(
                    {
                        "type": "mutation",
                        "decision": mut_match.group(1).upper(),
                        "mutation": mut_match.group(2),
                        "receipt_id": rid,
                        "source": block["command"],
                    }
                )
            continue

        listing_matches = re.findall(
            r"^\d+\.\s*(\w+)\s*\|\s*([A-F0-9]{16})\s*\|\s*prev=(\w+)\s*\|\s*decision=(\w+)",
            block["output"],
            re.MULTILINE | re.IGNORECASE,
        )
        for mutation, rid, previous, decision in listing_matches:
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append(
                    {
                        "type": "mutation_listing",
                        "mutation": mutation,
                        "receipt_id": rid,
                        "previous": previous,
                        "decision": decision.upper(),
                        "source": block["command"],
                    }
                )

    return receipts


def extract_artifact_unlocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    unlocks = []
    seen = set()

    for block in blocks:
        matches = re.findall(r"Unlocked document:\s*(\S+)", block["output"])
        for artifact in matches:
            if artifact not in seen:
                seen.add(artifact)
                unlocks.append({"artifact": artifact, "source": block["command"], "method": "transition"})

        if "explain" in block["command"]:
            initial_matches = re.findall(
                r"unlocked artifacts:\s*\n\s+-\s+(\S+)",
                block["output"],
                re.IGNORECASE,
            )
            for artifact in initial_matches:
                if artifact not in seen:
                    seen.add(artifact)
                    unlocks.append({"artifact": artifact, "source": block["command"], "method": "initial"})

    return unlocks


def extract_final_state(blocks: List[Dict[str, Any]]) -> Dict[str, str]:
    for block in blocks:
        if "demo" in block["command"]:
            final_status_match = re.search(
                r"FINAL STATUS\s*=+\s*\{[^}]*current_state['\"]?\s*:\s*['\"]?(\w+)",
                block["output"],
                re.DOTALL,
            )
            if final_status_match:
                return {"current_state": final_status_match.group(1)}

            demo_final = re.findall(r"State transition:\s*\w+\s*->\s*(\w+)", block["output"])
            if demo_final:
                return {"current_state": demo_final[-1]}

    for block in blocks:
        if "verify" in block["command"]:
            state_match = re.search(r"current_state['\"]?\s*:\s*['\"]?(\w+)", block["output"])
            if state_match:
                return {"current_state": state_match.group(1)}

    for block in reversed(blocks):
        state_match = re.search(r"current_state['\"]?\s*:\s*['\"]?(\w+)", block["output"])
        if state_match:
            return {"current_state": state_match.group(1)}

    return {}


def load_optional_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": f"Could not parse {path.name}"}


def validate_state_chain(transitions: List[Dict[str, str]]) -> Dict[str, Any]:
    if not transitions:
        return {"score": 0.0, "reason": "No state transitions found in output"}

    expected_sequence = ["state0", "state1", "state2", "state3", "state4"]
    chain = [transitions[0]["from"]] + [transition["to"] for transition in transitions]
    issues = []

    for index, (expected, actual) in enumerate(zip(expected_sequence, chain)):
        if expected != actual:
            issues.append(f"Position {index}: expected {expected}, got {actual}")

    if len(chain) != len(expected_sequence):
        issues.append(f"Chain length mismatch: expected {len(expected_sequence)}, got {len(chain)}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.25))

    return {
        "score": round(score, 4),
        "expected_chain": expected_sequence,
        "actual_chain": chain,
        "issues": issues,
        "reason": "Valid state chain" if not issues else f"{len(issues)} chain violation(s)",
    }


def validate_receipt_chain(receipts: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not receipts:
        return {"score": 0.0, "reason": "No receipts found in output"}

    issues = []
    ids = [receipt["receipt_id"] for receipt in receipts]

    if len(ids) != len(set(ids)):
        duplicates = [rid for rid in set(ids) if ids.count(rid) > 1]
        issues.append(f"Duplicate receipt IDs: {duplicates}")

    bad_format = [rid for rid in ids if not re.match(r"^[A-F0-9]{16}$", rid)]
    if bad_format:
        issues.append(f"Malformed receipt IDs: {bad_format}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.3))

    return {
        "score": round(score, 4),
        "receipt_count": len(receipts),
        "unique_ids": len(set(ids)),
        "issues": issues,
        "reason": f"{len(receipts)} valid receipts" if not issues else f"{len(issues)} receipt issue(s)",
    }


def validate_artifact_consistency(unlocks: List[Dict[str, str]]) -> Dict[str, Any]:
    if not unlocks:
        return {"score": 0.0, "reason": "No artifact unlocks found"}

    expected_artifacts = [
        "doc1_demo1.md",
        "doc2_demo2.md",
        "doc3_demo3.md",
        "doc4_demo4.md",
        "doc5_system_summary.md",
    ]
    actual = [unlock["artifact"] for unlock in unlocks]
    issues = []

    missing = [artifact for artifact in expected_artifacts if artifact not in actual]
    extra = [artifact for artifact in actual if artifact not in expected_artifacts]

    if missing:
        issues.append(f"Missing artifacts: {missing}")
    if extra:
        issues.append(f"Unexpected artifacts: {extra}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.2))

    return {
        "score": round(score, 4),
        "expected_count": len(expected_artifacts),
        "actual_count": len(set(actual)),
        "issues": issues,
        "reason": f"All {len(expected_artifacts)} artifacts unlocked"
        if not issues
        else f"{len(issues)} artifact issue(s)",
    }


def check_output_completeness(run_dir: Path, summary: Dict[str, Any]) -> Dict[str, Any]:
    commands = summary.get("commands", [])
    if not commands:
        return {"score": 0.0, "reason": "No command records in summary"}

    stdout_path = run_dir / "stdout.log"
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    issues = []

    for command in commands:
        command_text = command["command"]
        if command_text not in stdout_text:
            issues.append(f"Missing stdout for: {command_text}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.15))

    return {
        "score": round(score, 4),
        "command_count": len(commands),
        "issues": issues,
        "reason": "All outputs captured" if not issues else f"{len(issues)} completeness issue(s)",
    }


def detect_unexplained_variance(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    known_patterns = [
        r"^Runtime reset complete",
        r"^State transition:",
        r"^Action (allowed|denied):",
        r"^Mutation (allowed|denied):",
        r"^Unlocked document:",
        r"^Verifying StegVerse runtime",
        r"^Runtime verification PASSED",
        r"^StegVerse Runtime",
        r"^version: demo-suite",
        r"^current_state:",
        r"^current state:",
        r"^governed actions:",
        r"^governed mutations:",
        r"^unlocked artifacts:",
        r"^locked artifacts:",
        r"^next admissible steps:",
        r"^Causal release",
        r"^Bulk retrieval",
        r"^DEMO COMPLETE",
        r"^receipts verified:",
        r"^Causal integrity verified:",
        r"^report_\d+",
        r"^Status:",
        r"^Release state:",
        r"^\d+\.\s*\w+\s*\|",
        r"^\{",
        r"^\}",
        r"^\s*'",
        r"^\s*\[",
        r"^\s*\]",
        r"^\s*$",
        r"^={10,}",
        r"^-",
        r"^\s",
        r"^RESETTING RUNTIME",
        r"^INITIAL STATUS",
        r"^FINAL STATUS",
        r"^PRE-WORKFLOW ACTION CHECK",
        r"^PRE-WORKFLOW MUTATION CHECK",
        r"^INITIAL BULK RETRIEVAL CHECK",
        r"^POST-WORKFLOW ACTION CHECK",
        r"^POST-WORKFLOW MUTATION CHECK",
        r"^FINAL BULK RETRIEVAL CHECK",
        r"^RUNNING DEMO",
        r"^VERIFICATION",
        r"^Mutation receipt generated",
        r"^Action receipt generated",
        r"^runtime: StegVerse Runtime",
        r"^workflow states:",
        r"^documents governed:",
        r"^actions governed:",
        r"^mutations governed:",
        r"^governance model:",
        r"^documentation model:",
        r"^causal effect requires",
        r"^reports are governed",
        r"^Governed Execution",
        r"^Mutation Governance",
        r"^Capability Release",
        r"^completed steps:",
        r"^workflow receipts:",
        r"^action receipts:",
        r"^mutation receipts:",
        r"^total_receipts:",
        r"^unlocked_documents:",
        r"^StegVerse governed workflow",
        r"^StegVerse Demonstration Reports",
        r"^StegVerse Demonstration",
        r"^Expected denial:",
        r"^Action denied:",
        r"^Mutation denied:",
        r"^Causal release withheld",
        r"^Causal release granted",
        r"^Workflow receipt chain verified",
        r"^Action receipt chain verified",
        r"^Mutation receipt chain verified",
        r"^State and artifact consistency verified",
        r"^the runtime history remains",
        r"^Workflow receipts:",
        r"^Action receipts:",
        r"^Mutation receipts:",
        r"^.+: expected (ALLOW|DENY|FAIL_CLOSED), got (ALLOW|DENY|FAIL_CLOSED)",
        r"^admissibility=",
        r"^Governance Matrix:",
        r"^Random Sweep:",
        r"^Phase 1:",
        r"^Phase 2:",
    ]

    issues = []
    for block in blocks:
        for line in block["output"].splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if not any(re.match(pattern, line_stripped) for pattern in known_patterns):
                issues.append(f"Unrecognized: '{line_stripped[:80]}'")

    unique_issues = sorted(set(issues))[:10]
    score = 1.0 if not unique_issues else max(0.0, 1.0 - (len(unique_issues) * 0.1))

    return {
        "score": round(score, 4),
        "unexplained_patterns": unique_issues,
        "pattern_count": len(unique_issues),
        "reason": "No unexplained variance" if not unique_issues else f"{len(unique_issues)} unexplained pattern(s)",
        "interpretation": "All output matches known patterns."
        if score == 1.0
        else "Some output lines do not match known patterns."
        if score >= 0.8
        else "Significant unexplained variance. Recommend inspection.",
    }


def validate_admissibility_alignment(matrix: Dict[str, Any] | None, sweep: Dict[str, Any] | None) -> Dict[str, Any]:
    reports = [report for report in (matrix, sweep) if report]
    if not reports:
        return {
            "score": None,
            "available": False,
            "reason": "No GCAT/BCAT report found; admissibility alignment not evaluated.",
        }

    issues = []

    if matrix:
        if matrix.get("error"):
            issues.append(matrix["error"])
        elif not matrix.get("all_pass", False):
            issues.append("Governance matrix contains failed classifications.")

    if sweep:
        if sweep.get("error"):
            issues.append(sweep["error"])
        elif sweep.get("accuracy") != 1.0:
            issues.append(f"Random sweep accuracy below 100%: {sweep.get('accuracy')}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.4))

    return {
        "score": round(score, 4),
        "available": True,
        "issues": issues,
        "reason": "GCAT/BCAT expected decisions match observed decisions."
        if not issues
        else f"{len(issues)} admissibility alignment issue(s)",
    }


def compute_overall_confidence(axes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    weights = {
        "state_continuity": 0.22,
        "receipt_integrity": 0.18,
        "artifact_consistency": 0.13,
        "output_completeness": 0.13,
        "command_fidelity": 0.09,
        "unexplained_variance": 0.15,
    }

    admissibility_axis = axes.get("admissibility_alignment", {})
    if admissibility_axis.get("available"):
        weights["admissibility_alignment"] = 0.10

    total_weight = sum(weights.values())
    weighted_sum = 0.0

    for axis, weight in weights.items():
        score = axes.get(axis, {}).get("score")
        if score is None:
            continue
        weighted_sum += score * weight

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    unchecked = [
        "Internal SUT logic correctness beyond observed outputs",
        "Side effects outside captured stdout/stderr",
        "Cryptographic validity of receipt hashes beyond format validation",
        "Temporal ordering precision beyond available timestamps",
        "Environmental determinism across OS/Python/filesystem differences",
        "Full production GCAT/BCAT state modeling beyond the demo binding",
    ]

    return {
        "overall": round(overall, 4),
        "percentage": round(overall * 100, 2),
        "axis_weights": weights,
        "axis_scores": {
            axis: axes.get(axis, {}).get("score")
            for axis in weights
        },
        "unchecked_constraints": unchecked,
        "interpretation": "High confidence: reconstructed dataset matches original within observed boundaries."
        if overall >= 0.95
        else "Moderate confidence: observable discrepancies or missing proof surfaces detected."
        if overall >= 0.80
        else "Low confidence: significant gaps between original and reconstruction.",
    }


def reconstruct(run_dir: Path) -> Dict[str, Any]:
    summary_path = run_dir / "summary.json"
    stdout_path = run_dir / "stdout.log"

    if not summary_path.exists():
        return {"error": f"No summary.json found in {run_dir}"}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    blocks = parse_stdout_log(stdout_path)

    transitions = extract_state_transitions(blocks)
    receipts = extract_receipts(blocks)
    unlocks = extract_artifact_unlocks(blocks)
    final_state = extract_final_state(blocks)

    matrix = load_optional_json(run_dir / "matrix_report.json")
    sweep = load_optional_json(run_dir / "sweep_report.json")

    axes = {
        "state_continuity": validate_state_chain(transitions),
        "receipt_integrity": validate_receipt_chain(receipts),
        "artifact_consistency": validate_artifact_consistency(unlocks),
        "output_completeness": check_output_completeness(run_dir, summary),
        "command_fidelity": {
            "score": 1.0,
            "reason": f"{len(summary.get('commands', []))} commands recorded in summary",
        },
        "unexplained_variance": detect_unexplained_variance(blocks),
        "admissibility_alignment": validate_admissibility_alignment(matrix, sweep),
    }

    confidence = compute_overall_confidence(axes)

    return {
        "run_id": run_dir.name,
        "mode": summary.get("mode", "unknown"),
        "commit_hash": summary.get("commit_hash", "unknown"),
        "reconstruction": {
            "state_transitions": transitions,
            "receipts": receipts,
            "artifact_unlocks": unlocks,
            "final_state": final_state,
            "gcat_bcat": {
                "matrix_report": matrix,
                "sweep_report": sweep,
            },
        },
        "confidence": confidence,
        "axes": axes,
    }


def write_reconstruction_report(run_dir: Path, data: Dict[str, Any]) -> Path:
    report_path = run_dir / "reconstruction.md"

    lines = [
        "# Reconstruction & Confidence Analysis",
        "",
        f"**Run:** {data['run_id']}",
        f"**Mode:** {data['mode']}",
        f"**Commit:** `{data['commit_hash']}`",
        "",
        "---",
        "",
        "## What This Measures",
        "",
        "The confidence score answers one question:",
        "",
        "> Based only on observable evidence, how completely were we able to reconstruct the original finished test path?",
        "",
        "With GCAT/BCAT reports available, reconstruction also checks whether observed decisions align with the formal admissibility classification.",
        "",
        "---",
        "",
        f"## Overall Confidence: {data['confidence']['percentage']}%",
        "",
        f"*{data['confidence']['interpretation']}*",
        "",
        "### Axis Breakdown",
        "",
        "| Axis | Weight | Score | Status |",
        "|------|--------|-------|--------|",
    ]

    for axis, weight in data["confidence"]["axis_weights"].items():
        axis_data = data["axes"][axis]
        score = axis_data.get("score")
        reason = axis_data.get("reason", "")
        if score is None:
            score_text = "N/A"
            status = "N/A"
        else:
            score_text = f"{score:.0%}"
            status = "PASS" if score >= 0.95 else "WARN" if score >= 0.80 else "FAIL"
        lines.append(f"| {axis} | {weight:.0%} | {score_text} | {status} — {reason} |")

    rec = data["reconstruction"]

    lines.extend(["", "---", "", "## Reconstructed Timeline", ""])

    if rec["state_transitions"]:
        lines.append("### State Transitions")
        for transition in rec["state_transitions"]:
            lines.append(f"- `{transition['from']}` → `{transition['to']}` via `{transition['source']}`")
        lines.append("")

    if rec["receipts"]:
        lines.append("### Receipts")
        for receipt in rec["receipts"]:
            name = receipt.get("action") or receipt.get("mutation", "unknown")
            lines.append(f"- `{receipt['receipt_id']}` | {receipt['type']}:{name} | {receipt['decision']}")
        lines.append("")

    if rec["artifact_unlocks"]:
        lines.append("### Artifact Unlocks")
        for unlock in rec["artifact_unlocks"]:
            lines.append(f"- `{unlock['artifact']}` via `{unlock['source']}` ({unlock['method']})")
        lines.append("")

    if rec["final_state"]:
        lines.append("### Final State")
        lines.append(f"- `{rec['final_state'].get('current_state', 'unknown')}`")
        lines.append("")

    lines.extend(["---", "", "## GCAT/BCAT Admissibility", ""])

    admissibility_axis = data["axes"]["admissibility_alignment"]
    lines.append(admissibility_axis["reason"])
    lines.append("")

    matrix = rec["gcat_bcat"].get("matrix_report")
    if matrix and not matrix.get("error"):
        lines.append("### Governance Matrix")
        lines.append("")
        lines.append("| Action | Expected | Actual | Admissibility | I(x') | Result |")
        lines.append("|--------|----------|--------|---------------|-------|--------|")
        for case in matrix.get("cases", []):
            admissibility = case.get("admissibility", {})
            result = "PASS" if case.get("pass") else "FAIL"
            lines.append(
                f"| `{case.get('action')}` | {case.get('expected')} | {case.get('actual')} | "
                f"{admissibility.get('admissibility')} | {admissibility.get('invariant')} | {result} |"
            )
        lines.append("")

    sweep = rec["gcat_bcat"].get("sweep_report")
    if sweep and not sweep.get("error"):
        lines.append("### Random Sweep")
        lines.append("")
        lines.append(f"- Seed: `{sweep.get('seed')}`")
        lines.append(f"- Samples per phase: `{sweep.get('samples_per_phase')}`")
        lines.append(f"- Accuracy: `{sweep.get('accuracy')}`")
        lines.append(f"- Correct classifications: `{sweep.get('correct_classifications')}/{sweep.get('total_samples')}`")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Unchecked Constraints",
            "",
            "The following were **not** verified and limit the scope of this confidence score:",
            "",
        ]
    )

    for constraint in data["confidence"]["unchecked_constraints"]:
        lines.append(f"- {constraint}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Interpretation",
            "",
            "At 100%, the reconstructed path matches the observed finished test path within the chosen evidence boundary.",
            "",
            "Below 100%, the gap is interpreted as:",
            "",
            "```text",
            "known degraded reconstruction parameters",
            "+",
            "unknown or unexplained transition effects",
            "+",
            "admissibility uncertainty, when GCAT/BCAT data is missing or inconsistent",
            "=",
            "gap to complete reconstruction",
            "```",
            "",
            "ALLOW, DENY, and FAIL_CLOSED are all meaningful outcomes. A denial is a recorded boundary enforcement event, not an absence of system behavior.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python reconstruct.py <run_dir>")
        return 1

    run_dir = Path(sys.argv[1])
    data = reconstruct(run_dir)

    if "error" in data:
        print(f"Error: {data['error']}")
        return 1

    report_path = write_reconstruction_report(run_dir, data)
    json_path = run_dir / "reconstruction.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Reconstruction report: {report_path}")
    print(f"Reconstruction data: {json_path}")
    print(f"Overall confidence: {data['confidence']['percentage']}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
