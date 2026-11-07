import sys
import os
import re
import time
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

USER_AGENT = "LegalHubPersonal/1.0"

def get_law_fullpage(law_name: str):
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # Step 1: GET entry portal
    print(f"Step 1: Visiting entry portal for '{law_name}'...")
    req1 = urllib.request.Request(
        "https://lis.ly.gov.tw/lglawc/lglawkm",
        headers={"User-Agent": USER_AGENT}
    )
    with opener.open(req1, timeout=15) as resp:
        html1 = resp.read().decode('utf-8', errors='ignore')
    
    # Extract form action and hidden inputs
    soup1 = BeautifulSoup(html1, 'html.parser')
    form = soup1.find('form')
    action = form.get('action', '/lglawc/lglawkm')
    if not action.startswith('http'):
        action = f"https://lis.ly.gov.tw{action}"
    
    info_val = form.find('input', {'name': 'INFO'}).get('value', '')
    
    # Step 2: POST search form with law_name
    print(f"Step 2: Submitting search for '{law_name}'...")
    # LIS uses big5 or utf-8 query param. Let's test utf-8 / big5
    post_data = {
        'INFO': info_val,
        '@_1_6_T': 'T_LN/LW',
        '_1_6_T': law_name,
        '_IMG_檢索.x': '10',
        '_IMG_檢索.y': '10'
    }
    encoded_data = urllib.parse.urlencode(post_data).encode('utf-8')
    req2 = urllib.request.Request(
        action,
        data=encoded_data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://lis.ly.gov.tw/lglawc/lglawkm"
        }
    )
    time.sleep(1.0)
    with opener.open(req2, timeout=15) as resp:
        html2 = resp.read().decode('utf-8', errors='ignore')
        current_url = resp.geturl()
    
    print(f"Step 2 result URL: {current_url}, HTML length: {len(html2)}")
    
    # Check if we landed on search result list or directly on the law page
    soup2 = BeautifulSoup(html2, 'html.parser')
    # Look for 法條沿革 link
    history_link = None
    for a in soup2.find_all('a'):
        txt = a.get_text(strip=True)
        if '法條沿革' in txt:
            history_link = a.get('href')
            break
            
    if not history_link:
        # Check if there's a link to the law title in search results
        for a in soup2.find_all('a'):
            if law_name in a.get_text(strip=True) and 'lawsingle' in a.get('href', ''):
                law_link = a.get('href')
                if not law_link.startswith('http'):
                    law_link = f"https://lis.ly.gov.tw{law_link}"
                print(f"Following law link from results: {law_link}...")
                time.sleep(1.0)
                req_law = urllib.request.Request(law_link, headers={"User-Agent": USER_AGENT})
                with opener.open(req_law, timeout=15) as r_law:
                    html_law = r_law.read().decode('utf-8', errors='ignore')
                soup_law = BeautifulSoup(html_law, 'html.parser')
                for a_h in soup_law.find_all('a'):
                    if '法條沿革' in a_h.get_text(strip=True):
                        history_link = a_h.get('href')
                        break
                break

    if history_link:
        if not history_link.startswith('http'):
            history_link = f"https://lis.ly.gov.tw{history_link}"
        print(f"Found 法條沿革 (全法逐條理由) URL: {history_link}")
        time.sleep(1.0)
        req3 = urllib.request.Request(history_link, headers={"User-Agent": USER_AGENT})
        with opener.open(req3, timeout=20) as resp3:
            full_html = resp3.read().decode('utf-8', errors='ignore')
        print(f"Successfully retrieved full act page! Length: {len(full_html)}")
        return history_link, full_html
    else:
        print("Could not locate 法條沿革 link.")
        return None, None

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "行政程序法"
    get_law_fullpage(name)

