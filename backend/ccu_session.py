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
    def save_session(cookies: str) -> Dict[str, Any]:
        """
        Saves raw Cookie header string and verifies against CCU AutoRPA gateways.
        """
        os.makedirs(DATA_DIR, exist_ok=True)
        cookies = (cookies or "").strip()
        data = {
            "authenticated": False,
            "cookies": cookies,
            "lawbank_active": False,
            "lawdata_active": False,
            "last_checked": None,
            "institution": "國立中正大學圖書館 (AutoRPA)"
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

        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return session
