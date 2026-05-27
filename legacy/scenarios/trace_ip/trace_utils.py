LABEL_MAP = {
    'cloud_provider': '云服务商',
    'cdn': 'CDN/WAF',
    'crawler_scanner': '爬虫/扫描器',
    'residential': '家用宽带',
    'invalid_rdns': '无效RDNS',
    'excluded_domain': '排除域名',
    'other': '其他（需确认）',
}

CAT_WEIGHT = {
    'cloud_provider': 2,
    'residential': 1,
    'other': 0,
}


def is_china_ip(info):
    ipinfo = info.get('ipinfo_api', {})
    return (ipinfo.get('country_code', '') == 'CN'
            or 'China' in ipinfo.get('country', ''))


def extract_all_domains(info):
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


def extract_fofa_ports(info):
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


def has_domains(info):
    return len(extract_all_domains(info)) > 0


def has_ports(info):
    return len(extract_fofa_ports(info)) > 0


def trace_priority(info):
    is_cn = is_china_ip(info)
    has_dom = has_domains(info)
    has_pt = has_ports(info)
    if has_dom and is_cn:
        return 1
    if has_dom or (has_pt and is_cn):
        return 2
    if has_pt or is_cn:
        return 3
    return 4


def sort_key(info):
    n_dom = len(extract_all_domains(info))
    n_pt = len(extract_fofa_ports(info))
    cat = info.get('trace_classify', {}).get('category', 'other')
    return (-n_dom, -n_pt, -CAT_WEIGHT.get(cat, 0))


def cat_display(info):
    classify = info.get('trace_classify', {})
    category = classify.get('category', '')
    if category == 'other':
        return LABEL_MAP.get('other', '其他（需确认）')
    label = LABEL_MAP.get(category, category)
    matched_by = classify.get('matched_by', [])
    if matched_by and matched_by[0].get('note'):
        note = matched_by[0]['note']
        return f'{label}（{note}）'
    return label


def trace_action(info):
    has_dom = has_domains(info)
    has_pt = has_ports(info)
    is_cn = is_china_ip(info)
    actions = []
    if has_dom:
        actions.append(
            'ICP备案/WHOIS查询域名注册信息' if is_cn
            else 'WHOIS查询域名注册信息')
    if has_pt:
        actions.append('排查端口服务泄露信息')
    if not actions:
        actions.append('公开信息检索IP历史行为')
    return '；'.join(actions)
