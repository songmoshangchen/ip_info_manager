import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger('ip_info_manager.scenarios.ip_domain_lookup')


class BaseDomainLookupReporter(ABC):

    @abstractmethod
    def record_phase(self, phase_num: int, stats: dict):
        pass

    @abstractmethod
    def generate_summary(self, ips: list, report_data: dict):
        pass

    @abstractmethod
    def save_report(self):
        pass


class TextDomainLookupReporter(BaseDomainLookupReporter):

    def __init__(self, output_dir: str, prefix: str, ip_file: str):
        self._output_dir = output_dir
        self._prefix = prefix
        self._ip_file = ip_file
        self._report = {
            'report_time': None,
            'input_file': ip_file,
            'total_ips': 0,
            'phases': {},
        }

    @property
    def report(self) -> dict:
        return self._report

    @report.setter
    def report(self, value: dict):
        self._report = value

    def record_phase(self, phase_num: int, stats: dict):
        self._report['phases'][f'phase{phase_num}'] = stats

    def generate_summary(self, ips: list, report_data: dict):
        phase1 = self._report['phases'].get('phase1', {})
        phase2 = self._report['phases'].get('phase2', {})

        logger.info("=" * 60)
        logger.info("IP域名反查报告")
        logger.info("=" * 60)
        logger.info("输入文件: %s", self._ip_file)
        logger.info("总IP数: %d", len(ips))
        logger.info("报告时间: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        collect_stats = phase1.get('channel_stats', {})
        if collect_stats:
            logger.info("域名收集统计:")
            for ch, count in collect_stats.items():
                logger.info("  %s: %d 个域名", ch, count)

        verify_stats = phase2.get('verify_stats', {})
        if verify_stats:
            logger.info("DNS验证统计:")
            matched = verify_stats.get('matched', 0)
            changed = verify_stats.get('changed', 0)
            unresolved = verify_stats.get('unresolved', 0)
            timeout = verify_stats.get('timeout', 0)
            error = verify_stats.get('error', 0)
            logger.info("  匹配: %d, 变更: %d, 无法解析: %d, 超时: %d, 错误: %d",
                        matched, changed, unresolved, timeout, error)

        verified_map = phase2.get('verified_map', {})
        if verified_map:
            matched_file = os.path.join(
                self._output_dir, f'{self._prefix}.domain_lookup_matched')
            with open(matched_file, 'w', encoding='utf-8') as f:
                for ip, domains in verified_map.items():
                    for d in domains:
                        if d['status'] == 'matched':
                            f.write(f"{ip}\t{d['domain']}\n")
            logger.info("验证通过映射已保存: %s", matched_file)

        logger.info("=" * 60)

        self._report['phases']['phase3'] = {'status': 'done'}

    def save_report(self):
        self._report['report_time'] = datetime.now().isoformat()
        report_path = os.path.join(
            self._output_dir, f'{self._prefix}.domain_lookup_report')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self._report, f, ensure_ascii=False, indent=2)
        logger.info("报告已保存: %s", report_path)
