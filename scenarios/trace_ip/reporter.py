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
    def generate_docx_report(self, exclude_info=None):
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

    @staticmethod
    def _is_china_ip(info):
        ipinfo = info.get('ipinfo_api', {})
        return ipinfo.get('country_code', '') == 'CN' or 'China' in ipinfo.get('country', '')

    @staticmethod
    def _has_deep_data(info):
        az = info.get('aizhan', {})
        cz = info.get('chinaz', {})
        ff = info.get('fofa_host', {})
        if az.get('success'):
            return True
        if cz.get('success'):
            return True
        if ff and not ff.get('error', True):
            return True
        return False

    @staticmethod
    def _has_domains(info):
        domains = TextTraceReporter._extract_all_domains(info)
        return len(domains) > 0

    @staticmethod
    def _has_ports(info):
        ports = TextTraceReporter._extract_fofa_ports(info)
        return len(ports) > 0

    @staticmethod
    def _format_verify_status(verify_result):
        status = verify_result.get('status', '')
        resolved_ips = verify_result.get('resolved_ips', [])
        if status == 'matched':
            return '✅ 已确认'
        elif status == 'changed':
            ips_str = ', '.join(resolved_ips) if resolved_ips else '(无)'
            return f'🔄 → {ips_str}'
        elif status == 'unresolved':
            return '❌ 无法解析'
        elif status == 'timeout':
            return '⏱️ 超时'
        elif status == 'error':
            return '⚠️ 错误'
        return '—'

    def _write_ip_detail(self, builder, ip, info):
        ipinfo = info.get('ipinfo_api', {})
        rdns = info.get('rdns_ptr', {})
        country = ipinfo.get('country', 'N/A')
        org = ipinfo.get('as_name', 'N/A')
        hostname = rdns.get('hostname', '') if rdns.get('has_ptr') else 'N/A'
        location = self._extract_deep_location(info)
        isp = self._extract_deep_isp(info)
        builder.add_heading(ip, 3)
        builder.add_body(f'国家/地区：{country}    ASN/组织：{org}    RDNS：{hostname}    归属地：{location}    运营商：{isp}')

        domains = self._extract_all_domains(info)
        domain_verify = info.get('domain_verify', {})
        verify_results = {}
        if domain_verify and domain_verify.get('results'):
            for r in domain_verify['results']:
                verify_results[r['domain']] = r

        if domains:
            builder.add_heading(f'反查域名（共 {len(domains)} 个）', 3)
            builder.table_caption(f'{ip} 反查域名')
            d_rows = []
            has_verify = bool(verify_results)
            for d in domains:
                source_label = '爱站' if d['source'] == 'aizhan' else '站长之家'
                time_range = ''
                if d.get('start_time') or d.get('end_time'):
                    time_range = f"{d.get('start_time', '')} ~ {d.get('end_time', '')}"
                if has_verify:
                    vr = verify_results.get(d['domain'])
                    if vr:
                        status_label = self._format_verify_status(vr)
                    else:
                        status_label = '—'
                    d_rows.append([d['domain'], d.get('title', ''), time_range, source_label, status_label])
                else:
                    d_rows.append([d['domain'], d.get('title', ''), time_range, source_label])
            headers = ['域名', '网站标题', '解析时间段', '来源']
            if has_verify:
                headers.append('验证状态')
            builder.add_table(headers, d_rows)
        else:
            builder.add_body('未发现关联域名。')

        ports = self._extract_fofa_ports(info)
        if ports:
            builder.add_heading(f'开放端口与服务（共 {len(ports)} 个）', 3)
            builder.table_caption(f'{ip} 开放端口与服务')
            p_rows = []
            for p in ports:
                p_rows.append([str(p['port']), p['protocol'], p['products'], p['update_time']])
            builder.add_table(['端口', '协议', '产品/服务', '更新时间'], p_rows)
        else:
            builder.add_body('FOFA未探测到开放端口信息。')

    def generate_docx_report(self, exclude_info=None):
        from tools.docx_builder import DOCX_AVAILABLE, DocxBuilder

        if not DOCX_AVAILABLE:
            logger.warning('python-docx 未安装，跳过 docx 报告生成。安装命令：pip install python-docx')
            return False

        report_path = os.path.join(self._output_dir, f'{self._prefix}.trace_report')
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            if existing.get('phases') and not self._report.get('phases'):
                self._report['phases'] = existing['phases']
            if existing.get('total_ips') and not self._report.get('total_ips'):
                self._report['total_ips'] = existing['total_ips']
            for key in ('unclassified_rdns_count', 'unclassified_rdns_file',
                        'no_info_count', 'no_info_file'):
                if key in existing and key not in self._report:
                    self._report[key] = existing[key]

        self.save_report()

        json_path = os.path.join(self._output_dir, f'{self._prefix}.json')
        if not os.path.exists(json_path):
            logger.warning('找不到数据文件 %s，跳过 docx 生成', json_path)
            return False

        with open(json_path, 'r', encoding='utf-8') as f:
            ip_data = json.load(f)

        if exclude_info:
            exclude_set = exclude_info['exclude_ips']
            original_count = len(ip_data)
            ip_data = {ip: info for ip, info in ip_data.items() if ip not in exclude_set}
            logger.info("排除IP生效: 原始 %d 个, 排除 %d 个, 剩余 %d 个",
                        original_count, exclude_info['effective_count'], len(ip_data))

        report_data = {}
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

        report_time = report_data.get('report_time', datetime.now().strftime('%Y-%m-%d'))
        if 'T' in report_time:
            report_time = report_time.split('T')[0]

        total_ips = len(ip_data)

        classification = {}
        deep_needed = 0
        deep_skipped = 0
        unclassified_count = 0
        no_info_count = 0
        for ip, info in ip_data.items():
            classify = info.get('trace_classify', {})
            cat = classify.get('category', '')
            if cat:
                classification[cat] = classification.get(cat, 0) + 1
            if classify.get('need_deep_query'):
                deep_needed += 1
            else:
                deep_skipped += 1
            if classify.get('unclassified_rdns'):
                unclassified_count += 1
            if classify.get('no_info'):
                no_info_count += 1

        label_map = {
            'cloud_provider': '云服务商',
            'cdn': 'CDN/WAF节点',
            'crawler_scanner': '爬虫/扫描器',
            'residential': '家用宽带',
            'other': '其他（需确认）',
            'invalid_rdns': '无效RDNS',
            'excluded_domain': '排除域名',
        }
        desc_map = {
            'cloud_provider': 'AWS/阿里云/腾讯云等云主机，可能用于部署攻击工具',
            'cdn': '内容分发/防护节点，通常为误报或流量转发',
            'crawler_scanner': '自动化扫描工具（如Censys/Shodan），跳过深度查询',
            'residential': '个人宽带用户，可能为肉鸡或代理出口',
            'other': '未匹配已知规则，需人工或AI研判确认',
            'invalid_rdns': 'RDNS反解为纯IP地址格式，属于无效域名',
            'excluded_domain': '已排除的域名类型',
        }
        deep_query_map = {
            'cloud_provider': True,
            'cdn': False,
            'crawler_scanner': False,
            'residential': True,
            'other': True,
            'invalid_rdns': False,
            'excluded_domain': False,
        }
        cat_order = ['other', 'invalid_rdns', 'excluded_domain', 'crawler_scanner', 'residential', 'cloud_provider', 'cdn']

        builder = DocxBuilder(
            report_title='IP溯源分析报告',
            project_name=self._prefix,
            report_date=report_time,
            header_text='IP溯源分析报告',
        )
        builder.build()

        cn_chars = '一二三四五六七八九十'
        chapter_num = 1

        # ── 一、报告概述 ──
        builder.new_chapter()
        builder.add_heading(f'{cn_chars[chapter_num - 1]}、报告概述', 1)
        chapter_num += 1
        builder.add_body(f'本报告对目标IP地址进行了多维度关联分析，结合被动DNS数据、WHOIS注册信息、网络空间测绘数据以及IP反查域名信息，完成了对攻击来源的溯源定位。')
        builder.add_heading('1.1 分析目标', 2)
        if exclude_info:
            original_total = total_ips + exclude_info['effective_count']
            builder.add_body(
                f'本次分析原始 IP 共 {original_total} 个，'
                f'已排除 {exclude_info["effective_count"]} 个已溯源 IP，'
                f'剩余待溯源 IP {total_ips} 个。'
                f'通过多渠道信息采集与关联分析，判定其归属、用途及潜在风险。'
            )
        else:
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

        # ── 二、处理概览 ──
        builder.new_chapter()
        builder.add_heading(f'{cn_chars[chapter_num - 1]}、处理概览', 1)
        ch_overview = chapter_num
        chapter_num += 1

        ipinfo_ok = sum(1 for info in ip_data.values() if info.get('ipinfo_api', {}).get('as_name'))
        rdns_ok = sum(1 for info in ip_data.values() if info.get('rdns_ptr', {}).get('has_ptr'))
        rdns_matched = sum(1 for info in ip_data.values() if info.get('trace_classify', {}).get('matched_by'))

        builder.add_heading(f'{ch_overview}.1 基础情报采集统计', 2)
        builder.add_body(f'阶段1对 {total_ips} 个IP执行了基础情报采集（IPInfo + RDNS PTR），结果如下：')
        builder.table_caption('基础情报采集统计')
        builder.add_table(
            ['采集项', '成功', '失败/无数据', '说明'],
            [
                ['IPInfo', str(ipinfo_ok), str(total_ips - ipinfo_ok), 'ASN、组织、国家归属'],
                ['RDNS PTR', str(rdns_ok), str(total_ips - rdns_ok), '反向DNS主机名解析'],
                ['分类规则匹配', str(rdns_matched), str(total_ips - rdns_matched), '通过RDNS主机名或IPInfo组织信息匹配分类规则'],
            ],
        )

        if classification:
            builder.add_heading(f'{ch_overview}.2 自动分类统计', 2)
            builder.add_body(
                f'经自动化规则分类引擎判定，{total_ips} 个IP按归属和用途分为以下类别。'
                f'其中 {deep_needed} 个IP需进行深度查询（爱站网/站长之家反查域名），'
                f'{deep_skipped} 个IP因判定为扫描器或CDN节点而跳过深度查询。'
            )
            builder.table_caption('IP分类统计汇总')
            class_rows = []
            for cat in cat_order:
                count = classification.get(cat, 0)
                if count == 0:
                    continue
                pct = f'{count / total_ips * 100:.1f}%'
                deep_flag = '是' if deep_query_map.get(cat, True) else '否（跳过）'
                class_rows.append([
                    label_map.get(cat, cat), str(count), pct, deep_flag, desc_map.get(cat, ''),
                ])
            builder.add_table(['类别', '数量', '占比', '深度查询', '说明'], class_rows)
            builder.add_body(
                f'综上，共 {deep_needed} 个IP（云服务商 {classification.get("cloud_provider", 0)} 个 + '
                f'家用宽带 {classification.get("residential", 0)} 个 + '
                f'其他 {classification.get("other", 0)} 个）进入深度查询流程；'
                f'共 {deep_skipped} 个IP（爬虫/扫描器 {classification.get("crawler_scanner", 0)} 个 + '
                f'CDN/WAF {classification.get("cdn", 0)} 个）跳过深度查询。'
            )

        builder.add_heading(f'{ch_overview}.3 深度查询统计', 2)
        phase3 = report_data.get('phases', {}).get('phase3', {})
        deep_total = deep_needed
        builder.add_body(f'共对 {deep_total} 个IP执行了深度查询，各渠道查询结果如下：')
        builder.table_caption('渠道查询结果统计')
        ch_rows = [
            ['爱站网', str(aizhan_ok), str(deep_total - aizhan_ok), 'IP反查域名、归属地、运营商'],
            ['站长之家', str(chinaz_ok), str(deep_total - chinaz_ok), 'IP反查域名、历史解析记录'],
        ]
        if fofa_ok > 0:
            ch_rows.append(['FOFA', str(fofa_ok), str(deep_total - fofa_ok), '端口、服务、产品指纹'])
        builder.add_table(['数据源', '查询成功', '查询失败/无数据', '查询内容'], ch_rows)

        if unclassified_count > 0 or no_info_count > 0:
            builder.add_heading(f'{ch_overview}.4 待确认IP', 2)
            if unclassified_count > 0:
                builder.add_body(
                    f'有 {unclassified_count} 个IP的RDNS记录未匹配任何已知分类规则，'
                    f'可将其域名模式添加到 custom_rules.json 后重新分类。'
                )
            if no_info_count > 0:
                builder.add_body(
                    f'有 {no_info_count} 个IP既无RDNS记录也无IPInfo组织信息，无法自动分类，需通过其他方式确认。'
                )

        deep_ips = []
        for ip in sorted(ip_data.keys()):
            if ip_data[ip].get('trace_classify', {}).get('need_deep_query'):
                deep_ips.append(ip)

        if deep_ips:
            builder.add_heading(f'{ch_overview}.5 价值分级统计', 2)
            builder.add_body(
                f'对 {len(deep_ips)} 个深度查询IP按情报价值分级，'
                f'国内IP在同等数据条件下价值和优先级更高。'
            )
            high_total = sum(1 for ip in deep_ips if self._has_deep_data(ip_data[ip]) and self._is_china_ip(ip_data[ip]))
            mid_total = sum(1 for ip in deep_ips if self._has_deep_data(ip_data[ip]) and not self._is_china_ip(ip_data[ip]))
            low_total = len(deep_ips) - high_total - mid_total
            builder.table_caption('价值分级概览')
            builder.add_table(
                ['价值等级', 'IP数', '判定标准'],
                [
                    ['高价值（国内有数据）', str(high_total), '爱站/站长/Fofa有数据 且 国内IP'],
                    ['中价值（国外有数据）', str(mid_total), '爱站/站长/Fofa有数据 且 国外IP'],
                    ['低价值（无数据）', str(low_total), '所有深度查询渠道均无有效数据'],
                ],
            )

        # ── 三、溯源优先级 ──
        cat_weight = {'cloud_provider': 2, 'residential': 1, 'other': 0}

        def _cat_display(info):
            classify = info.get('trace_classify', {})
            category = classify.get('category', '')
            if category == 'other':
                return label_map.get('other', '其他（需确认）')
            label = label_map.get(category, category)
            matched_by = classify.get('matched_by', [])
            if matched_by and matched_by[0].get('note'):
                note = matched_by[0]['note']
                return f'{label}（{note}）'
            return label

        def _trace_priority(ip):
            info = ip_data[ip]
            is_cn = self._is_china_ip(info)
            has_dom = self._has_domains(info)
            has_pt = self._has_ports(info)
            if has_dom and is_cn:
                return 1
            if has_dom or (has_pt and is_cn):
                return 2
            if has_pt or is_cn:
                return 3
            return 4

        def _sort_key(ip):
            info = ip_data[ip]
            n_dom = len(self._extract_all_domains(info))
            n_pt = len(self._extract_fofa_ports(info))
            cat = info.get('trace_classify', {}).get('category', 'other')
            return (-n_dom, -n_pt, -cat_weight.get(cat, 0))

        p1_ips, p2_ips, p3_ips, p4_ips = [], [], [], []
        for ip in deep_ips:
            lvl = _trace_priority(ip)
            if lvl == 1:
                p1_ips.append(ip)
            elif lvl == 2:
                p2_ips.append(ip)
            elif lvl == 3:
                p3_ips.append(ip)
            else:
                p4_ips.append(ip)

        p1_ips.sort(key=_sort_key)
        p2_ips.sort(key=_sort_key)
        p3_ips.sort(key=_sort_key)
        p4_ips.sort(key=_sort_key)

        def _trace_action(ip):
            info = ip_data[ip]
            has_dom = self._has_domains(info)
            has_pt = self._has_ports(info)
            is_cn = self._is_china_ip(info)
            actions = []
            if has_dom:
                actions.append('ICP备案/WHOIS查询域名注册信息' if is_cn else 'WHOIS查询域名注册信息')
            if has_pt:
                actions.append('排查端口服务泄露信息')
            if not actions:
                actions.append('公开信息检索IP历史行为')
            return '；'.join(actions)

        def _count_domains(info):
            n = 0
            if info.get('aizhan', {}).get('success'):
                n += info['aizhan'].get('domain_count', 0)
            if info.get('chinaz', {}).get('success'):
                n += len(info.get('chinaz', {}).get('domains', []))
            return n

        if deep_ips:
            builder.new_chapter()
            ch_trace = chapter_num
            builder.add_heading(f'{cn_chars[chapter_num - 1]}、溯源优先级', 1)
            chapter_num += 1
            builder.add_body(
                f'基于决策树模型对 {len(deep_ips)} 个深度查询IP进行溯源优先级分级。'
                f'判定维度：是否有反查域名（最直接溯源线索）→ 是否有已知端口信息 → 是否为国内IP（管辖权内可操作）。'
                f'每个级别内按信息丰富度（域名数+端口数）降序排列。'
            )

            builder.table_caption('溯源优先级概览')
            builder.add_table(
                ['优先级', 'IP数', '判定标准', '建议溯源路径'],
                [
                    ['P1 核心溯源', str(len(p1_ips)), '有反查域名 + 国内IP', 'ICP备案查询域名持有者实名信息'],
                    ['P2 重点溯源', str(len(p2_ips)), '有反查域名（国外），或无域名但有端口信息（国内）', 'WHOIS查询域名注册信息；排查端口服务泄露信息'],
                    ['P3 辅助溯源', str(len(p3_ips)), '无域名但有端口信息（国外），或仅国内IP', '端口服务信息辅助分析；公开信息检索'],
                    ['P4 暂缓', str(len(p4_ips)), '无域名、无端口、国外IP', '信息不足，建议持续监控'],
                ],
            )

            verify_rows = []
            for ip in deep_ips:
                info = ip_data[ip]
                dv = info.get('domain_verify')
                if not dv or not dv.get('results'):
                    continue
                for r in dv['results']:
                    if r.get('status') != 'matched':
                        continue
                    verify_rows.append([
                        ip,
                        r.get('domain', ''),
                    ])
            if verify_rows:
                builder.add_heading('IP-域名验证状态', 2)
                builder.add_body(
                    f'对 {len(deep_ips)} 个深度查询IP进行 DNS 域名正向验证，'
                    f'以下 {len(verify_rows)} 条 IP-域名映射经确认仍然有效。'
                )
                builder.table_caption('IP-域名验证状态')
                builder.add_table(['IP', '域名'], verify_rows)

            if p1_ips:
                builder.add_heading(f'{ch_trace}.1 P1 核心溯源 — {len(p1_ips)} 个IP', 2)
                builder.add_body('有反查域名且为国内IP，可通过 ICP 备案查询域名持有者实名信息，溯源路径最短。')
                builder.table_caption('P1 核心溯源IP列表')
                p1_rows = []
                for ip in p1_ips:
                    info = ip_data[ip]
                    n_dom = _count_domains(info)
                    n_pt = len(self._extract_fofa_ports(info))
                    cat = _cat_display(info)
                    org = info.get('ipinfo_api', {}).get('as_name', 'N/A')
                    p1_rows.append([ip, org, cat, str(n_dom), str(n_pt), _trace_action(ip)])
                builder.add_table(['IP', '组织', '分类', '域名数', '端口数', '建议溯源路径'], p1_rows)

            if p2_ips:
                builder.add_heading(f'{ch_trace}.2 P2 重点溯源 — {len(p2_ips)} 个IP', 2)
                builder.add_body('有反查域名（国外），或无域名但有端口信息的国内IP。可通过 WHOIS 查询或端口服务排查获取线索。')
                builder.table_caption('P2 重点溯源IP列表')
                p2_rows = []
                for ip in p2_ips:
                    info = ip_data[ip]
                    n_dom = _count_domains(info)
                    n_pt = len(self._extract_fofa_ports(info))
                    cat = _cat_display(info)
                    country = info.get('ipinfo_api', {}).get('country', 'N/A')
                    org = info.get('ipinfo_api', {}).get('as_name', 'N/A')
                    p2_rows.append([ip, country, org, cat, str(n_dom), str(n_pt), _trace_action(ip)])
                builder.add_table(['IP', '国家', '组织', '分类', '域名数', '端口数', '建议溯源路径'], p2_rows)

            if p3_ips:
                builder.add_heading(f'{ch_trace}.3 P3 辅助溯源 — {len(p3_ips)} 个IP', 2)
                builder.add_body('无域名但有端口信息（国外），或仅国内IP无其他线索。可通过端口服务或公开信息检索辅助分析。')
                builder.table_caption('P3 辅助溯源IP列表')
                p3_rows = []
                for ip in p3_ips:
                    info = ip_data[ip]
                    n_dom = _count_domains(info)
                    n_pt = len(self._extract_fofa_ports(info))
                    cat = _cat_display(info)
                    country = info.get('ipinfo_api', {}).get('country', 'N/A')
                    org = info.get('ipinfo_api', {}).get('as_name', 'N/A')
                    p3_rows.append([ip, country, org, cat, str(n_dom), str(n_pt), _trace_action(ip)])
                builder.add_table(['IP', '国家', '组织', '分类', '域名数', '端口数', '建议溯源路径'], p3_rows)

            if p4_ips:
                builder.add_heading(f'{ch_trace}.4 P4 暂缓 — {len(p4_ips)} 个IP', 2)
                builder.add_body('无域名、无端口、国外IP，当前情报不足以支撑有效溯源，建议持续监控。')
                builder.table_caption('P4 暂缓IP列表')
                p4_rows = []
                for ip in p4_ips:
                    info = ip_data[ip]
                    cat = _cat_display(info)
                    country = info.get('ipinfo_api', {}).get('country', 'N/A')
                    org = info.get('ipinfo_api', {}).get('as_name', 'N/A')
                    p4_rows.append([ip, country, org, cat])
                builder.add_table(['IP', '国家', '组织', '分类'], p4_rows)

        # ── 四、AI研判结果 ──
        ai_ips = [ip for ip in sorted(ip_data.keys()) if ip_data[ip].get('ai_analysis')]

        if ai_ips:
            builder.new_chapter()
            builder.add_heading(f'{cn_chars[chapter_num - 1]}、AI研判结果', 1)
            chapter_num += 1
            builder.add_body(f'共 {len(ai_ips)} 个IP经AI研判分析，结果如下：')
            builder.table_caption('AI研判汇总')
            ai_rows = []
            for ip in ai_ips:
                ai = ip_data[ip]['ai_analysis']
                ai_rows.append([ip, ai.get('net_type', 'N/A'), ai.get('trace_value', 'N/A'), ai.get('action', 'N/A')])
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

        # ── 五、未识别RDNS记录 ──
        unclassified_path = os.path.join(self._output_dir, f'{self._prefix}.unclassified_rdns')
        if os.path.exists(unclassified_path):
            with open(unclassified_path, 'r', encoding='utf-8') as f:
                unclassified = json.load(f)
            if exclude_info:
                exclude_set = exclude_info['exclude_ips']
                unclassified = [item for item in unclassified if item.get('ip') not in exclude_set]
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
