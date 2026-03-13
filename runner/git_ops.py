from __future__ import annotations
from pathlib import Path
import shutil
import subprocess

def clone_repo(repo_url: str, target_dir: Path, branch: str = "main") -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--branch", branch, repo_url, str(target_dir)], check=True)

def fetch_and_checkout(target_dir: Path, ref: str) -> None:
    subprocess.run(["git", "-C", str(target_dir), "fetch", "--all", "--tags"], check=True)
    subprocess.run(["git", "-C", str(target_dir), "checkout", ref], check=True)

def get_commit_hash(target_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
