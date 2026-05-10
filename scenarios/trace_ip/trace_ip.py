import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .pipeline import TraceIPPipeline

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')


def _setup_logging():
    _logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')
    _logger.setLevel(logging.DEBUG)

    if not _logger.handlers:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s', '%H:%M:%S')
        console.setFormatter(formatter)
        _logger.addHandler(console)


def main():
    _setup_logging()

    parser = argparse.ArgumentParser(
        description='溯源IP处理流水线 - 自动采集、分类、深度查询',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('ip_file', help='IP列表文件路径（每行一个IP）')

    phase_group = parser.add_argument_group('阶段控制')
    phase_group.add_argument(
        '--from-phase', type=int, choices=[1, 2, 3, 4, 5],
        help='从指定阶段开始（默认从阶段1开始）')
    phase_group.add_argument(
        '--only-phase', type=int, choices=[1, 2, 3, 4, 5],
        help='只执行指定阶段')

    shortcut_group = parser.add_argument_group('快捷命令（等同于 --only-phase N）')
    shortcut_group.add_argument(
        '--collect-only', action='store_true',
        help='只执行 Phase 1（基础情报采集）')
    shortcut_group.add_argument(
        '--classify-only', action='store_true',
        help='只执行 Phase 2（自动分类过滤）')
    shortcut_group.add_argument(
        '--deep-query-only', action='store_true',
        help='只执行 Phase 3（深度查询）')
    shortcut_group.add_argument(
        '--summary-only', action='store_true',
        help='只执行 Phase 4（汇总输出）')
    shortcut_group.add_argument(
        '--generate-report', action='store_true',
        help='只执行 Phase 5（生成 Word + Excel 报告）')

    rule_group = parser.add_argument_group('分类规则')
    rule_group.add_argument(
        '--custom-rules', type=str,
        help='外部规则文件路径（默认使用 classifiers/custom_rules.json）')
    rule_group.add_argument(
        '--no-custom-rules', action='store_true',
        help='不加载外部规则文件')

    output_group = parser.add_argument_group('输出控制')
    output_group.add_argument(
        '--no-deep-query', action='store_true',
        help='分类后不执行深度查询阶段')
    output_group.add_argument(
        '--no-tagger', action='store_true',
        help='跳过 IP 标签打标阶段')
    output_group.add_argument(
        '--tagger-level', type=int, choices=[1, 2, 3],
        help='标签级别：1=快速(21源), 2=正常(31源), 3=全量(35源)')

    timeout_group = parser.add_argument_group('超时控制')
    timeout_group.add_argument(
        '--channel-timeout', type=int, default=0,
        help='单渠道查询超时秒数（0=不限时，默认 0）')

    args = parser.parse_args()

    shortcuts = [args.collect_only, args.classify_only,
                 args.deep_query_only, args.summary_only, args.generate_report]
    shortcut_map = {
        0: ('collect_only', 1),
        1: ('classify_only', 2),
        2: ('deep_query_only', 3),
        3: ('summary_only', 4),
        4: ('generate_report', 5),
    }

    active_shortcuts = [i for i, s in enumerate(shortcuts) if s]
    if len(active_shortcuts) > 1:
        names = [shortcut_map[i][0] for i in active_shortcuts]
        parser.error(f'快捷命令互斥，不能同时使用: {", ".join("--" + n.replace("_", "-") for n in names)}')

    if active_shortcuts and args.only_phase:
        name = shortcut_map[active_shortcuts[0]][0]
        parser.error(f'--only-phase 和 --{name.replace("_", "-")} 不能同时使用')

    if active_shortcuts:
        args.only_phase = shortcut_map[active_shortcuts[0]][1]

    if not os.path.exists(args.ip_file):
        logger.error("找不到文件 %s", args.ip_file)
        sys.exit(1)

    config = {
        'from_phase': args.from_phase,
        'only_phase': args.only_phase,
        'custom_rules': args.custom_rules,
        'no_custom_rules': args.no_custom_rules,
        'no_deep_query': args.no_deep_query,
        'channel_timeout': args.channel_timeout,
        'no_tagger': args.no_tagger,
        'tagger_level': args.tagger_level,
    }

    logger.info("=" * 60)
    logger.info("溯源IP处理流水线")
    logger.info("=" * 60)
    logger.info("IP文件: %s", args.ip_file)
    if args.from_phase:
        logger.info("起始阶段: %d", args.from_phase)
    if args.only_phase:
        phase_names = {1: '基础情报采集', 2: '自动分类过滤', 3: '深度查询', 4: '汇总输出', 5: '生成报告'}
        logger.info("仅执行阶段: %d - %s", args.only_phase, phase_names.get(args.only_phase, ''))
    if args.no_deep_query:
        logger.info("深度查询: 已禁用")
    if args.no_tagger:
        logger.info("标签打标: 已禁用")
    if args.tagger_level:
        logger.info("标签级别: %d", args.tagger_level)
    if args.channel_timeout:
        logger.info("渠道超时: %ds", args.channel_timeout)
    logger.info("=" * 60)

    pipeline = TraceIPPipeline(args.ip_file, config)

    total_ips = len(pipeline._ips)
    only_phase = args.only_phase
    from_phase = args.from_phase or 1

    if not only_phase or only_phase == 1:
        phase1_channels = 0
        if pipeline._config.get('phase1_ipinfo_enabled', True):
            phase1_channels += 1
        if pipeline._config.get('phase1_rdns_ptr_enabled', True):
            phase1_channels += 1
        phase1_avg = 2.0 * phase1_channels if phase1_channels > 0 else 0

        est_phase1 = total_ips * phase1_avg
        logger.info("Phase 1 预估: ~%d 分钟 (%d IP × %d 渠道 × %.0fs/IP)",
                     max(1, int(est_phase1 / 60)), total_ips, phase1_channels, phase1_avg)

    if (not only_phase or only_phase == 3) and from_phase <= 3 and not args.no_deep_query:
        phase3_channels = 0
        if pipeline._config.get('phase3_aizhan_enabled', True):
            phase3_channels += 1
        if pipeline._config.get('phase3_chinaz_enabled', True):
            phase3_channels += 1
        if pipeline._config.get('phase3_fofa_host_enabled', True):
            phase3_channels += 1
        phase3_avg = 3.0 * phase3_channels if phase3_channels > 0 else 0

        est_phase3 = total_ips * phase3_avg
        logger.info("Phase 3 预估: ~%d 分钟 (%d IP × %d 渠道 × %.0fs/IP)",
                     max(1, int(est_phase3 / 60)), total_ips, phase3_channels, phase3_avg)

    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("用户中断，正在保存进度...")
        pipeline._progress.flush()
        pipeline._batch_writer.flush_batch()
        logger.info("进度已保存，可使用 --from-phase 续查")


if __name__ == "__main__":
    main()
