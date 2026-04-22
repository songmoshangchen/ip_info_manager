import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')


class BaseTraceReporter(ABC):

    @abstractmethod
    def record_phase(self, phase_num: int, stats: dict):
        pass

    @abstractmethod
    def generate_summary(self, ips: list, report_data: dict):
        pass

    @abstractmethod
    def save_report(self):
        pass


class TextTraceReporter(BaseTraceReporter):

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
        phase2_data = self._report['phases'].get('phase2', {})
        classification = phase2_data.get('classification', {})
        deep_needed = phase2_data.get('deep_query_needed', 0)
        deep_skipped = phase2_data.get('deep_query_skipped', 0)
        unclassified_count = phase2_data.get('unclassified_rdns_count', 0)
        no_info_count = phase2_data.get('no_info_count', 0)

        logger.info("=" * 60)
        logger.info("溯源IP处理报告")
        logger.info("=" * 60)
        logger.info("输入文件: %s", self._ip_file)
        logger.info("总IP数: %d", len(ips))
        logger.info("报告时间: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        if classification:
            logger.info("分类统计:")
            for cat, count in sorted(classification.items(), key=lambda x: -x[1]):
                logger.info("  %s: %d", cat, count)

        logger.info("深度查询: %d 个IP", deep_needed)
        logger.info("跳过: %d 个IP", deep_skipped)
        logger.info("未识别RDNS: %d 条", unclassified_count)
        logger.info("信息不足IP: %d 条", no_info_count)

        if unclassified_count > 0:
            path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_rdns')
            logger.info("未识别RDNS文件: %s", path)
            logger.info("提示: 可将未识别的域名模式添加到 custom_rules.json，验证后合并到 builtin_rules.json")

        if no_info_count > 0:
            path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_no_info')
            logger.info("信息不足IP文件: %s", path)
            logger.info("提示: 这些IP无RDNS记录且无ipinfo org信息，需通过其他方式确认")

        logger.info("=" * 60)

        self._report['phases']['phase4'] = {'status': 'done'}
        self._report['unclassified_rdns_count'] = unclassified_count
        self._report['unclassified_rdns_file'] = os.path.join(
            self._output_dir, f'{self._prefix}.unclassified_rdns')
        self._report['no_info_count'] = no_info_count
        self._report['no_info_file'] = os.path.join(
            self._output_dir, f'{self._prefix}.unclassified_no_info')

    def save_report(self):
        self._report['report_time'] = datetime.now().isoformat()
        report_path = os.path.join(self._output_dir, f'{self._prefix}.trace_report')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self._report, f, ensure_ascii=False, indent=2)
        logger.info("报告已保存: %s", report_path)

    def save_unclassified(self, unclassified_list: list):
        output_path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_rdns')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unclassified_list, f, ensure_ascii=False, indent=2)
        if unclassified_list:
            logger.info("未识别RDNS已保存: %s (%d 条)", output_path, len(unclassified_list))

    def save_no_info(self, no_info_list: list):
        output_path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_no_info')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(no_info_list, f, ensure_ascii=False, indent=2)
        if no_info_list:
            logger.info("信息不足IP已保存: %s (%d 条)", output_path, len(no_info_list))
