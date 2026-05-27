import argparse
import logging
import os
import sys

from ip_info.processors.classifier.runner import BatchClassifier
from ip_info.store import IPReader, IPWriter
from ip_info.utils import load_ips

CHANNEL_NAME = "classifier"
DEFAULT_STORAGE = "data/ip_data.json"
DEFAULT_RULES_DIR = "config/classifier"
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="批量 IP 自动分类")
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
        "--rules-dir",
        default=DEFAULT_RULES_DIR,
        help=f"分类规则目录 (默认: {DEFAULT_RULES_DIR})",
    )
    parser.add_argument(
        "--custom-rules",
        default=None,
        help="自定义规则文件路径",
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

    logger.info("加载 %d 个 IP，渠道: %s", len(ips), CHANNEL_NAME)

    writer = IPWriter(args.storage_file)
    reader = IPReader(args.storage_file)

    classifier = BatchClassifier(
        ips=ips,
        writer=writer,
        reader=reader,
        rules_dir=args.rules_dir,
        custom_rules_path=args.custom_rules,
    )
    result = classifier.run()

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
