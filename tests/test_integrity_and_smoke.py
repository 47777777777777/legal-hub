import os
import sys
import subprocess
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_data_integrity_guardrail():
    script = os.path.join(BASE_DIR, "scripts", "verify_integrity.py")
    res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"Integrity check failed:\n{res.stdout}\n{res.stderr}"

def test_smoke_ui_playwright():
    script = os.path.join(BASE_DIR, "scripts", "smoke_ui.py")
    res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"Smoke UI check failed:\n{res.stdout}\n{res.stderr}"
