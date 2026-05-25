import json
import os
import sqlite3
import threading
from datetime import datetime, timezone


class SqliteDomainCache:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._local = threading.local()
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（线程安全）。"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def _init_db(self):
        """创建表和索引。"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS domain_cache (
                domain TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                resolved_ips TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

    def get(self, domain: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT status, resolved_ips, updated_at FROM domain_cache WHERE domain = ?", (domain,)
        ).fetchone()
        if row is None:
            return None
        status, resolved_ips_json, updated_at = row
        try:
            resolved_ips = json.loads(resolved_ips_json)
        except (json.JSONDecodeError, TypeError):
            return None
        return {
            "domain": domain,
            "status": status,
            "resolved_ips": resolved_ips,
            "verify_time": updated_at,
        }

    def set(self, domain: str, data: dict) -> None:
        status = data.get("status", "")
        resolved_ips = data.get("resolved_ips", [])
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
            (domain, status, json.dumps(resolved_ips, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
