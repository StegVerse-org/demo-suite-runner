from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"

def load_json_config(name: str):
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))
