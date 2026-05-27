from ip_info.processors.dns_verify.verifier import SUPPORTED_CHANNELS


def extract_domain_mappings(
    ip_data: dict,
    channels: tuple[str, ...] = SUPPORTED_CHANNELS,
) -> list[dict]:
    mappings = []
    ip = ip_data.get("ip", "")
    for channel in channels:
        channel_data = ip_data.get(channel)
        if not isinstance(channel_data, dict):
            continue
        domains = channel_data.get("domains", [])
        if not domains:
            continue
        for d in domains:
            domain = d if isinstance(d, str) else d.get("domain", "")
            if domain:
                mappings.append(
                    {
                        "domain": domain,
                        "target_ip": ip,
                        "sources": [channel],
                    }
                )
    return mappings
