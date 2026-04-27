import argparse
import ipaddress
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import Settings
from utils.logger_utils import get_batch_logger

_logger = get_batch_logger('ip_tagger')

BATCH_SIZE = 256


def load_manifest(manifest_path: str, level: int = None) -> list[dict]:
    if not os.path.exists(manifest_path):
        print(f"错误: 清单文件不存在: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    labels = [item['label'] for item in manifest]
    if len(labels) != len(set(labels)):
        dup = [l for l in labels if labels.count(l) > 1]
        print(f"错误: manifest.json 中存在重复标签名: {set(dup)}")
        sys.exit(1)

    if level is not None:
        manifest = [item for item in manifest if item.get('level', 1) <= level]

    return manifest


def validate_manifest(manifest: list[dict], config_dir: str):
    missing = []
    for item in manifest:
        fpath = os.path.join(config_dir, item['file'])
        if not os.path.exists(fpath):
            missing.append(item['file'])
    if missing:
        print(f"错误: 以下配置文件缺失: {', '.join(missing)}")
        print(f"请先运行: python tools/ip_tagger_updater.py")
        sys.exit(1)


def read_ip_file(ip_file: str) -> list[str]:
    ips = []
    with open(ip_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                ips.append(line)
    return ips


def ip_to_int(ip_str: str) -> int | None:
    try:
        return int(ipaddress.ip_address(ip_str))
    except (ValueError, TypeError):
        return None


def parse_entry_to_range(entry: str) -> tuple[int, int] | None:
    try:
        network = ipaddress.ip_network(entry, strict=False)
        return (int(network.network_address), int(network.broadcast_address))
    except ValueError:
        pass
    try:
        ip_obj = ipaddress.ip_address(entry)
        val = int(ip_obj)
        return (val, val)
    except ValueError:
        return None


def match_sorted_ips_streaming(
    sorted_ip_ints: list[tuple[str, int]],
    dataset_path: str,
    batch_size: int = BATCH_SIZE,
) -> set[int]:
    matched_indices = set()
    ip_ptr = 0
    total_ips = len(sorted_ip_ints)

    with open(dataset_path, 'r', encoding='utf-8', buffering=8192) as f:
        batch = []
        for line in f:
            if ip_ptr >= total_ips:
                break

            line = line.strip()
            if not line or line.startswith('#'):
                continue

            r = parse_entry_to_range(line)
            if r is None:
                continue

            batch.append(r)

            if len(batch) >= batch_size:
                batch.sort(key=lambda x: x[0])
                ip_ptr = _process_batch(batch, sorted_ip_ints, ip_ptr, total_ips, matched_indices)
                batch = []

        if batch and ip_ptr < total_ips:
            batch.sort(key=lambda x: x[0])
            ip_ptr = _process_batch(batch, sorted_ip_ints, ip_ptr, total_ips, matched_indices)

    return matched_indices


def _process_batch(
    batch: list[tuple[int, int]],
    sorted_ip_ints: list[tuple[str, int]],
    ip_ptr: int,
    total_ips: int,
    matched_indices: set[int],
) -> int:
    for range_start, range_end in batch:
        while ip_ptr < total_ips:
            _, ip_int = sorted_ip_ints[ip_ptr]
            if ip_int < range_start:
                ip_ptr += 1
            elif ip_int <= range_end:
                matched_indices.add(ip_ptr)
                ip_ptr += 1
            else:
                break
    return ip_ptr


def process_all_tags(
    ip_list: list[str],
    manifest: list[dict],
    config_dir: str,
) -> dict[str, list[dict]]:
    _logger.info(f"开始处理 {len(ip_list)} 个 IP，共 {len(manifest)} 个标签源")

    valid_items = []
    invalid_count = 0
    for ip_str in ip_list:
        val = ip_to_int(ip_str)
        if val is not None:
            valid_items.append((ip_str, val))
        else:
            invalid_count += 1
            _logger.warning(f"跳过无效 IP: {ip_str}")

    valid_items.sort(key=lambda x: x[1])
    _logger.info(f"有效 IP: {len(valid_items)}，无效 IP: {invalid_count}")

    ip_tags: dict[str, list[dict]] = {}

    total = len(manifest)
    for idx, item in enumerate(manifest):
        label = item['label']
        source_file = item['file']
        dataset_path = os.path.join(config_dir, source_file)

        _logger.info(f"[{idx + 1}/{total}] 加载标签源: {label} ({source_file})")
        t0 = time.time()

        matched = match_sorted_ips_streaming(valid_items, dataset_path)
        elapsed = time.time() - t0
        _logger.info(f"  匹配完成: {len(matched)} 个 IP 命中，耗时 {elapsed:.2f}s")

        for match_idx in matched:
            ip_str = valid_items[match_idx][0]
            if ip_str not in ip_tags:
                ip_tags[ip_str] = []
            ip_tags[ip_str].append({"label": label, "source": source_file})

    _logger.info(f"全部标签源处理完成: {len(ip_tags)}/{len(valid_items)} 个 IP 命中至少一个标签")

    return ip_tags


def _resolve_json_path(output: str = None) -> str:
    if output:
        return output

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings = Settings()
    base = os.path.join(project_root, 'data')
    if settings.storage_dir:
        s_dir = os.path.join(base, settings.storage_dir)
    else:
        s_dir = base
    return os.path.join(s_dir, settings.storage_name + '.json')


def write_matched_tags(
    ip_tags: dict[str, list[dict]],
    mode: str,
    output: str = None,
):
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    json_path = _resolve_json_path(output)

    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            data = json.loads(content) if content else {}
    else:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        data = {}

    written = 0

    for ip_str, details in ip_tags.items():
        if not details:
            continue

        labels = [d['label'] for d in details]

        if ip_str not in data:
            data[ip_str] = {"ip": ip_str}

        if mode == 'overwrite' or 'tags' not in data[ip_str]:
            data[ip_str]['tags'] = {
                "labels": labels,
                "details": details,
                "query_time": now,
            }
        else:
            existing = data[ip_str]['tags']
            existing_labels = set(existing.get('labels', []))
            existing_details = existing.get('details', [])

            new_labels = list(existing_labels | set(labels))

            existing_sources = {(d['label'], d['source']) for d in existing_details}
            merged_details = list(existing_details)
            for d in details:
                key = (d['label'], d['source'])
                if key not in existing_sources:
                    merged_details.append(d)
                    existing_sources.add(key)

            data[ip_str]['tags'] = {
                "labels": new_labels,
                "details": merged_details,
                "query_time": now,
            }

        written += 1

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _logger.info(f"已写入 {written} 个命中 IP 的标签数据到 {json_path} (模式: {mode})")
    return written


def run_tagger(ip_file: str, mode: str = 'accumulate', config_dir: str = None, output: str = None, level: int = None):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if config_dir is None:
        config_dir = os.path.join(project_root, 'config', 'ip_tagger')

    manifest_path = os.path.join(config_dir, 'manifest.json')

    _logger.info(f"IP 文件: {ip_file}")
    _logger.info(f"配置目录: {config_dir}")
    _logger.info(f"写入模式: {mode}")
    if level:
        _logger.info(f"标签级别: {level}")

    manifest = load_manifest(manifest_path, level=level)
    validate_manifest(manifest, config_dir)

    ip_list = read_ip_file(ip_file)
    if not ip_list:
        _logger.warning("IP 文件中没有有效内容，无需打标")
        return

    _logger.info(f"读取到 {len(ip_list)} 个 IP")

    ip_tags = process_all_tags(ip_list, manifest, config_dir)
    written = write_matched_tags(ip_tags, mode, output)

    total = len(ip_list)
    matched = len(ip_tags)
    print(f"完成: {matched}/{total} 个 IP 命中标签，已写入 {written} 条 (模式: {mode})")


def main():
    parser = argparse.ArgumentParser(description='IP 标签打标工具 — 基于本地威胁情报文件批量匹配 IP 标签')
    parser.add_argument('ip_file', help='IP 文件路径（每行一个 IP）')
    parser.add_argument('--mode', choices=['accumulate', 'overwrite'], default='accumulate',
                        help='写入模式: accumulate=累加(默认), overwrite=覆盖')
    parser.add_argument('--level', type=int, choices=[1, 2, 3], default=None,
                        help='标签级别: 1=快速(5源), 2=正常(13源), 3=全量(27源), 不指定则使用全部')
    parser.add_argument('--output', default=None,
                        help='输出 JSON 文件路径 (默认: 使用 Settings 定位)')
    parser.add_argument('--config-dir', default=None,
                        help='标签配置文件目录 (默认: config/ip_tagger)')
    parser.add_argument('--manifest', default=None,
                        help='清单文件路径 (默认: {config-dir}/manifest.json)')

    args = parser.parse_args()

    config_dir = args.config_dir
    if config_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(project_root, 'config', 'ip_tagger')

    if args.manifest:
        manifest_path = args.manifest
    else:
        manifest_path = os.path.join(config_dir, 'manifest.json')

    _logger.info(f"IP 文件: {args.ip_file}")
    _logger.info(f"配置目录: {config_dir}")
    _logger.info(f"清单文件: {manifest_path}")
    _logger.info(f"写入模式: {args.mode}")
    if args.level:
        _logger.info(f"标签级别: {args.level}")
    if args.output:
        _logger.info(f"输出文件: {args.output}")

    manifest = load_manifest(manifest_path, level=args.level)
    validate_manifest(manifest, config_dir)

    ip_list = read_ip_file(args.ip_file)
    if not ip_list:
        _logger.warning("IP 文件中没有有效内容，无需打标")
        print("IP 文件中没有有效内容，无需打标")
        return

    _logger.info(f"读取到 {len(ip_list)} 个 IP")

    ip_tags = process_all_tags(ip_list, manifest, config_dir)
    written = write_matched_tags(ip_tags, args.mode, args.output)

    total = len(ip_list)
    matched = len(ip_tags)
    print(f"完成: {matched}/{total} 个 IP 命中标签，已写入 {written} 条 (模式: {args.mode})")


if __name__ == "__main__":
    main()
