import argparse
import logging
import os
import sys

from ip_info.batch import run_concurrent
from ip_info.channel.port_scan import PortScanChannel
from ip_info.store import IPWriter
from ip_info.utils import load_ips

CHANNEL_NAME = "port_scan"
DEFAULT_STORAGE = "data/ip_data.json"
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description=f"批量 {CHANNEL_NAME} 查询")
    parser.add_argument("ip_file", help="IP 文件路径")
    parser.add_argument("--storage-file", default=DEFAULT_STORAGE, help=f"数据存储文件路径 (默认: {DEFAULT_STORAGE})")
    parser.add_argument("--no-validate", action="store_true", help="跳过渠道验证")
    parser.add_argument("--workers", type=int, default=1, help="并发线程数 (默认: 1)")
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

    logger.info("加载 %d 个 IP，渠道: %s, 并发: %d", len(ips), CHANNEL_NAME, args.workers)

    channel = PortScanChannel()
    writer = IPWriter(args.storage_file)
    tracker = writer.progress_tracker(CHANNEL_NAME)

    result = run_concurrent(
        ips=ips,
        channel=channel,
        writer=writer,
        channel_name=CHANNEL_NAME,
        workers=args.workers,
        delay=channel.default_delay,
        no_validate=args.no_validate,
        progress_tracker=tracker,
    )

    logger.info(
        "完成: 成功 %d, 失败 %d, 跳过 %d, 耗时 %.1fs, 提前停止: %s",
        result.success_count,
        result.fail_count,
        result.skip_count,
        result.total_elapsed,
        result.stop_reason or "否",
    )

    if result.stopped_early:
        sys.exit(1)


if __name__ == "__main__":
    main()
