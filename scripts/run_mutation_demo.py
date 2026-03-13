from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "runner" / "main.py"), "--mode", "mutation_governance", "--reset", "hard"], check=True)
