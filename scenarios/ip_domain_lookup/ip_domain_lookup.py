import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .pipeline import IPDomainLookupPipeline

logger = logging.getLogger('ip_info_manager.scenarios.ip_domain_lookup')


def _setup_logging():
    _logger = logging.getLogger('ip_info_manager.scenarios.ip_domain_lookup')
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
        description='IP域名反查流水线 - 域名收集、DNS验证、汇总报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('ip_file', help='IP列表文件路径（每行一个IP）')

    phase_group = parser.add_argument_group('阶段控制')
    phase_group.add_argument(
        '--from-phase', type=int, choices=[1, 2, 3, 4],
        help='从指定阶段开始（默认从阶段1开始）')
    phase_group.add_argument(
        '--only-phase', type=int, choices=[1, 2, 3, 4],
        help='只执行指定阶段')

    shortcut_group = parser.add_argument_group('快捷命令（等同于 --only-phase N）')
    shortcut_group.add_argument(
        '--collect-only', action='store_true',
        help='只执行 Phase 1（域名收集）')
    shortcut_group.add_argument(
        '--dns-verify-only', action='store_true',
        help='只执行 Phase 2（DNS 正向验证）')
    shortcut_group.add_argument(
        '--summary-only', action='store_true',
        help='只执行 Phase 3（汇总报告）')
    shortcut_group.add_argument(
        '--generate-report', action='store_true',
        help='只执行 Phase 4（生成 Word 报告）')

    timeout_group = parser.add_argument_group('超时控制')
    timeout_group.add_argument(
        '--channel-timeout', type=int, default=0,
        help='单渠道查询超时秒数（0=不限时，默认 0）')
    timeout_group.add_argument(
        '--dns-timeout', type=float, default=3.0,
        help='DNS 解析超时秒数（默认 3）')
    timeout_group.add_argument(
        '--dns-concurrency', type=int, default=10,
        help='DNS 并发线程数（默认 10）')

    args = parser.parse_args()

    shortcuts = [args.collect_only, args.dns_verify_only,
                 args.summary_only, args.generate_report]
    shortcut_map = {
        0: ('collect_only', 1),
        1: ('dns_verify_only', 2),
        2: ('summary_only', 3),
        3: ('generate_report', 4),
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
        'channel_timeout': args.channel_timeout,
        'dns_timeout': args.dns_timeout,
        'dns_concurrency': args.dns_concurrency,
    }

    logger.info("=" * 60)
    logger.info("IP域名反查流水线")
    logger.info("=" * 60)
    logger.info("IP文件: %s", args.ip_file)
    if args.from_phase:
        logger.info("起始阶段: %d", args.from_phase)
    if args.only_phase:
        phase_names = {1: '域名收集', 2: 'DNS 正向验证', 3: '汇总报告', 4: '生成 Word 报告'}
        logger.info("仅执行阶段: %d - %s", args.only_phase, phase_names.get(args.only_phase, ''))
    logger.info("DNS超时: %ss", args.dns_timeout)
    logger.info("DNS并发: %d", args.dns_concurrency)
    logger.info("=" * 60)

    pipeline = IPDomainLookupPipeline(args.ip_file, config)

    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("用户中断，正在保存进度...")
        pipeline._progress.flush()
        pipeline._batch_writer.flush_batch()
        logger.info("进度已保存，可使用 --from-phase 续查")


if __name__ == "__main__":
    main()
