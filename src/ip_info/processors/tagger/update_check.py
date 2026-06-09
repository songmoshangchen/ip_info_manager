"""标签数据源更新状态检查。"""

import os
import time


def check_tagger_update_status(config_dir: str) -> dict:
    """检查标签数据源的更新状态。

    Args:
        config_dir: 标签配置文件目录 (config/ip_tagger)

    Returns:
        dict: {
            "status": "up_to_date" | "stale" | "never_updated",
            "last_update": "YYYY-MM" | None,
            "current_month": "YYYY-MM",
            "message": str
        }
    """
    now = time.localtime()
    current_month = f"{now.tm_year}-{now.tm_mon:02d}"

    marker_path = os.path.join(config_dir, ".last_update")

    if not os.path.exists(marker_path):
        return {
            "status": "never_updated",
            "last_update": None,
            "current_month": current_month,
            "message": ("标签数据源从未更新，建议运行: python scripts/ip_tagger_updater.py --from-git"),
        }

    with open(marker_path, "r", encoding="utf-8") as f:
        last_update = f.read().strip()

    if last_update == current_month:
        return {
            "status": "up_to_date",
            "last_update": last_update,
            "current_month": current_month,
            "message": f"标签数据源已是最新 ({last_update})",
        }

    return {
        "status": "stale",
        "last_update": last_update,
        "current_month": current_month,
        "message": (
            f"标签数据源已过期 (上次更新: {last_update}，当前: {current_month})，"
            "建议运行: python scripts/ip_tagger_updater.py --from-git"
        ),
    }


def format_update_warning(result: dict) -> str:
    """格式化更新警告信息，使用醒目格式。

    Args:
        result: check_tagger_update_status() 的返回值

    Returns:
        醒目的警告字符串
    """
    if result["status"] == "up_to_date":
        return ""

    lines = [
        "",
        "=" * 70,
        ">>> 标签数据源更新提醒 <<<",
        "=" * 70,
        f"    状态: {result['status']}",
        f"    上次更新: {result['last_update'] or '从未更新'}",
        f"    当前月份: {result['current_month']}",
        "",
        "    建议运行更新命令:",
        "    python scripts/ip_tagger_updater.py --from-git",
        "=" * 70,
        "",
    ]
    return "\n".join(lines)
