"""verify_mapping 脚本的辅助工具函数。

提供 IP-域名映射解析、ip_data.json 提取、报告格式化等功能。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

SUPPORTED_CHANNELS = ("aizhan", "chinaz")


def parse_mappings_from_args(args: list[str]) -> list[dict]:
    """从命令行参数列表中解析 IP-域名对。

    每个参数格式为 "IP DOMAIN"，空格分隔。

    Args:
        args: 命令行参数列表。

    Returns:
        去重后的映射列表，每项包含 ip 和 domain。
    """
    seen: set[tuple[str, str]] = set()
    mappings: list[dict] = []
    for arg in args:
        parts = arg.strip().split()
        if len(parts) < 2:
            continue
        ip, domain = parts[0], parts[1]
        key = (ip, domain)
        if key in seen:
            continue
        seen.add(key)
        mappings.append({"ip": ip, "domain": domain})
    return mappings


def parse_mappings_from_file(filepath: str) -> list[dict]:
    """从文本文件解析 IP-域名对。

    每行格式为 "IP DOMAIN"，跳过空行和以 # 开头的注释行。

    Args:
        filepath: 文本文件路径。

    Returns:
        去重后的映射列表。
    """
    if not os.path.isfile(filepath):
        logger.warning("文件不存在: %s", filepath)
        return []

    seen: set[tuple[str, str]] = set()
    mappings: list[dict] = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            ip, domain = parts[0], parts[1]
            key = (ip, domain)
            if key in seen:
                continue
            seen.add(key)
            mappings.append({"ip": ip, "domain": domain})
    return mappings


def extract_mappings_from_ip_data(filepath: str) -> list[dict]:
    """从 ip_data.json 提取 IP-域名映射。

    遍历 aizhan 和 chinaz 渠道的 domains 字段。

    Args:
        filepath: ip_data.json 文件路径。

    Returns:
        映射列表，每项包含 ip、domain 和 sources。
    """
    if not os.path.isfile(filepath):
        logger.warning("文件不存在: %s", filepath)
        return []

    try:
        with open(filepath, encoding="utf-8") as f:
            store = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("读取文件失败: %s -> %s", filepath, e)
        return []

    mappings: list[dict] = []
    for ip, ip_data in store.items():
        if not isinstance(ip_data, dict):
            continue
        for channel in SUPPORTED_CHANNELS:
            channel_data = ip_data.get(channel)
            if not isinstance(channel_data, dict):
                continue
            domains = channel_data.get("domains", [])
            if not domains:
                continue
            for d in domains:
                domain = d if isinstance(d, str) else d.get("domain", "")
                if domain:
                    mappings.append({"ip": ip, "domain": domain, "sources": [channel]})
    return mappings


def format_report(verify_results: list[dict]) -> str:
    """格式化验证报告。

    Args:
        verify_results: 验证结果列表，每项包含 domain、target_ip、status、resolved_ips。

    Returns:
        格式化的报告字符串。
    """
    total = len(verify_results)
    matched = sum(1 for r in verify_results if r["status"] == "matched")
    changed = sum(1 for r in verify_results if r["status"] == "changed")
    unresolved = sum(1 for r in verify_results if r["status"] == "unresolved")
    timeout = sum(1 for r in verify_results if r["status"] == "timeout")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "域名映射验证报告",
        "=" * 60,
        f"验证时间: {now_str}",
        f"总映射数: {total}",
        f"  ✅ 仍然匹配: {matched}",
        f"  🔄 已变更:   {changed}",
        f"  ❌ 无法解析: {unresolved}",
        f"  ⏱️  解析超时: {timeout}",
        "=" * 60,
    ]

    if changed > 0:
        lines.append("")
        lines.append(f"--- 已变更的域名 ({changed} 个) ---")
        for r in verify_results:
            if r["status"] == "changed":
                resolved_str = ", ".join(r["resolved_ips"]) if r["resolved_ips"] else "无"
                lines.append(f"  🔄 {r['domain']}")
                lines.append(f"     原始IP: {r['target_ip']} -> 当前解析到: {resolved_str}")

    return "\n".join(lines)
