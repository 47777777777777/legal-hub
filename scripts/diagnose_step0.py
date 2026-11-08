import json
import sqlite3
import urllib.request
import subprocess

print("=== STEP 0-1: 5 SAMPLE ARTICLES PANEL API JSON (LOCAL VS REMOTE) ===")
sample_articles = ["1", "2", "92", "128", "175"]

for art_no in sample_articles:
    print(f"\n==================== Administrative Procedure Act Art {art_no} ====================")
    # Local
    try:
        url_local = f"http://127.0.0.1:8080/api/acts/admin_procedure_act/articles/{art_no}/panel"
        req = urllib.request.urlopen(url_local)
        data_local = json.loads(req.read().decode('utf-8'))
        d_loc = data_local.get("data", {})
        reasons_loc = d_loc.get("legislative_reasons", [])
        comps_loc = d_loc.get("amendment_comparison", [])
        print(f"LOCAL  /api/.../panel:")
        print(f"  legislative_reasons count: {len(reasons_loc)}, status: {d_loc.get('lis_reasons_status')}")
        if reasons_loc:
            print(f"  sample reason snippet (first 60 chars): {repr(reasons_loc[0].get('reason', '')[:60])}")
        print(f"  amendment_comparison count: {len(comps_loc)}")
        if comps_loc:
            print(f"  sample comparison snippet: {repr(comps_loc[0].get('new_content', '')[:60])}")
    except Exception as e:
        print(f"LOCAL error: {e}")

    # Remote
    try:
        url_remote = f"http://161.33.166.144/api/acts/admin_procedure_act/articles/{art_no}/panel"
        req = urllib.request.urlopen(url_remote)
        data_remote = json.loads(req.read().decode('utf-8'))
        d_rem = data_remote.get("data", {})
        reasons_rem = d_rem.get("legislative_reasons", [])
        comps_rem = d_rem.get("amendment_comparison", [])
        print(f"REMOTE /api/.../panel:")
        print(f"  legislative_reasons count: {len(reasons_rem)}, status: {d_rem.get('lis_reasons_status')}")
        if reasons_rem:
            print(f"  sample reason snippet (first 60 chars): {repr(reasons_rem[0].get('reason', '')[:60])}")
        print(f"  amendment_comparison count: {len(comps_rem)}")
        if comps_rem:
            print(f"  sample comparison snippet: {repr(comps_rem[0].get('new_content', '')[:60])}")
    except Exception as e:
        print(f"REMOTE error: {e}")

print("\n=== STEP 0-2: SELECT COUNT(*), COUNT(DISTINCT ACT_ID||'|'||ARTICLE_NO) FROM ARTICLE_REASONS ===")
# Local DB
conn_loc = sqlite3.connect("data/legal_hub.db")
cur_loc = conn_loc.cursor()
cur_loc.execute("SELECT count(*), count(DISTINCT act_id||'|'||article_no) FROM article_reasons;")
row_loc = cur_loc.fetchone()
print(f"LOCAL  DB article_reasons: total rows = {row_loc[0]}, distinct articles = {row_loc[1]}")
cur_loc.execute("SELECT count(*), count(DISTINCT act_id||'|'||article_no) FROM article_comparison;")
comp_loc = cur_loc.fetchone()
print(f"LOCAL  DB article_comparison: total rows = {comp_loc[0]}, distinct articles = {comp_loc[1]}")
conn_loc.close()

# Remote DB via SSH
res_rem = subprocess.run([
    "ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144",
    "python3 -c \"import sqlite3; conn=sqlite3.connect('legal-hub/data/legal_hub.db'); cur=conn.cursor(); cur.execute('SELECT count(*), count(DISTINCT act_id||\"|\"||article_no) FROM article_reasons;'); r=cur.fetchone(); cur.execute('SELECT count(*), count(DISTINCT act_id||\"|\"||article_no) FROM article_comparison;'); c=cur.fetchone(); print('REMOTE DB article_reasons:', r[0], r[1], '; article_comparison:', c[0], c[1])\""
], capture_output=True, text=True)
print(res_rem.stdout.strip())

