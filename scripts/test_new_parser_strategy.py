import gzip
import re
import sys
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")
from backend.lis.parser import parse_lis_article_no

def test_parse(gz_path):
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    art_fonts = soup.find_all('font', class_='artino')
    for af in art_fonts:
        art_raw = af.get_text(strip=True).replace(' ', '')
        art_no = parse_lis_article_no(art_raw)
        tbl = af.find_parent('table')
        if not tbl:
            continue
        cur_v = None
        versions = []
        for tr in tbl.find_all('tr', recursive=False):
            upd = tr.find('font', class_='upddate')
            th = tr.find('td', class_='artiupd_TH_2')
            rs = tr.find('td', class_='artiupd_RS_2')
            if upd:
                upd_txt = upd.get_text(strip=True)
                m_date = re.search(r'(\d{6,7})', upd_txt)
                m_act = re.search(r'\d{6,7}\s*([^\)]+)', upd_txt)
                if m_date:
                    if cur_v:
                        versions.append(cur_v)
                    cur_v = {
                        "version_date": m_date.group(1),
                        "action_type": m_act.group(1).strip() if m_act else "",
                        "content": "",
                        "reason": ""
                    }
            if cur_v:
                if th:
                    c_txt = th.get_text(separator='\n', strip=True)
                    if c_txt:
                        cur_v["content"] = cur_v["content"] + "\n" + c_txt if cur_v["content"] else c_txt
                if rs:
                    r_txt = rs.get_text(separator='\n', strip=True)
                    if r_txt:
                        cur_v["reason"] = cur_v["reason"] + "\n" + r_txt if cur_v["reason"] else r_txt
        if cur_v:
            versions.append(cur_v)
        for v in versions:
            if v["content"] or v["reason"]:
                results.append((art_no, v["version_date"], len(v["content"]), len(v["reason"]), v["reason"]))

    # Test verbatim substring
    import html as html_lib
    clean_raw = re.sub(r'\s+', '', html_lib.unescape(re.sub(r'<[^>]+>', '', html)))
    violations = []
    for art, date, c_len, r_len, reason in results:
        if reason:
            clean_r = re.sub(r'\s+', '', html_lib.unescape(reason))
            if clean_r not in clean_raw:
                violations.append((art, date, clean_r[:30]))

    print(f"{gz_path}: parsed {len(results)} versions, violations: {len(violations)}")
    if violations:
        print("  Violations:", violations)

test_parse("data/raw/lis/gz/A0040012.html.gz")
test_parse("data/raw/lis/gz/B0000005.html.gz")
test_parse("data/raw/lis/gz/A0030055.html.gz")
test_parse("data/raw/lis/gz/C0000001.html.gz")
