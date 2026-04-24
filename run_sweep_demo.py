from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "runner" / "main.py"), "--mode", "governance_random_sweep", "--reset", "hard", "--seed", "42", "--samples", "50"], check=True)
