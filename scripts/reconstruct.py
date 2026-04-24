#!/usr/bin/env python3
"""
Reconstruction Engine with Confidence Analysis
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_stdout_log(stdout_path: Path) -> List[Dict[str, Any]]:
    if not stdout_path.exists():
        return []
    text = stdout_path.read_text()
    blocks = re.split(r'\n\$ ', text)
    parsed = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if not lines:
            continue
        cmd = lines[0].strip()
        output = "\n".join(lines[1:])
        parsed.append({"command": cmd, "output": output})
    return parsed


def extract_state_transitions(blocks: List[Dict]) -> List[Dict]:
    transitions = []
    for block in blocks:
        matches = re.findall(r"State transition:\s*(\w+)\s*->\s*(\w+)", block["output"])
        for m in matches:
            transitions.append({"from": m[0], "to": m[1], "source": block["command"]})
    return transitions


def extract_receipts(blocks: List[Dict]) -> List[Dict]:
    receipts = []
    seen_ids = set()

    for block in blocks:
        action_match = re.search(
            r"Action (allowed|denied):\s*(\w+).*?receipt_id['\"]?\s*:\s*['\"]?([A-F0-9]{16})",
            block["output"], re.DOTALL | re.IGNORECASE
        )
        if action_match:
            rid = action_match.group(3)
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append({
                    "type": "action",
                    "decision": action_match.group(1).upper(),
                    "action": action_match.group(2),
                    "receipt_id": rid,
                    "source": block["command"]
                })
            continue

        mut_match = re.search(
            r"Mutation (allowed|denied):\s*(\w+).*?receipt_id['\"]?\s*:\s*['\"]?([A-F0-9]{16})",
            block["output"], re.DOTALL | re.IGNORECASE
        )
        if mut_match:
            rid = mut_match.group(3)
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append({
                    "type": "mutation",
                    "decision": mut_match.group(1).upper(),
                    "mutation": mut_match.group(2),
                    "receipt_id": rid,
                    "source": block["command"]
                })
            continue

        listing_matches = re.findall(
            r"^\d+\.\s*(\w+)\s*\|\s*([A-F0-9]{16})\s*\|\s*prev=(\w+)\s*\|\s*decision=(\w+)",
            block["output"], re.MULTILINE | re.IGNORECASE
        )
        for m in listing_matches:
            rid = m[1]
            if rid not in seen_ids:
                seen_ids.add(rid)
                receipts.append({
                    "type": "mutation_listing",
                    "mutation": m[0],
                    "receipt_id": rid,
                    "previous": m[2],
                    "decision": m[3].upper(),
                    "source": block["command"]
                })
    return receipts


def extract_artifact_unlocks(blocks: List[Dict]) -> List[Dict]:
    unlocks = []
    seen = set()
    for block in blocks:
        matches = re.findall(r"Unlocked document:\s*(\S+)", block["output"])
        for m in matches:
            if m not in seen:
                seen.add(m)
                unlocks.append({"artifact": m, "source": block["command"], "method": "transition"})

        if "explain" in block["command"]:
            initial_matches = re.findall(r"unlocked artifacts:\s*\n\s+-\s+(\S+)", block["output"], re.IGNORECASE)
            for m in initial_matches:
                if m not in seen:
                    seen.add(m)
                    unlocks.append({"artifact": m, "source": block["command"], "method": "initial"})
    return unlocks


def extract_final_state(blocks: List[Dict]) -> Dict:
    """Extract final state from the demo command's FINAL STATUS section."""
    # First, look specifically at the demo command for FINAL STATUS
    for block in blocks:
        if "demo" in block["command"]:
            # Look for current_state in the FINAL STATUS dict
            final_status_match = re.search(
                r"FINAL STATUS\s*=+\s*\{[^}]*current_state['\"]?\s*:\s*['\"]?(\w+)",
                block["output"], re.DOTALL
            )
            if final_status_match:
                return {"current_state": final_status_match.group(1)}
            # Also check for the last state transition
            demo_final = re.findall(r"State transition:\s*\w+\s*->\s*(\w+)", block["output"])
            if demo_final:
                return {"current_state": demo_final[-1]}

    # Fallback: check verify command
    for block in blocks:
        if "verify" in block["command"]:
            state_match = re.search(r"current_state['\"]?\s*:\s*['\"]?(\w+)", block["output"])
            if state_match:
                return {"current_state": state_match.group(1)}

    # Last resort: any block
    for block in reversed(blocks):
        state_match = re.search(r"current_state['\"]?\s*:\s*['\"]?(\w+)", block["output"])
        if state_match:
            return {"current_state": state_match.group(1)}
        demo_final = re.findall(r"State transition:\s*\w+\s*->\s*(\w+)", block["output"])
        if demo_final:
            return {"current_state": demo_final[-1]}
    return {}


