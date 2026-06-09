"""IP 标签源更新工具 — 支持 GitHub 下载、Git 克隆、本地压缩包导入。

用法:
  python scripts/ip_tagger_updater.py                          # 从 GitHub 逐文件下载
  python scripts/ip_tagger_updater.py --from-git               # git clone 整个仓库（推荐）
  python scripts/ip_tagger_updater.py --from-archive ./blocklist-ipsets-main.zip  # 从本地压缩包导入
  python scripts/ip_tagger_updater.py --dry-run                # 仅检查
  python scripts/ip_tagger_updater.py --force                  # 强制更新
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ip_tagger_updater")

DOWNLOAD_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 3
REQUEST_HEADERS = {
    "User-Agent": "ip-info-manager/ip-tagger-updater",
}
GITHUB_DELAY = 1
FIREHOL_REPO_URL = "https://github.com/firehol/blocklist-ipsets.git"


def load_manifest(manifest_path: str) -> list[dict]:
    if not os.path.exists(manifest_path):
        logger.error("清单文件不存在: %s", manifest_path)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_remote_file(url: str) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.head(url, headers=REQUEST_HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return {
                    "content_length": int(resp.headers.get("Content-Length", 0)),
                    "last_modified": resp.headers.get("Last-Modified", ""),
                }
            else:
                logger.warning("HEAD 请求失败: HTTP %s - %s", resp.status_code, url)
                return None
        except requests.RequestException as e:
            logger.warning("HEAD 请求异常 (尝试 %s/%s): %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    logger.error("HEAD 请求最终失败: %s", url)
    return None


def download_file(url: str, dest_path: str) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("  下载中: %s%s", url, f" (尝试 {attempt}/{MAX_RETRIES})" if attempt > 1 else "")
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
            if resp.status_code != 200:
                logger.error("  下载失败: HTTP %s", resp.status_code)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return False

            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

            size_kb = downloaded / 1024
            if total:
                size_mb = total / (1024 * 1024)
                logger.info("  下载完成: %.1f KB (%.2f MB)", size_kb, size_mb)
            else:
                logger.info("  下载完成: %.1f KB", size_kb)

            return True
        except requests.RequestException as e:
            logger.warning("  下载异常 (尝试 %s/%s): %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    logger.error("  下载最终失败: %s", url)
    return False


def update_sources(config_dir: str, manifest: list[dict], dry_run: bool = False, force: bool = False):
    updatable = [item for item in manifest if item.get("source_url")]
    skipped = [item for item in manifest if not item.get("source_url")]

    logger.info("共 %d 个标签源，%d 个可自动更新，%d 个自定义", len(manifest), len(updatable), len(skipped))

    for item in skipped:
        logger.info("跳过（自定义）: %s (%s)", item["label"], item["file"])

    results = {"updated": [], "skipped": [], "failed": [], "new": []}

    for idx, item in enumerate(updatable):
        label = item["label"]
        filename = item["file"]
        url = item["source_url"]
        dest_path = os.path.join(config_dir, filename)

        logger.info("[%d/%d] 检查: %s (%s)", idx + 1, len(updatable), label, filename)

        remote_info = check_remote_file(url)
        if remote_info is None:
            logger.error("  无法获取远程文件信息，跳过")
            results["failed"].append({"label": label, "file": filename, "reason": "HEAD请求失败"})
            continue

        remote_size = remote_info["content_length"]

        if os.path.exists(dest_path) and not force:
            local_size = os.path.getsize(dest_path)
            if local_size == remote_size and remote_size > 0:
                logger.info("  文件已是最新 (本地: %d B, 远程: %d B)", local_size, remote_size)
                results["skipped"].append({"label": label, "file": filename})
                continue

        if not os.path.exists(dest_path):
            logger.info("  新文件，将下载")
            results["new"].append({"label": label, "file": filename})
        elif force:
            logger.info("  强制更新 (本地: %d B, 远程: %d B)", os.path.getsize(dest_path), remote_size)
        else:
            logger.info("  有更新 (本地: %d B, 远程: %d B)", os.path.getsize(dest_path), remote_size)

        if dry_run:
            logger.info("  [DRY-RUN] 将下载: %s", url)
            results["updated"].append({"label": label, "file": filename})
        else:
            success = download_file(url, dest_path)
            if success:
                results["updated"].append({"label": label, "file": filename})
            else:
                results["failed"].append({"label": label, "file": filename, "reason": "下载失败"})

        if idx < len(updatable) - 1:
            time.sleep(GITHUB_DELAY)

    return results


def import_from_directory(source_dir: str, config_dir: str, manifest: list[dict]):
    logger.info("从本地目录导入: %s", source_dir)

    updatable = [item for item in manifest if item.get("source_url")]
    results = {"updated": [], "skipped": [], "failed": [], "new": []}

    for item in updatable:
        filename = item["file"]
        label = item["label"]
        src_path = os.path.join(source_dir, filename)
        dest_path = os.path.join(config_dir, filename)

        if not os.path.exists(src_path):
            logger.warning("  目录中不存在: %s，跳过", filename)
            results["skipped"].append({"label": label, "file": filename})
            continue

        if os.path.exists(dest_path):
            local_size = os.path.getsize(dest_path)
            src_size = os.path.getsize(src_path)
            if local_size == src_size:
                logger.info("  跳过（相同）: %s (%s)", label, filename)
                results["skipped"].append({"label": label, "file": filename})
                continue

        logger.info("  复制: %s (%s)", label, filename)
        shutil.copy2(src_path, dest_path)
        size_kb = os.path.getsize(dest_path) / 1024
        logger.info("  完成: %.1f KB", size_kb)

        if not os.path.exists(os.path.join(config_dir, filename)):
            results["new"].append({"label": label, "file": filename})
        else:
            results["updated"].append({"label": label, "file": filename})

    return results


def import_from_archive(archive_path: str, config_dir: str, manifest: list[dict]):
    logger.info("从压缩包导入: %s", archive_path)

    if not os.path.exists(archive_path):
        logger.error("压缩包不存在: %s", archive_path)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.info("解压到临时目录: %s", tmp_dir)
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(tmp_dir)

        extracted_root = tmp_dir
        top_items = os.listdir(tmp_dir)
        if len(top_items) == 1 and os.path.isdir(os.path.join(tmp_dir, top_items[0])):
            extracted_root = os.path.join(tmp_dir, top_items[0])

        logger.info("解压根目录: %s", extracted_root)
        return import_from_directory(extracted_root, config_dir, manifest)


def import_from_git(config_dir: str, manifest: list[dict], repo_url: str = FIREHOL_REPO_URL):
    logger.info("从 Git 仓库克隆: %s", repo_url)

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = os.path.join(tmp_dir, "blocklist-ipsets")

        try:
            logger.info("执行 git clone（浅克隆，仅最新提交）...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, repo_dir],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error("git clone 失败: %s", result.stderr)
                sys.exit(1)
            logger.info("git clone 完成")
        except FileNotFoundError:
            logger.error("未找到 git 命令，请确保已安装 Git 并添加到 PATH")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            logger.error("git clone 超时（5分钟）")
            sys.exit(1)

        return import_from_directory(repo_dir, config_dir, manifest)


def print_summary(results: dict, dry_run: bool = False, source: str = ""):
    prefix = "[DRY-RUN] " if dry_run else ""
    source_label = f"（来源: {source}）" if source else ""
    print(f"\n{prefix}更新摘要{source_label}:")
    print(f"  新增: {len(results['new'])} 个")
    print(f"  更新: {len(results['updated'])} 个")
    print(f"  跳过（已是最新）: {len(results['skipped'])} 个")
    print(f"  失败: {len(results['failed'])} 个")

    if results["failed"]:
        print("\n  失败详情:")
        for item in results["failed"]:
            reason = item.get("reason", "未知")
            print(f"    - {item['label']} ({item['file']}): {reason}")


def main():
    parser = argparse.ArgumentParser(
        description="IP 标签源更新工具 — 支持 GitHub 下载、Git 克隆、本地压缩包导入",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/ip_tagger_updater.py                          # 从 GitHub 逐文件下载
  python scripts/ip_tagger_updater.py --from-git               # git clone 整个仓库（推荐）
  python scripts/ip_tagger_updater.py --from-archive ./blocklist-ipsets-main.zip  # 从本地压缩包导入
  python scripts/ip_tagger_updater.py --dry-run                # 仅检查
  python scripts/ip_tagger_updater.py --force                  # 强制更新
        """,
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--from-git",
        action="store_true",
        help="通过 git clone 下载 FireHOL 仓库（浅克隆）",
    )
    source_group.add_argument(
        "--from-archive",
        type=str,
        default=None,
        metavar="ZIP_PATH",
        help="从本地 ZIP 压缩包导入（支持 GitHub 下载的 zip）",
    )

    parser.add_argument("--dry-run", action="store_true", help="仅检查更新，不实际下载")
    parser.add_argument("--force", action="store_true", help="强制更新所有文件（跳过缓存检查）")
    parser.add_argument(
        "--config-dir",
        default=None,
        help="标签配置文件目录 (默认: config/ip_tagger)",
    )

    args = parser.parse_args()

    config_dir = args.config_dir
    if config_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(project_root, "config", "ip_tagger")

    manifest_path = os.path.join(config_dir, "manifest.json")

    logger.info("配置目录: %s", config_dir)
    logger.info("清单文件: %s", manifest_path)

    manifest = load_manifest(manifest_path)

    if args.from_git:
        logger.info("模式: Git 克隆")
        if args.dry_run:
            logger.info("[DRY-RUN] 将执行 git clone + 导入")
            print("[DRY-RUN] 将执行 git clone + 导入")
            return
        results = import_from_git(config_dir, manifest)
        print_summary(results, source="git clone")
    elif args.from_archive:
        logger.info("模式: 本地压缩包 (%s)", args.from_archive)
        if args.dry_run:
            logger.info("[DRY-RUN] 将从 %s 导入", args.from_archive)
            print(f"[DRY-RUN] 将从 {args.from_archive} 导入")
            return
        results = import_from_archive(args.from_archive, config_dir, manifest)
        print_summary(results, source=f"压缩包: {os.path.basename(args.from_archive)}")
    else:
        if args.dry_run:
            logger.info("模式: DRY-RUN（仅检查）")
        if args.force:
            logger.info("模式: 强制更新")
        results = update_sources(config_dir, manifest, dry_run=args.dry_run, force=args.force)
        print_summary(results, dry_run=args.dry_run, source="GitHub 下载")

    if not args.dry_run and results.get("failed") is not None and len(results.get("failed", [])) == 0:
        now = time.localtime()
        current_month = f"{now.tm_year}-{now.tm_mon:02d}"
        marker_path = os.path.join(config_dir, ".last_update")
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(current_month)
        logger.info("已更新标记: %s", current_month)


if __name__ == "__main__":
    main()
