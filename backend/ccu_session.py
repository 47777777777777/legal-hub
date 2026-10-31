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
        - Raw Cookie string (e.g. 'sessionid=abc; ...')
        - Header format (e.g. 'Cookie: sessionid=abc')
        - Bare sessionid token (e.g. 'mgw0fifytmkbv0kvvgku73lrougb8jzs')
        - Full cURL command (e.g. "curl '...' -H 'cookie: sessionid=...'")
        """
        if not raw:
            return ""
        raw = raw.strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1].strip()

        # If full cURL command (bash / cmd / PowerShell)
        if "curl " in raw.lower() or "curl.exe" in raw.lower():
            import re
            m = re.search(r"-(?:H|b|-header)\s+['\"](?:cookie:\s*)?([^'\"]+)['\"]", raw, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
            else:
                m2 = re.search(r"['\"]cookie:\s*([^'\"]+)['\"]", raw, re.IGNORECASE)
                if m2:
                    raw = m2.group(1).strip()

        # If leading 'Cookie:' header label
        if raw.lower().startswith("cookie:"):
            raw = raw[7:].strip()

        # If user pasted only the bare sessionid token (20-50 chars alphanumeric)
        import re
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
                # If redirected to SSO login page, not authenticated
                if "idm.lib.ccu.edu.tw" not in final_url and "login" not in final_url.lower():
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
                    lawdata_ok = True
        except Exception as e:
            print(f"Lawdata health check: {e}")

        session["lawbank_active"] = lawbank_ok
        session["lawdata_active"] = lawdata_ok
        session["authenticated"] = lawbank_ok or lawdata_ok

        if not session["authenticated"]:
            low_cookies = cookies.lower()
            if "flysheet-proxy" not in low_cookies and "lawbank" not in low_cookies and "sessionid" not in low_cookies:
                session["hint"] = "貼上的內容缺少中正 AutoRPA 代理通行證（如 flysheet-proxy、lawbank 等）。請從 Network（網路）分頁選「Copy as cURL」整段貼上！"
            elif "flysheet-proxy" not in low_cookies and "asp.net_sessionid" in low_cookies:
                session["hint"] = "已偵測到 ASP.NET_SessionId，但缺少代理關鍵的 flysheet-proxy 與 lawbank。請從 Network（網路）分頁對首頁請求點右鍵選「Copy as cURL」整段貼上！"
            else:
                session["hint"] = "已接收到代理 Cookie，但連線驗證未通過（可能 Session 已過期）。請在中正 AutoRPA 頁面按 F5 重新整理後再次複製。"
        else:
            session["hint"] = "中正 AutoRPA 連線認證成功！"

        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return session