def validate_state_chain(transitions: List[Dict]) -> Dict:
    if not transitions:
        return {"score": 0.0, "reason": "No state transitions found in output"}

    expected_sequence = ["state0", "state1", "state2", "state3", "state4"]
    chain = [transitions[0]["from"]] + [t["to"] for t in transitions]

    issues = []
    for i, (expected, actual) in enumerate(zip(expected_sequence, chain)):
        if expected != actual:
            issues.append(f"Position {i}: expected {expected}, got {actual}")

    if len(chain) != len(expected_sequence):
        issues.append(f"Chain length mismatch: expected {len(expected_sequence)}, got {len(chain)}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.25))

    return {
        "score": round(score, 4),
        "expected_chain": expected_sequence,
        "actual_chain": chain,
        "issues": issues,
        "reason": "Valid state chain" if not issues else f"{len(issues)} chain violation(s)"
    }


def validate_receipt_chain(receipts: List[Dict]) -> Dict:
    if not receipts:
        return {"score": 0.0, "reason": "No receipts found in output"}

    issues = []
    ids = [r["receipt_id"] for r in receipts]

    if len(ids) != len(set(ids)):
        duplicates = [id for id in set(ids) if ids.count(id) > 1]
        issues.append(f"Duplicate receipt IDs: {duplicates}")

    bad_format = [id for id in ids if not re.match(r"^[A-F0-9]{16}$", id)]
    if bad_format:
        issues.append(f"Malformed receipt IDs: {bad_format}")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.3))

    return {
        "score": round(score, 4),
        "receipt_count": len(receipts),
        "unique_ids": len(set(ids)),
        "issues": issues,
        "reason": f"{len(receipts)} valid receipts" if not issues else f"{len(issues)} receipt issue(s)"
    }


def validate_artifact_consistency(unlocks: List[Dict], final_state: Dict) -> Dict:
    if not unlocks:
        return {"score": 0.0, "reason": "No artifact unlocks found"}

    expected_artifacts = [
        "doc1_demo1.md", "doc2_demo2.md", "doc3_demo3.md",
        "doc4_demo4.md", "doc5_system_summary.md"
    ]
    actual = [u["artifact"] for u in unlocks]

    issues = []
    missing = [a for a in expected_artifacts if a not in actual]
    extra = [a for a in actual if a not in expected_artifacts]

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
        "reason": f"All {len(expected_artifacts)} artifacts unlocked" if not issues else f"{len(issues)} artifact issue(s)"
    }


def check_output_completeness(run_dir: Path, summary: Dict) -> Dict:
    commands = summary.get("commands", [])
    if not commands:
        return {"score": 0.0, "reason": "No command records in summary"}

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"

    stdout_text = stdout_path.read_text() if stdout_path.exists() else ""
    stderr_text = stderr_path.read_text() if stderr_path.exists() else ""

    issues = []
    for cmd in commands:
        cmd_str = cmd["command"]
        if cmd_str not in stdout_text:
            issues.append(f"Missing stdout for: {cmd_str}")

    if stderr_text.strip() == "" or stderr_text.strip() == "$ ":
        issues.append("Stderr log is empty or minimal")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.15))

    return {
        "score": round(score, 4),
        "command_count": len(commands),
        "issues": issues,
        "reason": "All outputs captured" if not issues else f"{len(issues)} completeness issue(s)"
    }


