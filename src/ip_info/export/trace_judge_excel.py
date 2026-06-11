import json
import logging
import os
from dataclasses import dataclass, field

from ip_info.utils.excel_grouped import (
    ColumnDef,
    GroupLogic,
    SheetDef,
    generate_grouped_excel,
)

logger = logging.getLogger(__name__)

LABEL_MAP = {
    "cloud_provider": "云服务商",
    "cdn": "CDN/WAF",
    "crawler_scanner": "爬虫/扫描器",
    "residential": "家用宽带",
    "invalid_rdns": "无效RDNS",
    "excluded_domain": "排除域名",
    "other": "其他（需确认）",
}


@dataclass
class ChannelMapping:
    ipinfo: str = "ipinfo_api"
    classifier: str = "classifier"
    domain_sources: list[str] = field(default_factory=lambda: ["aizhan", "chinaz"])
    fofa_ports: str = "fofa_host"
    port_scan: str = "port_scan"
    tagger: str = "tagger"
    rdns: str = "rdns_ptr"


# ===== 数据提取（通过 ChannelMapping）=====


def _is_china_ip(info, ch: ChannelMapping):
    ipinfo = info.get(ch.ipinfo) or {}
    return ipinfo.get("country_code", "") == "CN" or "China" in ipinfo.get("country", "")


def _extract_domains(info, ch: ChannelMapping):
    domains = []
    for src_name in ch.domain_sources:
        src = info.get(src_name) or {}
        if not src.get("success"):
            continue
        for d in src.get("domains", []):
            domain = d.get("domain", "")
            if domain and domain not in [x["domain"] for x in domains]:
                domains.append({"domain": domain, "source": src_name})
    return domains


def _extract_fofa_ports(info, ch: ChannelMapping):
    fofa = info.get(ch.fofa_ports) or {}
    if fofa.get("error"):
        return []
    return fofa.get("ports", [])


def _extract_port_scan_ports(info, ch: ChannelMapping):
    ps = info.get(ch.port_scan) or {}
    if not ps or "error" in ps:
        return []
    return ps.get("open_ports", [])


def _cat_display(info, ch: ChannelMapping):
    classify = info.get(ch.classifier) or {}
    category = classify.get("category", "")
    label = LABEL_MAP.get(category, category)
    matched_by = classify.get("matched_by", [])
    if matched_by and matched_by[0].get("note"):
        note = matched_by[0]["note"]
        return f"{label}（{note}）"
    return label


def _cat_note(info, ch: ChannelMapping):
    classify = info.get(ch.classifier) or {}
    matched_by = classify.get("matched_by", [])
    if matched_by and matched_by[0].get("note"):
        return matched_by[0]["note"]
    return ""


def _get_category(info, ch: ChannelMapping):
    classify = info.get(ch.classifier) or {}
    return classify.get("category", "other")


def _is_no_trace(info, ch: ChannelMapping):
    """仅排除确定性噪音：爬虫/扫描器、CDN/WAF。"""
    category = _get_category(info, ch)
    return category in ("crawler_scanner", "cdn")


def _has_open_ports(info, ch: ChannelMapping):
    return len(_extract_fofa_ports(info, ch)) > 0 or len(_extract_port_scan_ports(info, ch)) > 0


def _trace_priority(info, ch: ChannelMapping):
    """
    P1-P4 优先级规则（P5 由 _is_no_trace 单独处理）。
    维度：分类、地理位置、域名、端口。
    核心原则：默认偏向高优先级，宁可多查不漏。
    """
    category = _get_category(info, ch)
    has_dom = len(_extract_domains(info, ch)) > 0
    has_pt = _has_open_ports(info, ch)
    is_cn = _is_china_ip(info, ch)

    # P1: 恶意基础设施 / 国内+有域名 / 国内+有端口
    if category == "malicious":
        return 1
    if is_cn and has_dom:
        return 1
    if is_cn and has_pt:
        return 1

    # P2: 国外+有域名+服务器 / 国外+有端口+服务器 / 国内+家宽
    if not is_cn and has_dom and category in ("cloud_provider",):
        return 2
    if not is_cn and has_pt and category in ("cloud_provider",):
        return 2
    if is_cn and category == "residential":
        return 2

    # P3: 国外+服务器（无域名无端口） / 国内+other（无域名）
    if not is_cn and category in ("cloud_provider",) and not has_dom and not has_pt:
        return 3
    if is_cn and category == "other" and not has_dom:
        return 3

    # P4: 其余（国外+家宽/other、无域名无端口）
    return 4


def _sort_key(info, ch: ChannelMapping):
    n_dom = len(_extract_domains(info, ch))
    n_pt = len(_extract_fofa_ports(info, ch)) + len(_extract_port_scan_ports(info, ch))
    cat_weight = {"malicious": 3, "cloud_provider": 2, "residential": 1, "other": 0}
    cat = _get_category(info, ch)
    return (-n_dom, -n_pt, -cat_weight.get(cat, 0))


