import argparse
import logging
import os
import sys

from ip_info.batch import BaseBatchQuery
from ip_info.channel.ipinfo_free import IpinfoFreeChannel
from ip_info.store import IPWriter
from ip_info.utils import load_ips

CHANNEL_NAME = "ipinfo_free"
DEFAULT_STORAGE = "data/ip_data.json"
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description=f"批量 {CHANNEL_NAME} 查询")
    parser.add_argument("ip_file", help="IP 文件路径")
    parser.add_argument("--storage-file", default=DEFAULT_STORAGE, help=f"数据存储文件路径 (默认: {DEFAULT_STORAGE})")
    parser.add_argument("--no-validate", action="store_true", help="跳过渠道验证")
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

    channel = IpinfoFreeChannel()
    writer = IPWriter(args.storage_file)
    tracker = writer.progress_tracker(CHANNEL_NAME)

    query = BaseBatchQuery(
        channel_name=CHANNEL_NAME,
        channel=channel,
        writer=writer,
        ips=ips,
        delay=channel.default_delay,
        no_validate=args.no_validate,
        progress_tracker=tracker,
    )
    result = query.run()

    logger.info(
        "完成: 成功 %d, 失败 %d, 耗时 %.1fs, 提前停止: %s",
        result.success_count,
        result.fail_count,
        result.total_elapsed,
        result.stop_reason or "否",
    )

    if result.stopped_early:
        sys.exit(1)


if __name__ == "__main__":
    main()
