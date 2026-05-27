import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import Settings
from reader import IPReader

AI_CATEGORIES = {'other', 'cloud_provider', 'residential'}
DEFAULT_BATCH_SIZE = 10
CHANNEL_NAME = 'ai_analysis'
OUTPUT_FIELDS = ['net_type', 'trace_value', 'action', 'note']


def _build_reader():
    prefix = Settings().trace_ip_project_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'trace_ip', prefix)
    scenario_settings = Settings().model_copy(update={'storage_name': prefix})
    return IPReader(settings=scenario_settings, storage_dir=output_dir)


def _load_all_ip_data(reader):
    all_data = reader._load_data()
    return all_data


def _filter_ips(all_data, categories=None, skip_analyzed=True):
    if categories is None:
        categories = AI_CATEGORIES

    filtered = []
    for ip in sorted(all_data.keys()):
        info = all_data[ip]
        classify = info.get('trace_classify', {})
        cat = classify.get('category', '')
        if cat not in categories:
            continue
        if skip_analyzed and CHANNEL_NAME in info:
            continue
        filtered.append(ip)
    return filtered


def batch(size=DEFAULT_BATCH_SIZE, offset=0, categories=None):
    reader = _build_reader()

    all_data = _load_all_ip_data(reader)
    if not all_data:
        print('没有找到任何IP数据。')
        return []

    filtered = _filter_ips(all_data, categories=categories, skip_analyzed=True)
    total = len(filtered)

    if offset >= total:
        print(f'偏移量 {offset} 超出范围，共 {total} 个待研判IP。')
        return []

    batch_ips = filtered[offset:offset + size]
    actual_size = len(batch_ips)

    print(f'待研判IP总数: {total}，本次读取: {actual_size} 个（偏移: {offset}）')
    print('=' * 60)

    results = []
    for ip in batch_ips:
        ip_data = all_data[ip]
        results.append(ip_data)
        print(json.dumps(ip_data, ensure_ascii=False, indent=2))
        print('-' * 60)

    return results


def count(categories=None):
    reader = _build_reader()

    all_data = _load_all_ip_data(reader)
    if not all_data:
        print('没有找到任何IP数据。')
        return

    analyzed = 0
    pending = 0
    cat_stats = {}

    for ip in sorted(all_data.keys()):
        info = all_data[ip]
        classify = info.get('trace_classify', {})
        cat = classify.get('category', '')
        if cat not in (categories or AI_CATEGORIES):
            continue
        cat_label = classify.get('label', cat)
        cat_stats[cat_label] = cat_stats.get(cat_label, 0) + 1
        if CHANNEL_NAME in info:
            analyzed += 1
        else:
            pending += 1

    total = analyzed + pending
    print(f'需要AI研判的IP总数: {total}')
    print(f'  已完成研判: {analyzed}')
    print(f'  待研判:     {pending}')
    if cat_stats:
        print('分类分布:')
        for label, cnt in sorted(cat_stats.items(), key=lambda x: -x[1]):
            print(f'  {label}: {cnt}')


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='AI研判辅助工具 - 批量读取待研判IP数据')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    batch_parser = subparsers.add_parser('batch', help='批量读取待研判IP数据')
    batch_parser.add_argument(
        '--size', type=int, default=DEFAULT_BATCH_SIZE,
        help=f'每批读取数量（默认 {DEFAULT_BATCH_SIZE}）')
    batch_parser.add_argument(
        '--offset', type=int, default=0,
        help='偏移量（默认 0）')
    batch_parser.add_argument(
        '--categories', type=str, default=None,
        help='筛选分类，逗号分隔（默认 other,cloud_provider,residential）')
    batch_parser.add_argument(
        '--include-analyzed', action='store_true',
        help='包含已完成研判的IP')

    count_parser = subparsers.add_parser('count', help='统计待研判IP数量')
    count_parser.add_argument(
        '--categories', type=str, default=None,
        help='筛选分类，逗号分隔（默认 other,cloud_provider,residential）')

    args = parser.parse_args()

    categories = None
    if args.categories:
        categories = set(args.categories.split(','))

    if args.command == 'batch':
        batch(
            size=args.size,
            offset=args.offset,
            categories=categories,
        )
    elif args.command == 'count':
        count(categories=categories)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