# ===== 列定义构建 =====


def _build_trace_columns(exclude_ips=None, ch=None):
    ch = ch or ChannelMapping()

    def _extract_ip(ip, info):
        return ip

    def _extract_needs(ip, info):
        if exclude_ips and ip in exclude_ips:
            return "否"
        if _is_no_trace(info, ch):
            return "否"
        return "是"

    def _extract_country(ip, info):
        return (info.get(ch.ipinfo) or {}).get("country", "")

    def _extract_org(ip, info):
        return (info.get(ch.ipinfo) or {}).get("as_name", "")

    def _extract_cat(ip, info):
        return _cat_display(info, ch)

    def _extract_cat_note(ip, info):
        return _cat_note(info, ch)

    def _extract_domain_count(ip, info):
        return str(len(_extract_domains(info, ch)))

    def _extract_domain_list(ip, info):
        domains = _extract_domains(info, ch)
        return "\n".join(d["domain"] for d in domains)

    def _extract_fofa_count(ip, info):
        return str(len(_extract_fofa_ports(info, ch)))

    def _extract_fofa_list(ip, info):
        ports = _extract_fofa_ports(info, ch)
        strs = []
        for p in ports:
            s = str(p.get("port", ""))
            products = ", ".join(pr.get("product", "") for pr in p.get("products", []))
            if products:
                s = f"{s}({products})"
            strs.append(s)
        return "\n".join(strs)

    def _extract_scan_count(ip, info):
        return str(len(_extract_port_scan_ports(info, ch)))

    def _extract_scan_list(ip, info):
        ports = _extract_port_scan_ports(info, ch)
        strs = []
        for p in ports:
            s = str(p.get("port", ""))
            product = p.get("product", "")
            service = p.get("service", "")
            if product:
                s = f"{s}({product})"
            elif service:
                s = f"{s}({service})"
            strs.append(s)
        return "\n".join(strs)

    def _extract_tags(ip, info):
        tags_data = (info.get(ch.tagger) or {}).get("tags", [])
        return ", ".join(tags_data) if isinstance(tags_data, list) else str(tags_data)

    def _extract_rdns(ip, info):
        rdns = info.get(ch.rdns) or {}
        return rdns.get("hostname", "") if rdns.get("has_ptr") else ""

    return [
        ColumnDef("IP", _extract_ip, width=18),
        ColumnDef("需要溯源", _extract_needs, width=10),
        ColumnDef("分类", _extract_cat, width=22),
        ColumnDef("分类说明", _extract_cat_note, width=20),
        ColumnDef("威胁标签", _extract_tags, width=20),
        ColumnDef("RDNS", _extract_rdns, width=25),
        ColumnDef("域名数", _extract_domain_count, width=8),
        ColumnDef("反查域名列表", _extract_domain_list, width=40),
        ColumnDef("扫描端口数", _extract_scan_count, width=12),
        ColumnDef("扫描开放端口", _extract_scan_list, width=40),
        ColumnDef("Fofa端口数", _extract_fofa_count, width=10),
        ColumnDef("Fofa开放端口", _extract_fofa_list, width=30),
        ColumnDef("国家", _extract_country, width=10),
        ColumnDef("ASN/组织", _extract_org, width=25),
    ]


def _build_trace_only_columns(ch=None):
    """仅溯源模式：去掉"需要溯源"列"""
    ch = ch or ChannelMapping()

    def _extract_ip(ip, info):
        return ip

    def _extract_country(ip, info):
        return (info.get(ch.ipinfo) or {}).get("country", "")

    def _extract_org(ip, info):
        return (info.get(ch.ipinfo) or {}).get("as_name", "")

    def _extract_cat(ip, info):
        return _cat_display(info, ch)

    def _extract_cat_note(ip, info):
        return _cat_note(info, ch)

    def _extract_domain_count(ip, info):
        return str(len(_extract_domains(info, ch)))

    def _extract_domain_list(ip, info):
        domains = _extract_domains(info, ch)
        return "\n".join(d["domain"] for d in domains)

    def _extract_fofa_count(ip, info):
        return str(len(_extract_fofa_ports(info, ch)))

    def _extract_fofa_list(ip, info):
        ports = _extract_fofa_ports(info, ch)
        strs = []
        for p in ports:
            s = str(p.get("port", ""))
            products = ", ".join(pr.get("product", "") for pr in p.get("products", []))
            if products:
                s = f"{s}({products})"
            strs.append(s)
        return "\n".join(strs)

    def _extract_scan_count(ip, info):
        return str(len(_extract_port_scan_ports(info, ch)))

    def _extract_scan_list(ip, info):
        ports = _extract_port_scan_ports(info, ch)
        strs = []
        for p in ports:
            s = str(p.get("port", ""))
            product = p.get("product", "")
            service = p.get("service", "")
            if product:
                s = f"{s}({product})"
            elif service:
                s = f"{s}({service})"
            strs.append(s)
        return "\n".join(strs)

    def _extract_tags(ip, info):
        tags_data = (info.get(ch.tagger) or {}).get("tags", [])
        return ", ".join(tags_data) if isinstance(tags_data, list) else str(tags_data)

    def _extract_rdns(ip, info):
        rdns = info.get(ch.rdns) or {}
        return rdns.get("hostname", "") if rdns.get("has_ptr") else ""

    return [
        ColumnDef("IP", _extract_ip, width=18),
        ColumnDef("分类", _extract_cat, width=22),
        ColumnDef("分类说明", _extract_cat_note, width=20),
        ColumnDef("威胁标签", _extract_tags, width=20),
        ColumnDef("RDNS", _extract_rdns, width=25),
        ColumnDef("域名数", _extract_domain_count, width=8),
        ColumnDef("反查域名列表", _extract_domain_list, width=40),
        ColumnDef("扫描端口数", _extract_scan_count, width=12),
        ColumnDef("扫描开放端口", _extract_scan_list, width=40),
        ColumnDef("Fofa端口数", _extract_fofa_count, width=10),
        ColumnDef("Fofa开放端口", _extract_fofa_list, width=30),
        ColumnDef("国家", _extract_country, width=10),
        ColumnDef("ASN/组织", _extract_org, width=25),
    ]


