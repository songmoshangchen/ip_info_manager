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

    @staticmethod
    def _extract_deep_location(info):
        aizhan = info.get('aizhan', {})
        chinaz = info.get('chinaz', {})
        if aizhan.get('success') and aizhan.get('location'):
            return aizhan['location']
        if chinaz.get('success') and chinaz.get('location'):
            return chinaz['location']
        return 'N/A'

    @staticmethod
    def _extract_deep_isp(info):
        aizhan = info.get('aizhan', {})
        chinaz = info.get('chinaz', {})
        if aizhan.get('success') and aizhan.get('isp'):
            return aizhan['isp']
        if chinaz.get('success') and chinaz.get('isp'):
            return chinaz['isp']
        return 'N/A'

    @staticmethod
    def _extract_all_domains(info):
        domains = {}
        for src_name in ('aizhan', 'chinaz'):
            src = info.get(src_name, {})
            if not src.get('success'):
                continue
            for d in src.get('domains', []):
                domain = d.get('domain', '')
                if domain and domain not in domains:
                    domains[domain] = {'domain': domain, 'source': src_name}
                    if d.get('title'):
                        domains[domain]['title'] = d['title']
                    if d.get('start_time'):
                        domains[domain]['start_time'] = d['start_time']
                    if d.get('end_time'):
                        domains[domain]['end_time'] = d['end_time']
        return list(domains.values())

    @staticmethod
    def _extract_fofa_ports(info):
        fofa = info.get('fofa_host', {})
        if fofa.get('error'):
            return []
        ports = []
        for p in fofa.get('ports', []):
            products = ', '.join(pr.get('product', '') for pr in p.get('products', []))
            ports.append({
                'port': p.get('port', ''),
                'protocol': p.get('protocol', ''),
                'update_time': p.get('update_time', ''),
                'products': products,
            })
        return ports

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

        cn_chars = '一二三四五六七八九十'
        chapter_num = 1

        builder.new_chapter()
        builder.add_heading(f'{cn_chars[chapter_num - 1]}、报告概述', 1)
        chapter_num += 1
        builder.add_body(f'本报告对目标IP地址进行了多维度关联分析，结合被动DNS数据、WHOIS注册信息、网络空间测绘数据以及IP反查域名信息，完成了对攻击来源的溯源定位。')
        builder.add_heading('1.1 分析目标', 2)
        builder.add_body(f'本次分析共涉及 {total_ips} 个 IP 地址，通过多渠道信息采集与关联分析，判定其归属、用途及潜在风险。')
        builder.add_heading('1.2 分析方法', 2)
        builder.add_body('采用以下多渠道关联分析方法：')
        builder.add_body('（1）IP基础信息查询（IPInfo）：获取IP的ASN、组织、国家等归属信息；')
        builder.add_body('（2）反向DNS解析（RDNS PTR）：通过反向解析获取IP关联的主机名；')
        builder.add_body('（3）爱站网IP反查：查询IP关联的域名及网站标题，获取地理位置和运营商信息；')
        builder.add_body('（4）站长之家IP反查：查询IP关联的域名及历史解析时间段，交叉验证归属地信息；')
        builder.add_body('（5）FOFA网络空间测绘：探测IP开放的端口、运行的服务及产品指纹信息。')
        builder.add_heading('1.3 数据源统计', 2)
        aizhan_ok = sum(1 for info in ip_data.values() if info.get('aizhan', {}).get('success'))
        chinaz_ok = sum(1 for info in ip_data.values() if info.get('chinaz', {}).get('success'))
        fofa_ok = sum(1 for info in ip_data.values() if info.get('fofa_host', {}) and not info.get('fofa_host', {}).get('error', True))
        builder.table_caption('数据源查询统计')
        builder.add_table(
            ['数据源', '查询成功数', '说明'],
            [
                ['IPInfo', str(total_ips), 'ASN、组织、国家归属'],
                ['RDNS PTR', str(total_ips), '反向DNS主机名'],
                ['爱站网', str(aizhan_ok), 'IP反查域名、归属地、运营商'],
                ['站长之家', str(chinaz_ok), 'IP反查域名、历史解析记录'],
                ['FOFA', str(fofa_ok), '端口、服务、产品指纹'],
            ],
        )

        builder.new_chapter()
        builder.add_heading(f'{cn_chars[chapter_num - 1]}、目标信息', 1)
        chapter_num += 1
        builder.add_body('以下为全部目标IP的基础信息汇总，结合多渠道数据进行综合展示。')
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
            cat = label_map.get(classify.get('category', ''), classify.get('label', 'N/A'))
            location = self._extract_deep_location(info)
            isp = self._extract_deep_isp(info)
            ip_rows.append([ip, country, org, hostname, location, isp, cat])
        builder.add_table(['IP地址', '国家', 'ASN/组织', 'RDNS', '归属地', '运营商', '分类'], ip_rows)

        if classification:
            builder.new_chapter()
            builder.add_heading(f'{cn_chars[chapter_num - 1]}、分类统计', 1)
            chapter_num += 1
            builder.add_body('经自动化规则分类引擎判定，各类别IP分布如下：')
            builder.table_caption('IP分类统计')
            class_rows = []
            for cat, count in sorted(classification.items(), key=lambda x: -x[1]):
                class_rows.append([label_map.get(cat, cat), str(count)])
            builder.add_table(['类别', '数量'], class_rows)

        deep_ips = []
        for ip in sorted(ip_data.keys()):
            info = ip_data[ip]
            classify = info.get('trace_classify', {})
            if classify.get('need_deep_query'):
                deep_ips.append(ip)

        if deep_ips:
            builder.new_chapter()
            builder.add_heading(f'{cn_chars[chapter_num - 1]}、深度查询详情', 1)
            chapter_num += 1
            builder.add_body(f'以下 {len(deep_ips)} 个IP经分类判定需要进行深度查询，其爱站网、站长之家、FOFA查询结果如下：')

            for ip in deep_ips:
                info = ip_data[ip]
                builder.add_heading(ip, 2)

                location = self._extract_deep_location(info)
                isp = self._extract_deep_isp(info)
                builder.add_body(f'归属地：{location}    运营商：{isp}')

                domains = self._extract_all_domains(info)
                if domains:
                    builder.add_heading(f'反查域名（共 {len(domains)} 个）', 3)
                    builder.table_caption(f'{ip} 反查域名')
                    d_rows = []
                    for d in domains:
                        source_label = '爱站' if d['source'] == 'aizhan' else '站长之家'
                        time_range = ''
                        if d.get('start_time') or d.get('end_time'):
                            time_range = f"{d.get('start_time', '')} ~ {d.get('end_time', '')}"
                        d_rows.append([
                            d['domain'],
                            d.get('title', ''),
                            time_range,
                            source_label,
                        ])
                    builder.add_table(['域名', '网站标题', '解析时间段', '来源'], d_rows)
                else:
                    builder.add_body('未发现关联域名。')

                ports = self._extract_fofa_ports(info)
                if ports:
                    builder.add_heading(f'开放端口与服务（共 {len(ports)} 个）', 3)
                    builder.table_caption(f'{ip} 开放端口与服务')
                    p_rows = []
                    for p in ports:
                        p_rows.append([
                            str(p['port']),
                            p['protocol'],
                            p['products'],
                            p['update_time'],
                        ])
                    builder.add_table(['端口', '协议', '产品/服务', '更新时间'], p_rows)
                else:
                    builder.add_body('FOFA未探测到开放端口信息。')

        ai_ips = []
        for ip in sorted(ip_data.keys()):
            info = ip_data[ip]
            if info.get('ai_analysis'):
                ai_ips.append(ip)

        if ai_ips:
            builder.new_chapter()
            builder.add_heading(f'{cn_chars[chapter_num - 1]}、AI研判结果', 1)
            chapter_num += 1
            builder.add_body(f'共 {len(ai_ips)} 个IP经AI研判分析，结果如下：')
            builder.table_caption('AI研判汇总')
            ai_rows = []
            for ip in ai_ips:
                ai = ip_data[ip]['ai_analysis']
                ai_rows.append([
                    ip,
                    ai.get('net_type', 'N/A'),
                    ai.get('trace_value', 'N/A'),
                    ai.get('action', 'N/A'),
                ])
            builder.add_table(['IP', '网络类型', '溯源价值', '建议操作'], ai_rows)

            builder.add_heading('研判详情', 2)
            for ip in ai_ips:
                ai = ip_data[ip]['ai_analysis']
                builder.add_heading(ip, 3)
                builder.add_body(f'网络类型：{ai.get("net_type", "N/A")}')
                builder.add_body(f'溯源价值：{ai.get("trace_value", "N/A")}')
                builder.add_body(f'建议操作：{ai.get("action", "N/A")}')
                if ai.get('note'):
                    builder.add_body(f'分析说明：{ai["note"]}')

        builder.new_chapter()
        builder.add_heading(f'{cn_chars[chapter_num - 1]}、查询统计', 1)
        chapter_num += 1
        builder.add_body(f'需要深度查询：{deep_needed} 个IP，跳过深度查询：{deep_skipped} 个IP，未识别RDNS：{unclassified_count} 条，信息不足IP：{no_info_count} 条。')

        unclassified_path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_rdns')
        if os.path.exists(unclassified_path):
            with open(unclassified_path, 'r', encoding='utf-8') as f:
                unclassified = json.load(f)
            if unclassified:
                builder.new_chapter()
                builder.add_heading(f'{cn_chars[chapter_num - 1]}、未识别RDNS记录', 1)
                chapter_num += 1
                builder.add_body('以下RDNS记录未匹配任何已知规则，需进一步确认：')
                builder.table_caption('未识别RDNS记录')
                u_rows = [[item.get('ip', ''), item.get('hostname', ''), item.get('ipinfo_org', ''), item.get('ipinfo_country', '')] for item in unclassified]
                builder.add_table(['IP', '主机名', '组织', '国家'], u_rows)

        output = os.path.join(self._output_dir, f'{self._prefix}.trace_report.docx')
        builder.save(output)
        logger.info('docx 报告已生成：%s', output)
        return True
