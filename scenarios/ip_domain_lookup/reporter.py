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

    @abstractmethod
    def generate_docx_report(self):
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

    def generate_docx_report(self):
        from tools.docx_builder import DOCX_AVAILABLE, DocxBuilder

        if not DOCX_AVAILABLE:
            logger.warning('python-docx 未安装，跳过 docx 报告生成。安装命令：pip install python-docx')
            return False

        self.save_report()

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        if not os.path.exists(json_path):
            logger.warning('找不到数据文件 %s，跳过 docx 生成', json_path)
            return False

        with open(json_path, 'r', encoding='utf-8') as f:
            ip_data = json.load(f)

        report_path = os.path.join(self._output_dir, f'{self._prefix}.domain_lookup_report')
        report_data = {}
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

        report_time = report_data.get('report_time', datetime.now().strftime('%Y-%m-%d'))
        if 'T' in report_time:
            report_time = report_time.split('T')[0]

        total_ips = report_data.get('total_ips', len(ip_data))
        phase1 = report_data.get('phases', {}).get('phase1', {})
        phase2 = report_data.get('phases', {}).get('phase2', {})
        channel_stats = phase1.get('channel_stats', {})
        verify_stats = phase2.get('verify_stats', {})

        status_map = {
            'matched': '匹配（域名仍指向原IP）',
            'changed': '变更（域名指向其他IP）',
            'unresolved': '无法解析（域名可能已过期）',
            'timeout': '超时',
            'error': '错误',
        }

        matched_path = os.path.join(self._output_dir, f'{self._prefix}.domain_lookup_matched')
        matched_data = []
        if os.path.exists(matched_path):
            with open(matched_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            matched_data.append((parts[0], parts[1]))

        builder = DocxBuilder(
            report_title='IP域名反查报告',
            project_name=self._prefix,
            report_date=report_time,
            header_text='IP域名反查报告',
        )
        builder.build()

        builder.new_chapter()
        builder.add_heading('一、报告概述', 1)
        total_candidates = sum(ip_data[ip].get('ip_domain_lookup', {}).get('candidates', []) and len(ip_data[ip].get('ip_domain_lookup', {}).get('candidates', [])) or 0 for ip in ip_data)
        builder.add_body(f'本报告对目标IP地址进行了多渠道域名反向查询，并通过DNS解析验证确认域名当前是否仍指向目标IP。共涉及 {total_ips} 个 IP 地址，收集候选域名 {total_candidates} 个。')

        if channel_stats:
            builder.new_chapter()
            builder.add_heading('二、域名收集统计', 1)
            builder.table_caption('域名收集渠道统计')
            ch_rows = [[ch, str(count)] for ch, count in sorted(channel_stats.items(), key=lambda x: -x[1])]
            builder.add_table(['收集渠道', '域名数量'], ch_rows)

        if verify_stats:
            builder.new_chapter()
            builder.add_heading('三、DNS验证统计', 1)
            builder.add_body('对所有候选域名进行DNS解析验证，结果如下：')
            builder.table_caption('DNS验证结果统计')
            v_rows = [[status_map.get(st, st), str(count)] for st, count in verify_stats.items()]
            builder.add_table(['验证状态', '数量'], v_rows)

        if matched_data:
            builder.new_chapter()
            builder.add_heading('四、验证通过映射（按IP分表）', 1)
            builder.add_body('以下为各IP地址验证确认仍指向目标IP的全部域名列表：')

            by_ip = {}
            for ip, domain in matched_data:
                by_ip.setdefault(ip, []).append(domain)

            for ip in sorted(by_ip.keys()):
                builder.table_caption(f'{ip} 验证通过域名')
                rows = [[ip, d] for d in sorted(by_ip[ip])]
                builder.add_table(['IP', '域名'], rows)

        builder.new_chapter()
        builder.add_heading('五、IP域名收集详情', 1)
        builder.add_body('各IP地址的域名反查汇总统计：')
        builder.table_caption('IP域名反查汇总')
        summary_rows = []
        for ip in sorted(ip_data.keys()):
            info = ip_data[ip]
            lookup = info.get('ip_domain_lookup', {})
            summary = lookup.get('summary', {})
            candidates = lookup.get('candidates', [])
            matched = summary.get('matched', 0)
            changed = summary.get('changed', 0)
            unresolved = summary.get('unresolved', 0)
            summary_rows.append([ip, str(len(candidates)), str(matched), str(changed), str(unresolved)])
        builder.add_table(['IP', '候选域名数', '匹配', '变更', '无法解析'], summary_rows)

        output = os.path.join(self._output_dir, f'{self._prefix}.domain_lookup_report.docx')
        builder.save(output)
        logger.info('docx 报告已生成：%s', output)
        return True
