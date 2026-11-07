"""
backend/updater/base.py

Unified Source Plugin Interface & Safety Guardrails:
1. Default dry-run mode (apply only with explicit flag)
2. Automatic pre-write backup with 14-run rotation (data/backup/)
3. Anomaly volume abort (>3% total articles or >50% of single act)
4. Atomic transactions with immediate verification & rollback
5. Rate limiting <= 1 req/sec & User-Agent: LegalHubPersonal/1.0
6. Canary regression checks before execution
"""

import os
import sys
import abc
import json
import time
import shutil
import hashlib
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backup")
USER_AGENT = "LegalHubPersonal/1.0"


def backup_database(db_path: str = DB_PATH, backup_dir: str = BACKUP_DIR, keep_count: int = 14) -> str:
    """Create a point-in-time timestamped backup of the SQLite database and prune to keep_count."""
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"legal_hub_backup_{ts}.db")
    
    # Use SQLite backup API for clean concurrent backup
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(backup_file)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    
    # Prune old backups
    backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("legal_hub_backup_") and f.endswith(".db")])
    if len(backups) > keep_count:
        for old_b in backups[:-keep_count]:
            try:
                os.remove(old_b)
            except OSError:
                pass
                
    return backup_file


def check_anomaly(
    diff_result: Dict[str, Any],
    conn: sqlite3.Connection,
    max_total_ratio: float = 0.03,
    max_act_ratio: float = 0.50
) -> Tuple[bool, str]:
    """
    Check if the proposed diff exceeds anomaly volume safety thresholds:
    - Total changed articles > 3% of entire database
    - Any single act changed articles > 50% of its current articles
    """
    changes = diff_result.get("changes", [])
    if not changes:
        return False, ""
        
    cur = conn.cursor()
    total_articles = cur.execute("SELECT count(*) FROM articles").fetchone()[0] or 1
    
    # Count distinct changed articles
    changed_arts = set((c["act_id"], c["article_no"]) for c in changes if c.get("article_no"))
    total_changed = len(changed_arts)
    
    if total_changed / total_articles > max_total_ratio:
        ratio_pct = (total_changed / total_articles) * 100
        return True, f"Total changed articles ({total_changed}, {ratio_pct:.2f}%) exceeds safety threshold of {max_total_ratio*100:.1f}%."

    # Check per act (acts explicitly marked abolished are governed by the total database threshold)
    abolished_acts = set(c["act_id"] for c in changes if c.get("change_type") == "abolish_act")
    by_act = {}
    for act_id, art_no in changed_arts:
        if act_id in abolished_acts:
            continue
        by_act[act_id] = by_act.get(act_id, 0) + 1
        
    for act_id, count in by_act.items():
        act_total = cur.execute("SELECT count(*) FROM articles WHERE act_id = ?", (act_id,)).fetchone()[0]
        if act_total and act_total > 0 and (count / act_total) > max_act_ratio:
            ratio_pct = (count / act_total) * 100
            return True, f"Act '{act_id}' has {count}/{act_total} changed articles ({ratio_pct:.2f}%), exceeding safety threshold of {max_act_ratio*100:.1f}%."

    return False, ""


class Source(abc.ABC):
    """Abstract base class for all legal data source plugins."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.user_agent = self.config.get("user_agent", USER_AGENT)
        self.rate_limit_sec = float(self.config.get("rate_limit_sec", 1.0))
        self.last_request_time = 0.0

    def throttle(self):
        """Enforce rate limiting <= 1 req/sec."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_sec:
            time.sleep(self.rate_limit_sec - elapsed)
        self.last_request_time = time.time()

    @abc.abstractmethod
    def run_canary(self) -> Tuple[bool, str]:
        """
        Run canary check against fixed baseline sample page.
        Returns (passed: bool, message: str).
        """
        pass

    @abc.abstractmethod
    def check(self) -> Dict[str, Any]:
        """
        Lightweight check to see if remote source has changed.
        Returns dict containing has_changes: bool, and change metadata.
        """
        pass

    @abc.abstractmethod
    def fetch(self, check_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download only the changed raw data and save to data/raw/... with headers and fetched_at.
        Returns dict containing raw file paths and metadata.
        """
        pass

    @abc.abstractmethod
    def diff(self, fetch_result: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Compare raw fetch result with current database state.
        Produces list of planned additions, revisions, deletions, without writing to database.
        """
        pass

    @abc.abstractmethod
    def apply(self, diff_result: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Apply planned changes inside a database transaction.
        Returns dict of applied counts and revision IDs.
        """
        pass

    @abc.abstractmethod
    def verify(self, apply_result: Dict[str, Any], conn: sqlite3.Connection) -> Tuple[bool, str]:
        """
        Perform strict post-write integrity assertions (verbatim checks, check 1-9 rules).
        Returns (passed: bool, error_msg: str).
        """
        pass

