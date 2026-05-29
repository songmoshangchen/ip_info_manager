"""Phase 1-4 完整运行脚本。

用法: python scripts/run_pipeline.py <ip_file> <output_dir>
      [--skip channel1,channel2] [--no-skip-dynamic] [--only-phase N]
例:   python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524
      python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524 --skip aizhan,fofa_host,port_scan
      python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524 --no-skip-dynamic
      python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524 --only-phase 2
"""

import argparse
import logging
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def filter_by_classification_for_pipeline(ips, context):
    from ip_info.pipeline.core.filter_ips import filter_ips_by_classification

    return filter_ips_by_classification(ips, context.reader)


def main():
    from ip_info.channel.chinaz import ChinazChannel
    from ip_info.channel.ipinfo_api import IpinfoApiChannel
    from ip_info.channel.port_scan import PortScanChannel
    from ip_info.channel.rdns_ptr import RdnsPtrChannel
    from ip_info.pipeline.core.batch_factory import BatchFactory
    from ip_info.pipeline.core.builder import PipelineBuilder
    from ip_info.pipeline.core.context import PipelineContext
    from ip_info.pipeline.trace_steps import (
        BasicCollectPhase,
        ClassifyTagPhase,
        DeepQueryPhase,
        VerifyScanPhase,
    )
    from ip_info.store.json_store import IPReader, IPWriter
    from ip_info.store.sqlite_cache import SqliteDomainCache
    from ip_info.utils.load_ips import load_ips
    from ip_info.utils.progress import SqliteProgressTracker

    parser = argparse.ArgumentParser(description="IP 信息采集流水线")
    parser.add_argument("ip_file", help="IP 列表文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--skip", default="", help="跳过的渠道，逗号分隔 (如: aizhan,fofa_host,port_scan)")
    parser.add_argument("--no-skip-dynamic", action="store_true", help="强制对动态 IP 也执行深度查询")
    parser.add_argument("--only-phase", type=int, default=None, help="只执行指定阶段 (1-4)")
    args = parser.parse_args()

    skip_names = {s.strip() for s in args.skip.split(",") if s.strip()}
    if skip_names:
        logger.info("将跳过渠道: %s", ", ".join(sorted(skip_names)))

    if args.only_phase is not None and args.only_phase not in {1, 2, 3, 4}:
        logger.error("--only-phase 必须为 1-4 的整数")
        sys.exit(1)

    ip_file = args.ip_file
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    storage_file = os.path.join(output_dir, "ip_data.json")
    domain_cache_db = os.path.join(output_dir, "domain_cache.db")
    progress_db = os.path.join(output_dir, "progress.db")
    rules_dir = os.path.join(project_root, "config", "classifier")
    tagger_config_dir = os.path.join(project_root, "config", "ip_tagger")
    progress_tracker = SqliteProgressTracker(progress_db)

    start = time.time()

    ips = load_ips(ip_file)
    logger.info("加载 IP: %d 个 (文件: %s)", len(ips), ip_file)
    if not ips:
        logger.error("无有效 IP，退出")
        sys.exit(1)

    writer = IPWriter(storage_file)
    reader = IPReader(storage_file)
    domain_cache = SqliteDomainCache(domain_cache_db)

    ctx = PipelineContext(
        writer=writer,
        reader=reader,
        progress_tracker=progress_tracker,
        domain_cache=domain_cache,
    )

    ipinfo_ch = IpinfoApiChannel()
    rdns_ch = RdnsPtrChannel()
    aizhan_step = BatchFactory.try_create(
        "aizhan",
        ips=ips,
        writer=writer,
        progress_tracker=progress_tracker,
        workers=1,
    )
    fofa_step = BatchFactory.try_create(
        "fofa_host",
        ips=ips,
        writer=writer,
        progress_tracker=progress_tracker,
        workers=2,
    )
    chinaz_ch = ChinazChannel()
    nmap_ch = PortScanChannel()

    builder = PipelineBuilder(ctx)
    builder.with_ips(ips)

    builder.add_phase(
        BasicCollectPhase(
            ips=ips,
            ipinfo_channel=ipinfo_ch,
            rdns_channel=rdns_ch,
            context=ctx,
            ipinfo_workers=2,
            rdns_workers=3,
        )
    )

    prefix = os.path.splitext(os.path.basename(storage_file))[0]
    builder.add_phase(
        ClassifyTagPhase(
            ips=ips,
            context=ctx,
            rules_dir=rules_dir,
            tagger_config_dir=tagger_config_dir,
            output_dir=output_dir,
            prefix=prefix,
        )
    )

    builder.with_filter("分类与标签", filter_by_classification_for_pipeline)

    if not args.no_skip_dynamic:
        builder.skip_dynamic_ips()

    from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep

    deep_steps = []
    if aizhan_step and "aizhan" not in skip_names:
        deep_steps.append(aizhan_step)
    if "chinaz" not in skip_names:
        deep_steps.append(
            ChannelBatchStep(
                channel_name="chinaz",
                channel=chinaz_ch,
                ips=ips,
                writer=writer,
                workers=2,
                progress_tracker=progress_tracker,
            )
        )
    if fofa_step and "fofa_host" not in skip_names:
        deep_steps.append(fofa_step)

    builder.add_phase(
        DeepQueryPhase(
            ips=ips,
            context=ctx,
            steps=deep_steps,
        )
    )

    builder.add_phase(
        VerifyScanPhase(
            ips=ips,
            nmap_channel=nmap_ch if "port_scan" not in skip_names else None,
            context=ctx,
            max_age_days=7,
            dns_timeout=3.0,
            dns_concurrency=10,
            nmap_workers=3,
        )
    )

    pipeline = builder.build()

    if args.only_phase is not None:
        result = pipeline.run(only_phase=args.only_phase)
    else:
        result = pipeline.run()

    if result.success:
        from ip_info.export.trace_judge_excel import generate_trace_judge_excel

        exclude_ips_path = os.path.join(output_dir, "exclude_ips.txt")
        exclude_ips = None
        if os.path.exists(exclude_ips_path):
            with open(exclude_ips_path, "r", encoding="utf-8") as f:
                exclude_ips = {line.strip() for line in f if line.strip()}
            logger.info("加载排除 IP: %d 个", len(exclude_ips))

        excel_ok = generate_trace_judge_excel(output_dir, prefix, exclude_ips=exclude_ips)
        if excel_ok:
            logger.info("溯源判断 Excel 已生成: %s", os.path.join(output_dir, f"{prefix}.trace_judge.xlsx"))
        else:
            logger.warning("溯源判断 Excel 生成失败")

    total = time.time() - start
    logger.info("=" * 60)
    logger.info("全流程完成! 总耗时: %.1fs", total)
    logger.info("存储: %s", storage_file)
    logger.info("域名缓存: %s", domain_cache_db)

    all_ips = reader.list_all_ips()
    for ip in all_ips:
        channels = reader.list_ip_channels(ip)
        logger.info("  %s: %s", ip, channels)


if __name__ == "__main__":
    main()
