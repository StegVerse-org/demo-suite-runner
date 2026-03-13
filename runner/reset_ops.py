from __future__ import annotations
from pathlib import Path
import shutil

def soft_reset(target_repo_dir: Path) -> None:
    shutil.rmtree(target_repo_dir / ".stegverse_runtime", ignore_errors=True)
