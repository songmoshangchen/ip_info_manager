import argparse
import logging
import os
import sys

from ip_info.processors.tagger.runner import BatchTagger
from ip_info.store import IPWriter
from ip_info.utils import load_ips

CHANNEL_NAME = "tagger"
DEFAULT_STORAGE = "data/ip_data.json"
DEFAULT_CONFIG_DIR = "config/ip_tagger"
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="批量 IP 标签打标")
    parser.add_argument(
        "ip_file",
        help="IP 文件路径",
    )
    parser.add_argument(
        "--storage-file",
        default=DEFAULT_STORAGE,
        help=f"数据存储文件路径 (默认: {DEFAULT_STORAGE})",
    )
    parser.add_argument(
        "--config-dir",
        default=DEFAULT_CONFIG_DIR,
        help=f"标签配置文件目录 (默认: {DEFAULT_CONFIG_DIR})",
    )
    parser.add_argument(
        "--mode",
        choices=["accumulate", "overwrite"],
        default="accumulate",
        help="写入模式: accumulate=累加(默认), overwrite=覆盖",
    )
    parser.add_argument(
        "--level",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="标签级别: 1=快速(21源), 2=正常(31源), 3=全量(35源)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log_dir = "data/logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, f"{CHANNEL_NAME}.log"), encoding="utf-8"),
        ],
    )

    ips = load_ips(args.ip_file)

    logger.info("加载 %d 个 IP，渠道: %s, 模式: %s", len(ips), CHANNEL_NAME, args.mode)

    writer = IPWriter(args.storage_file)
    tracker = writer.progress_tracker(CHANNEL_NAME)

    tagger = BatchTagger(
        ips=ips,
        writer=writer,
        reader=writer,
        config_dir=args.config_dir,
        level=args.level,
        mode=args.mode,
        progress_tracker=tracker,
    )
    result = tagger.run()

    logger.info(
        "完成: 成功 %d, 失败 %d, 跳过 %d, 耗时 %.1fs",
        result.success_count,
        result.fail_count,
        result.skip_count,
        result.total_elapsed,
    )

    if result.stopped_early:
        sys.exit(1)


if __name__ == "__main__":
    main()