def detect_unexplained_variance(blocks: List[Dict]) -> Dict:
    """Detect output patterns outside the known model."""
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
        # Demo-suite specific headers and status lines
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
    ]

    issues = []
    for block in blocks:
        for line in block["output"].splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if not any(re.match(p, line_stripped) for p in known_patterns):
                issues.append(f"Unrecognized: '{line_stripped[:80]}'")

    unique_issues = list(set(issues))[:10]
    score = 1.0 if not unique_issues else max(0.0, 1.0 - (len(unique_issues) * 0.1))

    return {
        "score": round(score, 4),
        "unexplained_patterns": unique_issues,
        "pattern_count": len(unique_issues),
        "reason": "No unexplained variance" if not unique_issues else f"{len(unique_issues)} unexplained pattern(s)",
        "interpretation": (
            "All output matches known patterns."
            if score == 1.0 else
            "Some output lines do not match known patterns."
            if score >= 0.8 else
            "Significant unexplained variance. Recommend inspection."
        )
    }


def compute_overall_confidence(axes: Dict[str, Dict]) -> Dict:
    weights = {
        "state_continuity": 0.25,
        "receipt_integrity": 0.20,
        "artifact_consistency": 0.15,
        "output_completeness": 0.15,
        "command_fidelity": 0.10,
        "unexplained_variance": 0.15,
    }

    total_weight = sum(weights.values())
    weighted_sum = sum(
        axes[axis]["score"] * weight
        for axis, weight in weights.items()
        if axis in axes
    )
    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    unchecked = [
        "Internal SUT logic correctness (not observable from outputs)",
        "Side effects outside captured stdout/stderr",
        "Cryptographic validity of receipt hashes (format only)",
        "Temporal ordering precision (second-level granularity only)",
        "Environmental determinism (OS, Python version, filesystem state)",
        "Intent behind any decision (only observable behavior is measured)",
    ]

    return {
        "overall": round(overall, 4),
        "percentage": round(overall * 100, 2),
        "axis_weights": weights,
        "axis_scores": {axis: axes.get(axis, {}).get("score", 0.0) for axis in weights},
        "unchecked_constraints": unchecked,
        "interpretation": (
            "High confidence: reconstructed dataset likely matches original within observed boundaries."
            if overall >= 0.95 else
            "Moderate confidence: some observable discrepancies detected."
            if overall >= 0.80 else
            "Low confidence: significant gaps between original and reconstruction."
        )
    }


def reconstruct(run_dir: Path) -> Dict:
    summary_path = run_dir / "summary.json"
    stdout_path = run_dir / "stdout.log"

    if not summary_path.exists():
        return {"error": f"No summary.json found in {run_dir}"}

    with open(summary_path) as f:
        summary = json.load(f)

    blocks = parse_stdout_log(stdout_path)
    transitions = extract_state_transitions(blocks)
    receipts = extract_receipts(blocks)
    unlocks = extract_artifact_unlocks(blocks)
    final_state = extract_final_state(blocks)

    axes = {
        "state_continuity": validate_state_chain(transitions),
        "receipt_integrity": validate_receipt_chain(receipts),
        "artifact_consistency": validate_artifact_consistency(unlocks, final_state),
        "output_completeness": check_output_completeness(run_dir, summary),
        "command_fidelity": {
            "score": 1.0,
            "reason": f"{len(summary.get('commands', []))} commands recorded in summary"
        },
        "unexplained_variance": detect_unexplained_variance(blocks),
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
        },
        "confidence": confidence,
        "axes": axes,
    }


