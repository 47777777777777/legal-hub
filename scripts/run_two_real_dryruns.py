import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.updater.moj import MojSource
from backend.updater.runner import execute_update_run

conn = sqlite3.connect("data/legal_hub.db")
src = MojSource({"test_chlaw_file": "data/ChLaw.json"})

print("=== RUN 1: REAL DATABASE DRY-RUN ===")
res1 = execute_update_run(src, apply=False, mode="test", conn=conn)
print(f"Run 1 Status: {res1.get('status')}")
print(f"Run 1 Counts: {res1.get('counts')}")
print(f"Run 1 Changes Count: {len(res1.get('changes', []))}")

print("\n=== RUN 2: REAL DATABASE DRY-RUN ===")
res2 = execute_update_run(src, apply=False, mode="test", conn=conn)
print(f"Run 2 Status: {res2.get('status')}")
print(f"Run 2 Counts: {res2.get('counts')}")
print(f"Run 2 Changes Count: {len(res2.get('changes', []))}")

conn.close()

