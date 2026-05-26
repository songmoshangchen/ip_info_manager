"""缓存转换工具：JSON 与 SQLite 之间的互转。

支持 progress 和 domain_cache 两种缓存的导入/导出/合并操作。
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ConvertStats:
    """转换操作统计信息。"""

    exported: int = 0
    imported: int = 0
    skipped: int = 0

    def __str__(self) -> str:
        parts = []
        if self.exported:
            parts.append(f"导出 {self.exported} 条")
        if self.imported:
            parts.append(f"导入 {self.imported} 条")
        if self.skipped:
            parts.append(f"跳过 {self.skipped} 条")
        return "，".join(parts) if parts else "无操作"


def _ensure_progress_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
    )
    conn.commit()


def _ensure_domain_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS domain_cache "
        "(domain TEXT PRIMARY KEY, status TEXT NOT NULL, resolved_ips TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.commit()


def _count_progress(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]


def _count_domain_cache(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM domain_cache").fetchone()[0]


def export_progress_to_json(db_path: str, output_path: str) -> ConvertStats:
    """将 progress.db 导出为 JSON 文件。"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
    conn.close()

    records = [{"ip": ip, "channel": channel} for ip, channel in rows]

    data = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "source": db_path,
        "records": records,
    }

    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return ConvertStats(exported=len(records))


def import_progress_from_json(json_path: str, db_path: str) -> ConvertStats:
    """从 JSON 文件导入到 progress.db。"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])

    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    _ensure_progress_table(conn)

    before = _count_progress(conn)

    conn.executemany(
        "INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)",
        [(r["ip"], r["channel"]) for r in records],
    )
    conn.commit()

    after = _count_progress(conn)
    conn.close()

    imported = after - before
    skipped = len(records) - imported

    return ConvertStats(imported=imported, skipped=skipped)


def import_progress_from_text(text_path: str, db_path: str) -> ConvertStats:
    """从旧版 .progress 文本文件导入到 progress.db。

    文件格式: 每行一条记录，格式为 ip\\tchannel
    当 channel 为空时，格式为 ip（兼容旧格式）
    """
    records: list[tuple[str, str]] = []

    try:
        with open(text_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "\t" in line:
                    ip, channel = line.split("\t", 1)
                    records.append((ip, channel))
                else:
                    records.append((line, ""))
    except FileNotFoundError:
        return ConvertStats()

    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    _ensure_progress_table(conn)

    before = _count_progress(conn)

    conn.executemany("INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)", records)
    conn.commit()

    after = _count_progress(conn)
    conn.close()

    imported = after - before
    skipped = len(records) - imported

    return ConvertStats(imported=imported, skipped=skipped)


def merge_progress_dbs(src_db: str, dst_db: str) -> ConvertStats:
    """将源 progress.db 的记录合并到目标 progress.db。"""
    src_conn = sqlite3.connect(src_db)
    rows = src_conn.execute("SELECT ip, channel FROM progress").fetchall()
    src_conn.close()

    parent_dir = os.path.dirname(dst_db)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    dst_conn = sqlite3.connect(dst_db)
    _ensure_progress_table(dst_conn)

    before = _count_progress(dst_conn)

    dst_conn.executemany("INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)", rows)
    dst_conn.commit()

    after = _count_progress(dst_conn)
    dst_conn.close()

    imported = after - before
    skipped = len(rows) - imported

    return ConvertStats(imported=imported, skipped=skipped)


def export_domain_cache_to_json(db_path: str, output_path: str) -> ConvertStats:
    """将 domain_cache.db 导出为 JSON 文件。"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT domain, status, resolved_ips, updated_at FROM domain_cache ORDER BY domain").fetchall()
    conn.close()

    records = []
    for domain, status, resolved_ips_json, updated_at in rows:
        try:
            resolved_ips = json.loads(resolved_ips_json)
        except (json.JSONDecodeError, TypeError):
            resolved_ips = []
        records.append(
            {
                "domain": domain,
                "status": status,
                "resolved_ips": resolved_ips,
                "updated_at": updated_at,
            }
        )

    data = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "source": db_path,
        "records": records,
    }

    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return ConvertStats(exported=len(records))


def import_domain_cache_from_json(json_path: str, db_path: str) -> ConvertStats:
    """从 JSON 文件导入到 domain_cache.db。"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])

    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    _ensure_domain_cache_table(conn)

    before = _count_domain_cache(conn)

    rows = [
        (
            r["domain"],
            r["status"],
            json.dumps(r["resolved_ips"], ensure_ascii=False),
            r["updated_at"],
        )
        for r in records
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()

    after = _count_domain_cache(conn)
    conn.close()

    imported = after - before
    skipped = len(records) - imported

    return ConvertStats(imported=imported, skipped=skipped)


def delete_progress_channel(db_path: str, channel: str) -> int:
    """删除 progress.db 中指定渠道的所有记录。返回删除数量。"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("DELETE FROM progress WHERE channel = ?", (channel,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    return deleted


def delete_progress_all(db_path: str) -> int:
    """删除 progress.db 中所有记录。返回删除数量。"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("DELETE FROM progress")
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    return deleted
