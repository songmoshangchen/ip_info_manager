"""缓存转换 CLI 工具：JSON 与 SQLite 之间的互转。

用法:
    # Progress: 导出为 JSON
    python scripts/cache_converter.py progress export data/0518-0524/progress.db --output progress_backup.json

    # Progress: 从 JSON 导入
    python scripts/cache_converter.py progress import progress_backup.json data/0518-0524/progress.db

    # Progress: 从旧版 .progress 文本文件导入
    python scripts/cache_converter.py progress import-text \
        data/202604/202604_ip_data.trace_phase1.progress data/0518-0524/progress.db

    # Progress: 合并两个数据库
    python scripts/cache_converter.py progress merge data/202604/progress.db data/0518-0524/progress.db

    # Domain cache: 导出为 JSON
    python scripts/cache_converter.py domain export data/0518-0524/domain_cache.db --output domain_backup.json

    # Domain cache: 从 JSON 导入
    python scripts/cache_converter.py domain import domain_backup.json data/0518-0524/domain_cache.db
"""

import argparse
import os
import sys

# 将 src/ 添加到 sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from ip_info.utils.cache_converter import (  # noqa: E402
    clean_channel_for_ips,
    delete_progress_all,
    delete_progress_channel,
    export_domain_cache_to_json,
    export_progress_to_json,
    import_domain_cache_from_json,
    import_progress_from_json,
    import_progress_from_text,
    merge_progress_dbs,
)


def cmd_progress_export(args):
    stats = export_progress_to_json(args.db_path, args.output)
    print(f"[progress export] {stats}")


def cmd_progress_import(args):
    stats = import_progress_from_json(args.json_path, args.db_path)
    print(f"[progress import] {stats}")


def cmd_progress_import_text(args):
    stats = import_progress_from_text(args.text_path, args.db_path)
    print(f"[progress import-text] {stats}")


def cmd_progress_merge(args):
    stats = merge_progress_dbs(args.src_db, args.dst_db)
    print(f"[progress merge] {stats}")


def cmd_progress_delete_channel(args):
    deleted = delete_progress_channel(args.db_path, args.channel)
    print(f"[progress delete-channel] 已删除 {deleted} 条 {args.channel} 渠道记录")


def cmd_progress_delete_all(args):
    deleted = delete_progress_all(args.db_path)
    print(f"[progress delete-all] 已删除 {deleted} 条记录")


def cmd_progress_clean(args):
    """清理渠道数据：同时删除 progress.db 记录和 ip_data.json 数据。"""
    # 推断 ip_data.json 路径
    json_path = args.json_path
    if not json_path:
        # 默认与 progress.db 同目录
        dir_path = os.path.dirname(args.db_path)
        json_path = os.path.join(dir_path, "ip_data.json")

    if not os.path.exists(json_path):
        print(f"[progress clean] 错误: ip_data.json 不存在: {json_path}")
        return

    ips = None
    if args.ips:
        ips = [ip.strip() for ip in args.ips.split(",") if ip.strip()]

    result = clean_channel_for_ips(json_path, args.db_path, args.channel, ips)

    scope = f"IP {','.join(ips)}" if ips else "所有 IP"
    print(
        f"[progress clean] 已清理 {scope} 的 {args.channel} 渠道: "
        f"进度记录 {result['progress_deleted']} 条, 数据记录 {result['data_deleted']} 条"
    )


def cmd_domain_export(args):
    stats = export_domain_cache_to_json(args.db_path, args.output)
    print(f"[domain export] {stats}")


def cmd_domain_import(args):
    stats = import_domain_cache_from_json(args.json_path, args.db_path)
    print(f"[domain import] {stats}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="缓存转换工具：JSON 与 SQLite 之间的互转",
    )
    subparsers = parser.add_subparsers(dest="cache_type", required=True)

    # === progress 子命令 ===
    progress_parser = subparsers.add_parser("progress", help="进度缓存操作")
    progress_sub = progress_parser.add_subparsers(dest="action", required=True)

    # progress export
    p_export = progress_sub.add_parser("export", help="导出 progress.db 为 JSON")
    p_export.add_argument("db_path", help="progress.db 文件路径")
    p_export.add_argument("--output", "-o", required=True, help="输出 JSON 文件路径")
    p_export.set_defaults(func=cmd_progress_export)

    # progress import
    p_import = progress_sub.add_parser("import", help="从 JSON 导入到 progress.db")
    p_import.add_argument("json_path", help="输入 JSON 文件路径")
    p_import.add_argument("db_path", help="目标 progress.db 文件路径")
    p_import.set_defaults(func=cmd_progress_import)

    # progress import-text
    p_import_text = progress_sub.add_parser("import-text", help="从旧版 .progress 文本文件导入")
    p_import_text.add_argument("text_path", help="旧版 .progress 文本文件路径")
    p_import_text.add_argument("db_path", help="目标 progress.db 文件路径")
    p_import_text.set_defaults(func=cmd_progress_import_text)

    # progress merge
    p_merge = progress_sub.add_parser("merge", help="合并两个 progress.db")
    p_merge.add_argument("src_db", help="源 progress.db 文件路径")
    p_merge.add_argument("dst_db", help="目标 progress.db 文件路径")
    p_merge.set_defaults(func=cmd_progress_merge)

    # progress delete-channel
    p_del_ch = progress_sub.add_parser("delete-channel", help="删除指定渠道的进度记录")
    p_del_ch.add_argument("db_path", help="progress.db 文件路径")
    p_del_ch.add_argument("channel", help="要删除的渠道名称")
    p_del_ch.set_defaults(func=cmd_progress_delete_channel)

    # progress delete-all
    p_del_all = progress_sub.add_parser("delete-all", help="删除所有进度记录")
    p_del_all.add_argument("db_path", help="progress.db 文件路径")
    p_del_all.set_defaults(func=cmd_progress_delete_all)

    # progress clean (同时清理 progress.db + ip_data.json)
    p_clean = progress_sub.add_parser(
        "clean",
        help="清理渠道数据（同时删除 progress.db 记录和 ip_data.json 数据）",
    )
    p_clean.add_argument("db_path", help="progress.db 文件路径")
    p_clean.add_argument("channel", help="要清理的渠道名称")
    p_clean.add_argument("--ips", default="", help="指定 IP 列表（逗号分隔），不指定则清理所有 IP")
    p_clean.add_argument("--json-path", default="", help="ip_data.json 路径（默认与 progress.db 同目录）")
    p_clean.set_defaults(func=cmd_progress_clean)

    # === domain 子命令 ===
    domain_parser = subparsers.add_parser("domain", help="域名缓存操作")
    domain_sub = domain_parser.add_subparsers(dest="action", required=True)

    # domain export
    d_export = domain_sub.add_parser("export", help="导出 domain_cache.db 为 JSON")
    d_export.add_argument("db_path", help="domain_cache.db 文件路径")
    d_export.add_argument("--output", "-o", required=True, help="输出 JSON 文件路径")
    d_export.set_defaults(func=cmd_domain_export)

    # domain import
    d_import = domain_sub.add_parser("import", help="从 JSON 导入到 domain_cache.db")
    d_import.add_argument("json_path", help="输入 JSON 文件路径")
    d_import.add_argument("db_path", help="目标 domain_cache.db 文件路径")
    d_import.set_defaults(func=cmd_domain_import)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
