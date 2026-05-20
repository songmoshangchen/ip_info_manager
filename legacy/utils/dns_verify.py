import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable

logger = logging.getLogger('ip_info_manager.utils.dns_verify')

SUPPORTED_CHANNELS = ('aizhan', 'chinaz')


def resolve_domain(domain: str, timeout: float = 3.0) -> list | None:
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


def verify_one(domain: str, target_ip: str, timeout: float = 3.0) -> dict:
    resolved = resolve_domain(domain, timeout)

    if resolved is None:
        status = 'timeout'
    elif len(resolved) == 0:
        status = 'unresolved'
    elif target_ip in resolved:
        status = 'matched'
    else:
        status = 'changed'

    return {
        'domain': domain,
        'status': status,
        'resolved_ips': resolved if resolved is not None else [],
    }


def batch_verify(
    candidates: list[dict],
    timeout: float = 3.0,
    concurrency: int = 10,
    progress_callback: Callable = None,
) -> list[dict]:
    results = []
    total = len(candidates)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {}
        for i, item in enumerate(candidates):
            future = executor.submit(
                verify_one, item['domain'], item['target_ip'], timeout)
            future_to_idx[future] = i

        done_count = 0
        for future in as_completed(future_to_idx):
            done_count += 1
            idx = future_to_idx[future]
            try:
                result = future.result()
            except Exception as e:
                item = candidates[idx]
                result = {
                    'domain': item['domain'],
                    'status': 'error',
                    'resolved_ips': [],
                }
                logger.warning("DNS验证异常: %s -> %s", item['domain'], e)

            results.append((idx, result))
            if progress_callback:
                progress_callback(done_count, total)

    results.sort(key=lambda x: x[0])
    return [r for _, r in results]


def build_verify_results(
    candidates: list[dict],
    verify_results: list[dict],
) -> dict[str, list]:
    ip_results = {}
    for i, candidate in enumerate(candidates):
        ip = candidate['target_ip']
        domain = candidate['domain']
        sources = candidate.get('sources', [])
        vr = verify_results[i]

        if ip not in ip_results:
            ip_results[ip] = []

        ip_results[ip].append({
            'domain': domain,
            'sources': sources,
            'status': vr['status'],
            'resolved_ips': vr['resolved_ips'],
        })

    return ip_results


def add_verify_stats(grouped_results: dict[str, list]) -> dict[str, dict]:
    verify_data = {}
    for ip, items in grouped_results.items():
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


def extract_domain_mappings(
    ip_data: dict,
    channels: tuple = SUPPORTED_CHANNELS,
) -> list[dict]:
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
                        'domain': d['domain'],
                        'target_ip': ip,
                        'sources': [channel],
                    })
                elif isinstance(d, str):
                    mappings.append({
                        'domain': d,
                        'target_ip': ip,
                        'sources': [channel],
                    })
    return mappings
