import os
import urllib.request
import zipfile
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
order_path = os.path.join(DATA_DIR, "ChOrder.json")

if not os.path.exists(order_path):
    print("Downloading ChOrder.json...")
    url = "https://law.moj.gov.tw/api/ch/order/json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        buf = io.BytesIO(resp.read())
    with zipfile.ZipFile(buf) as z:
        z.extract("ChOrder.json", DATA_DIR)
    print(f"Extracted ChOrder.json ({os.path.getsize(order_path)} bytes)")

from scripts.sync_orders_corpus import sync_orders
sync_orders()

