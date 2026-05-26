"""quick_query 脚本的辅助工具函数。

提供 IP 解析、输出目录生成、Phase 参数解析等功能。
"""

from __future__ import annotations

import ipaddress
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Phase 依赖关系：Phase N 需要 Phase dependencies[N] 的结果
_PHASE_DEPENDENCIES: dict[int, set[int]] = {
    2: {1},
    3: {2},
    4: {3},
}

ALL_PHASES: set[int] = {1, 2, 3, 4}


def parse_ips_from_args(args: list[str]) -> list[str]:
    """从命令行参数列表中解析有效 IP 地址。

    跳过以 -- 开头的标志参数，校验 IP 格式，去重保持顺序。

    Args:
        args: 命令行参数列表（不含脚本名）。

    Returns:
        去重后的有效 IP 列表，保持原始顺序。
    """
    seen: set[str] = set()
    ips: list[str] = []
    for arg in args:
        if arg.startswith("--"):
            continue
        try:
            ipaddress.ip_address(arg)
        except ValueError:
            continue
        if arg not in seen:
            seen.add(arg)
            ips.append(arg)
    return ips


def generate_output_dir(base_dir: str | None = None) -> str:
    """自动生成时间戳命名的输出目录并创建。

    Args:
        base_dir: 基础目录路径，默认为项目根目录下的 data/quick。

    Returns:
        生成的目录绝对路径。
    """
    if base_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        base_dir = os.path.join(project_root, "data", "quick")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def parse_phases(phase_str: str | None) -> set[int]:
    """解析 --phase 参数，自动补全依赖 Phase。

    Phase 依赖关系：
    - Phase 2 需要 Phase 1 结果
    - Phase 3 需要 Phase 2 分类
    - Phase 4 需要 Phase 3 结果

    Args:
        phase_str: 逗号分隔的 Phase 编号字符串，如 "1,3"。
                   None 或空字符串表示执行所有 Phase。

    Returns:
        包含所有需要执行的 Phase 编号集合。
    """
    if not phase_str:
        return set(ALL_PHASES)

    phases: set[int] = set()
    for part in phase_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            continue
        if n in ALL_PHASES:
            phases.add(n)

    # 自动补全依赖
    changed = True
    while changed:
        changed = False
        for phase in list(phases):
            deps = _PHASE_DEPENDENCIES.get(phase, set())
            for dep in deps:
                if dep not in phases:
                    phases.add(dep)
                    changed = True

    return phases
