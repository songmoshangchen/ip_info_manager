import json
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
    ChinazSettings, FofaSettings, Settings, TraceIPSettings,
)
from reader import IPReader
from writer import IPWriter

from utils.pid_manager import PidManager

from .classifier import IPClassifier
from .excel_exporter import generate_trace_excel
from .progress import BatchIPWriter, ProgressManager
from .reporter import BaseTraceReporter, TextTraceReporter
from utils.dns_verify import (
    extract_domain_mappings, batch_verify as dns_batch_verify,
    build_verify_results as dns_build_verify_results,
    add_verify_stats as dns_add_verify_stats,
)

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')

DEEP_QUERY_CATEGORIES = {'cloud_provider', 'residential', 'other'}

PHASE_NAMES = {
    1: '基础情报采集',
    2: '自动分类过滤 + 标签打标',
    3: '深度查询',
    4: '汇总输出',
    5: '生成报告（Word + Excel）',
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

    SCENARIO_NAME = 'trace_ip'

    def __init__(self, ip_file: str, config: dict,
                 reporter: BaseTraceReporter = None):
        self._config = config
        self._config['ip_file'] = ip_file
        self._ips = _load_ips(ip_file)

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        self._output_dir = self._resolve_output_dir(project_root)

        prefix = Settings().trace_ip_project_name
        self._prefix = prefix

        scenario_settings = Settings().model_copy(update={'storage_name': prefix})

        self._ip_reader = IPReader(settings=scenario_settings, storage_dir=self._output_dir)

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
        self._batch_writer = BatchIPWriter(IPWriter(settings=scenario_settings, storage_dir=self._output_dir))
        self._pid = PidManager(self._output_dir, prefix)

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

        phases_to_run = [only_phase] if only_phase else [1, 2, 3, 4, 5]

        self._check_dependencies(phases_to_run)

        self._pid.write_pid(
            'trace_ip', self._config.get('ip_file', ''),
            len(self._ips),
            current_phase=phases_to_run[0] if phases_to_run else 1,
            from_phase=from_phase,
            only_phase=only_phase,
        )

        try:
            self._run_phases(phases_to_run, from_phase, only_phase)
        finally:
            self._pid.remove_pid()

    def _check_dependencies(self, phases_to_run):
        if 5 in phases_to_run:
            from tools.docx_builder import DOCX_AVAILABLE
            if not DOCX_AVAILABLE:
                logger.error("=" * 60)
                logger.error("缺少必需依赖: python-docx")
                logger.error("Phase 5 (生成报告) 需要此依赖才能生成 Word 报告")
                logger.error("安装命令: pip install python-docx")
                logger.error("=" * 60)
                sys.exit(1)

            try:
                import openpyxl
            except ImportError:
                logger.error("=" * 60)
                logger.error("缺少必需依赖: openpyxl")
                logger.error("Phase 5 (生成报告) 需要此依赖才能生成 Excel 报告")
                logger.error("安装命令: pip install openpyxl")
                logger.error("=" * 60)
                sys.exit(1)

    def _run_phases(self, phases_to_run, from_phase, only_phase):
        phase_methods = {
            1: self._phase1_collect_basic,
            2: self._phase2_classify,
            3: self._phase3_deep_query,
            4: self._phase4_summary,
            5: self._phase5_generate_reports,
        }

        for phase_num in phases_to_run:
            if phase_num != 1 and not only_phase:
                if from_phase and phase_num < from_phase:
                    logger.info("跳过阶段 %d（已完成）", phase_num)
                    continue

            self._pid.update_heartbeat(current_phase=phase_num)

            logger.info("")
            logger.info("=" * 60)
            logger.info("阶段 %d: %s", phase_num, PHASE_NAMES.get(phase_num, ''))
            logger.info("=" * 60)

            phase_methods[phase_num]()

        if 5 not in phases_to_run:
            self._reporter.save_report()

    def _resolve_output_dir(self, project_root: str) -> str:
        project_name = Settings().trace_ip_project_name
        output_dir = os.path.join(
            project_root, 'data', self.SCENARIO_NAME, project_name)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    # ── Phase 1: 基础情报采集 ──

    def _phase1_collect_basic(self):
        if self._progress.is_phase_done(1):
            logger.info("阶段1已完成，跳过")
            return

        processed = self._progress.load_completed(1)
        if processed:
            pct = len(processed) / len(self._ips) * 100 if self._ips else 0
            logger.info("发现进度文件: 已处理 %d/%d (%.1f%%)，将从断点继续",
                        len(processed), len(self._ips), pct)

        json_ips = self._ip_reader.list_all_ips()
        processed_from_json = set()
        for ip in json_ips:
            if ip not in self._ips:
                continue
            ip_data = self._ip_reader.get_ip_data(ip)
            if not ip_data:
                continue
            has_phase1_data = True
            if 'ipinfo_api' not in ip_data or 'raw_error' in ip_data.get('ipinfo_api', {}):
                has_phase1_data = False
            if 'rdns_ptr' not in ip_data:
                has_phase1_data = False
            if has_phase1_data:
                processed_from_json.add(ip)

        if processed_from_json:
            new_from_json = processed_from_json - processed
            if new_from_json:
                logger.info("从JSON中发现 %d 个IP已有完整阶段1数据（不在进度文件中），自动跳过",
                            len(new_from_json))
            processed = processed | processed_from_json

        ipinfo_settings = IpinfoSettings()
        rdns_settings = RdnsSettings()
        trace_settings = TraceIPSettings()
        channel_timeout = self._config.get('channel_timeout', 0)

        total = len(self._ips)
        skipped = len(processed)
        success_count = 0
        fail_count = 0

        delays = []
        enabled_channels = []

        logger.info("总IP数: %d", total)
        logger.info("已完成: %d", skipped)
        logger.info("剩余: %d", total - skipped)
        logger.info("-" * 60)

        if trace_settings.phase1_ipinfo_enabled:
            delays.append(ipinfo_settings.ipinfo_query_delay)
            enabled_channels.append('ipinfo_api')
            logger.info("✓ IPInfo 查询: 已启用")
        else:
            logger.info("✗ IPInfo 查询: 已禁用")

        if trace_settings.phase1_rdns_ptr_enabled:
            delays.append(rdns_settings.rdns_query_delay)
            enabled_channels.append('rdns_ptr')
            logger.info("✓ RDNS PTR 反向解析: 已启用")
        else:
            logger.info("✗ RDNS PTR 反向解析: 已禁用")

        if not enabled_channels:
            logger.error("没有启用的采集渠道，请检查配置文件中的 IP_TRACE_IP_PHASE1_*_ENABLED 选项")
            return

        logger.info("-" * 60)
        logger.info("已启用渠道: %s", ', '.join(enabled_channels))
        logger.info("-" * 60)

        max_delay = max(delays) if delays else 0
        _p1_start = time.time()
        _p1_new_count = 0

        with self._batch_writer:
            for i, ip in enumerate(self._ips, 1):
                if ip in processed:
                    continue

                _p1_new_count += 1

                channel_specs = []

                if trace_settings.phase1_ipinfo_enabled:
                    channel_specs.append(
                        ('ipinfo_api', fetch_ipinfo,
                         {'key': ipinfo_settings.ipinfo_access_token, 'delay': 0}))

                if trace_settings.phase1_rdns_ptr_enabled:
                    channel_specs.append(
                        ('rdns_ptr', fetch_rdns_ptr,
                         {'timeout': rdns_settings.rdns_query_timeout, 'delay': 0}))

                results = self._query_channels_parallel(ip, channel_specs, channel_timeout)

                ipinfo_data = results.get('ipinfo_api', {'raw_error': 'no result'}) if trace_settings.phase1_ipinfo_enabled else None
                rdns_data = results.get('rdns_ptr', {'raw_error': 'no result'}) if trace_settings.phase1_rdns_ptr_enabled else None

                if ipinfo_data:
                    if 'raw_error' in ipinfo_data:
                        logger.info("[%d/%d] %s [ipinfo ❌]", i, total, ip)
                        fail_count += 1
                    else:
                        country = ipinfo_data.get('country', 'N/A')
                        org = ipinfo_data.get('as_name', 'N/A')
                        logger.info("[%d/%d] %s [ipinfo ✅ %s/%s]",
                                    i, total, ip, country, org)
                        success_count += 1

                if rdns_data:
                    if rdns_data.get('has_ptr'):
                        hostname = rdns_data.get('hostname', 'N/A')
                        logger.info("  [rdns ✅ %s]", hostname)
                    else:
                        logger.info("  [rdns ❌]")

                if trace_settings.phase1_ipinfo_enabled:
                    self._batch_writer.add(ip, 'ipinfo_api', ipinfo_data)

                if trace_settings.phase1_rdns_ptr_enabled:
                    self._batch_writer.add(ip, 'rdns_ptr', rdns_data)

                self._batch_writer.flush_batch()

                self._progress.record(ip, 1)
                self._progress.flush()

                self._pid.update_heartbeat(current_phase=1)

                if _p1_new_count > 0:
                    elapsed = time.time() - _p1_start
                    remaining = total - i
                    if remaining > 0:
                        avg = elapsed / _p1_new_count
                        eta_s = remaining * avg
                        eta_m = int(eta_s // 60)
                        eta_sec = int(eta_s % 60)
                        logger.info("  ETA: ~%dmin%02ds (剩余 %d 个IP)", eta_m, eta_sec, remaining)

                time.sleep(max_delay)

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

        if not self._config.get('no_tagger'):
            self._run_ip_tagger()

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
        prefix = Settings().trace_ip_project_name
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

        prefix = Settings().trace_ip_project_name
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
            pct = len(processed) / len(filtered_ips) * 100 if filtered_ips else 0
            logger.info("发现进度文件: 已处理 %d/%d (%.1f%%)，将从断点继续",
                         len(processed), len(filtered_ips), pct)

        json_ips = self._ip_reader.list_all_ips()
        processed_from_json = set()
        for ip in json_ips:
            if ip not in filtered_ips:
                continue
            ip_data = self._ip_reader.get_ip_data(ip)
            if not ip_data:
                continue
            has_phase3_data = False
            for ch in ('aizhan', 'chinaz', 'fofa_host'):
                if ch in ip_data and 'raw_error' not in ip_data[ch]:
                    has_phase3_data = True
                    break
            if has_phase3_data:
                processed_from_json.add(ip)

        if processed_from_json:
            new_from_json = processed_from_json - processed
            if new_from_json:
                logger.info("从JSON中发现 %d 个IP已有阶段3数据（不在进度文件中），自动跳过",
                            len(new_from_json))
            processed = processed | processed_from_json

        aizhan_settings = AizhanSettings()
        chinaz_settings = ChinazSettings()
        fofa_settings = FofaSettings()
        trace_settings = TraceIPSettings()
        channel_timeout = self._config.get('channel_timeout', 0)

        total = len(filtered_ips)
        skipped = len([ip for ip in filtered_ips if ip in processed])

        delays = []
        enabled_channels = []

        logger.info("需要深度查询的IP: %d", total)
        logger.info("已完成: %d", skipped)
        logger.info("剩余: %d", total - skipped)
        logger.info("-" * 60)

        if trace_settings.phase3_aizhan_enabled:
            delays.append(aizhan_settings.aizhan_query_delay)
            enabled_channels.append('aizhan')
            logger.info("✓ 爱站网 IP 反查域名: 已启用")
        else:
            logger.info("✗ 爱站网 IP 反查域名: 已禁用")

        if trace_settings.phase3_chinaz_enabled:
            delays.append(chinaz_settings.chinaz_query_delay)
            enabled_channels.append('chinaz')
            logger.info("✓ 站长之家 IP 反查域名: 已启用")
        else:
            logger.info("✗ 站长之家 IP 反查域名: 已禁用")

        if trace_settings.phase3_fofa_host_enabled:
            delays.append(fofa_settings.fofa_query_delay)
            enabled_channels.append('fofa_host')
            logger.info("✓ Fofa Host 聚合查询: 已启用")
        else:
            logger.info("✗ Fofa Host 聚合查询: 已禁用")

        if not enabled_channels:
            logger.warning("深度查询没有启用的采集渠道，请检查配置文件中的 IP_TRACE_IP_PHASE3_*_ENABLED 选项")

        logger.info("-" * 60)
        logger.info("已启用渠道: %s", ', '.join(enabled_channels))
        logger.info("-" * 60)

        max_delay = max(delays) if delays else 0

        _p3_start = time.time()
        new_count = 0
        with self._batch_writer:
            for i, ip in enumerate(filtered_ips, 1):
                if ip in processed:
                    continue

                new_count += 1
                logger.info("[%d/%d] 深度查询: %s", i, total, ip)

                channel_specs = []

                if trace_settings.phase3_aizhan_enabled:
                    channel_specs.append(
                        ('aizhan', fetch_aizhan,
                         {'cookie': aizhan_settings.aizhan_cookie, 'delay': 0}))

                if trace_settings.phase3_chinaz_enabled:
                    channel_specs.append(
                        ('chinaz', fetch_chinaz,
                         {'cookie': chinaz_settings.chinaz_cookie, 'delay': 0}))

                if trace_settings.phase3_fofa_host_enabled:
                    channel_specs.append(
                        ('fofa_host', fetch_fofa_host,
                         {'key': fofa_settings.fofa_api_key, 'delay': 0}))

                if not channel_specs:
                    logger.warning("没有可用的深度查询渠道，跳过此 IP")
                    continue

                results = self._query_channels_parallel(ip, channel_specs, channel_timeout)

                aizhan_data = results.get('aizhan', {'raw_error': 'no result'}) if trace_settings.phase3_aizhan_enabled else None
                chinaz_data = results.get('chinaz', {'raw_error': 'no result'}) if trace_settings.phase3_chinaz_enabled else None
                fofa_data = results.get('fofa_host', {'raw_error': 'no result'}) if trace_settings.phase3_fofa_host_enabled else None

                if aizhan_data:
                    if aizhan_data.get('success'):
                        dc = aizhan_data.get('domain_count', 0)
                        loc = aizhan_data.get('location', 'N/A')
                        logger.info("  爱站: ✅ %s - %d 个域名", loc, dc)
                    else:
                        logger.info("  爱站: ❌ %s",
                                    aizhan_data.get('error', 'N/A'))

                if chinaz_data:
                    if chinaz_data.get('success'):
                        dc = len(chinaz_data.get('domains', []))
                        loc = chinaz_data.get('location', 'N/A')
                        logger.info("  站长: ✅ %s - %d 个域名", loc, dc)
                    else:
                        logger.info("  站长: ❌ %s",
                                    chinaz_data.get('error', 'N/A'))

                if fofa_data:
                    if 'raw_error' in fofa_data:
                        logger.info("  Fofa Host: ❌ %s",
                                    fofa_data.get('error_message', 'N/A'))
                    else:
                        logger.info("  Fofa Host: ✅")

                if trace_settings.phase3_aizhan_enabled:
                    self._batch_writer.add(ip, 'aizhan', aizhan_data)

                if trace_settings.phase3_chinaz_enabled:
                    self._batch_writer.add(ip, 'chinaz', chinaz_data)

                if trace_settings.phase3_fofa_host_enabled:
                    self._batch_writer.add(ip, 'fofa_host', fofa_data)

                self._batch_writer.flush_batch()

                self._progress.record(ip, 3)
                self._progress.flush()

                self._pid.update_heartbeat(current_phase=3)

                if new_count > 1:
                    elapsed = time.time() - _p3_start
                    remaining = total - i
                    if remaining > 0:
                        avg = elapsed / new_count
                        eta_s = remaining * avg
                        eta_m = int(eta_s // 60)
                        eta_sec = int(eta_s % 60)
                        logger.info("  ETA: ~%dmin%02ds (剩余 %d 个IP)", eta_m, eta_sec, remaining)

                time.sleep(max_delay)

        self._progress.mark_phase_done(3)

        self._dns_verify_phase3(filtered_ips, trace_settings)

        self._reporter.record_phase(3, {
            'status': 'done',
            'ips_deep_queried': total,
            'resumed_from': skipped,
            'newly_queried': new_count,
        })

        logger.info("阶段3完成: 深度查询 %d 个IP "
                     "(断点续跑 %d, 新增 %d)",
                     total, skipped, new_count)

    def _dns_verify_phase3(self, filtered_ips, trace_settings):
        if self._config.get('no_dns_verify'):
            logger.info("已跳过 DNS 域名验证（--no-dns-verify）")
            return

        if not trace_settings.phase3_dns_verify_enabled:
            logger.info("DNS 域名验证: 已禁用（配置项 PHASE3_DNS_VERIFY_ENABLED=false）")
            return

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        if not os.path.exists(json_path):
            logger.info("DNS 域名验证: 无数据文件，跳过")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            ip_data = json.load(f)

        filtered_data = {ip: ip_data[ip] for ip in filtered_ips if ip in ip_data}
        if not filtered_data:
            logger.info("DNS 域名验证: 无深度查询数据，跳过")
            return

        mappings = extract_domain_mappings(filtered_data)
        if not mappings:
            logger.info("DNS 域名验证: 未提取到域名映射，跳过")
            return

        dns_timeout = trace_settings.dns_verify_timeout
        dns_concurrency = trace_settings.dns_verify_concurrency

        logger.info("-" * 60)
        logger.info("开始 DNS 域名验证 (%d 个域名, 并发: %d, 超时: %.1fs)",
                     len(mappings), dns_concurrency, dns_timeout)

        def on_progress(done, total_count):
            if done % 20 == 0 or done == total_count:
                logger.info("DNS 验证进度: %d/%d", done, total_count)

        verify_results = dns_batch_verify(
            mappings, timeout=dns_timeout,
            concurrency=dns_concurrency, progress_callback=on_progress)

        grouped = dns_build_verify_results(mappings, verify_results)
        verify_data = dns_add_verify_stats(grouped)

        verify_stats = {'matched': 0, 'changed': 0, 'unresolved': 0,
                        'timeout': 0, 'error': 0}
        for ip, vd in verify_data.items():
            for st in ('matched', 'changed', 'unresolved', 'timeout', 'error'):
                verify_stats[st] += vd.get(st, 0)

        with self._batch_writer:
            for ip, vd in verify_data.items():
                self._batch_writer.add(ip, 'domain_verify', vd)
            self._batch_writer.flush_batch()

        logger.info("DNS 验证完成: 匹配 %d, 变更 %d, 无法解析 %d, 超时 %d, 错误 %d",
                     verify_stats['matched'], verify_stats['changed'],
                     verify_stats['unresolved'], verify_stats['timeout'],
                     verify_stats['error'])

    # ── Phase 4: 汇总输出 ──

    def _phase4_summary(self):
        self._reporter.generate_summary(self._ips, self._reporter.report)

    # ── Phase 5: 生成报告（Word + Excel） ──

    def _phase5_generate_reports(self):
        exclude_ips_file = self._config.get('exclude_ips_file')
        exclude_info = None

        if exclude_ips_file:
            exclude_info = self._load_exclude_ips(exclude_ips_file)

        self._reporter.generate_docx_report(exclude_info=exclude_info)
        generate_trace_excel(self._output_dir, self._prefix, exclude_info=exclude_info)
        self._print_report_summary(exclude_info=exclude_info)

    def _load_exclude_ips(self, exclude_ips_file: str) -> dict | None:
        if not os.path.exists(exclude_ips_file):
            logger.warning("排除IP文件不存在: %s，将不排除任何IP", exclude_ips_file)
            return None

        with open(exclude_ips_file, 'r', encoding='utf-8') as f:
            exclude_set = set(line.strip() for line in f if line.strip())

        if not exclude_set:
            logger.info("排除IP文件为空，将不排除任何IP")
            return None

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        if not os.path.exists(json_path):
            logger.warning("找不到数据文件 %s，将不排除任何IP", json_path)
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            ip_data = json.load(f)

        data_ips = set(ip_data.keys())
        effective_excludes = exclude_set & data_ips
        not_in_data = exclude_set - data_ips

        if not_in_data:
            logger.info("排除文件中有 %d 个IP不在数据中（已忽略）: %s",
                        len(not_in_data), ', '.join(sorted(not_in_data)[:10]))
            if len(not_in_data) > 10:
                logger.info("  ... 共 %d 个", len(not_in_data))

        if not effective_excludes:
            logger.info("排除文件中的IP均不在当前数据中，将不排除任何IP")
            return None

        logger.info("排除IP: 文件中 %d 个, 有效排除 %d 个, 不在数据中 %d 个",
                    len(exclude_set), len(effective_excludes), len(not_in_data))

        return {
            'exclude_ips': effective_excludes,
            'total_in_file': len(exclude_set),
            'effective_count': len(effective_excludes),
            'not_in_data_count': len(not_in_data),
            'not_in_data_ips': sorted(not_in_data),
        }

    def _print_report_summary(self, exclude_info=None):
        from scenarios.trace_ip.excel_exporter import _trace_priority, _extract_all_domains

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            ip_data = json.load(f)

        if exclude_info:
            exclude_set = exclude_info['exclude_ips']
            ip_data = {ip: info for ip, info in ip_data.items() if ip not in exclude_set}

        p_groups = {1: [], 2: [], 3: [], 4: []}
        for ip, info in ip_data.items():
            if info.get('trace_classify', {}).get('need_deep_query'):
                lvl = _trace_priority(ip, info)
                p_groups[lvl].append((ip, info))

        logger.info("")
        logger.info("=" * 60)
        logger.info("报告摘要")
        logger.info("=" * 60)
        if exclude_info:
            logger.info("原始IP数: %d, 已排除: %d, 剩余: %d",
                        len(ip_data) + exclude_info['effective_count'],
                        exclude_info['effective_count'], len(ip_data))
        logger.info("P1 核心溯源: %d 个IP", len(p_groups[1]))
        if p_groups[1]:
            for ip, _ in p_groups[1][:10]:
                logger.info("  %s", ip)
            if len(p_groups[1]) > 10:
                logger.info("  ... 共 %d 个", len(p_groups[1]))
        logger.info("P2 重点溯源: %d 个IP", len(p_groups[2]))
        logger.info("P3 辅助溯源: %d 个IP", len(p_groups[3]))
        logger.info("P4 暂缓: %d 个IP", len(p_groups[4]))

        max_domains = 0
        top_ip = None
        for ip, info in ip_data.items():
            domains = _extract_all_domains(info)
            if len(domains) > max_domains:
                max_domains = len(domains)
                top_ip = ip

        if top_ip and max_domains > 0:
            logger.info("高价值IP: %s (%d 个域名)", top_ip, max_domains)

        docx_path = os.path.join(self._output_dir, f'{self._prefix}.trace_report.docx')
        xlsx_path = os.path.join(self._output_dir, f'{self._prefix}.trace_report.xlsx')
        if os.path.exists(docx_path):
            logger.info("Word 报告: %s", docx_path)
        if os.path.exists(xlsx_path):
            logger.info("Excel 报告: %s", xlsx_path)
        logger.info("=" * 60)

    # ── IP 标签打标 ──

    def _run_ip_tagger(self):
        from tools.ip_tagger import run_tagger

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        level = self._config.get('tagger_level')

        logger.info("")
        logger.info("=" * 60)
        logger.info("IP 标签打标")
        logger.info("=" * 60)

        run_tagger(
            ip_file=self._config.get('ip_file', ''),
            mode='accumulate',
            output=json_path,
            level=level,
        )

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