# ===== Sheet 定义 =====

JUDGE_SHEET_DEFS = [
    SheetDef("P1 核心溯源"),
    SheetDef("P2 重点溯源"),
    SheetDef("P3 辅助溯源"),
    SheetDef("P4 暂缓"),
    SheetDef("P5 不需溯源", header_color="A6A6A6"),
]

TRACE_ONLY_SHEET_DEFS = [
    SheetDef("P1 核心溯源"),
    SheetDef("P2 重点溯源"),
    SheetDef("P3 辅助溯源"),
    SheetDef("P4 暂缓"),
]


# ===== 逻辑构建 =====


def _build_judge_logic(exclude_ips=None, ch=None):
    ch = ch or ChannelMapping()

    def group(ip, info):
        if _is_no_trace(info, ch):
            return 4
        return _trace_priority(info, ch) - 1

    def sort(ip, info):
        return _sort_key(info, ch)

    def mark(ip, info):
        if exclude_ips and ip in exclude_ips:
            return False
        if _is_no_trace(info, ch):
            return False
        return True

    return GroupLogic(group=group, sort_key=sort, mark_fn=mark)


def _build_trace_only_logic(exclude_ips=None, ch=None):
    ch = ch or ChannelMapping()

    def group(ip, info):
        return _trace_priority(info, ch) - 1

    def sort(ip, info):
        return _sort_key(info, ch)

    return GroupLogic(group=group, sort_key=sort, mark_fn=None)


def _load_ip_data(output_dir, prefix):
    json_path = os.path.join(output_dir, f"{prefix}.json")
    if not os.path.exists(json_path):
        logger.warning("找不到数据文件 %s，跳过 Excel 导出", json_path)
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _filter_trace_only(ip_data, exclude_ips, ch):
    ch = ch or ChannelMapping()
    filtered = {}
    for ip, info in ip_data.items():
        if exclude_ips and ip in exclude_ips:
            continue
        if _is_no_trace(info, ch):
            continue
        filtered[ip] = info
    return filtered


# ===== 公共入口 =====


def generate_trace_judge_excel(output_dir, prefix, exclude_ips=None, channels=None):
    """模式1: 全量输出，含 P5 + 需要溯源列。"""
    ip_data = _load_ip_data(output_dir, prefix)
    if ip_data is None:
        return False

    ch = channels or ChannelMapping()
    columns = _build_trace_columns(exclude_ips, ch)
    logic = _build_judge_logic(exclude_ips, ch)

    return generate_grouped_excel(
        ip_data=ip_data,
        output_dir=output_dir,
        prefix=f"{prefix}.trace_judge",
        columns=columns,
        sheets=JUDGE_SHEET_DEFS,
        logic=logic,
        mark_column=1,
    )


def generate_trace_only_excel(output_dir, prefix, exclude_ips=None, channels=None):
    """模式2: 仅需要溯源的 IP，无 P5，无需要溯源列。"""
    ip_data = _load_ip_data(output_dir, prefix)
    if ip_data is None:
        return False

    ch = channels or ChannelMapping()
    filtered_data = _filter_trace_only(ip_data, exclude_ips, ch)
    columns = _build_trace_only_columns(ch)
    logic = _build_trace_only_logic(exclude_ips, ch)

    return generate_grouped_excel(
        ip_data=filtered_data,
        output_dir=output_dir,
        prefix=f"{prefix}.trace_only",
        columns=columns,
        sheets=TRACE_ONLY_SHEET_DEFS,
        logic=logic,
    )
