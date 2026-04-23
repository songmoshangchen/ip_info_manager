import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from channel.rdns_ptr import fetch_channel as fetch_rdns_ptr
from channel.aizhan import fetch_channel as fetch_aizhan
from channel.chinaz import fetch_channel as fetch_chinaz
from config import RdnsSettings, AizhanSettings, ChinazSettings
from reader import IPReader
from writer import IPWriter

from .dns_validator import batch_verify, build_verify_results
from .progress import BatchIPWriter, ProgressManager
from .reporter import BaseDomainLookupReporter, TextDomainLookupReporter

logger = logging.getLogger('ip_info_manager.scenarios.ip_domain_lookup')

PHASE_NAMES = {
    1: '域名收集',
    2: 'DNS正向验证',
    3: '汇总报告',
}


def _load_ips(ip_file: str) -> list:
    ips = []
    with open(ip_file, 'r', encoding='utf-8') as f:
        for line in f:
            ip = line.strip()
            if ip:
                ips.append(ip)
    return ips


class IPDomainLookupPipeline:

    def __init__(self, ip_file: str, config: dict,
                 reporter: BaseDomainLookupReporter = None):
        self._config = config
        self._ips = _load_ips(ip_file)
        self._ip_reader = IPReader()

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._output_dir = self._resolve_output_dir(project_dir)

        prefix = self._ip_reader.settings.storage_name

        self._progress = ProgressManager(self._output_dir, prefix)
        self._progress._PHASE_CONFIG = {
            1: 'domain_lookup_phase1.progress',
            2: 'domain_lookup_phase2.progress',
        }
        self._progress._PHASE_MARKERS = {
            1: 'domain_lookup_phase1_done',
            2: 'domain_lookup_phase2_done',
        }

        self._batch_writer = BatchIPWriter(IPWriter())

        if reporter:
            self._reporter = reporter
        else:
            self._reporter = TextDomainLookupReporter(
                self._output_dir, prefix, os.path.abspath(ip_file))
        self._reporter.report['total_ips'] = len(self._ips)

    def run(self):
        from_phase = self._config.get('from_phase')
        only_phase = self._config.get('only_phase')

        if from_phase and from_phase > 1:
            self._progress.clear_from(from_phase)
            logger.info("从阶段 %d 开始，已清除后续阶段的标记文件", from_phase)

        phases_to_run = [only_phase] if only_phase else [1, 2, 3]

        phase_methods = {
            1: self._phase1_collect_domains,
            2: self._phase2_dns_verify,
            3: self._phase3_summary,
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

    # ── Phase 1: 域名收集 ──

    def _phase1_collect_domains(self):
        if self._progress.is_phase_done(1):
            logger.info("阶段1已完成，跳过")
            return

        processed = self._progress.load_completed(1)
        if processed:
            logger.info("发现进度文件，已完成 %d 个IP，从断点继续", len(processed))

        rdns_settings = RdnsSettings()
        aizhan_settings = AizhanSettings()
        chinaz_settings = ChinazSettings()
        channel_timeout = self._config.get('channel_timeout', 0)

        total = len(self._ips)
        skipped = len(processed)
        success_count = 0

        logger.info("总IP数: %d", total)
        logger.info("已完成: %d", skipped)
        logger.info("剩余: %d", total - skipped)
        logger.info("-" * 60)

        max_delay = max(
            rdns_settings.rdns_query_delay,
            aizhan_settings.aizhan_query_delay,
            chinaz_settings.chinaz_query_delay,
        )

        channel_stats = defaultdict(int)

        with self._batch_writer:
            for i, ip in enumerate(self._ips, 1):
                if ip in processed:
                    continue

                results = self._query_channels_parallel(ip, [
                    ('rdns_ptr', fetch_rdns_ptr, {
                        'timeout': rdns_settings.rdns_query_timeout, 'delay': 0}),
                    ('aizhan', fetch_aizhan, {
                        'cookie': aizhan_settings.aizhan_cookie, 'delay': 0}),
                    ('chinaz', fetch_chinaz, {
                        'cookie': chinaz_settings.chinaz_cookie, 'delay': 0}),
                ], channel_timeout)

                candidates = self._extract_domains(ip, results)

                for c in candidates:
                    for src in c['sources']:
                        channel_stats[src] += 1

                lookup_data = {
                    'collect_time': datetime.now().isoformat(),
                    'candidates': candidates,
                    'candidate_count': len(candidates),
                }

                self._batch_writer.add(ip, 'ip_domain_lookup', lookup_data)
                self._batch_writer.flush_batch()

                self._progress.record(ip, 1)
                self._progress.flush()

                cand_count = len(candidates)
                if cand_count > 0:
                    logger.info("[%d/%d] %s 收集到 %d 个候选域名",
                                i, total, ip, cand_count)
                    success_count += 1
                else:
                    logger.info("[%d/%d] %s 未收集到域名", i, total, ip)

                time.sleep(max_delay)

        self._progress.mark_phase_done(1)

        self._reporter.record_phase(1, {
            'status': 'done',
            'ips_processed': total,
            'ips_with_domains': success_count,
            'resumed_from': skipped,
            'channel_stats': dict(channel_stats),
        })

        logger.info("阶段1完成: 处理 %d 个IP, 有域名 %d, 断点续跑 %d",
                     total, success_count, skipped)

    # ── Phase 2: DNS 正向验证 ──

    def _phase2_dns_verify(self):
        if self._progress.is_phase_done(2):
            logger.info("阶段2已完成，跳过")
            return

        processed = self._progress.load_completed(2)
        if processed:
            logger.info("发现进度文件，已完成 %d 个IP，从断点继续", len(processed))

        dns_timeout = self._config.get('dns_timeout', 3.0)
        dns_concurrency = self._config.get('dns_concurrency', 10)

        total = len(self._ips)
        skipped = len(processed)

        all_candidates = []
        ips_to_verify = []

        for ip in self._ips:
            if ip in processed:
                continue
            ip_data = self._ip_reader.get_ip_data(ip)
            if not ip_data:
                continue

            lookup = ip_data.get('ip_domain_lookup', {})
            candidates = lookup.get('candidates', [])
            if not candidates:
                continue

            for c in candidates:
                all_candidates.append({
                    'domain': c['domain'],
                    'target_ip': ip,
                    'sources': c.get('sources', []),
                })
            ips_to_verify.append(ip)

        need_verify = len(ips_to_verify)
        logger.info("需要验证的IP: %d (候选域名: %d)", need_verify, len(all_candidates))
        logger.info("已完成: %d", skipped)
        logger.info("DNS超时: %ss, 并发: %d", dns_timeout, dns_concurrency)
        logger.info("-" * 60)

        if not all_candidates:
            self._progress.mark_phase_done(2)
            self._reporter.record_phase(2, {
                'status': 'done',
                'verify_stats': {},
                'verified_map': {},
            })
            return

        logger.info("开始DNS验证 (%d 个域名)...", len(all_candidates))

        def on_progress(done, total_count):
            if done % 20 == 0 or done == total_count:
                logger.info("验证进度: %d/%d", done, total_count)

        verify_results = batch_verify(
            all_candidates, timeout=dns_timeout,
            concurrency=dns_concurrency, progress_callback=on_progress)

        verify_map = build_verify_results(all_candidates, verify_results)

        verify_stats = {'matched': 0, 'changed': 0, 'unresolved': 0,
                        'timeout': 0, 'error': 0}
        for ip, domains in verify_map.items():
            for d in domains:
                st = d['status']
                if st in verify_stats:
                    verify_stats[st] += 1

        with self._batch_writer:
            for ip in ips_to_verify:
                ip_data = self._ip_reader.get_ip_data(ip)
                if not ip_data:
                    continue

                lookup = ip_data.get('ip_domain_lookup', {})
                lookup['verify_time'] = datetime.now().isoformat()
                lookup['verified_domains'] = verify_map.get(ip, [])
                lookup['summary'] = {
                    st: sum(1 for d in verify_map.get(ip, []) if d['status'] == st)
                    for st in ('matched', 'changed', 'unresolved', 'timeout', 'error')
                }

                self._batch_writer.add(ip, 'ip_domain_lookup', lookup)

            self._batch_writer.flush_batch()

        for ip in ips_to_verify:
            self._progress.record(ip, 2)
        self._progress.flush()

        self._progress.mark_phase_done(2)

        self._reporter.record_phase(2, {
            'status': 'done',
            'verify_stats': verify_stats,
            'verified_map': {ip: domains for ip, domains in verify_map.items()},
        })

        logger.info("阶段2完成: 验证 %d 个域名", len(all_candidates))
        logger.info("  匹配: %d, 变更: %d, 无法解析: %d, 超时: %d, 错误: %d",
                     verify_stats['matched'], verify_stats['changed'],
                     verify_stats['unresolved'], verify_stats['timeout'],
                     verify_stats['error'])

    # ── Phase 3: 汇总报告 ──

    def _phase3_summary(self):
        self._reporter.generate_summary(self._ips, self._reporter.report)

    # ── 域名提取 ──

    def _extract_domains(self, ip: str, results: dict) -> list:
        domain_sources = defaultdict(list)

        rdns_data = results.get('rdns_ptr', {})
        if rdns_data.get('has_ptr'):
            hostname = rdns_data.get('hostname', '')
            if hostname:
                domain_sources[hostname].append('rdns_ptr')
            for alias in rdns_data.get('aliases', []):
                domain_sources[alias].append('rdns_ptr')

        for ch_name in ('aizhan', 'chinaz'):
            ch_data = results.get(ch_name, {})
            if ch_data.get('success'):
                for d in ch_data.get('domains', []):
                    domain = d.get('domain', '') if isinstance(d, dict) else d
                    if domain:
                        domain_sources[domain].append(ch_name)

        candidates = []
        for domain, sources in domain_sources.items():
            candidates.append({
                'domain': domain,
                'sources': sources,
            })

        return candidates

    # ── 并行查询 ──

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
                logger.warning("IP %s 渠道 %s 查询超时 (%ds)", ip, name, channel_timeout)
                results[name] = {
                    'raw_error': f'channel timeout after {channel_timeout}s'}

        for name, _, _ in channel_specs:
            if name not in results:
                results[name] = {'raw_error': 'no result'}

        return results
