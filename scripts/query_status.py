"""查询项目进度 CLI 工具。

用法:
    python scripts/query_status.py <project_dir>           # 查看指定项目进度
    python scripts/query_status.py <project_dir> --json    # JSON 格式输出
    python scripts/query_status.py <project_dir> -c aizhan # 过滤指定渠道
    python scripts/query_status.py --list                  # 查看所有项目概览
"""

import argparse
import os
import sys

# 将 src/ 添加到 sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from ip_info.utils.query_status import (  # noqa: E402
    compute_progress,
    format_json,
    format_table,
    load_ip_count,
    query_channel_counts,
    query_domain_cache_count,
)


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


def main():
    parser = argparse.ArgumentParser(description="查询 IP 信息采集项目进度")
    parser.add_argument("project_dir", nargs="?", help="项目目录路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("-c", "--channel", default="", help="过滤指定渠道")
    parser.add_argument("--list", action="store_true", help="查看所有项目概览")
    parser.add_argument("--data-dir", default="data", help="数据根目录（默认 data/）")
    args = parser.parse_args()

    if args.list:
        print(list_projects(args.data_dir))
    elif args.project_dir:
        print(query_project(args.project_dir, args.channel, args.json))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
