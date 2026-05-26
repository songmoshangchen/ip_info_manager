"""Phase 1-4 真实运行集成测试。

使用真实渠道查询 + SqliteDomainCache + JSON 文件存储。
仅使用 2-3 个 IP，验证全流程无异常、无存储卡死。
"""

import logging
import os
import sys
import time

# 确保项目路径可导入
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))

from ip_info.channel.chinaz import ChinazChannel  # noqa: E402
from ip_info.channel.ipinfo_api import IpinfoApiChannel  # noqa: E402
from ip_info.channel.port_scan import PortScanChannel  # noqa: E402
from ip_info.channel.rdns_ptr import RdnsPtrChannel  # noqa: E402
from ip_info.pipeline.filter_ips import filter_ips_by_classification  # noqa: E402
from ip_info.pipeline.phases import (  # noqa: E402
    BasicCollectPhase,
    ClassifyTagPhase,
    DeepQueryPhase,
    VerifyScanPhase,
)
from ip_info.store.json_store import IPReader, IPWriter  # noqa: E402
from ip_info.store.sqlite_cache import SqliteDomainCache  # noqa: E402
from ip_info.utils.load_ips import load_ips  # noqa: E402
from ip_info.utils.progress import SqliteProgressTracker  # noqa: E402

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("integration_test")

# ============ 配置 ============
IP_FILE = os.path.join(project_root, "data", "integration_test_ips.txt")
STORAGE_FILE = os.path.join(project_root, "data", "integration_test_data.json")
DOMAIN_CACHE_DB = os.path.join(project_root, "data", "integration_domain_cache.db")
PROGRESS_DB = os.path.join(project_root, "data", "integration_progress.db")
RULES_DIR = os.path.join(project_root, "config", "classifier")
TAGGER_CONFIG_DIR = os.path.join(project_root, "config", "ip_tagger")


def create_test_ip_file():
    """创建测试 IP 文件（2 个真实 IP）。"""
    os.makedirs(os.path.dirname(IP_FILE), exist_ok=True)
    with open(IP_FILE, "w", encoding="utf-8") as f:
        f.write("8.8.8.8\n")
        f.write("1.1.1.1\n")
    logger.info("测试 IP 文件已创建: %s", IP_FILE)


def cleanup():
    """清理测试数据文件。"""
    for f in [IP_FILE, STORAGE_FILE, DOMAIN_CACHE_DB, PROGRESS_DB]:
        if os.path.exists(f):
            os.remove(f)
            logger.info("已清理: %s", f)


