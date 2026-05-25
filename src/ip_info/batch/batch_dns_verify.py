import argparse
import logging
import os
import sys

from ip_info.processors.dns_verify.runner import BatchDnsVerify
from ip_info.store import IPReader, IPWriter
from ip_info.utils import load_ips

CHANNEL_NAME = "domain_verify"
DEFAULT_STORAGE = "data/ip_data.json"
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="批量 DNS 域名验证")
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
        "--timeout",
        type=float,
        default=3.0,
        help="DNS 解析超时秒数 (默认: 3.0)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="并发线程数 (默认: 10)",
    )
    parser.add_argument(
        "--max-age-days",
        type=float,
        default=7,
        help="验证结果有效天数，超过则重新验证 (默认: 7, 设为 0 则强制全量)",
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

    verifier = BatchDnsVerify(
        ips=ips,
        writer=writer,
        reader=reader,
        timeout=args.timeout,
        concurrency=args.concurrency,
        max_age_days=args.max_age_days,
    )
    result = verifier.run()

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
