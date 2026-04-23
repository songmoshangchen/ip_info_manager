import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from channel.ipinfo_api import fetch_channel as fetch_ipinfo
from channel.rdns_ptr import fetch_channel as fetch_rdns_ptr
from channel.aizhan import fetch_channel as fetch_aizhan
from channel.chinaz import fetch_channel as fetch_chinaz
from channel.fofa_host import fetch_channel as fetch_fofa_host
from config import (
    IpinfoSettings, RdnsSettings, AizhanSettings,
    ChinazSettings, FofaSettings, Settings,
)
from reader import IPReader
from writer import IPWriter

from .classifier import IPClassifier
from .progress import BatchIPWriter, ProgressManager
from .reporter import BaseTraceReporter, TextTraceReporter

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')

DEEP_QUERY_CATEGORIES = {'cloud_provider', 'residential', 'other'}

PHASE_NAMES = {
    1: '基础情报采集',
    2: '自动分类过滤',
    3: '深度查询',
    4: '汇总输出',
}


def _load_ips(ip_file: str) -> list:
    ips = []
    with open(ip_file, 'r', encoding='utf-8') as f:
        for line in f:
            ip = line.strip()
            if ip:
                ips.append(ip)
    return ips


class TraceIPPipeline:

    def __init__(self, ip_file: str, config: dict,
                 reporter: BaseTraceReporter = None):
        self._config = config
        self._ips = _load_ips(ip_file)
        self._ip_reader = IPReader()

        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._output_dir = self._resolve_output_dir(project_dir)

        prefix = self._ip_reader.settings.storage_name

        classifiers_dir = os.path.join(os.path.dirname(__file__), 'classifiers')
        builtin_path = os.path.join(classifiers_dir, 'builtin_rules.json')
        custom_path = None
        if not config.get('no_custom_rules'):
            custom_path = config.get('custom_rules')
            if not custom_path:
                default_custom = os.path.join(classifiers_dir, 'custom_rules.json')
                if os.path.exists(default_custom):
                    custom_path = default_custom

        self._classifier = IPClassifier(builtin_path, custom_path)
        self._progress = ProgressManager(self._output_dir, prefix)
        self._batch_writer = BatchIPWriter(IPWriter())

        if reporter:
            self._reporter = reporter
        else:
            self._reporter = TextTraceReporter(
                self._output_dir, prefix, os.path.abspath(ip_file))
        self._reporter.report['total_ips'] = len(self._ips)

    def run(self):
        from_phase = self._config.get('from_phase')
        only_phase = self._config.get('only_phase')

        if from_phase and from_phase > 1:
            self._progress.clear_from(from_phase)
            logger.info("从阶段 %d 开始，已清除后续阶段的标记文件", from_phase)

        phases_to_run = [only_phase] if only_phase else [1, 2, 3, 4]

        phase_methods = {
            1: self._phase1_collect_basic,
            2: self._phase2_classify,
            3: self._phase3_deep_query,
            4: self._phase4_summary,
        }

        for phase_num in phases_to_run:
            if phase_num != 1 and not only_phase:
                if from_phase and phase_num < from_phase:
                    logger.info("跳过阶段 %d（已完成）", phase_num)
                    continue

            logger.info("")
            logger.info("=" * 60)
            logger.info("阶段 %d: %s", phase_num, PHASE_NAMES.get(phase_num, ''))
            logger.info("=" * 60)

            phase_methods[phase_num]()

        self._reporter.save_report()

    def _resolve_output_dir(self, project_dir: str) -> str:
        output_dir = self._ip_reader.settings.storage_dir
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(project_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    # ── Phase 1: 基础情报采集 ──

    def _phase1_collect_basic(self):
        if self._progress.is_phase_done(1):
            logger.info("阶段1已完成，跳过")
            return

        processed = self._progress.load_completed(1)
        if processed:
            logger.info("发现进度文件，已完成 %d 个IP，从断点继续", len(processed))

        ipinfo_settings = IpinfoSettings()
        rdns_settings = RdnsSettings()
        channel_timeout = self._config.get('channel_timeout', 0)

        total = len(self._ips)
        skipped = len(processed)
        success_count = 0
        fail_count = 0

        logger.info("总IP数: %d", total)
        logger.info("已完成: %d", skipped)
        logger.info("剩余: %d", total - skipped)
        logger.info("IPInfo 查询间隔: %ss", ipinfo_settings.ipinfo_query_delay)
        logger.info("RDNS 查询超时: %ss", rdns_settings.rdns_query_timeout)
        logger.info("-" * 60)

        with self._batch_writer:
            for i, ip in enumerate(self._ips, 1):
                if ip in processed:
                    continue

                results = self._query_channels_parallel(ip, [
                    ('ipinfo_api', fetch_ipinfo,
                     {'key': ipinfo_settings.ipinfo_access_token, 'delay': 0}),
                    ('rdns_ptr', fetch_rdns_ptr,
                     {'timeout': rdns_settings.rdns_query_timeout, 'delay': 0}),
                ], channel_timeout)

                ipinfo_data = results.get('ipinfo_api', {'raw_error': 'no result'})
                rdns_data = results.get('rdns_ptr', {'raw_error': 'no result'})

                if 'raw_error' in ipinfo_data:
                    logger.info("[%d/%d] %s [ipinfo ❌] [rdns ...]",
                                i, total, ip)
                    fail_count += 1
                else:
                    country = ipinfo_data.get('country', 'N/A')
                    org = ipinfo_data.get('as_name', 'N/A')
                    logger.info("[%d/%d] %s [ipinfo ✅ %s/%s]",
                                i, total, ip, country, org)
                    success_count += 1

                if rdns_data.get('has_ptr'):
                    hostname = rdns_data.get('hostname', 'N/A')
                    logger.info("  [rdns ✅ %s]", hostname)
                else:
                    logger.info("  [rdns ❌]")

                self._batch_writer.add(ip, 'ipinfo_api', ipinfo_data)
                self._batch_writer.add(ip, 'rdns_ptr', rdns_data)
                self._batch_writer.flush_batch()

                self._progress.record(ip, 1)
                self._progress.flush()

                time.sleep(ipinfo_settings.ipinfo_query_delay)

        self._progress.mark_phase_done(1)

        self._reporter.record_phase(1, {
            'status': 'done',
            'ips_processed': total,
            'success': success_count,
            'fail': fail_count,
            'resumed_from': skipped,
        })

        logger.info("阶段1完成: 处理 %d 个IP (断点续跑 %d), "
                     "新增成功 %d, 新增失败 %d",
                     total, skipped, success_count, fail_count)

    # ── Phase 2: 自动分类过滤 ──

    def _phase2_classify(self):
        if self._progress.is_phase_done(2):
            logger.info("阶段2已完成，跳过")
            return

        classification = {}
        stats = {}
        unclassified_rdns = []
        no_info_ips = []

        total = len(self._ips)
        logger.info("总IP数: %d", total)
        logger.info("内置规则分类: %s", ', '.join(self._classifier.categories))
        logger.info("-" * 60)

        with self._batch_writer:
            for i, ip in enumerate(self._ips, 1):
                ip_data = self._ip_reader.get_ip_data(ip)

                if not ip_data:
                    result = {
                        'category': 'other',
                        'label': '其他',
                        'matched_by': [],
                        'need_deep_query': True,
                        'classify_time': datetime.now().isoformat(),
                    }
                else:
                    classify_result = self._classifier.classify(ip_data)
                    result = classify_result.to_dict()

                classification[ip] = result
                cat = result['category']
                stats[cat] = stats.get(cat, 0) + 1

                self._batch_writer.add(ip, 'trace_classify', result)

                label = result['label']
                matched_info = ''
                if result['matched_by']:
                    first = result['matched_by'][0]
                    matched_info = f" ← {first['field']} ~ {first['pattern']}"
                logger.info("[%d/%d] %s → %s%s", i, total, ip, label, matched_info)

                if cat == 'other' and ip_data:
                    rdns_data = ip_data.get('rdns_ptr', {})
                    if rdns_data.get('has_ptr'):
                        unclassified_rdns.append({
                            'ip': ip,
                            'hostname': rdns_data.get('hostname', ''),
                            'aliases': rdns_data.get('aliases', []),
                            'ipinfo_org': ip_data.get('ipinfo_api', {}).get('as_name', ''),
                            'ipinfo_country': ip_data.get('ipinfo_api', {}).get('country', ''),
                            'ipinfo_region': ip_data.get('ipinfo_api', {}).get('region', ''),
                        })
                    elif not ip_data.get('ipinfo_api', {}).get('as_name'):
                        no_info_ips.append({
                            'ip': ip,
                            'hostname': '',
                            'aliases': [],
                            'ipinfo_org': '',
                            'ipinfo_country': ip_data.get('ipinfo_api', {}).get('country', ''),
                            'ipinfo_region': ip_data.get('ipinfo_api', {}).get('region', ''),
                        })

            self._batch_writer.flush_batch()

        self._reporter.save_unclassified(unclassified_rdns)
        self._reporter.save_no_info(no_info_ips)

        filtered_ips = [
            ip for ip, cls in classification.items()
            if cls['category'] in DEEP_QUERY_CATEGORIES
        ]
        prefix = self._ip_reader.settings.storage_name
        filtered_file = os.path.join(
            self._output_dir, f'{prefix}.trace_filtered_ips')
        with open(filtered_file, 'w', encoding='utf-8') as f:
            for ip in filtered_ips:
                f.write(ip + '\n')

        self._progress.mark_phase_done(2)

        deep_needed = len(filtered_ips)
        deep_skipped = total - deep_needed

        self._reporter.record_phase(2, {
            'status': 'done',
            'classification': stats,
            'deep_query_needed': deep_needed,
            'deep_query_skipped': deep_skipped,
            'unclassified_rdns_count': len(unclassified_rdns),
            'no_info_count': len(no_info_ips),
        })

        logger.info("=" * 60)
        logger.info("分类统计:")
        for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
            logger.info("  %s: %d", cat, count)
        logger.info("需要深度查询: %d", deep_needed)
        logger.info("跳过深度查询: %d", deep_skipped)
        logger.info("未识别RDNS: %d", len(unclassified_rdns))
        logger.info("信息不足IP: %d", len(no_info_ips))
        logger.info("过滤后IP列表: %s", filtered_file)
        logger.info("=" * 60)

    # ── Phase 3: 深度查询 ──

    def _phase3_deep_query(self):
        if self._config.get('no_deep_query'):
            logger.info("已跳过深度查询（--no-deep-query）")
            self._reporter.record_phase(3, {
                'status': 'skipped', 'ips_deep_queried': 0})
            return

        if self._progress.is_phase_done(3):
            logger.info("阶段3已完成，跳过")
            return

        prefix = self._ip_reader.settings.storage_name
        filtered_file = os.path.join(
            self._output_dir, f'{prefix}.trace_filtered_ips')
        if not os.path.exists(filtered_file):
            logger.info("未找到过滤后的IP文件，使用全量IP")
            filtered_ips = self._ips
        else:
            with open(filtered_file, 'r', encoding='utf-8') as f:
                filtered_ips = [line.strip() for line in f if line.strip()]

        if not filtered_ips:
            logger.info("没有需要深度查询的IP")
            self._reporter.record_phase(3, {
                'status': 'done', 'ips_deep_queried': 0})
            self._progress.mark_phase_done(3)
            return

        processed = self._progress.load_completed(3)
        if processed:
            logger.info("发现进度文件，已完成 %d 个IP，从断点继续",
                         len(processed))

        aizhan_settings = AizhanSettings()
        chinaz_settings = ChinazSettings()
        fofa_settings = FofaSettings()
        channel_timeout = self._config.get('channel_timeout', 0)

        total = len(filtered_ips)
        skipped = len([ip for ip in filtered_ips if ip in processed])

        logger.info("需要深度查询的IP: %d", total)
        logger.info("已完成: %d", skipped)
        logger.info("剩余: %d", total - skipped)
        logger.info("爱站网查询间隔: %ss", aizhan_settings.aizhan_query_delay)
        logger.info("站长之家查询间隔: %ss", chinaz_settings.chinaz_query_delay)
        logger.info("Fofa Host 查询间隔: %ss", fofa_settings.fofa_query_delay)
        logger.info("-" * 60)

        max_delay = max(
            aizhan_settings.aizhan_query_delay,
            chinaz_settings.chinaz_query_delay,
            fofa_settings.fofa_query_delay,
        )

        new_count = 0
        with self._batch_writer:
            for i, ip in enumerate(filtered_ips, 1):
                if ip in processed:
                    continue

                new_count += 1
                logger.info("[%d/%d] 深度查询: %s", i, total, ip)

                results = self._query_channels_parallel(ip, [
                    ('aizhan', fetch_aizhan,
                     {'cookie': aizhan_settings.aizhan_cookie, 'delay': 0}),
                    ('chinaz', fetch_chinaz,
                     {'cookie': chinaz_settings.chinaz_cookie, 'delay': 0}),
                    ('fofa_host', fetch_fofa_host,
                     {'key': fofa_settings.fofa_api_key, 'delay': 0}),
                ], channel_timeout)

                aizhan_data = results.get('aizhan', {'raw_error': 'no result'})
                chinaz_data = results.get('chinaz', {'raw_error': 'no result'})
                fofa_data = results.get('fofa_host', {'raw_error': 'no result'})

                if aizhan_data.get('success'):
                    dc = aizhan_data.get('domain_count', 0)
                    loc = aizhan_data.get('location', 'N/A')
                    logger.info("  爱站: ✅ %s - %d 个域名", loc, dc)
                else:
                    logger.info("  爱站: ❌ %s",
                                aizhan_data.get('error', 'N/A'))

                if chinaz_data.get('success'):
                    dc = len(chinaz_data.get('domains', []))
                    loc = chinaz_data.get('location', 'N/A')
                    logger.info("  站长: ✅ %s - %d 个域名", loc, dc)
                else:
                    logger.info("  站长: ❌ %s",
                                chinaz_data.get('error', 'N/A'))

                if 'raw_error' in fofa_data:
                    logger.info("  Fofa Host: ❌ %s",
                                fofa_data.get('error_message', 'N/A'))
                else:
                    logger.info("  Fofa Host: ✅")

                self._batch_writer.add(ip, 'aizhan', aizhan_data)
                self._batch_writer.add(ip, 'chinaz', chinaz_data)
                self._batch_writer.add(ip, 'fofa_host', fofa_data)
                self._batch_writer.flush_batch()

                self._progress.record(ip, 3)
                self._progress.flush()

                time.sleep(max_delay)

        self._progress.mark_phase_done(3)

        self._reporter.record_phase(3, {
            'status': 'done',
            'ips_deep_queried': total,
            'resumed_from': skipped,
            'newly_queried': new_count,
        })

        logger.info("阶段3完成: 深度查询 %d 个IP "
                     "(断点续跑 %d, 新增 %d)",
                     total, skipped, new_count)

    # ── Phase 4: 汇总输出 ──

    def _phase4_summary(self):
        self._reporter.generate_summary(self._ips, self._reporter.report)

    # ── 并行查询核心方法 ──

    def _query_channels_parallel(
            self, ip: str, channel_specs: list,
            channel_timeout: int = 0) -> dict:
        results = {}

        with ThreadPoolExecutor(max_workers=len(channel_specs)) as executor:
            future_to_name = {}
            for name, fetch_func, kwargs in channel_specs:
                future = executor.submit(fetch_func, ip, **kwargs)
                future_to_name[future] = name

            timeout_sec = channel_timeout if channel_timeout > 0 else None
            done, not_done = wait(future_to_name, timeout=timeout_sec)

            for future in done:
                name = future_to_name[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.warning("IP %s 渠道 %s 查询异常: %s", ip, name, e)
                    results[name] = {'raw_error': str(e)}

            for future in not_done:
                name = future_to_name[future]
                future.cancel()
                logger.warning("IP %s 渠道 %s 查询超时 (%ds)",
                               ip, name, channel_timeout)
                results[name] = {
                    'raw_error': f'channel timeout after {channel_timeout}s'}

        for name, _, _ in channel_specs:
            if name not in results:
                results[name] = {'raw_error': 'no result'}

        return results
