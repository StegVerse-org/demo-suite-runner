from __future__ import annotations
from pathlib import Path
import json

def write_summary_json(path: Path, summary):
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

def build_markdown_report(summary):
    lines = []
    lines.append(f"# {summary['mode']} run report")
    lines.append("")
    lines.append(f"- Status: **{summary['status']}**")
    lines.append(f"- Reset mode: `{summary['reset_mode']}`")
    lines.append(f"- Target repo: `{summary['repo_url']}`")
    lines.append(f"- Ref: `{summary['ref']}`")
    lines.append(f"- Commit: `{summary['commit_hash']}`")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for item in summary["commands"]:
        lines.append(f"### `{item['command']}`")
        lines.append(f"- Return code: `{item['returncode']}`")
        lines.append(f"- Duration seconds: `{item['duration_seconds']}`")
        lines.append("")
    lines.append("## Final Verdict")
    lines.append("")
    lines.append(summary["verdict"])
    lines.append("")
    return "\n".join(lines)

def write_markdown_report(path: Path, summary):
    path.write_text(build_markdown_report(summary), encoding="utf-8")
