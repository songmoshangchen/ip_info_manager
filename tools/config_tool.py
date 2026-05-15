import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import ENV_FILE


REQUIRED_PREFIX = 'IP_'

PATH_SAFE_KEYS = {
    'IP_STORAGE_DIR',
    'IP_STORAGE_NAME',
    'IP_IP_DOMAIN_LOOKUP_PROJECT_NAME',
    'IP_TRACE_IP_PROJECT_NAME',
}


def _validate_path_safety(key, value):
    if key not in PATH_SAFE_KEYS:
        return
    v = value.strip()
    if not v:
        return
    if os.path.isabs(v):
        raise ValueError(f"不允许使用绝对路径: {v}")
    normalized = os.path.normpath(v)
    parts = normalized.replace('\\', '/').split('/')
    if '..' in parts:
        raise ValueError(f"不允许包含 \"..\" 路径遍历: {v}")
    if key != 'IP_STORAGE_DIR' and ('\\' in v or '/' in v):
        raise ValueError(f"名称不允许包含路径分隔符: {v}")


CONFIG_GROUPS = [
    {
        'name': 'output',
        'label': '输出文件配置',
        'items': [
            {
                'key': 'IP_STORAGE_DIR',
                'desc': '通用数据存储子目录（相对于 data/，可为空，不允许绝对路径和场景保留名）',
                'default': '',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_STORAGE_NAME',
                'desc': '通用数据存储文件名（用于数据文件命名前缀）',
                'default': 'ip_data',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_PROJECT_NAME',
                'desc': 'IP域名反查流水线项目名称（输出到 data/ip_domain_lookup/{项目名称}/）',
                'default': 'temp',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PROJECT_NAME',
                'desc': '溯源IP处理流水线项目名称（输出到 data/trace_ip/{项目名称}/）',
                'default': 'temp',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
        ],
    },
    {
        'name': 'credentials',
        'label': 'API Key / Cookie 凭证配置',
        'items': [
            {
                'key': 'IP_FOFA_API_KEY',
                'desc': 'Fofa API Key（Fofa 网络空间搜索引擎凭证）',
                'default': '',
                'type': 'str',
                'required': True,
                'sensitive': True,
            },
            {
                'key': 'IP_IPINFO_ACCESS_TOKEN',
                'desc': 'IPInfo Access Token（IP 地理信息查询凭证）',
                'default': '',
                'type': 'str',
                'required': True,
                'sensitive': True,
            },
            {
                'key': 'IP_AIZHAN_COOKIE',
                'desc': '爱站网 Cookie（浏览器登录 aizhan.com 后获取，用于 IP 反查域名）',
                'default': '',
                'type': 'str',
                'required': True,
                'sensitive': True,
            },
            {
                'key': 'IP_CHINAZ_COOKIE',
                'desc': '站长之家 Cookie（可选，有 Cookie 可查更多信息，用于 IP 反查域名/SEO 数据）',
                'default': '',
                'type': 'str',
                'required': False,
                'sensitive': True,
            },
            {
                'key': 'IP_ZOOMEYE_API_KEY',
                'desc': 'ZoomEye API Key（ZoomEye 网络空间测绘引擎凭证）',
                'default': '',
                'type': 'str',
                'required': False,
                'sensitive': True,
            },
        ],
    },
    {
        'name': 'delays',
        'label': '查询间隔与超时配置',
        'items': [
            {
                'key': 'IP_FOFA_QUERY_DELAY',
                'desc': 'Fofa 查询间隔（秒），避免触发频率限制',
                'default': '2',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IPINFO_QUERY_DELAY',
                'desc': 'IPInfo 查询间隔（秒），避免触发频率限制',
                'default': '1.2',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_RDNS_QUERY_DELAY',
                'desc': 'RDNS PTR 反向解析查询间隔（秒）',
                'default': '0.1',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_RDNS_QUERY_TIMEOUT',
                'desc': 'RDNS PTR 反向解析查询超时（秒）',
                'default': '1.5',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_WHOIS_QUERY_DELAY',
                'desc': 'Whois 查询间隔（秒），避免触发频率限制',
                'default': '0.5',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_WHOIS_QUERY_TIMEOUT',
                'desc': 'Whois 查询超时（秒）',
                'default': '2',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_AIZHAN_QUERY_DELAY',
                'desc': '爱站网查询间隔（秒），避免触发频率限制',
                'default': '2',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_CHINAZ_QUERY_DELAY',
                'desc': '站长之家查询间隔（秒），避免触发频率限制',
                'default': '2',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_ZOOMEYE_QUERY_DELAY',
                'desc': 'ZoomEye 查询间隔（秒），避免触发频率限制',
                'default': '2.0',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_SSL_CERT_PORT',
                'desc': 'SSL 证书获取端口',
                'default': '443',
                'type': 'int',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_SSL_CERT_TIMEOUT',
                'desc': 'SSL 连接超时（秒）',
                'default': '5',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_SSL_CERT_QUERY_DELAY',
                'desc': 'SSL 证书查询间隔（秒）',
                'default': '0.5',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
        ],
    },
    {
        'name': 'ip_domain_lookup',
        'label': 'IP域名反查流水线 - 渠道开关',
        'items': [
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED',
                'desc': '启用 RDNS PTR 反向解析（通过 DNS 反向查询获取 IP 关联域名）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED',
                'desc': '启用爱站网 IP 反查域名（通过 aizhan.com 查询 IP 绑定的域名）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED',
                'desc': '启用站长之家 IP 反查域名（通过 chinaz.com 查询 IP 绑定的域名）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED',
                'desc': '启用 ZoomEye 网络空间测绘（通过 ZoomEye 搜索 IP 关联的服务和域名）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED',
                'desc': '启用 Fofa 搜索查询（通过 Fofa 搜索 IP 关联的资产信息）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED',
                'desc': '启用 SSL 证书域名提取（通过解析 SSL 证书获取关联域名）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
        ],
    },
    {
        'name': 'trace_ip',
        'label': '溯源IP处理流水线 - 渠道开关',
        'items': [
            {
                'key': 'IP_TRACE_IP_PHASE1_IPINFO_ENABLED',
                'desc': '阶段1-基础情报采集：启用 IPInfo 查询（获取 IP 地理位置/ASN/组织信息）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED',
                'desc': '阶段1-基础情报采集：启用 RDNS PTR 反向解析',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PHASE3_AIZHAN_ENABLED',
                'desc': '阶段3-深度查询：启用爱站网 IP 反查域名',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PHASE3_CHINAZ_ENABLED',
                'desc': '阶段3-深度查询：启用站长之家 IP 反查域名',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED',
                'desc': '阶段3-深度查询：启用 Fofa Host 聚合查询（查询 IP 关联的所有主机资产）',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PHASE4_DNS_VERIFY_ENABLED',
                'desc': '阶段4-DNS域名正向验证：启用 DNS 域名正向验证',
                'default': 'true',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_DNS_VERIFY_TIMEOUT',
                'desc': 'DNS 域名验证超时（秒）',
                'default': '3.0',
                'type': 'float',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_DNS_VERIFY_CONCURRENCY',
                'desc': 'DNS 域名验证并发线程数',
                'default': '10',
                'type': 'int',
                'required': False,
                'sensitive': False,
            },
        ],
    },
    {
        'name': 'port_scan',
        'label': '溯源IP流水线 - 端口扫描配置（Phase 5）',
        'items': [
            {
                'key': 'IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED',
                'desc': '阶段5-端口扫描：启用端口扫描（默认关闭，需显式启用）',
                'default': 'false',
                'type': 'bool',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PORT_SCAN_NMAP_PATH',
                'desc': 'nmap 可执行文件路径（Windows 需完整路径）',
                'default': 'nmap',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PORT_SCAN_TIMEOUT',
                'desc': '单 IP 端口扫描超时（秒）',
                'default': '90',
                'type': 'int',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PORT_SCAN_PORT_LIST',
                'desc': '端口列表文件路径',
                'default': 'config/port_scan/top1000.txt',
                'type': 'str',
                'required': False,
                'sensitive': False,
            },
            {
                'key': 'IP_TRACE_IP_PORT_SCAN_CONCURRENCY',
                'desc': '端口扫描并发数（1=串行，>1=并发）',
                'default': '1',
                'type': 'int',
                'required': False,
                'sensitive': False,
            },
        ],
    },
]


def _build_key_registry():
    registry = {}
    for group in CONFIG_GROUPS:
        for item in group['items']:
            registry[item['key']] = {**item, 'group_name': group['name'], 'group_label': group['label']}
    return registry


KEY_REGISTRY = _build_key_registry()


def _mask_value(value, visible=6):
    if not value or len(value) <= visible:
        return value
    return value[:visible] + '****'


def _validate_value_type(value, type_name):
    if type_name == 'bool':
        if value.lower() not in ('true', 'false'):
            raise ValueError(f"布尔类型的值只能是 'true' 或 'false'，收到: {value}")
    elif type_name == 'int':
        try:
            int(value)
        except ValueError:
            raise ValueError(f"整数类型的值必须是数字，收到: {value}")
    elif type_name == 'float':
        try:
            float(value)
        except ValueError:
            raise ValueError(f"浮点数类型的值必须是数字，收到: {value}")


class EnvManager:

    def __init__(self, env_path=None):
        self.env_path = env_path or ENV_FILE

    def _parse_lines(self):
        if not os.path.exists(self.env_path):
            return []
        with open(self.env_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_lines(self, lines):
        with open(self.env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def list_all(self):
        lines = self._parse_lines()
        result = {}
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, _, value = stripped.partition('=')
                key = key.strip()
                if key.startswith(REQUIRED_PREFIX):
                    result[key] = value
        return result

    def get(self, key):
        self._validate_key(key)
        all_items = self.list_all()
        if key not in all_items:
            return None
        return all_items[key]

    def set(self, key, value):
        self._validate_key(key)
        if key in KEY_REGISTRY:
            _validate_value_type(value, KEY_REGISTRY[key]['type'])
        lines = self._parse_lines()
        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                existing_key, _, _ = stripped.partition('=')
                if existing_key.strip() == key:
                    lines[i] = f'{key}={value}\n'
                    found = True
                    break
        if not found:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] = lines[-1] + '\n'
            lines.append(f'{key}={value}\n')
        self._write_lines(lines)
        return True

    def delete(self, key):
        self._validate_key(key)
        lines = self._parse_lines()
        new_lines = []
        found = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue
            if '=' in stripped:
                existing_key, _, _ = stripped.partition('=')
                if existing_key.strip() == key:
                    found = True
                    continue
            new_lines.append(line)
        if found:
            self._write_lines(new_lines)
        return found

    def bulk_set(self, items):
        for key, value in items.items():
            self.set(key, value)
        return len(items)

    def _validate_key(self, key):
        if not key.startswith(REQUIRED_PREFIX):
            raise ValueError(f"Key 必须以 '{REQUIRED_PREFIX}' 开头，收到: {key}")


def _cmd_groups(mgr):
    print("配置分组列表")
    print("=" * 70)
    for group in CONFIG_GROUPS:
        item_count = len(group['items'])
        print(f"  {group['name']:<22s} {group['label']} ({item_count} 项)")
    print(f"\n共 {len(CONFIG_GROUPS)} 个分组，{len(KEY_REGISTRY)} 个配置项")
    print(f"配置文件: {mgr.env_path}")


def _cmd_list(mgr, group_filter=None):
    all_items = mgr.list_all()
    if not all_items and not group_filter:
        print(f"配置文件为空或不存在: {mgr.env_path}")
        return

    groups_to_show = CONFIG_GROUPS
    if group_filter:
        groups_to_show = [g for g in CONFIG_GROUPS if g['name'] == group_filter]
        if not groups_to_show:
            print(f"未找到分组: {group_filter}")
            print(f"可用分组: {', '.join(g['name'] for g in CONFIG_GROUPS)}")
            sys.exit(1)

    max_key_len = max(len(k) for k in KEY_REGISTRY) + 2

    for group in groups_to_show:
        print(f"\n{'─' * 70}")
        print(f"  [{group['name']}] {group['label']}")
        print(f"{'─' * 70}")
        for item in group['items']:
            key = item['key']
            value = all_items.get(key)
            if value is None:
                display_val = '(未设置)'
            elif item['sensitive']:
                display_val = _mask_value(value)
            else:
                display_val = value[:40] + '...' if len(value) > 40 else value

            default_tag = ''
            if value is not None and value != item['default']:
                default_tag = f"  (默认: {item['default']})"
            elif value is None and item['default']:
                default_tag = f"  (默认: {item['default']})"

            req_tag = ' *' if item['required'] else ''

            print(f"  {key:<{max_key_len}s} {display_val}{req_tag}{default_tag}")
        print()

    total_in_groups = sum(len(g['items']) for g in groups_to_show)
    print(f"共 {total_in_groups} 个配置项  |  * = 必填项  |  配置文件: {mgr.env_path}")


def _cmd_status(mgr):
    all_items = mgr.list_all()
    print("配置状态总览")
    print("=" * 70)
    print(f"配置文件: {mgr.env_path}")

    cred_ok = 0
    cred_missing = 0
    cred_total = 0
    switch_on = 0
    switch_off = 0

    for group in CONFIG_GROUPS:
        print(f"\n  [{group['label']}]")
        for item in group['items']:
            key = item['key']
            value = all_items.get(key)

            if item['type'] == 'bool':
                cred_total += 0
                if value is None or value.lower() == item['default'].lower():
                    status = 'ON' if (value or item['default']).lower() == 'true' else 'OFF'
                else:
                    status = 'ON' if value.lower() == 'true' else 'OFF'
                if status == 'ON':
                    switch_on += 1
                else:
                    switch_off += 1
                print(f"    {key:<45s} [{'ON':>3s}]" if status == 'ON'
                      else f"    {key:<45s} [{'OFF':>4s}]")
            elif item['sensitive']:
                cred_total += 1
                if value and value != '' and 'your_' not in value:
                    cred_ok += 1
                    print(f"    {key:<45s} [已配置]")
                else:
                    cred_missing += 1
                    tag = ' (必填!)' if item['required'] else ' (可选)'
                    print(f"    {key:<45s} [未配置]{tag}")
            else:
                display = value if value else f"(默认: {item['default']})"
                print(f"    {key:<45s} {display}")

    print(f"\n{'=' * 70}")
    print(f"  凭证: {cred_ok}/{cred_total} 已配置", end='')
    if cred_missing > 0:
        print(f"  ({cred_missing} 未配置)")
    else:
        print()

    enabled_total = switch_on + switch_off
    if enabled_total > 0:
        print(f"  开关: {switch_on} 启用 / {switch_off} 禁用 (共 {enabled_total} 个)")

    issues = []
    for group in CONFIG_GROUPS:
        for item in group['items']:
            if item['required'] and item['sensitive']:
                value = all_items.get(item['key'], '')
                if not value or 'your_' in value:
                    issues.append(f"缺少必填凭证: {item['key']}")
            if item['type'] == 'bool':
                value = all_items.get(item['key'], item['default'])
                if value.lower() not in ('true', 'false'):
                    issues.append(f"无效布尔值: {item['key']}={value}")
            if item['type'] in ('int', 'float'):
                value = all_items.get(item['key'])
                if value is not None:
                    try:
                        _validate_value_type(value, item['type'])
                    except ValueError:
                        issues.append(f"无效数值: {item['key']}={value}")

    if issues:
        print(f"\n  ? 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"  ? 配置检查通过，无异常")


def _cmd_info(mgr, key):
    if key not in KEY_REGISTRY:
        print(f"未找到配置项: {key}")
        print("提示: 使用 'groups' 命令查看所有可用分组，使用 'list' 查看所有配置项")
        sys.exit(1)

    meta = KEY_REGISTRY[key]
    all_items = mgr.list_all()
    current = all_items.get(key)

    print(f"配置项详情")
    print("=" * 60)
    print(f"  键名:     {key}")
    print(f"  所属分组: {meta['group_label']} ({meta['group_name']})")
    print(f"  说明:     {meta['desc']}")
    print(f"  类型:     {meta['type']}")
    print(f"  默认值:   {meta['default']}")
    if meta['sensitive']:
        if current:
            print(f"  当前值:   {_mask_value(current)}")
        else:
            print(f"  当前值:   (未设置)")
    else:
        print(f"  当前值:   {current if current is not None else '(未设置)'}")
    print(f"  必填:     {'是' if meta['required'] else '否'}")
    print(f"  敏感:     {'是（显示时会脱敏）' if meta['sensitive'] else '否'}")

    if meta['type'] == 'bool':
        print(f"\n  提示: 布尔值只接受 true 或 false")
    elif meta['type'] in ('int', 'float'):
        print(f"\n  提示: 数值类型，请输入有效数字")

    if current is None and meta['default']:
        print(f"\n  注意: 当前未设置，运行时将使用默认值 '{meta['default']}'")


def _cmd_check(mgr):
    all_items = mgr.list_all()
    issues = []
    warnings = []

    for group in CONFIG_GROUPS:
        for item in group['items']:
            key = item['key']
            value = all_items.get(key)

            if item['required'] and item['sensitive']:
                if not value or 'your_' in value:
                    issues.append((key, item['desc'], '缺少必填凭证'))

            if item['type'] == 'bool' and value is not None:
                if value.lower() not in ('true', 'false'):
                    issues.append((key, item['desc'], f'无效布尔值: {value}'))

            if item['type'] in ('int', 'float') and value is not None:
                try:
                    _validate_value_type(value, item['type'])
                except ValueError as e:
                    issues.append((key, item['desc'], str(e)))

            if value is not None and value == '' and item['required']:
                issues.append((key, item['desc'], '必填项为空'))

            if value is not None and item['sensitive'] and 'your_' in value:
                warnings.append((key, item['desc'], '仍使用模板占位符'))

    print("配置完整性检查")
    print("=" * 60)

    if not issues and not warnings:
        print("? 所有配置检查通过，无异常")
    else:
        if issues:
            print(f"\n? 错误 ({len(issues)} 项):")
            for key, desc, reason in issues:
                print(f"  [错误] {key}")
                print(f"         说明: {desc}")
                print(f"         问题: {reason}")
        if warnings:
            print(f"\n? 警告 ({len(warnings)} 项):")
            for key, desc, reason in warnings:
                print(f"  [警告] {key}")
                print(f"         说明: {desc}")
                print(f"         问题: {reason}")

    return len(issues) == 0


def main():
    parser = argparse.ArgumentParser(
        description='.env 配置管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python config_tool.py groups                  查看所有配置分组
  python config_tool.py list                    按分组列出所有配置
  python config_tool.py list --group credentials  只看凭证配置
  python config_tool.py status                  查看配置状态总览
  python config_tool.py info IP_FOFA_API_KEY    查看某配置项详情
  python config_tool.py check                   检查配置完整性
  python config_tool.py get IP_STORAGE_DIR      获取配置值
  python config_tool.py set IP_STORAGE_DIR temp 设置配置值
  python config_tool.py delete IP_STORAGE_DIR   删除配置项
  python config_tool.py bulk-set IP_A=1 IP_B=2  批量设置""",
    )
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    subparsers.add_parser('groups', help='列出所有配置分组')

    list_parser = subparsers.add_parser('list', help='按分组列出配置项（含描述和默认值）')
    list_parser.add_argument('--group', '-g', help='只显示指定分组（使用 groups 命令查看分组名）')

    subparsers.add_parser('status', help='查看配置状态总览（凭证/开关/异常）')

    info_parser = subparsers.add_parser('info', help='查看某个配置项的详细信息')
    info_parser.add_argument('key', help='配置键名')

    subparsers.add_parser('check', help='检查配置完整性（缺少必填项/无效值）')

    get_parser = subparsers.add_parser('get', help='获取配置值（仅输出值）')
    get_parser.add_argument('key', help='配置键名')

    set_parser = subparsers.add_parser('set', help='设置配置值（自动校验类型）')
    set_parser.add_argument('key', help='配置键名')
    set_parser.add_argument('value', nargs='?', default='', help='配置值（不传或传空则清空该项）')

    delete_parser = subparsers.add_parser('delete', help='删除配置项')
    delete_parser.add_argument('key', help='配置键名')

    bulk_parser = subparsers.add_parser('bulk-set', help='批量设置配置项')
    bulk_parser.add_argument('items', nargs='+', help='键值对，格式: KEY=VALUE')

    args = parser.parse_args()

    try:
        mgr = EnvManager()

        if args.command == 'groups':
            _cmd_groups(mgr)

        elif args.command == 'list':
            _cmd_list(mgr, group_filter=args.group)

        elif args.command == 'status':
            _cmd_status(mgr)

        elif args.command == 'info':
            _cmd_info(mgr, args.key)

        elif args.command == 'check':
            ok = _cmd_check(mgr)
            if not ok:
                sys.exit(1)

        elif args.command == 'get':
            value = mgr.get(args.key)
            if value is None:
                if args.key in KEY_REGISTRY:
                    print(f"(未设置，默认值: {KEY_REGISTRY[args.key]['default']})")
                else:
                    print(f"未找到: {args.key}")
                sys.exit(1)
            print(value)

        elif args.command == 'set':
            _validate_path_safety(args.key, args.value)
            mgr.set(args.key, args.value)
            display_val = args.value[:30] + '...' if len(args.value) > 30 else args.value
            print(f"已设置: {args.key}={display_val}")
            if args.key in KEY_REGISTRY:
                meta = KEY_REGISTRY[args.key]
                print(f"  说明: {meta['desc']}")

        elif args.command == 'delete':
            if mgr.delete(args.key):
                print(f"已删除: {args.key}")
                if args.key in KEY_REGISTRY:
                    meta = KEY_REGISTRY[args.key]
                    print(f"  说明: {meta['desc']}")
                    if meta['default']:
                        print(f"  将回退到默认值: {meta['default']}")
            else:
                print(f"未找到: {args.key}")
                sys.exit(1)

        elif args.command == 'bulk-set':
            items = {}
            for item in args.items:
                if '=' not in item:
                    print(f"错误: 格式无效 '{item}'，应为 KEY=VALUE")
                    sys.exit(1)
                key, _, value = item.partition('=')
                _validate_path_safety(key, value)
                items[key] = value
            count = mgr.bulk_set(items)
            print(f"已批量设置 {count} 个配置项")

        else:
            parser.print_help()

    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