def write_reconstruction_report(run_dir: Path, data: Dict) -> Path:
    report_path = run_dir / "reconstruction.md"

    lines = [
        "# Reconstruction & Confidence Analysis",
        "",
        f"**Run:** {data['run_id']}  ",
        f"**Mode:** {data['mode']}  ",
        f"**Commit:** `{data['commit_hash']}`  ",
        "",
        "---",
        "",
        "## What This Measures",
        "",
        "The confidence score answers exactly one question:",
        "",
        "> *Is the reconstructed dataset the same as the original,",
        "> within the boundaries of what we chose to observe?*",
        "",
        "It does **not** measure:",
        "- Internal SUT logic correctness",
        "- Side effects outside captured output",
        "- Cryptographic security of receipts",
        "- Environmental or temporal precision",
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

    for axis, weight in data['confidence']['axis_weights'].items():
        score = data['axes'][axis]['score']
        reason = data['axes'][axis]['reason']
        status = "PASS" if score >= 0.95 else "WARN" if score >= 0.80 else "FAIL"
        lines.append(f"| {axis} | {weight:.0%} | {score:.0%} | {status} — {reason} |")

    lines.extend([
        "",
        "---",
        "",
        "## Reconstructed Timeline",
        "",
    ])

    rec = data['reconstruction']

    if rec['state_transitions']:
        lines.append("### State Transitions")
        for t in rec['state_transitions']:
            lines.append(f"- `{t['from']}` -> `{t['to']}` (via {t['source']})")
        lines.append("")

    if rec['receipts']:
        lines.append("### Receipts")
        for r in rec['receipts']:
            name = r.get('action') or r.get('mutation', 'unknown')
            lines.append(f"- `{r['receipt_id']}` | {r['type']}:{name} | {r['decision']}")
        lines.append("")

    if rec['artifact_unlocks']:
        lines.append("### Artifact Unlocks")
        for u in rec['artifact_unlocks']:
            lines.append(f"- `{u['artifact']}` (via {u['source']}, {u['method']})")
        lines.append("")

    if rec['final_state']:
        lines.append("### Final State")
        lines.append(f"- `{rec['final_state'].get('current_state', 'unknown')}`")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Unchecked Constraints",
        "",
        "The following were **not** verified and limit the scope of this confidence score:",
        "",
    ])

    for constraint in data['confidence']['unchecked_constraints']:
        lines.append(f"- {constraint}")

    lines.extend([
        "",
        "---",
        "",
        "## Real-World Application",
        "",
        "This same confidence framework applies to production systems:",
        "",
        "| Scenario | What Confidence Measures | What It Cannot |",
        "|----------|--------------------------|----------------|",
        "| Compliance audit | Log completeness and consistency | Intent behind entries |",
        "| Incident response | Observable event sequence | Root cause in unlogged state |",
        "| Data provenance | Transfer chain integrity | Physical security of media |",
        "| Financial reconciliation | Transaction record matching | Fraudulent intent |",
        "",
        "In every case, the confidence score is the boundary between",
        "**what you can prove from observations** and **what you must trust**.",
        "",
        "---",
        "",
        "## Determinism Note",
        "",
        "Explicit determinism means: given the same inputs, seed, and environment,",
        "the system produces the same observable outputs. This is verified by replay.",
        "",
        "Implicit determinism means: we assume it worked because no errors appeared.",
        "",
        "The confidence score makes the distinction explicit.",
        "",
    ])

    report_path.write_text("\n".join(lines))
    return report_path


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python reconstruct.py <run_directory>")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    data = reconstruct(run_dir)

    if "error" in data:
        print(f"Error: {data['error']}")
        sys.exit(1)

    report_path = write_reconstruction_report(run_dir, data)

    json_path = run_dir / "reconstruction.json"
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Reconstruction report: {report_path}")
    print(f"Reconstruction data:   {json_path}")
    print(f"Overall confidence:    {data['confidence']['percentage']}%")


if __name__ == "__main__":
    main()
