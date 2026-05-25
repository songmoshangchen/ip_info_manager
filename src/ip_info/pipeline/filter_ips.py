import logging

from ip_info.store.protocols import IPDataReader

logger = logging.getLogger(__name__)


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
