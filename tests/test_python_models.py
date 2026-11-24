import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_sim_snn_stdp_runs():
    script = ROOT / "sim" / "sim_snn_stdp.py"
    assert script.exists(), f"Script não encontrado: {script}"
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    assert res.returncode == 0


def test_encode_signal_aer_runs():
    script = ROOT / "sim" / "encode_signal_aer.py"
    assert script.exists(), f"Script não encontrado: {script}"
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    assert res.returncode == 0
