import ipaddress

BATCH_SIZE = 256


def ip_to_int(ip_str: str) -> int | None:
    """IP 字符串转整数，无效返回 None"""
    try:
        return int(ipaddress.ip_address(ip_str))
    except (ValueError, TypeError):
        return None


def parse_entry_to_range(entry: str) -> tuple[int, int] | None:
    """解析 IP/CIDR 为范围，无效返回 None"""
    try:
        network = ipaddress.ip_network(entry, strict=False)
        return (int(network.network_address), int(network.broadcast_address))
    except ValueError:
        pass
    try:
        ip_obj = ipaddress.ip_address(entry)
        val = int(ip_obj)
        return (val, val)
    except ValueError:
        return None


def match_sorted_ips_streaming(
    sorted_ip_ints: list[tuple[str, int]],
    dataset_path: str,
    batch_size: int = BATCH_SIZE,
) -> set[int]:
    """流式双指针匹配算法。返回命中 IP 的索引集合。"""
    matched_indices = set()
    ip_ptr = 0
    total_ips = len(sorted_ip_ints)

    with open(dataset_path, "r", encoding="utf-8", buffering=8192) as f:
        batch = []
        for line in f:
            if ip_ptr >= total_ips:
                break

            line = line.strip()
            if not line or line.startswith("#"):
                continue

            r = parse_entry_to_range(line)
            if r is None:
                continue

            batch.append(r)

            if len(batch) >= batch_size:
                batch.sort(key=lambda x: x[0])
                ip_ptr = _process_batch(batch, sorted_ip_ints, ip_ptr, total_ips, matched_indices)
                batch = []

        if batch and ip_ptr < total_ips:
            batch.sort(key=lambda x: x[0])
            ip_ptr = _process_batch(batch, sorted_ip_ints, ip_ptr, total_ips, matched_indices)

    return matched_indices


def _process_batch(
    batch: list[tuple[int, int]],
    sorted_ip_ints: list[tuple[str, int]],
    ip_ptr: int,
    total_ips: int,
    matched_indices: set[int],
) -> int:
    """处理一批 IP 范围，返回更新后的 ip_ptr"""
    for range_start, range_end in batch:
        while ip_ptr < total_ips:
            _, ip_int = sorted_ip_ints[ip_ptr]
            if ip_int < range_start:
                ip_ptr += 1
            elif ip_int <= range_end:
                matched_indices.add(ip_ptr)
                ip_ptr += 1
            else:
                break
    return ip_ptr
