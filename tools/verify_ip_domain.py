import json
import os
import sys
import socket
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SUPPORTED_CHANNELS = ('aizhan', 'chinaz')


def load_ip_data(data_file):
    if not os.path.exists(data_file):
        print(f"错误: 找不到文件 {data_file}")
        sys.exit(1)
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)


def save_ip_data(data_file, data):
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_domain_mappings(ip_data, channels):
    mappings = []
    for ip, entry in ip_data.items():
        if not isinstance(entry, dict):
            continue
        for channel in channels:
            channel_data = entry.get(channel)
            if not isinstance(channel_data, dict):
                continue
            if not channel_data.get('success'):
                continue
            domains = channel_data.get('domains', [])
            for d in domains:
                if isinstance(d, dict) and d.get('domain'):
                    mappings.append({
                        'ip': ip,
                        'domain': d['domain'],
                        'source': channel,
                    })
                elif isinstance(d, str):
                    mappings.append({
                        'ip': ip,
                        'domain': d,
                        'source': channel,
                    })
    return mappings


def resolve_domain(domain, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        _, _, ip_list = socket.gethostbyname_ex(domain)
        return ip_list
    except socket.gaierror:
        return []
    except socket.timeout:
        return None
    except Exception:
        return []


def verify_one(mapping, timeout=3):
    ip = mapping['ip']
    domain = mapping['domain']
    source = mapping['source']
    resolved = resolve_domain(domain, timeout)

    if resolved is None:
        status = 'timeout'
    elif len(resolved) == 0:
        status = 'unresolved'
    elif ip in resolved:
        status = 'matched'
    else:
        status = 'changed'

    return {
        'domain': domain,
        'source': source,
        'original_ip': ip,
        'resolved_ips': resolved if resolved is not None else [],
        'status': status,
    }


def batch_verify(mappings, concurrency=10, timeout=3):
    results = []
    total = len(mappings)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {}
        for i, m in enumerate(mappings):
            future = executor.submit(verify_one, m, timeout)
            future_to_idx[future] = i

        done_count = 0
        for future in as_completed(future_to_idx):
            done_count += 1
            idx = future_to_idx[future]
            try:
                result = future.result()
            except Exception as e:
                m = mappings[idx]
                result = {
                    'domain': m['domain'],
                    'source': m['source'],
                    'original_ip': m['ip'],
                    'resolved_ips': [],
                    'status': 'error',
                }
            results.append((idx, result))
            if done_count % 50 == 0 or done_count == total:
                print(f"\r验证进度: {done_count}/{total}", end='', flush=True)

    print()
    results.sort(key=lambda x: x[0])
    return [r for _, r in results]


def build_verify_results(results):
    from collections import defaultdict
    ip_results = defaultdict(list)
    for r in results:
        ip_results[r['original_ip']].append(r)

    verify_data = {}
    for ip, items in ip_results.items():
        matched = sum(1 for r in items if r['status'] == 'matched')
        changed = sum(1 for r in items if r['status'] == 'changed')
        unresolved = sum(1 for r in items if r['status'] == 'unresolved')
        timeout = sum(1 for r in items if r['status'] == 'timeout')
        error = sum(1 for r in items if r['status'] == 'error')

        verify_data[ip] = {
            'verify_time': datetime.now().isoformat(),
            'total_domains': len(items),
            'matched': matched,
            'changed': changed,
            'unresolved': unresolved,
            'timeout': timeout,
            'error': error,
            'results': items,
        }
    return verify_data


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

    results = batch_verify(mappings, args.concurrency, args.timeout)

    print_report(results, args.show_all)

    if not args.dry_run:
        verify_data = build_verify_results(results)
        for ip, verify in verify_data.items():
            if ip in ip_data:
                ip_data[ip]['domain_verify'] = verify

        save_ip_data(data_file, ip_data)
        print(f"验证结果已写回: {data_file}")
    else:
        print("(dry-run 模式，未写回数据)")


if __name__ == "__main__":
    main()
