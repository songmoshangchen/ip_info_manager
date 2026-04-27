import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.logger_utils import get_batch_logger

_logger = get_batch_logger('ip_tagger_updater')

DOWNLOAD_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 3
REQUEST_HEADERS = {
    'User-Agent': 'ip-info-manager/ip-tagger-updater',
}
GITHUB_DELAY = 1


def load_manifest(manifest_path: str) -> list[dict]:
    if not os.path.exists(manifest_path):
        print(f"错误: 清单文件不存在: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_remote_file(url: str) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.head(url, headers=REQUEST_HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return {
                    'content_length': int(resp.headers.get('Content-Length', 0)),
                    'last_modified': resp.headers.get('Last-Modified', ''),
                }
            else:
                _logger.warning(f"HEAD 请求失败: HTTP {resp.status_code} - {url}")
                return None
        except requests.RequestException as e:
            _logger.warning(f"HEAD 请求异常 (尝试 {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    _logger.error(f"HEAD 请求最终失败: {url}")
    return None


def download_file(url: str, dest_path: str) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _logger.info(f"  下载中: {url}" + (f" (尝试 {attempt}/{MAX_RETRIES})" if attempt > 1 else ""))
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
            if resp.status_code != 200:
                _logger.error(f"  下载失败: HTTP {resp.status_code}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return False

            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0

            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

            size_kb = downloaded / 1024
            if total:
                size_mb = total / (1024 * 1024)
                _logger.info(f"  下载完成: {size_kb:.1f} KB ({size_mb:.2f} MB)")
            else:
                _logger.info(f"  下载完成: {size_kb:.1f} KB")

            return True
        except requests.RequestException as e:
            _logger.warning(f"  下载异常 (尝试 {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    _logger.error(f"  下载最终失败: {url}")
    return False


def update_sources(config_dir: str, manifest: list[dict], dry_run: bool = False, force: bool = False):
    updatable = [item for item in manifest if item.get('source_url')]
    skipped = [item for item in manifest if not item.get('source_url')]

    _logger.info(f"共 {len(manifest)} 个标签源，{len(updatable)} 个可自动更新，{len(skipped)} 个自定义")

    for item in skipped:
        _logger.info(f"跳过（自定义）: {item['label']} ({item['file']})")

    results = {'updated': [], 'skipped': [], 'failed': [], 'new': []}

    for idx, item in enumerate(updatable):
        label = item['label']
        filename = item['file']
        url = item['source_url']
        dest_path = os.path.join(config_dir, filename)

        _logger.info(f"[{idx + 1}/{len(updatable)}] 检查: {label} ({filename})")

        remote_info = check_remote_file(url)
        if remote_info is None:
            _logger.error(f"  无法获取远程文件信息，跳过")
            results['failed'].append({'label': label, 'file': filename, 'reason': 'HEAD请求失败'})
            continue

        remote_size = remote_info['content_length']

        if os.path.exists(dest_path) and not force:
            local_size = os.path.getsize(dest_path)
            if local_size == remote_size and remote_size > 0:
                _logger.info(f"  文件已是最新 (本地: {local_size} B, 远程: {remote_size} B)")
                results['skipped'].append({'label': label, 'file': filename})
                continue

        if not os.path.exists(dest_path):
            _logger.info(f"  新文件，将下载")
            results['new'].append({'label': label, 'file': filename})
        elif force:
            _logger.info(f"  强制更新 (本地: {os.path.getsize(dest_path)} B, 远程: {remote_size} B)")
        else:
            _logger.info(f"  有更新 (本地: {os.path.getsize(dest_path)} B, 远程: {remote_size} B)")

        if dry_run:
            _logger.info(f"  [DRY-RUN] 将下载: {url}")
            results['updated'].append({'label': label, 'file': filename})
        else:
            success = download_file(url, dest_path)
            if success:
                results['updated'].append({'label': label, 'file': filename})
            else:
                results['failed'].append({'label': label, 'file': filename, 'reason': '下载失败'})

        if idx < len(updatable) - 1:
            time.sleep(GITHUB_DELAY)

    return results


def print_summary(results: dict, dry_run: bool):
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"\n{prefix}更新摘要:")
    print(f"  新增: {len(results['new'])} 个")
    print(f"  更新: {len(results['updated'])} 个")
    print(f"  跳过（已是最新）: {len(results['skipped'])} 个")
    print(f"  失败: {len(results['failed'])} 个")

    if results['failed']:
        print(f"\n  失败详情:")
        for item in results['failed']:
            reason = item.get('reason', '未知')
            print(f"    - {item['label']} ({item['file']}): {reason}")


def main():
    parser = argparse.ArgumentParser(
        description='IP 标签源自动更新工具 — 从 FireHOL blocklist-ipsets 下载最新标签源文件')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅检查更新，不实际下载')
    parser.add_argument('--force', action='store_true',
                        help='强制更新所有文件（跳过缓存检查）')
    parser.add_argument('--config-dir', default=None,
                        help='标签配置文件目录 (默认: config/ip_tagger)')

    args = parser.parse_args()

    config_dir = args.config_dir
    if config_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(project_root, 'config', 'ip_tagger')

    manifest_path = os.path.join(config_dir, 'manifest.json')

    _logger.info(f"配置目录: {config_dir}")
    _logger.info(f"清单文件: {manifest_path}")
    if args.dry_run:
        _logger.info("模式: DRY-RUN（仅检查）")
    if args.force:
        _logger.info("模式: 强制更新")

    manifest = load_manifest(manifest_path)
    results = update_sources(config_dir, manifest, dry_run=args.dry_run, force=args.force)
    print_summary(results, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
