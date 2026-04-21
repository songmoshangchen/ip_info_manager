import json
import os
import sys
import time
import argparse
from datetime import datetime
from collections import OrderedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.ipinfo_api import fetch_ipinfo
from channel.rdns_ptr import fetch_rdns_ptr
from channel.aizhan import fetch_aizhan
from channel.chinaz import fetch_chinaz
from channel.fofa import fetch_fofa_host_detail
from config import IpinfoSettings, RdnsSettings, AizhanSettings, ChinazSettings, FofaSettings
from writer import IPWriter
from reader import IPReader


CLASSIFIERS_DIR = os.path.join(os.path.dirname(__file__), 'classifiers')
BUILTIN_RULES_FILE = os.path.join(CLASSIFIERS_DIR, 'builtin_rules.json')
CUSTOM_RULES_FILE = os.path.join(CLASSIFIERS_DIR, 'custom_rules.json')

DEEP_QUERY_CATEGORIES = {'cloud_provider', 'residential', 'other'}


class TraceIPPipeline:

    def __init__(self, ip_file, args):
        self.ip_file = os.path.abspath(ip_file)
        self.args = args

        self.ip_writer = IPWriter()
        self.ip_reader = IPReader()

        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = self._resolve_output_dir()

        self.prefix = self.ip_reader.settings.storage_name
        self.phase_markers = {
            1: f'{self.prefix}.trace_phase1_done',
            2: f'{self.prefix}.trace_phase2_done',
            3: f'{self.prefix}.trace_phase3_done',
        }
        self.progress_files = {
            1: f'{self.prefix}.trace_phase1.progress',
            3: f'{self.prefix}.trace_phase3.progress',
        }

        self.builtin_rules = self._load_rules_file(BUILTIN_RULES_FILE)
        self.custom_rules = {}
        if not args.no_custom_rules:
            custom_path = args.custom_rules if args.custom_rules else CUSTOM_RULES_FILE
            if os.path.exists(custom_path):
                self.custom_rules = self._load_rules_file(custom_path)

        self.ips = self._load_ips()
        self.report = {
            'report_time': None,
            'input_file': self.ip_file,
            'total_ips': len(self.ips),
            'phases': {},
        }

    def _resolve_output_dir(self):
        if self.args.output_dir_explicit:
            output_dir = self.args.output_dir
        else:
            output_dir = self.ip_reader.settings.storage_dir
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.project_dir, output_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _load_ips(self):
        ips = []
        with open(self.ip_file, 'r', encoding='utf-8') as f:
            for line in f:
                ip = line.strip()
                if ip:
                    ips.append(ip)
        return ips

    def _load_rules_file(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)

    def _is_phase_done(self, phase):
        marker = os.path.join(self.output_dir, self.phase_markers[phase])
        return os.path.exists(marker)

    def _mark_phase_done(self, phase):
        marker = os.path.join(self.output_dir, self.phase_markers[phase])
        with open(marker, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())

    def _load_progress(self, phase):
        if phase not in self.progress_files:
            return set()
        progress_file = os.path.join(self.output_dir, self.progress_files[phase])
        processed = set()
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                for line in f:
                    ip = line.strip()
                    if ip:
                        processed.add(ip)
        return processed

    def _save_progress(self, phase, ip):
        if phase not in self.progress_files:
            return
        progress_file = os.path.join(self.output_dir, self.progress_files[phase])
        with open(progress_file, 'a', encoding='utf-8') as f:
            f.write(ip + '\n')

    def _clear_progress(self, phase):
        if phase not in self.progress_files:
            return
        progress_file = os.path.join(self.output_dir, self.progress_files[phase])
        if os.path.exists(progress_file):
            os.remove(progress_file)

    def _clear_phase_markers(self):
        for marker_name in self.phase_markers.values():
            path = os.path.join(self.output_dir, marker_name)
            if os.path.exists(path):
                os.remove(path)

    def run(self):
        from_phase = self.args.from_phase
        only_phase = self.args.only_phase

        if from_phase and from_phase > 1:
            self._clear_phase_markers_from(from_phase)
            print(f"从阶段 {from_phase} 开始，已清除后续阶段的标记文件")

        phases_to_run = []
        if only_phase:
            phases_to_run = [only_phase]
        else:
            phases_to_run = [1, 2, 3, 4]

        phase_methods = {
            1: self.phase1_collect_basic,
            2: self.phase2_classify,
            3: self.phase3_deep_query,
            4: self.phase4_summary,
        }

        for phase_num in phases_to_run:
            if phase_num != 1 and not only_phase:
                if from_phase and phase_num < from_phase:
                    print(f"跳过阶段 {phase_num}（已完成）")
                    continue

            print(f"\n{'=' * 60}")
            print(f"阶段 {phase_num}: {self._phase_name(phase_num)}")
            print(f"{'=' * 60}")

            phase_methods[phase_num]()

        self.report['report_time'] = datetime.now().isoformat()
        self._save_report()

    def _clear_phase_markers_from(self, phase):
        for p in range(phase, 4):
            marker = os.path.join(self.output_dir, self.phase_markers[p])
            if os.path.exists(marker):
                os.remove(marker)
            self._clear_progress(p)

    def _phase_name(self, phase):
        names = {
            1: '基础情报采集',
            2: '自动分类过滤',
            3: '深度查询',
            4: '汇总输出',
        }
        return names.get(phase, '')

    # ── Phase 1: 基础情报采集 ──

    def phase1_collect_basic(self):
        if self._is_phase_done(1):
            print("阶段1已完成，跳过")
            return

        processed = self._load_progress(1)
        if processed:
            print(f"发现进度文件，已完成 {len(processed)} 个IP，从断点继续")

        ipinfo_settings = IpinfoSettings()
        rdns_settings = RdnsSettings()

        total = len(self.ips)
        skipped = len(processed)
        success_count = 0
        fail_count = 0

        print(f"总IP数: {total}")
        print(f"已完成: {skipped}")
        print(f"剩余: {total - skipped}")
        print(f"IPInfo 查询间隔: {ipinfo_settings.ipinfo_query_delay}s")
        print(f"RDNS 查询超时: {rdns_settings.rdns_query_timeout}s")
        print("-" * 60)

        for i, ip in enumerate(self.ips, 1):
            if ip in processed:
                continue

            print(f"[{i}/{total}] 正在采集: {ip}", end=' ', flush=True)

            ipinfo_data = fetch_ipinfo(ip, ipinfo_settings.ipinfo_access_token)
            if 'raw_error' in ipinfo_data:
                print(f"[ipinfo ❌]", end=' ', flush=True)
                fail_count += 1
            else:
                country = ipinfo_data.get('country', 'N/A')
                org = ipinfo_data.get('as_name', 'N/A')
                print(f"[ipinfo ✅ {country}/{org}]", end=' ', flush=True)
                success_count += 1

            self.ip_writer.add_or_update_ip(ip, 'ipinfo_api', ipinfo_data)

            rdns_data = fetch_rdns_ptr(ip, rdns_settings.rdns_query_timeout)
            if rdns_data.get('has_ptr'):
                hostname = rdns_data.get('hostname', 'N/A')
                print(f"[rdns ✅ {hostname}]")
            else:
                print(f"[rdns ❌]")

            self.ip_writer.add_or_update_ip(ip, 'rdns_ptr', rdns_data)

            self._save_progress(1, ip)

            time.sleep(ipinfo_settings.ipinfo_query_delay)

        self._mark_phase_done(1)

        self.report['phases']['phase1'] = {
            'status': 'done',
            'ips_processed': total,
            'success': success_count,
            'fail': fail_count,
            'resumed_from': skipped,
        }

        print(f"\n阶段1完成: 处理 {total} 个IP (断点续跑 {skipped}), 新增成功 {success_count}, 新增失败 {fail_count}")

    # ── Phase 2: 自动分类过滤 ──

    def phase2_classify(self):
        if self._is_phase_done(2):
            print("阶段2已完成，跳过")
            return

        merged_rules = OrderedDict()
        for key, val in self.builtin_rules.items():
            merged_rules[key] = val
        for key, val in self.custom_rules.items():
            merged_rules[key] = val

        classification = {}
        stats = {}
        unclassified = []

        total = len(self.ips)
        print(f"总IP数: {total}")
        print(f"内置规则分类: {', '.join(self.builtin_rules.keys())}")
        if self.custom_rules:
            print(f"外部规则分类: {', '.join(self.custom_rules.keys())}")
        print("-" * 60)

        for i, ip in enumerate(self.ips, 1):
            ip_data = self.ip_reader.get_ip_data(ip)
            if not ip_data:
                classify_result = {
                    'category': 'other',
                    'label': '其他',
                    'matched_by': [],
                    'need_deep_query': True,
                    'classify_time': datetime.now().isoformat(),
                }
            else:
                classify_result = self._classify_ip(ip, ip_data, merged_rules)

            classification[ip] = classify_result
            cat = classify_result['category']
            stats[cat] = stats.get(cat, 0) + 1

            self.ip_writer.add_or_update_ip(ip, 'trace_classify', classify_result)

            label = classify_result['label']
            matched_info = ''
            if classify_result['matched_by']:
                first = classify_result['matched_by'][0]
                matched_info = f" ← {first['field']} ~ {first['pattern']}"
            print(f"[{i}/{total}] {ip} → {label}{matched_info}")

            if cat == 'other' and ip_data:
                rdns_data = ip_data.get('rdns_ptr', {})
                if rdns_data.get('has_ptr'):
                    unclassified.append({
                        'ip': ip,
                        'hostname': rdns_data.get('hostname', ''),
                        'aliases': rdns_data.get('aliases', []),
                        'ipinfo_org': ip_data.get('ipinfo_api', {}).get('as_name', ''),
                        'ipinfo_country': ip_data.get('ipinfo_api', {}).get('country', ''),
                        'ipinfo_region': ip_data.get('ipinfo_api', {}).get('region', ''),
                    })
                elif not ip_data.get('ipinfo_api', {}).get('as_name'):
                    unclassified.append({
                        'ip': ip,
                        'hostname': '',
                        'aliases': [],
                        'ipinfo_org': '',
                        'ipinfo_country': ip_data.get('ipinfo_api', {}).get('country', ''),
                        'ipinfo_region': ip_data.get('ipinfo_api', {}).get('region', ''),
                    })

        self._save_unclassified(unclassified)

        filtered_ips = [
            ip for ip, cls in classification.items()
            if cls['category'] in DEEP_QUERY_CATEGORIES
        ]
        filtered_file = os.path.join(self.output_dir, f'{self.prefix}.trace_filtered_ips')
        with open(filtered_file, 'w', encoding='utf-8') as f:
            for ip in filtered_ips:
                f.write(ip + '\n')

        self._mark_phase_done(2)

        deep_needed = len(filtered_ips)
        deep_skipped = total - deep_needed

        self.report['phases']['phase2'] = {
            'status': 'done',
            'classification': stats,
            'deep_query_needed': deep_needed,
            'deep_query_skipped': deep_skipped,
            'unclassified_rdns_count': len(unclassified),
        }

        print(f"\n{'=' * 60}")
        print("分类统计:")
        for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")
        print(f"\n需要深度查询: {deep_needed}")
        print(f"跳过深度查询: {deep_skipped}")
        print(f"未识别RDNS: {len(unclassified)}")
        print(f"过滤后IP列表: {filtered_file}")
        print(f"{'=' * 60}")

    def _classify_ip(self, ip, ip_data, rules):
        for rule_source, (cat_key, cat_def) in enumerate(rules.items()):
            patterns = cat_def.get('patterns', [])
            for pattern in patterns:
                field_value = self._extract_nested_field(ip_data, pattern['field'])
                if field_value is None:
                    continue
                if self._match_pattern(field_value, pattern):
                    return {
                        'category': cat_key,
                        'label': cat_def.get('label', cat_key),
                        'description': cat_def.get('description', ''),
                        'matched_by': [{
                            'rule_source': 'builtin' if rule_source < len(self.builtin_rules) else 'custom',
                            'field': pattern['field'],
                            'pattern': pattern['match'],
                            'type': pattern['type'],
                            'value': str(field_value),
                        }],
                        'need_deep_query': cat_def.get('need_deep_query', True),
                        'classify_time': datetime.now().isoformat(),
                    }

        return {
            'category': 'other',
            'label': '其他',
            'description': '未匹配任何已知规则',
            'matched_by': [],
            'need_deep_query': True,
            'classify_time': datetime.now().isoformat(),
        }

    def _extract_nested_field(self, data, field_path):
        parts = field_path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def _match_pattern(self, field_value, pattern):
        match_str = pattern['match']
        match_type = pattern.get('type', 'contains')

        if field_value is None:
            return False

        value_str = str(field_value).lower()
        match_str_lower = match_str.lower()

        if match_type == 'suffix':
            return value_str.endswith(match_str_lower)
        elif match_type == 'contains':
            return match_str_lower in value_str
        elif match_type == 'prefix':
            return value_str.startswith(match_str_lower)
        elif match_type == 'exact':
            return value_str == match_str_lower
        return False

    def _save_unclassified(self, unclassified_list):
        output_path = os.path.join(self.output_dir, f'{self.prefix}.unclassified_rdns')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unclassified_list, f, ensure_ascii=False, indent=2)
        if unclassified_list:
            print(f"未识别RDNS已保存: {output_path} ({len(unclassified_list)} 条)")

    # ── Phase 3: 深度查询 ──

    def phase3_deep_query(self):
        if self.args.no_deep_query:
            print("已跳过深度查询（--no-deep-query）")
            self.report['phases']['phase3'] = {'status': 'skipped', 'ips_deep_queried': 0}
            return

        if self._is_phase_done(3):
            print("阶段3已完成，跳过")
            return

        filtered_file = os.path.join(self.output_dir, f'{self.prefix}.trace_filtered_ips')
        if not os.path.exists(filtered_file):
            print("未找到过滤后的IP文件，使用全量IP")
            filtered_ips = self.ips
        else:
            with open(filtered_file, 'r', encoding='utf-8') as f:
                filtered_ips = [line.strip() for line in f if line.strip()]

        if not filtered_ips:
            print("没有需要深度查询的IP")
            self.report['phases']['phase3'] = {'status': 'done', 'ips_deep_queried': 0}
            self._mark_phase_done(3)
            return

        processed = self._load_progress(3)
        if processed:
            print(f"发现进度文件，已完成 {len(processed)} 个IP，从断点继续")

        aizhan_settings = AizhanSettings()
        chinaz_settings = ChinazSettings()
        fofa_settings = FofaSettings()

        total = len(filtered_ips)
        skipped = len([ip for ip in filtered_ips if ip in processed])
        print(f"需要深度查询的IP: {total}")
        print(f"已完成: {skipped}")
        print(f"剩余: {total - skipped}")
        print(f"爱站网查询间隔: {aizhan_settings.aizhan_query_delay}s")
        print(f"站长之家查询间隔: {chinaz_settings.chinaz_query_delay}s")
        print(f"Fofa查询间隔: {fofa_settings.fofa_query_delay}s")
        print("-" * 60)

        new_count = 0
        for i, ip in enumerate(filtered_ips, 1):
            if ip in processed:
                continue

            new_count += 1
            print(f"[{i}/{total}] 深度查询: {ip}")

            aizhan_data = fetch_aizhan(ip, aizhan_settings.aizhan_cookie, delay=0)
            if aizhan_data.get('success'):
                dc = aizhan_data.get('domain_count', 0)
                loc = aizhan_data.get('location', 'N/A')
                print(f"  爱站: ✅ {loc} - {dc} 个域名")
            else:
                print(f"  爱站: ❌ {aizhan_data.get('error', 'N/A')}")
            self.ip_writer.add_or_update_ip(ip, 'aizhan', aizhan_data)
            time.sleep(aizhan_settings.aizhan_query_delay)

            chinaz_data = fetch_chinaz(ip, chinaz_settings.chinaz_cookie, delay=0)
            if chinaz_data.get('success'):
                dc = len(chinaz_data.get('domains', []))
                loc = chinaz_data.get('location', 'N/A')
                print(f"  站长: ✅ {loc} - {dc} 个域名")
            else:
                print(f"  站长: ❌ {chinaz_data.get('error', 'N/A')}")
            self.ip_writer.add_or_update_ip(ip, 'chinaz', chinaz_data)
            time.sleep(chinaz_settings.chinaz_query_delay)

            fofa_data = fetch_fofa_host_detail(ip, fofa_settings.fofa_api_key)
            if 'raw_error' in fofa_data:
                print(f"  Fofa: ❌ {fofa_data.get('error_message', 'N/A')}")
            else:
                print(f"  Fofa: ✅")
            self.ip_writer.add_or_update_ip(ip, 'fofa', fofa_data)
            time.sleep(fofa_settings.fofa_query_delay)

            self._save_progress(3, ip)

        self._mark_phase_done(3)

        self.report['phases']['phase3'] = {
            'status': 'done',
            'ips_deep_queried': total,
            'resumed_from': skipped,
            'newly_queried': new_count,
        }

        print(f"\n阶段3完成: 深度查询 {total} 个IP (断点续跑 {skipped}, 新增 {new_count})")

    # ── Phase 4: 汇总输出 ──

    def phase4_summary(self):
        phase2_data = self.report['phases'].get('phase2', {})
        classification = phase2_data.get('classification', {})

        print(f"\n{'=' * 60}")
        print("溯源IP处理报告")
        print(f"{'=' * 60}")
        print(f"输入文件: {self.ip_file}")
        print(f"总IP数: {len(self.ips)}")
        print(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if classification:
            print(f"\n分类统计:")
            for cat, count in sorted(classification.items(), key=lambda x: -x[1]):
                print(f"  {cat}: {count}")

        deep_needed = phase2_data.get('deep_query_needed', 0)
        deep_skipped = phase2_data.get('deep_query_skipped', 0)
        unclassified_count = phase2_data.get('unclassified_rdns_count', 0)

        print(f"\n深度查询: {deep_needed} 个IP")
        print(f"跳过: {deep_skipped} 个IP")
        print(f"未识别RDNS: {unclassified_count} 条")

        if unclassified_count > 0:
            print(f"\n未识别RDNS文件: {os.path.join(self.output_dir, f'{self.prefix}.unclassified_rdns')}")
            print("提示: 可将未识别的域名模式添加到 custom_rules.json，验证后合并到 builtin_rules.json")

        print(f"\n{'=' * 60}")

        self.report['phases']['phase4'] = {'status': 'done'}
        self.report['unclassified_rdns_count'] = unclassified_count
        self.report['unclassified_rdns_file'] = os.path.join(self.output_dir, f'{self.prefix}.unclassified_rdns')

    def _save_report(self):
        report_path = os.path.join(self.output_dir, f'{self.prefix}.trace_report')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='溯源IP处理流水线 - 自动采集、分类、深度查询',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('ip_file', help='IP列表文件路径（每行一个IP）')

    phase_group = parser.add_argument_group('阶段控制')
    phase_group.add_argument(
        '--from-phase', type=int, choices=[1, 2, 3, 4],
        help='从指定阶段开始（默认从阶段1开始）'
    )
    phase_group.add_argument(
        '--only-phase', type=int, choices=[1, 2, 3, 4],
        help='只执行指定阶段'
    )

    rule_group = parser.add_argument_group('分类规则')
    rule_group.add_argument(
        '--custom-rules', type=str,
        help='外部规则文件路径（默认使用 classifiers/custom_rules.json）'
    )
    rule_group.add_argument(
        '--no-custom-rules', action='store_true',
        help='不加载外部规则文件'
    )

    output_group = parser.add_argument_group('输出控制')
    output_group.add_argument(
        '--output-dir', type=str, default=None,
        help='输出目录（默认跟随 .env 中的 IP_STORAGE_DIR）'
    )
    output_group.add_argument(
        '--no-deep-query', action='store_true',
        help='分类后不执行深度查询阶段'
    )

    args = parser.parse_args()
    args.output_dir_explicit = args.output_dir is not None
    if args.output_dir is None:
        args.output_dir = 'data'

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    print("=" * 60)
    print("溯源IP处理流水线")
    print("=" * 60)
    print(f"IP文件: {args.ip_file}")
    print(f"内置规则: {BUILTIN_RULES_FILE}")
    if not args.no_custom_rules:
        custom_path = args.custom_rules if args.custom_rules else CUSTOM_RULES_FILE
        print(f"外部规则: {custom_path}")
    else:
        print("外部规则: 已禁用")
    print(f"输出目录: {args.output_dir}")
    if args.from_phase:
        print(f"起始阶段: {args.from_phase}")
    if args.only_phase:
        print(f"仅执行阶段: {args.only_phase}")
    if args.no_deep_query:
        print("深度查询: 已禁用")
    print("=" * 60)

    pipeline = TraceIPPipeline(args.ip_file, args)
    pipeline.run()


if __name__ == "__main__":
    main()
