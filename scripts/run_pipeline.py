"""Phase 1-4 完整运行脚本。

用法: python scripts/run_pipeline.py <ip_file> <output_dir> [--skip channel1,channel2] [--no-skip-dynamic]
例:   python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524
      python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524 --skip aizhan,fofa_host,port_scan
      python scripts/run_pipeline.py data/0518-0524/ips.txt data/0518-0524 --no-skip-dynamic
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


def _try_channel(name):
    """尝试初始化渠道，失败返回 None。"""
    try:
        if name == "aizhan":
            from ip_info.channel.aizhan import AizhanChannel

            return AizhanChannel()
        elif name == "fofa":
            from ip_info.channel.fofa_host import FofaHostChannel

            return FofaHostChannel()
    except Exception:
        return None
    return None


def filter_by_classification_for_pipeline(ips, context):
    """Pipeline filter: 根据分类结果过滤 IP，返回需要深度查询的 IP。"""
    from ip_info.pipeline.filter_ips import filter_ips_by_classification

    return filter_ips_by_classification(ips, context.reader)


def filter_dynamic_ips_for_pipeline(ips, context):
    """Pipeline filter: 识别动态 IP，存储到 context，返回非动态 IP。

    动态 IP 会被写入 context.config['dynamic_ips'] 以便后续 Phase 使用。
    """
    from ip_info.pipeline.filter_ips import filter_dynamic_ips

    dynamic_list, non_dynamic_list = filter_dynamic_ips(ips, context.reader)
    if context.config is None:
        context.config = {}
    context.config["dynamic_ips"] = set(dynamic_list)
    return non_dynamic_list


def main():
    from ip_info.channel.chinaz import ChinazChannel
    from ip_info.channel.ipinfo_api import IpinfoApiChannel
    from ip_info.channel.port_scan import PortScanChannel
    from ip_info.channel.rdns_ptr import RdnsPtrChannel
    from ip_info.pipeline.builder import PipelineBuilder
    from ip_info.pipeline.context import PipelineContext
    from ip_info.pipeline.phases import (
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
    args = parser.parse_args()

    skip_names = {s.strip() for s in args.skip.split(",") if s.strip()}
    if skip_names:
        logger.info("将跳过渠道: %s", ", ".join(sorted(skip_names)))

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

    # 加载 IP
    ips = load_ips(ip_file)
    logger.info("加载 IP: %d 个 (文件: %s)", len(ips), ip_file)
    if not ips:
        logger.error("无有效 IP，退出")
        sys.exit(1)

    # 初始化存储
    writer = IPWriter(storage_file)
    reader = IPReader(storage_file)
    domain_cache = SqliteDomainCache(domain_cache_db)

    ctx = PipelineContext(
        writer=writer,
        reader=reader,
        progress_tracker=progress_tracker,
        domain_cache=domain_cache,
    )

    # 初始化渠道
    ipinfo_ch = IpinfoApiChannel()
    rdns_ch = RdnsPtrChannel()
    aizhan_ch = _try_channel("aizhan")
    fofa_ch = _try_channel("fofa")
    chinaz_ch = ChinazChannel()
    nmap_ch = PortScanChannel()

    # 使用 PipelineBuilder 构建流水线
    builder = PipelineBuilder(ctx)
    builder.with_ips(ips)
    builder.with_channel("ipinfo_api", ipinfo_ch)
    builder.with_channel("rdns_ptr", rdns_ch)
    builder.with_channel("aizhan", aizhan_ch or chinaz_ch)
    builder.with_channel("chinaz", chinaz_ch)
    builder.with_channel("fofa_host", fofa_ch or chinaz_ch)
    builder.with_channel("port_scan", nmap_ch)

    # 跳过指定渠道
    for name in skip_names:
        builder.skip_channel(name)

    # 注册 Phase 1: 基础情报采集
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

    # 注册 Phase 2: 分类 + 标签
    builder.add_phase(
        ClassifyTagPhase(
            ips=ips,
            context=ctx,
            rules_dir=rules_dir,
            tagger_config_dir=tagger_config_dir,
        )
    )

    # 注册过滤器: 分类后过滤 IP
    builder.with_filter("分类与标签", filter_by_classification_for_pipeline)

    # 注册过滤器: 识别动态 IP (除非 --no-skip-dynamic)
    if not args.no_skip_dynamic:
        builder.with_filter("分类与标签", filter_dynamic_ips_for_pipeline)

    # 注册 Phase 3: 深度查询
    builder.add_phase(
        DeepQueryPhase(
            ips=ips,
            aizhan_channel=aizhan_ch or chinaz_ch,
            chinaz_channel=chinaz_ch,
            fofa_channel=fofa_ch or chinaz_ch,
            context=ctx,
            aizhan_workers=1,
            chinaz_workers=2,
            fofa_workers=2,
        )
    )

    # 注册 Phase 4: 验证 + Nmap 扫描
    builder.add_phase(
        VerifyScanPhase(
            ips=ips,
            nmap_channel=nmap_ch,
            context=ctx,
            max_age_days=7,
            dns_timeout=3.0,
            dns_concurrency=10,
            nmap_workers=3,
        )
    )

    # 构建并运行流水线
    pipeline = builder.build()
    pipeline.run()

    # 汇总
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
