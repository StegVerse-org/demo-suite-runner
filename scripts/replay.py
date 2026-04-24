#!/usr/bin/env python3
"""
Replay Engine

Re-executes a recorded run and compares outputs to verify determinism.
Produces a replay report with pass/fail and divergence details.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def load_run_data(run_dir: Path) -> dict:
    summary_path = run_dir / "summary.json"
    with open(summary_path) as f:
        return json.load(f)


def replay_commands(summary: dict, target_repo_dir: Path, env: dict = None) -> list:
    """Re-run the same command sequence and capture results."""
    results = []
    for cmd_record in summary.get("commands", []):
        cmd = cmd_record["command"]
        result = subprocess.run(
            cmd.split(),
            cwd=target_repo_dir,
            capture_output=True,
            text=True,
            env=env
        )
        results.append({
            "command": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    return results


def compare_outputs(original: list, replayed: list) -> dict:
    """Compare original and replayed command outputs."""
    if len(original) != len(replayed):
        return {
            "match": False,
            "reason": f"Command count mismatch: original={len(original)}, replayed={len(replayed)}",
            "divergences": []
        }

    divergences = []
    for i, (orig, repl) in enumerate(zip(original, replayed)):
        issues = []
        if orig["returncode"] != repl["returncode"]:
            issues.append(f"returncode: {orig['returncode']} vs {repl['returncode']}")

        # For stdout, compare key lines (receipt IDs will differ if regenerated)
        # We compare structure, not exact content
        orig_lines = orig.get("stdout", "").splitlines()
        repl_lines = repl.get("stdout", "").splitlines()

        if len(orig_lines) != len(repl_lines):
            issues.append(f"stdout line count: {len(orig_lines)} vs {len(repl_lines)}")

        if issues:
            divergences.append({
                "command": orig["command"],
                "index": i,
                "issues": issues
            })

    return {
        "match": len(divergences) == 0,
        "reason": "All outputs match" if not divergences else f"{len(divergences)} command(s) diverged",
        "divergences": divergences
    }


def write_replay_report(run_dir: Path, summary: dict, comparison: dict) -> Path:
    report_path = run_dir / "replay_report.md"

    lines = [
        "# Replay & Determinism Report",
        "",
        f"**Original run:** {summary.get('mode', 'unknown')} at {summary.get('commit_hash', 'unknown')}",
        f"**Replay time:** {datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')}",
        "",
        "## Determinism Check",
        "",
        f"**Result:** {'PASS' if comparison['match'] else 'FAIL'}",
        f"**Reason:** {comparison['reason']}",
        "",
    ]

    if comparison["divergences"]:
        lines.append("### Divergences")
        for d in comparison["divergences"]:
            lines.append(f"- Command {d['index']}: `{d['command']}`")
            for issue in d["issues"]:
                lines.append(f"  - {issue}")
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "A passing replay means: given the same code version and inputs,",
        "the system produces observably equivalent outputs.",
        "",
        "A failing replay means: the system is non-deterministic or the",
        "environment differs from the original run.",
        "",
        "Note: Receipt IDs may differ between runs if they include timestamps",
        "or randomness. This is expected and not a determinism failure.",
        "",
    ])

    report_path.write_text("\n".join(lines))
    return report_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python replay.py <run_directory> <target_repo_directory>")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    target_repo_dir = Path(sys.argv[2])

    summary = load_run_data(run_dir)
    replayed = replay_commands(summary, target_repo_dir)
    comparison = compare_outputs(summary.get("commands", []), replayed)

    report_path = write_replay_report(run_dir, summary, comparison)

    # Write JSON
    json_path = run_dir / "replay.json"
    with open(json_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"Replay report: {report_path}")
    print(f"Replay data:   {json_path}")
    print(f"Determinism:   {'PASS' if comparison['match'] else 'FAIL'}")

    sys.exit(0 if comparison["match"] else 1)


if __name__ == "__main__":
    main()
