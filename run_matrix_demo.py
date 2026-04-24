from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "runner" / "main.py"), "--mode", "governance_matrix", "--reset", "hard"], check=True)
