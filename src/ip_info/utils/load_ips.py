"""IP 列表文件加载工具。

处理 UTF-8 BOM、去空行、去重。
"""

from __future__ import annotations


def load_ips(file_path: str) -> list[str]:
    """从文件加载 IP 列表。

    Args:
        file_path: IP 文件路径，每行一个 IP。

    Returns:
        去重后的 IP 列表，保持原始顺序。
    """
    with open(file_path, encoding="utf-8-sig") as f:
        seen: set[str] = set()
        ips: list[str] = []
        for line in f:
            ip = line.strip()
            if ip and ip not in seen:
                seen.add(ip)
                ips.append(ip)
        return ips
