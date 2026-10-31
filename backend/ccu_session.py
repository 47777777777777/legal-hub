"""
CCU AutoRPA Session & Authentication Bridge.
Manages authenticated proxy sessions for CCU Lawbank and CCU Lawdata.
"""
import os
import json
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSION_FILE = os.path.join(DATA_DIR, "ccu_session.json")

LAWBANK_URL = "https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/"
LAWDATA_URL = "https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/"


class CCUSessionManager:
    @staticmethod
    def get_session_file() -> str:
        return SESSION_FILE

    @staticmethod
    def load_session() -> Dict[str, Any]:
        if not os.path.exists(SESSION_FILE):
            return {
                "authenticated": False,
                "cookies": "",
                "lawbank_active": False,
                "lawdata_active": False,
                "last_checked": None,
                "institution": "國立中正大學圖書館 (AutoRPA)"
            }
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "authenticated": False,
                "cookies": "",
                "lawbank_active": False,
                "lawdata_active": False,
                "last_checked": None,
                "institution": "國立中正大學圖書館 (AutoRPA)"
            }

    @staticmethod
    def clean_cookie_input(raw: str) -> str:
        """
        Normalizes and sanitizes cookie input from user.
        Accepts:
        - Raw Cookie string (e.g. 'flysheet-proxy=abc; lawbank=def')
        - Header format (e.g. 'Cookie: flysheet-proxy=abc')
        - Multi-line Request Headers (e.g. from Chrome 'Copy request headers')
        - Full cURL command (bash, cmd, PowerShell)
        - PowerShell Invoke-WebRequest / Invoke-RestMethod headers block
        - JavaScript fetch snippet
        - Bare session/proxy token
        """
        if not raw:
            return ""
        raw = raw.strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1].strip()

        import re

        # 1. Multi-line headers (e.g. 'Copy request headers' from DevTools)
        m_head = re.search(r"(?:^|\n)\s*cookie:\s*([^\r\n]+)", raw, re.IGNORECASE)
        if m_head:
            return m_head.group(1).strip()

        # 2. PowerShell format: @{"cookie"="..."} or headers['cookie'] = '...'
        m_ps = re.search(r"cookie[\"']?\s*(?:=|=>|:)\s*[\"']([^\"'\r\n]+)[\"']", raw, re.IGNORECASE)
        if m_ps and ("powershell" in raw.lower() or "$headers" in raw.lower() or "@{" in raw):
            return m_ps.group(1).strip()

        # 3. If full cURL command (bash / cmd / PowerShell)
        if "curl " in raw.lower() or "curl.exe" in raw.lower():
            raw_clean = raw.replace('^"', '"').replace("^'", "'").replace("`", "")
            m_curl = re.search(r"-(?:H|b|-header)\s+[\"']?(?:cookie:\s*)?([^\"']+)[\"']?", raw_clean, re.IGNORECASE)
            if m_curl:
                return m_curl.group(1).strip()
            m_curl2 = re.search(r"[\"']cookie:\s*([^\"'\r\n]+)[\"']", raw_clean, re.IGNORECASE)
            if m_curl2:
                return m_curl2.group(1).strip()

        # 4. Fetch format: 'cookie': '...'
        if "fetch(" in raw.lower():
            m_fetch = re.search(r"[\"']cookie[\"']\s*:\s*[\"']([^\"'\r\n]+)[\"']", raw, re.IGNORECASE)
            if m_fetch:
                return m_fetch.group(1).strip()

        # 5. If leading 'Cookie:' header label
        if raw.lower().startswith("cookie:"):
            raw = raw[7:].strip()

        # 6. If user pasted only the bare sessionid/proxy token (20-50 chars alphanumeric)
        if re.match(r"^[a-zA-Z0-9_-]{20,50}$", raw):
            raw = f"sessionid={raw}"

        return raw

    @staticmethod
    def save_session(cookies: str) -> Dict[str, Any]:
        """
        Saves Cookie header string and verifies against CCU AutoRPA gateways.
        """
        os.makedirs(DATA_DIR, exist_ok=True)
        cookies = CCUSessionManager.clean_cookie_input(cookies)
        data = {
            "authenticated": False,
            "cookies": cookies,
            "lawbank_active": False,
            "lawdata_active": False,
            "last_checked": None,
            "institution": "國立中正大學圖書館 (AutoRPA)",
            "hint": None
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Immediately check health if cookies provided
        if cookies:
            return CCUSessionManager.check_status()
        return data

    @staticmethod
    def check_status() -> Dict[str, Any]:
        """
        Tests session cookies against both LawBank and LawData AutoRPA endpoints.
        """
        session = CCUSessionManager.load_session()
        cookies = session.get("cookies", "").strip()

        if not cookies:
            session["authenticated"] = False
            session["lawbank_active"] = False
            session["lawdata_active"] = False
            return session

        import datetime
        session["last_checked"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # 1. Test LawBank
        lawbank_ok = False
        try:
            req = urllib.request.Request(
                LAWBANK_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0",
                    "Cookie": cookies
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                final_url = resp.url
                html_sample = resp.read(2048).decode("utf-8", errors="ignore")
                # If redirected to SSO login page, not authenticated
                if "idm.lib.ccu.edu.tw" not in final_url and "login" not in final_url.lower():
                    # Must contain sessionid or authenticated proxy identity, not bare guest buy auth
                    if "BuyAuth.aspx" not in html_sample or "sessionid" in cookies.lower():
                        lawbank_ok = True
        except Exception as e:
            print(f"Lawbank health check: {e}")

        # 2. Test LawData
        lawdata_ok = False
        try:
            req = urllib.request.Request(
                LAWDATA_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0",
                    "Cookie": cookies
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                final_url = resp.url
                if "idm.lib.ccu.edu.tw" not in final_url and "login" not in final_url.lower():
                    if "sessionid" in cookies.lower() or "flysheet-proxy" in cookies.lower():
                        lawdata_ok = True
        except Exception as e:
            print(f"Lawdata health check: {e}")

        # Strict check: Session MUST have sessionid token to be truly authenticated
        has_sessionid = "sessionid=" in cookies.lower() or "sessionid" in cookies.lower()
        session["lawbank_active"] = lawbank_ok and has_sessionid
        session["lawdata_active"] = lawdata_ok and has_sessionid
        session["authenticated"] = (lawbank_ok or lawdata_ok) and has_sessionid

        if not session["authenticated"]:
            low_cookies = cookies.lower()
            if low_cookies.startswith("accept:") or ("text/html" in low_cookies and "flysheet" not in low_cookies):
                session["hint"] = "您剛才複製到的是「Accept」格式標頭，並非「Cookie」。在 Network 分頁請直接在左側請求名稱上按右鍵選「Copy → Copy as cURL (bash 或 cmd)」，整段貼上即可！"
            elif not has_sessionid:
                session["hint"] = "⚠️ 貼上的內容缺少核心憑證「sessionid」！目前僅有代理暫存碼（訪客狀態）。請依照上方【方式一】在 Application → Cookies → autorpa.lib.ccu.edu.tw 雙擊複製名為「sessionid」的值（約 32 碼英數字）貼上！"
            else:
                session["hint"] = "已接收到 sessionid，但中正 AutoRPA 驗證未通過（可能登入已逾期）。請在法源或月旦分頁按 F5 重新登入後再次複製。"
        else:
            session["hint"] = "中正 AutoRPA 連線認證成功！已成功綁定 sessionid。"

        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return session

