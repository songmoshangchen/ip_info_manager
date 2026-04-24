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

    @abstractmethod
    def generate_docx_report(self):
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

        report_path = os.path.join(self._output_dir, f'{self._prefix}.trace_report')
        report_data = {}
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

        report_time = report_data.get('report_time', datetime.now().strftime('%Y-%m-%d'))
        if 'T' in report_time:
            report_time = report_time.split('T')[0]

        total_ips = report_data.get('total_ips', len(ip_data))
        phase2 = report_data.get('phases', {}).get('phase2', {})
        classification = phase2.get('classification', {})
        deep_needed = phase2.get('deep_query_needed', 0)
        deep_skipped = phase2.get('deep_query_skipped', 0)
        unclassified_count = phase2.get('unclassified_rdns_count', 0)
        no_info_count = phase2.get('no_info_count', 0)

        label_map = {
            'cloud_provider': '云服务商',
            'cdn': 'CDN/WAF节点',
            'crawler_scanner': '爬虫/扫描器',
            'residential': '家用宽带',
            'other': '其他（需确认）',
        }

        builder = DocxBuilder(
            report_title='IP溯源分析报告',
            project_name=self._prefix,
            report_date=report_time,
            header_text='IP溯源分析报告',
        )
        builder.build()

        builder.new_chapter()
        builder.add_heading('一、报告概述', 1)
        builder.add_body(f'本报告对目标IP地址进行了多维度关联分析，结合被动DNS数据、WHOIS注册信息以及网络流量特征，完成了对攻击来源的溯源定位。')
        builder.add_heading('1.1 分析目标', 2)
        builder.add_body(f'本次分析共涉及 {total_ips} 个 IP 地址，通过多渠道信息采集与关联分析，判定其归属、用途及潜在风险。')
        builder.add_heading('1.2 分析方法', 2)
        builder.add_body('采用以下多渠道关联分析方法：被动DNS历史记录查询、WHOIS注册信息查询、反向DNS解析、自动化规则分类引擎。')

        builder.new_chapter()
        builder.add_heading('二、目标信息', 1)
        builder.table_caption('IP基本信息汇总')
        ip_rows = []
        for ip in sorted(ip_data.keys()):
            info = ip_data[ip]
            ipinfo = info.get('ipinfo_api', {})
            rdns = info.get('rdns_ptr', {})
            classify = info.get('trace_classify', {})
            country = ipinfo.get('country', 'N/A')
            org = ipinfo.get('as_name', 'N/A')
            hostname = rdns.get('hostname', '') if rdns.get('has_ptr') else 'N/A'
            cat = classify.get('label', 'N/A')
            ip_rows.append([ip, country, org, hostname, cat])
        builder.add_table(['IP地址', '国家', 'ASN/组织', 'RDNS', '分类'], ip_rows)

        if classification:
            builder.new_chapter()
            builder.add_heading('三、分类统计', 1)
            builder.add_body('经自动化规则分类引擎判定，各类别IP分布如下：')
            builder.table_caption('IP分类统计')
            class_rows = []
            for cat, count in sorted(classification.items(), key=lambda x: -x[1]):
                class_rows.append([label_map.get(cat, cat), str(count)])
            builder.add_table(['类别', '数量'], class_rows)

        builder.new_chapter()
        builder.add_heading('四、查询统计', 1)
        builder.add_body(f'需要深度查询：{deep_needed} 个IP，跳过深度查询：{deep_skipped} 个IP，未识别RDNS：{unclassified_count} 条，信息不足IP：{no_info_count} 条。')

        unclassified_path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_rdns')
        if os.path.exists(unclassified_path):
            with open(unclassified_path, 'r', encoding='utf-8') as f:
                unclassified = json.load(f)
            if unclassified:
                builder.new_chapter()
                builder.add_heading('五、未识别RDNS记录', 1)
                builder.add_body('以下RDNS记录未匹配任何已知规则，需进一步确认：')
                builder.table_caption('未识别RDNS记录')
                u_rows = [[item.get('ip', ''), item.get('hostname', ''), item.get('ipinfo_org', ''), item.get('ipinfo_country', '')] for item in unclassified]
                builder.add_table(['IP', '主机名', '组织', '国家'], u_rows)

        output = os.path.join(self._output_dir, f'{self._prefix}.trace_report.docx')
        builder.save(output)
        logger.info('docx 报告已生成：%s', output)
        return True
