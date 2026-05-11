import json
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.dns_verify import (
    SUPPORTED_CHANNELS,
    extract_domain_mappings,
    batch_verify,
    build_verify_results,
    add_verify_stats,
)


def load_ip_data(data_file):
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"找不到文件 {data_file}")
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)


def save_ip_data(data_file, data):
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_report(results, show_all=False):
    total = len(results)
    matched = sum(1 for r in results if r['status'] == 'matched')
    changed = sum(1 for r in results if r['status'] == 'changed')
    unresolved = sum(1 for r in results if r['status'] == 'unresolved')
    timeout = sum(1 for r in results if r['status'] == 'timeout')
    error = sum(1 for r in results if r['status'] == 'error')

    print("\n" + "=" * 70)
    print(f"域名映射验证报告")
    print("=" * 70)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总域名数: {total}")
    print(f"  ✅ 仍然匹配: {matched}")
    print(f"  🔄 已变更:   {changed}")
    print(f"  ❌ 无法解析: {unresolved}")
    print(f"  ⏱️  解析超时: {timeout}")
    print(f"  ⚠️  其他错误: {error}")
    print("=" * 70)

    if show_all:
        print(f"\n--- 所有域名验证结果 ---")
        for r in results:
            status_icon = {'matched': '✅', 'changed': '🔄', 'unresolved': '❌', 'timeout': '⏱️', 'error': '⚠️'}
            icon = status_icon.get(r['status'], '?')
            resolved_str = ', '.join(r['resolved_ips']) if r['resolved_ips'] else '(无)'
            print(f"  {icon} [{r['source']}] {r['domain']}")
            print(f"     原始IP: {r['original_ip']} -> 解析到: {resolved_str}")
    else:
        changed_results = [r for r in results if r['status'] == 'changed']
        unresolved_results = [r for r in results if r['status'] in ('unresolved', 'timeout')]

        if changed_results:
            print(f"\n--- 已变更的域名 ({len(changed_results)} 个) ---")
            for r in changed_results:
                resolved_str = ', '.join(r['resolved_ips']) if r['resolved_ips'] else '(无)'
                print(f"  🔄 [{r['source']}] {r['domain']}")
                print(f"     原始IP: {r['original_ip']} -> 当前解析到: {resolved_str}")

        if unresolved_results:
            print(f"\n--- 无法解析的域名 ({len(unresolved_results)} 个) ---")
            for r in unresolved_results:
                status_text = '超时' if r['status'] == 'timeout' else '无法解析'
                print(f"  ❌ [{r['source']}] {r['domain']} ({status_text})")

    print()


def main():
    parser = argparse.ArgumentParser(description='验证 IP-域名映射是否仍然有效')
    parser.add_argument('data_file', help='JSON 数据文件路径')
    parser.add_argument('--channel', choices=['aizhan', 'chinaz', 'all'], default='all',
                        help='验证哪些渠道的域名（默认: all）')
    parser.add_argument('--concurrency', type=int, default=10, help='并发线程数（默认: 10）')
    parser.add_argument('--timeout', type=float, default=3.0, help='DNS 解析超时秒数（默认: 3）')
    parser.add_argument('--dry-run', action='store_true', help='仅输出验证结果，不写回 JSON 文件')
    parser.add_argument('--show-all', action='store_true', help='显示所有域名验证结果（默认只显示变更/无法解析）')

    args = parser.parse_args()
    data_file = os.path.abspath(args.data_file)

    print(f"数据文件: {data_file}")

    channels = SUPPORTED_CHANNELS if args.channel == 'all' else (args.channel,)

    ip_data = load_ip_data(data_file)
    print(f"已加载 {len(ip_data)} 个 IP 条目")

    mappings = extract_domain_mappings(ip_data, channels)
    print(f"共提取 {len(mappings)} 个 IP-域名映射（渠道: {', '.join(channels)}）")

    if not mappings:
        print("没有需要验证的域名映射")
        return

    print(f"开始验证（并发: {args.concurrency}, 超时: {args.timeout}s）")
    print("-" * 70)

    def on_progress(done, total):
        print(f"\r验证进度: {done}/{total}", end='', flush=True)
        if done == total:
            print()

    verify_results = batch_verify(mappings, args.concurrency, args.timeout, progress_callback=on_progress)

    display_results = []
    for i, m in enumerate(mappings):
        vr = verify_results[i]
        display_results.append({
            'domain': vr['domain'],
            'source': ', '.join(m.get('sources', [m.get('source', '')])),
            'original_ip': m['target_ip'],
            'resolved_ips': vr['resolved_ips'],
            'status': vr['status'],
        })

    print_report(display_results, args.show_all)

    if not args.dry_run:
        grouped = build_verify_results(mappings, verify_results)
        verify_data = add_verify_stats(grouped)
        for ip, verify in verify_data.items():
            if ip in ip_data:
                ip_data[ip]['domain_verify'] = verify

        save_ip_data(data_file, ip_data)
        print(f"验证结果已写回: {data_file}")
    else:
        print("(dry-run 模式，未写回数据)")


if __name__ == "__main__":
    main()
