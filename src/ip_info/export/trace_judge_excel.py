import json
import logging
import os

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


def _is_china_ip(info):
    ipinfo = info.get("ipinfo_api") or {}
    return ipinfo.get("country_code", "") == "CN" or "China" in ipinfo.get("country", "")


def _extract_domains(info):
    domains = []
    for src_name in ("aizhan", "chinaz"):
        src = info.get(src_name) or {}
        if not src.get("success"):
            continue
        for d in src.get("domains", []):
            domain = d.get("domain", "")
            if domain and domain not in [x["domain"] for x in domains]:
                domains.append({"domain": domain, "source": src_name})
    return domains


def _extract_fofa_ports(info):
    fofa = info.get("fofa_host") or {}
    if fofa.get("error"):
        return []
    return fofa.get("ports", [])


def _extract_port_scan_ports(info):
    ps = info.get("port_scan") or {}
    if not ps or "error" in ps:
        return []
    return ps.get("open_ports", [])


def _cat_display(info):
    classify = info.get("classifier") or {}
    category = classify.get("category", "")
    label = LABEL_MAP.get(category, category)
    matched_by = classify.get("matched_by", [])
    if matched_by and matched_by[0].get("note"):
        note = matched_by[0]["note"]
        return f"{label}（{note}）"
    return label


def _cat_note(info):
    classify = info.get("classifier") or {}
    matched_by = classify.get("matched_by", [])
    if matched_by and matched_by[0].get("note"):
        return matched_by[0]["note"]
    return ""


def _is_no_trace(info):
    classify = info.get("classifier") or {}
    category = classify.get("category", "")
    if category in ("crawler_scanner", "cdn"):
        return True
    if not classify.get("need_deep_query", True):
        return True
    return False


def _trace_priority(info):
    has_dom = len(_extract_domains(info)) > 0
    has_pt = len(_extract_fofa_ports(info)) > 0
    is_cn = _is_china_ip(info)
    if has_dom and is_cn:
        return 1
    if has_dom or (has_pt and is_cn):
        return 2
    if has_pt or is_cn:
        return 3
    return 4


def _sort_key(info):
    n_dom = len(_extract_domains(info))
    n_pt = len(_extract_fofa_ports(info))
    cat_weight = {"cloud_provider": 2, "residential": 1, "other": 0}
    classify = info.get("classifier") or {}
    cat = classify.get("category", "other")
    return (-n_dom, -n_pt, -cat_weight.get(cat, 0))


def _build_trace_columns(exclude_ips=None):
    def _extract_ip(ip, info):
        return ip

    def _extract_needs(ip, info):
        if exclude_ips and ip in exclude_ips:
            return "否"
        if _is_no_trace(info):
            return "否"
        return "是"

    def _extract_country(ip, info):
        return (info.get("ipinfo_api") or {}).get("country", "")

    def _extract_org(ip, info):
        return (info.get("ipinfo_api") or {}).get("as_name", "")

    def _extract_cat(ip, info):
        return _cat_display(info)

    def _extract_cat_note(ip, info):
        return _cat_note(info)

    def _extract_domain_count(ip, info):
        return str(len(_extract_domains(info)))

    def _extract_domain_list(ip, info):
        domains = _extract_domains(info)
        return "\n".join(d["domain"] for d in domains)

    def _extract_fofa_count(ip, info):
        return str(len(_extract_fofa_ports(info)))

    def _extract_fofa_list(ip, info):
        ports = _extract_fofa_ports(info)
        strs = []
        for p in ports:
            s = str(p.get("port", ""))
            products = ", ".join(pr.get("product", "") for pr in p.get("products", []))
            if products:
                s = f"{s}({products})"
            strs.append(s)
        return "\n".join(strs)

    def _extract_scan_count(ip, info):
        return str(len(_extract_port_scan_ports(info)))

    def _extract_scan_list(ip, info):
        ports = _extract_port_scan_ports(info)
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
        tags_data = (info.get("tagger") or {}).get("tags", [])
        return ", ".join(tags_data) if isinstance(tags_data, list) else str(tags_data)

    def _extract_rdns(ip, info):
        rdns = info.get("rdns_ptr") or {}
        return rdns.get("hostname", "") if rdns.get("has_ptr") else ""

    return [
        ColumnDef("IP", _extract_ip, width=18),
        ColumnDef("需要溯源", _extract_needs, width=10),
        ColumnDef("国家", _extract_country, width=10),
        ColumnDef("ASN/组织", _extract_org, width=25),
        ColumnDef("分类", _extract_cat, width=22),
        ColumnDef("分类说明", _extract_cat_note, width=20),
        ColumnDef("域名数", _extract_domain_count, width=8),
        ColumnDef("反查域名列表", _extract_domain_list, width=40),
        ColumnDef("Fofa端口数", _extract_fofa_count, width=10),
        ColumnDef("Fofa开放端口", _extract_fofa_list, width=30),
        ColumnDef("扫描端口数", _extract_scan_count, width=12),
        ColumnDef("扫描开放端口", _extract_scan_list, width=40),
        ColumnDef("威胁标签", _extract_tags, width=20),
        ColumnDef("RDNS", _extract_rdns, width=25),
    ]


TRACE_SHEET_DEFS = [
    SheetDef("P1 核心溯源"),
    SheetDef("P2 重点溯源"),
    SheetDef("P3 辅助溯源"),
    SheetDef("P4 暂缓"),
    SheetDef("P5 不需溯源", header_color="A6A6A6"),
]


def _build_trace_logic(exclude_ips=None):
    def group(ip, info):
        if _is_no_trace(info):
            return 4
        return _trace_priority(info) - 1

    def sort(ip, info):
        return _sort_key(info)

    def mark(ip, info):
        if exclude_ips and ip in exclude_ips:
            return False
        if _is_no_trace(info):
            return False
        return True

    return GroupLogic(group=group, sort_key=sort, mark_fn=mark)


def generate_trace_judge_excel(output_dir, prefix, exclude_ips=None):
    json_path = os.path.join(output_dir, f"{prefix}.json")
    if not os.path.exists(json_path):
        logger.warning("找不到数据文件 %s，跳过 Excel 导出", json_path)
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        ip_data = json.load(f)

    columns = _build_trace_columns(exclude_ips)
    logic = _build_trace_logic(exclude_ips)

    result = generate_grouped_excel(
        ip_data=ip_data,
        output_dir=output_dir,
        prefix=f"{prefix}.trace_judge",
        columns=columns,
        sheets=TRACE_SHEET_DEFS,
        logic=logic,
        mark_column=1,
    )
    return result
