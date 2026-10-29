"""
Downloads official Taiwan MOJ Open Data zip and extracts ChLaw.json
"""
import os
import sys
import io
import zipfile
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHLAW_PATH = os.path.join(DATA_DIR, "ChLaw.json")

OFFICIAL_LAWS_ZIP_URL = "https://law.moj.gov.tw/api/ch/law/json"

def fetch_chlaw_json():
    if os.path.exists(CHLAW_PATH) and os.path.getsize(CHLAW_PATH) > 10000000:
        print(f"ChLaw.json already exists at {CHLAW_PATH} ({os.path.getsize(CHLAW_PATH) / (1024*1024):.2f} MB)")
        return CHLAW_PATH

    print(f"Downloading official open data from {OFFICIAL_LAWS_ZIP_URL}...")
    req = urllib.request.Request(
        OFFICIAL_LAWS_ZIP_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        buf = io.BytesIO(resp.read())

    print("Extracting ChLaw.json from zip...")
    with zipfile.ZipFile(buf) as z:
        z.extract("ChLaw.json", DATA_DIR)

    print(f"Successfully extracted ChLaw.json to {CHLAW_PATH} ({os.path.getsize(CHLAW_PATH) / (1024*1024):.2f} MB)")
    return CHLAW_PATH

if __name__ == "__main__":
    fetch_chlaw_json()

