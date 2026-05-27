import logging

from ip_info.store.protocols import IPDataReader

logger = logging.getLogger(__name__)

_DYNAMIC_KEYWORDS = ("dynamic", "dhcp", "pppoe", "broadband", "adsl", "dialup", "pool")


def _is_dynamic_ip(classifier_data: dict | None) -> bool:
    if classifier_data is None:
        return False
    if classifier_data.get("category") != "residential":
        return False
    for match in classifier_data.get("matched_by", []):
        pattern = match.get("pattern", "").lower()
        for kw in _DYNAMIC_KEYWORDS:
            if kw in pattern:
                return True
    return False


def filter_dynamic_ips(
    ips: list[str],
    reader: IPDataReader,
) -> tuple[list[str], list[str]]:
    """将 IP 列表分为动态 IP 和非动态 IP。

    动态 IP 的判定条件：分类为 residential，且 matched_by 的 pattern
    包含 dynamic/dhcp/pppoe/broadband/adsl/dialup/pool 关键词。

    Returns:
        (dynamic_ips, non_dynamic_ips) — 动态 IP 和非动态 IP 列表，保持原始顺序。
    """
    dynamic_ips = []
    non_dynamic_ips = []
    for ip in ips:
        classifier_data = reader.get_channel_data(ip, "classifier")
        if _is_dynamic_ip(classifier_data):
            dynamic_ips.append(ip)
        else:
            non_dynamic_ips.append(ip)
    if dynamic_ips:
        logger.info("识别 %d 个动态 IP (将跳过深度查询)", len(dynamic_ips))
    return dynamic_ips, non_dynamic_ips


def filter_ips_by_classification(
    ips: list[str],
    reader: IPDataReader,
) -> list[str]:
    """根据分类结果过滤 IP，返回需要深度查询的 IP 列表。

    保留 need_deep_query=True 的 IP（cloud_provider/residential/other），
    过滤 need_deep_query=False 的 IP（invalid_rdns/cdn/crawler_scanner）。
    无分类数据的 IP 默认保留。
    """
    filtered_ips = []
    for ip in ips:
        classifier_data = reader.get_channel_data(ip, "classifier")
        if classifier_data is None:
            filtered_ips.append(ip)
            continue
        if classifier_data.get("need_deep_query", True):
            filtered_ips.append(ip)
        else:
            logger.info("过滤 IP: %s (分类: %s)", ip, classifier_data.get("category", "unknown"))
    return filtered_ips
