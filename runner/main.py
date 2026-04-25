from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from capture import write_lines
from config import ROOT, load_json_config
from execute import maybe_make_launcher_executable, run_command
from git_ops import clone_repo, fetch_and_checkout, get_commit_hash
from report import write_markdown_report, write_summary_json
from reset_ops import soft_reset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless runner for stegverse-demo-suite")
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "execution_governance",
            "mutation_governance",
            "governance_matrix",
            "governance_random_sweep",
            "full",
        ],
    )
    parser.add_argument("--reset", required=True, choices=["soft", "hard"])
    parser.add_argument("--ref", default=None, help="Git ref to checkout, e.g. main or v1.0.0")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for governance_random_sweep")
    parser.add_argument("--samples", type=int, default=50, help="Samples per phase for governance_random_sweep")
    parser.add_argument("--no-reconstruct", action="store_true", help="Skip reconstruction and confidence analysis")
    return parser.parse_args()


def load_mode_commands(mode: str) -> dict:
    mapping = {
        "execution_governance": "execution_governance.json",
        "mutation_governance": "mutation_governance.json",
        "governance_matrix": "governance_matrix.json",
        "governance_random_sweep": "governance_random_sweep.json",
        "full": "full.json",
    }
    return load_json_config(mapping[mode])


def copy_optional_report(target_repo_dir: Path, run_dir: Path, report_name: str) -> dict | None:
    source = target_repo_dir / report_name
    if not source.exists():
        return None

    destination = run_dir / report_name
    shutil.copyfile(source, destination)

    try:
        return json.loads(destination.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": f"Could not parse {report_name}"}


def main() -> None:
    args = parse_args()
    do_reconstruct = not args.no_reconstruct

    default = load_json_config("default.json")
    repo_url = default["repo_url"]
    work_root = ROOT / default["work_root"]
    target_repo_dir = work_root / default["target_repo_name"]
    ref = args.ref or default["default_ref"]

    if args.reset == "hard":
        clone_repo(repo_url, target_repo_dir, branch=default["default_ref"])
        if ref != default["default_ref"]:
            fetch_and_checkout(target_repo_dir, ref)
    else:
        if not target_repo_dir.exists():
            clone_repo(repo_url, target_repo_dir, branch=default["default_ref"])
        if ref != default["default_ref"]:
            fetch_and_checkout(target_repo_dir, ref)
        soft_reset(target_repo_dir)

    maybe_make_launcher_executable(target_repo_dir)
    commit_hash = get_commit_hash(target_repo_dir)

    config = load_mode_commands(args.mode)
    commands = config.get("commands", [])

    os.environ["SV_SEED"] = str(args.seed)
    os.environ["SV_SAMPLES"] = str(args.samples)

    results = []
    command_log = []
    stdout_log = []
    stderr_log = []

    for command in commands:
        result = run_command(target_repo_dir, command)
        results.append(result)
        command_log.append(command)
        stdout_log.append(f"$ {command}\n{result['stdout']}")
        stderr_log.append(f"$ {command}\n{result['stderr']}")

        if result["returncode"] != 0:
            break

    status = "PASS" if all(result["returncode"] == 0 for result in results) else "FAIL"
    verdict = f"Run {status}: {args.mode} against {ref} at {commit_hash}"

    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = ROOT / "runs" / f"{stamp}_{args.mode}"
    run_dir.mkdir(parents=True, exist_ok=True)

    write_lines(run_dir / "commands.log", command_log)
    write_lines(run_dir / "stdout.log", stdout_log)
    write_lines(run_dir / "stderr.log", stderr_log)

    summary = {
        "status": status,
        "mode": args.mode,
        "reset_mode": args.reset,
        "repo_url": repo_url,
        "ref": ref,
        "commit_hash": commit_hash,
        "commands": [
            {
                "command": result["command"],
                "returncode": result["returncode"],
                "duration_seconds": result["duration_seconds"],
            }
            for result in results
        ],
        "verdict": verdict,
    }

    matrix_data = copy_optional_report(target_repo_dir, run_dir, "matrix_report.json")
    if matrix_data is not None:
        summary["matrix"] = matrix_data

    sweep_data = copy_optional_report(target_repo_dir, run_dir, "sweep_report.json")
    if sweep_data is not None:
        summary["sweep"] = sweep_data

    write_summary_json(run_dir / "summary.json", summary)
    write_markdown_report(run_dir / "report.md", summary)

    if do_reconstruct:
        recon_script = ROOT / "scripts" / "reconstruct.py"
        if recon_script.exists():
            recon_result = subprocess.run(
                ["python", str(recon_script), str(run_dir)],
                capture_output=True,
                text=True,
            )
            print(recon_result.stdout)
            if recon_result.returncode != 0:
                print(f"Reconstruction warning: {recon_result.stderr}")

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_markdown_report(reports_dir / f"{args.mode}_latest.md", summary)
    write_summary_json(reports_dir / f"{args.mode}_latest.json", summary)

    if do_reconstruct:
        reconstruction_md = run_dir / "reconstruction.md"
        reconstruction_json = run_dir / "reconstruction.json"
        if reconstruction_md.exists():
            shutil.copyfile(reconstruction_md, reports_dir / f"{args.mode}_reconstruction_latest.md")
        if reconstruction_json.exists():
            shutil.copyfile(reconstruction_json, reports_dir / f"{args.mode}_reconstruction_latest.json")

    print(f"Run complete: {status}")
    print(f"Artifacts: {run_dir}")
    print(f"Latest report: {reports_dir / f'{args.mode}_latest.md'}")
    if do_reconstruct:
        print(f"Reconstruction: {run_dir / 'reconstruction.md'}")


if __name__ == "__main__":
    main()
