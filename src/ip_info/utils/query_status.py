"""查询进度查看工具。

纯静态查询 progress.db 和 domain_cache.db，不依赖 Channel/Pipeline 代码。
"""

from __future__ import annotations

import json
import os
import sqlite3


def query_channel_counts(db_path: str) -> dict[str, int]:
    """查询 progress.db 中各渠道的已完成 IP 数量。"""
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT channel, COUNT(*) FROM progress GROUP BY channel").fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


def compute_progress(total_ips: int, channel_counts: dict[str, int]) -> dict[str, dict]:
    """给定 IP 总数和渠道完成数，计算剩余和完成率。"""
    result = {}
    for channel, completed in channel_counts.items():
        capped = min(completed, total_ips)
        remaining = max(0, total_ips - capped)
        percentage = round(min(capped / total_ips * 100, 100.0), 1) if total_ips > 0 else 0.0
        result[channel] = {
            "completed": capped,
            "remaining": remaining,
            "percentage": percentage,
        }
    return result


def query_domain_cache_count(db_path: str) -> int:
    """查询 domain_cache.db 中的记录数。"""
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        (count,) = conn.execute("SELECT COUNT(*) FROM domain_cache").fetchone()
        return count
    finally:
        conn.close()


def load_ip_count(project_dir: str) -> int:
    """从项目目录获取 IP 总数。优先读 ips.txt，其次读 ip_data.json。"""
    ips_file = os.path.join(project_dir, "ips.txt")
    if os.path.exists(ips_file):
        with open(ips_file, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    json_file = os.path.join(project_dir, "ip_data.json")
    if os.path.exists(json_file):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        return len(data)

    return 0


def format_table(project: str, total_ips: int, progress: dict[str, dict], domain_cache_count: int) -> str:
    """格式化终端表格输出。"""
    lines = [
        f"项目进度: {project}",
        f"IP 总数: {total_ips}",
        "=" * 60,
        f"{'渠道':<20} {'已完成':>8} {'剩余':>8} {'完成率':>8}",
        "-" * 60,
    ]
    for channel, info in sorted(progress.items()):
        lines.append(f"{channel:<20} {info['completed']:>8} {info['remaining']:>8} {info['percentage']:>7.1f}%")
    lines.append("-" * 60)
    lines.append(f"域名缓存: {domain_cache_count} 条记录")
    return "\n".join(lines)


def format_json(project: str, total_ips: int, progress: dict[str, dict], domain_cache_count: int) -> str:
    """格式化 JSON 输出。"""
    data = {
        "project": project,
        "total_ips": total_ips,
        "channels": progress,
        "domain_cache_count": domain_cache_count,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def query_project(project_dir: str, channel_filter: str = "", as_json: bool = False) -> str:
    """查询单个项目的进度。"""
    project_dir = os.path.abspath(project_dir)
    project_name = os.path.basename(project_dir)

    progress_db = os.path.join(project_dir, "progress.db")
    domain_cache_db = os.path.join(project_dir, "domain_cache.db")

    total_ips = load_ip_count(project_dir)
    channel_counts = query_channel_counts(progress_db)

    if channel_filter:
        channel_counts = {k: v for k, v in channel_counts.items() if k == channel_filter}

    progress = compute_progress(total_ips, channel_counts)
    domain_count = query_domain_cache_count(domain_cache_db)

    if as_json:
        return format_json(project_name, total_ips, progress, domain_count)
    return format_table(project_name, total_ips, progress, domain_count)


def list_projects(data_dir: str = "data") -> str:
    """扫描 data/ 目录下所有包含 progress.db 的子目录，输出概览。"""
    data_dir = os.path.abspath(data_dir)
    if not os.path.isdir(data_dir):
        return f"数据目录不存在: {data_dir}"

    projects = []
    for name in sorted(os.listdir(data_dir)):
        subdir = os.path.join(data_dir, name)
        if not os.path.isdir(subdir):
            continue
        progress_db = os.path.join(subdir, "progress.db")
        if not os.path.exists(progress_db):
            continue

        total_ips = load_ip_count(subdir)
        channel_counts = query_channel_counts(progress_db)
        progress = compute_progress(total_ips, channel_counts)

        if progress:
            overall = sum(v["percentage"] for v in progress.values()) / len(progress)
        else:
            overall = 0.0

        projects.append(
            {
                "name": name,
                "total_ips": total_ips,
                "channels": len(progress),
                "overall": round(overall, 1),
            }
        )

    if not projects:
        return "未找到包含 progress.db 的项目"

    lines = [
        f"{'项目':<30} {'IP数':>6} {'渠道数':>6} {'整体完成率':>10}",
        "-" * 60,
    ]
    for p in projects:
        lines.append(f"{p['name']:<30} {p['total_ips']:>6} {p['channels']:>6} {p['overall']:>9.1f}%")
    return "\n".join(lines)