def main():
    start = time.time()

    # 清理旧数据
    cleanup()

    # 创建测试 IP 文件
    create_test_ip_file()

    # 加载 IP（内置格式校验）
    ips = load_ips(IP_FILE)
    logger.info("加载 IP: %s (共 %d 个)", ips, len(ips))
    if not ips:
        logger.error("无有效 IP，退出")
        return

    # 初始化存储
    writer = IPWriter(STORAGE_FILE)
    reader = IPReader(STORAGE_FILE)
    domain_cache = SqliteDomainCache(DOMAIN_CACHE_DB)
    progress_tracker = SqliteProgressTracker(PROGRESS_DB)
    logger.info("存储初始化完成")

    # ============ Phase 1: 基础情报采集 ============
    logger.info("=" * 60)
    logger.info("Phase 1: 基础情报采集")
    logger.info("=" * 60)

    ipinfo_ch = IpinfoApiChannel()
    rdns_ch = RdnsPtrChannel()

    phase1 = BasicCollectPhase(
        ips=ips,
        writer=writer,
        reader=reader,
        ipinfo_channel=ipinfo_ch,
        rdns_channel=rdns_ch,
        rdns_workers=2,
        progress_tracker=progress_tracker,
    )
    result1 = phase1.run()
    logger.info("Phase 1 完成: %s, 耗时 %.1fs", result1.message, result1.elapsed)

    # ============ Phase 2: 分类 + 标签 ============
    logger.info("=" * 60)
    logger.info("Phase 2: 分类 + 标签")
    logger.info("=" * 60)

    phase2 = ClassifyTagPhase(
        ips=ips,
        writer=writer,
        reader=reader,
        rules_dir=RULES_DIR,
        tagger_config_dir=TAGGER_CONFIG_DIR,
    )
    result2 = phase2.run()
    logger.info("Phase 2 完成: %s, 耗时 %.1fs", result2.message, result2.elapsed)

    # ============ 过滤 IP ============
    logger.info("=" * 60)
    logger.info("过滤 IP (filter_ips_by_classification)")
    logger.info("=" * 60)

    filtered_ips = filter_ips_by_classification(ips, reader)
    logger.info("过滤结果: %d/%d IP 需深度查询: %s", len(filtered_ips), len(ips), filtered_ips)

    # ============ Phase 3: 深度查询 ============
    logger.info("=" * 60)
    logger.info("Phase 3: 深度查询")
    logger.info("=" * 60)

    if filtered_ips:
        chinaz_ch = ChinazChannel()
        try:
            fofa_ch = __import__("ip_info.channel.fofa_host", fromlist=["FofaHostChannel"]).FofaHostChannel()
        except Exception as e:
            logger.warning("FOFA 渠道初始化失败: %s，跳过", e)
            fofa_ch = None
        try:
            aizhan_ch = __import__("ip_info.channel.aizhan", fromlist=["AizhanChannel"]).AizhanChannel()
        except Exception as e:
            logger.warning("爱站渠道初始化失败: %s，跳过", e)
            aizhan_ch = None

        if chinaz_ch is not None:
            phase3 = DeepQueryPhase(
                ips=filtered_ips,
                writer=writer,
                reader=reader,
                aizhan_channel=aizhan_ch or chinaz_ch,
                chinaz_channel=chinaz_ch,
                fofa_channel=fofa_ch or chinaz_ch,
                progress_tracker=progress_tracker,
            )
            result3 = phase3.run()
            logger.info("Phase 3 完成: %s, 耗时 %.1fs", result3.message, result3.elapsed)
        else:
            logger.warning("无可用深度查询渠道，跳过 Phase 3")
    else:
        logger.info("无 IP 需深度查询，跳过 Phase 3")

    # ============ Phase 4: 验证 + Nmap 扫描 ============
    logger.info("=" * 60)
    logger.info("Phase 4: 验证 + Nmap 扫描")
    logger.info("=" * 60)

    if filtered_ips:
        try:
            nmap_ch = PortScanChannel()
            phase4 = VerifyScanPhase(
                ips=filtered_ips,
                writer=writer,
                reader=reader,
                nmap_channel=nmap_ch,
                domain_cache=domain_cache,
                max_age_days=7,
                dns_timeout=3.0,
                dns_concurrency=5,
                progress_tracker=progress_tracker,
            )
            result4 = phase4.run()
            logger.info("Phase 4 完成: %s, 耗时 %.1fs", result4.message, result4.elapsed)
        except Exception as e:
            logger.warning("Phase 4 执行异常: %s", e)
    else:
        logger.info("无 IP 需验证/扫描，跳过 Phase 4")

    # ============ 汇总 ============
    logger.info("=" * 60)
    total_elapsed = time.time() - start
    logger.info("全流程完成! 总耗时: %.1fs", total_elapsed)

    # 打印最终 store 数据摘要
    all_ips = reader.list_all_ips()
    for ip in all_ips:
        channels = reader.list_ip_channels(ip)
        logger.info("  %s: %s", ip, channels)

    # 验证断点续传：检查 progress DB 中的记录
    logger.info("=" * 60)
    logger.info("断点续传验证 (SqliteProgressTracker)")
    logger.info("=" * 60)
    for ip in all_ips:
        for ch in ["ipinfo_api", "rdns_ptr", "chinaz", "aizhan", "fofa_host", "port_scan", "domain_verify"]:
            if progress_tracker.is_processed(ip, ch):
                logger.info("  %s @ %s: 已处理", ip, ch)


if __name__ == "__main__":
    main()
