"""临时 IP 快速查询脚本。

支持命令行直接传 IP 或从文件读取，自动生成独立输出目录，
支持 --phase 和 --skip 参数选择执行的 Phase 和渠道。

用法:
  python scripts/quick_query.py 8.8.8.8 1.1.1.1 9.9.9.9
  python scripts/quick_query.py --file ips.txt
  python scripts/quick_query.py 8.8.8.8 --phase 1,3
  python scripts/quick_query.py 8.8.8.8 --skip aizhan,fofa_host
  python scripts/quick_query.py 8.8.8.8 --output data/quick_test
"""

import argparse
import logging
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))  # noqa: E402

from ip_info.utils.quick_query import generate_output_dir, parse_ips_from_args, parse_phases  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quick_query")


def _disable_channels(channels: list, skip_names: set[str]) -> None:  # noqa: E402
    """手动禁用指定渠道。"""
    for ch in channels:
        if ch.channel_name in skip_names:
            ch.disabled = True
            logger.info("手动禁用渠道: %s", ch.channel_name)


def main():
    from ip_info.channel.chinaz import ChinazChannel  # noqa: E402
    from ip_info.channel.ipinfo_api import IpinfoApiChannel  # noqa: E402
    from ip_info.channel.port_scan import PortScanChannel  # noqa: E402
    from ip_info.channel.rdns_ptr import RdnsPtrChannel  # noqa: E402
    from ip_info.pipeline.core.context import PipelineContext  # noqa: E402
    from ip_info.pipeline.core.filter_ips import filter_ips_by_classification  # noqa: E402
    from ip_info.pipeline.trace_steps import (  # noqa: E402
        BasicCollectPhase,
        ClassifyTagPhase,
        DeepQueryPhase,
        VerifyScanPhase,
    )
    from ip_info.store.json_store import IPReader, IPWriter  # noqa: E402
    from ip_info.store.sqlite_cache import SqliteDomainCache  # noqa: E402
    from ip_info.utils.load_ips import load_ips  # noqa: E402
    from ip_info.utils.progress import SqliteProgressTracker  # noqa: E402

    parser = argparse.ArgumentParser(description="临时 IP 快速查询脚本")
    parser.add_argument("ips", nargs="*", help="IP 地址列表")
    parser.add_argument("--file", help="从文件读取 IP 列表")
    parser.add_argument("--output", help="输出目录（默认自动生成 data/quick/YYYYMMDD_HHMMSS/）")
    parser.add_argument("--phase", default="", help="执行的 Phase，逗号分隔 (如: 1,3)，默认全部")
    parser.add_argument("--skip", default="", help="跳过的渠道，逗号分隔 (如: aizhan,fofa_host)")
    args = parser.parse_args()

    # 解析 IP 列表
    ips = parse_ips_from_args(args.ips)
    if args.file:
        file_ips = load_ips(args.file)
        seen = set(ips)
        for ip in file_ips:
            if ip not in seen:
                seen.add(ip)
                ips.append(ip)

    if not ips:
        logger.error("无有效 IP，退出")
        sys.exit(1)

    logger.info("待查询 IP: %d 个", len(ips))

    # 解析参数
    phases = parse_phases(args.phase)
    skip_names = {s.strip() for s in args.skip.split(",") if s.strip()}

    if skip_names:
        logger.info("将跳过渠道: %s", ", ".join(sorted(skip_names)))
    logger.info("执行 Phase: %s", ", ".join(str(p) for p in sorted(phases)))

    # 输出目录
    if args.output:
        output_dir = args.output
    else:
        output_dir = generate_output_dir()
    os.makedirs(output_dir, exist_ok=True)

    storage_file = os.path.join(output_dir, "ip_data.json")
    domain_cache_db = os.path.join(output_dir, "domain_cache.db")
    progress_db = os.path.join(output_dir, "progress.db")
    rules_dir = os.path.join(project_root, "config", "classifier")
    tagger_config_dir = os.path.join(project_root, "config", "ip_tagger")
    progress_tracker = SqliteProgressTracker(progress_db)

    logger.info("输出目录: %s", output_dir)

    start = time.time()

    # 初始化存储
    writer = IPWriter(storage_file)
    reader = IPReader(storage_file)
    domain_cache = SqliteDomainCache(domain_cache_db)

    # Phase 1: 基础情报采集
    if 1 in phases:
        logger.info("=" * 60)
        logger.info("Phase 1: 基础情报采集 (%d IP)", len(ips))
        logger.info("=" * 60)
        ipinfo_ch = IpinfoApiChannel()
        rdns_ch = RdnsPtrChannel()
        _disable_channels([ipinfo_ch, rdns_ch], skip_names)
        ctx = PipelineContext(
            writer=writer,
            reader=reader,
            progress_tracker=progress_tracker,
            domain_cache=domain_cache,
        )
        phase1 = BasicCollectPhase(
            ips=ips,
            ipinfo_channel=ipinfo_ch,
            rdns_channel=rdns_ch,
            context=ctx,
            ipinfo_workers=2,
            rdns_workers=3,
        )
        r1 = phase1.run()
        logger.info("Phase 1 完成: %s, 耗时 %.1fs", r1.message, r1.elapsed)

    # Phase 2: 分类 + 标签
    if 2 in phases:
        logger.info("=" * 60)
        logger.info("Phase 2: 分类 + 标签 (%d IP)", len(ips))
        logger.info("=" * 60)
        phase2 = ClassifyTagPhase(
            ips=ips,
            context=ctx,
            rules_dir=rules_dir,
            tagger_config_dir=tagger_config_dir,
        )
        r2 = phase2.run()
        logger.info("Phase 2 完成: %s, 耗时 %.1fs", r2.message, r2.elapsed)

    # 过滤 IP（Phase 3/4 需要）
    filtered_ips = ips
    if 2 in phases:
        filtered_ips = filter_ips_by_classification(ips, reader)
        logger.info("过滤: %d/%d IP 需深度查询", len(filtered_ips), len(ips))

    # Phase 3: 深度查询
    if 3 in phases and filtered_ips:
        logger.info("=" * 60)
        logger.info("Phase 3: 深度查询 (%d IP)", len(filtered_ips))
        logger.info("=" * 60)
        from ip_info.pipeline.core.batch_factory import BatchFactory

        aizhan_step = BatchFactory.try_create(
            "aizhan",
            ips=filtered_ips,
            writer=writer,
            progress_tracker=progress_tracker,
            workers=1,
        )
        fofa_step = BatchFactory.try_create(
            "fofa_host",
            ips=filtered_ips,
            writer=writer,
            progress_tracker=progress_tracker,
            workers=2,
        )
        chinaz_ch = ChinazChannel()

        from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep

        deep_steps = []
        if aizhan_step and "aizhan" not in skip_names:
            deep_steps.append(aizhan_step)
        if "chinaz" not in skip_names:
            deep_steps.append(
                ChannelBatchStep(
                    channel_name="chinaz",
                    channel=chinaz_ch,
                    ips=filtered_ips,
                    writer=writer,
                    workers=2,
                    progress_tracker=progress_tracker,
                )
            )
        if fofa_step and "fofa_host" not in skip_names:
            deep_steps.append(fofa_step)

        phase3 = DeepQueryPhase(
            ips=filtered_ips,
            context=ctx,
            steps=deep_steps,
        )
        r3 = phase3.run()
        logger.info("Phase 3 完成: %s, 耗时 %.1fs", r3.message, r3.elapsed)
    elif 3 in phases:
        logger.info("无 IP 需深度查询，跳过 Phase 3")

    # Phase 4: 验证 + Nmap 扫描
    if 4 in phases and filtered_ips:
        logger.info("=" * 60)
        logger.info("Phase 4: 验证 + Nmap 扫描 (%d IP)", len(filtered_ips))
        logger.info("=" * 60)
        nmap_ch = PortScanChannel()
        _disable_channels([nmap_ch], skip_names)
        phase4 = VerifyScanPhase(
            ips=filtered_ips,
            nmap_channel=nmap_ch,
            context=ctx,
            max_age_days=7,
            dns_timeout=3.0,
            dns_concurrency=10,
            nmap_workers=3,
        )
        r4 = phase4.run()
        logger.info("Phase 4 完成: %s, 耗时 %.1fs", r4.message, r4.elapsed)
    elif 4 in phases:
        logger.info("无 IP 需验证/扫描，跳过 Phase 4")

    # 汇总
    total = time.time() - start
    logger.info("=" * 60)
    logger.info("查询完成! 总耗时: %.1fs", total)
    logger.info("输出目录: %s", output_dir)
    logger.info("数据文件: %s", storage_file)

    all_ips = reader.list_all_ips()
    for ip in all_ips:
        channels = reader.list_ip_channels(ip)
        logger.info("  %s: %s", ip, channels)


if __name__ == "__main__":
    main()
