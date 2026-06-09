"""标签数据源更新状态检查。"""

import json
import os
from datetime import datetime

STATUS_FILE = ".update_status.json"


def load_update_status(config_dir: str) -> dict:
    """加载每个源的更新状态。

    Returns:
        dict: {filename: {"updated_at": "YYYY-MM-DD HH:MM", "status": "success"|"failed"|"skipped", "size": int}}
    """
    status_path = os.path.join(config_dir, STATUS_FILE)
    if not os.path.exists(status_path):
        return {}
    with open(status_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_tagger_update_status(config_dir: str) -> dict:
    """检查标签数据源的更新状态。

    基于 .update_status.json 中每个源的最新更新时间判断：
    - up_to_date: 所有源本月都已成功更新
    - stale: 部分源本月未更新
    - never_updated: 从未更新过

    Args:
        config_dir: 标签配置文件目录 (config/ip_tagger)

    Returns:
        dict: {
            "status": "up_to_date" | "stale" | "never_updated",
            "total": int,
            "updated_this_month": int,
            "failed_count": int,
            "never_updated_count": int,
            "current_month": "YYYY-MM",
            "message": str
        }
    """
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"

    update_status = load_update_status(config_dir)

    if not update_status:
        return {
            "status": "never_updated",
            "total": 0,
            "updated_this_month": 0,
            "failed_count": 0,
            "never_updated_count": 0,
            "current_month": current_month,
            "message": ("标签数据源从未更新，建议运行: python scripts/ip_tagger_updater.py --from-git"),
        }

    total = len(update_status)
    updated_this_month = 0
    failed_count = 0
    never_updated_count = 0

    for info in update_status.values():
        status = info.get("status", "")
        updated_at = info.get("updated_at", "")

        if status == "failed":
            failed_count += 1
        elif status == "success" and updated_at.startswith(current_month):
            updated_this_month += 1
        elif status == "skipped" and updated_at.startswith(current_month):
            # skipped 也算已检查
            updated_this_month += 1
        else:
            never_updated_count += 1

    if never_updated_count == 0 and failed_count == 0:
        return {
            "status": "up_to_date",
            "total": total,
            "updated_this_month": updated_this_month,
            "failed_count": 0,
            "never_updated_count": 0,
            "current_month": current_month,
            "message": f"标签数据源已是最新 ({updated_this_month}/{total} 本月已更新)",
        }

    status = "stale"
    if updated_this_month == 0 and failed_count == total:
        status = "never_updated"

    parts = []
    if never_updated_count > 0:
        parts.append(f"{never_updated_count} 个源本月未更新")
    if failed_count > 0:
        parts.append(f"{failed_count} 个源更新失败")

    return {
        "status": status,
        "total": total,
        "updated_this_month": updated_this_month,
        "failed_count": failed_count,
        "never_updated_count": never_updated_count,
        "current_month": current_month,
        "message": (
            f"标签数据源需要更新 ({'，'.join(parts)})，建议运行: python scripts/ip_tagger_updater.py --from-git"
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
        f"    本月已更新: {result['updated_this_month']}/{result['total']}",
    ]
    if result["failed_count"] > 0:
        lines.append(f"    更新失败: {result['failed_count']} 个源")
    if result["never_updated_count"] > 0:
        lines.append(f"    本月未更新: {result['never_updated_count']} 个源")
    lines.extend(
        [
            "",
            "    建议运行更新命令:",
            "    python scripts/ip_tagger_updater.py --from-git",
            "",
            "    仅更新指定源:",
            "    python scripts/ip_tagger_updater.py --source <文件名或标签名>",
            "",
            "    查看各源状态:",
            "    python scripts/ip_tagger_updater.py --status",
            "=" * 70,
            "",
        ]
    )
    return "\n".join(lines)
