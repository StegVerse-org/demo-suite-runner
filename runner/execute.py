from __future__ import annotations
from pathlib import Path
import subprocess
import time

def run_command(repo_dir: Path, command: str):
    start = time.time()
    completed = subprocess.run(
        command,
        cwd=str(repo_dir),
        shell=True,
        capture_output=True,
        text=True,
    )
    duration = round(time.time() - start, 3)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "duration_seconds": duration,
    }

def maybe_make_launcher_executable(repo_dir: Path) -> None:
    launcher = repo_dir / "stegverse"
    if launcher.exists():
        try:
            launcher.chmod(0o755)
        except Exception:
            pass
