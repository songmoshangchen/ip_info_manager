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


def _disable_channels(channels: list, skip_names: set[str]) -> None:
    """手动禁用指定渠道。"""
    for ch in channels:
        if ch.channel_name in skip_names:
            ch.disabled = True
            logger.info("手动禁用渠道: %s", ch.channel_name)


def main():
    from ip_info.channel.chinaz import ChinazChannel
    from ip_info.channel.ipinfo_api import IpinfoApiChannel
    from ip_info.channel.port_scan import PortScanChannel
    from ip_info.channel.rdns_ptr import RdnsPtrChannel
    from ip_info.pipeline.context import PipelineContext
    from ip_info.pipeline.filter_ips import filter_dynamic_ips, filter_ips_by_classification
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

    # Phase 1: 基础情报采集
    logger.info("=" * 60)
    logger.info("Phase 1: 基础情报采集 (%d IP)", len(ips))
    logger.info("=" * 60)
    ipinfo_ch = IpinfoApiChannel()
    rdns_ch = RdnsPtrChannel()
    _disable_channels([ipinfo_ch, rdns_ch], skip_names)
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

    # 过滤 IP
    logger.info("=" * 60)
    filtered_ips = filter_ips_by_classification(ips, reader)
    logger.info("过滤: %d/%d IP 需深度查询", len(filtered_ips), len(ips))

    # 识别动态 IP
    dynamic_ips: set[str] = set()
    if not args.no_skip_dynamic and filtered_ips:
        dynamic_list, _non_dynamic_list = filter_dynamic_ips(filtered_ips, reader)
        dynamic_ips = set(dynamic_list)
        if dynamic_ips:
            logger.info("动态 IP: %d 个将跳过深度查询 (使用 --no-skip-dynamic 强制查询)", len(dynamic_ips))

    # Phase 3: 深度查询
    if filtered_ips:
        logger.info("=" * 60)
        logger.info("Phase 3: 深度查询 (%d IP)", len(filtered_ips))
        logger.info("=" * 60)
        aizhan_ch = _try_channel("aizhan")
        fofa_ch = _try_channel("fofa")
        chinaz_ch = ChinazChannel()
        all_phase3_channels = [ch for ch in [aizhan_ch, chinaz_ch, fofa_ch] if ch is not None]
        _disable_channels(all_phase3_channels, skip_names)
        phase3 = DeepQueryPhase(
            ips=filtered_ips,
            aizhan_channel=aizhan_ch or chinaz_ch,
            chinaz_channel=chinaz_ch,
            fofa_channel=fofa_ch or chinaz_ch,
            context=ctx,
            aizhan_workers=1,
            chinaz_workers=2,
            fofa_workers=2,
            skip_ips=dynamic_ips,
        )
        r3 = phase3.run()
        logger.info("Phase 3 完成: %s, 耗时 %.1fs", r3.message, r3.elapsed)
    else:
        logger.info("无 IP 需深度查询，跳过 Phase 3")

    # Phase 4: 验证 + Nmap 扫描
    if filtered_ips:
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
            skip_ips=dynamic_ips,
        )
        r4 = phase4.run()
        logger.info("Phase 4 完成: %s, 耗时 %.1fs", r4.message, r4.elapsed)
    else:
        logger.info("无 IP 需验证/扫描，跳过 Phase 4")

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
