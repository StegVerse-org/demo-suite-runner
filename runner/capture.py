from __future__ import annotations
from pathlib import Path

def write_lines(path: Path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
