"""IP-域名映射验证脚本。

给定 IP-域名对，验证域名是否仍然解析到该 IP。
支持从命令行、文件或 ip_data.json 中获取映射数据。

用法:
  python scripts/verify_mapping.py "8.8.8.8 dns.google" "1.1.1.1 one.one.one.one"
  python scripts/verify_mapping.py --file mappings.txt
  python scripts/verify_mapping.py --data data/0518-0524/ip_data.json
  python scripts/verify_mapping.py --file mappings.txt --timeout 5.0 --concurrency 20
  python scripts/verify_mapping.py --file mappings.txt --output result.json
  python scripts/verify_mapping.py --data data/0518-0524/ip_data.json --update
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))  # noqa: E402

from ip_info.processors.dns_verify.verifier import verify_one  # noqa: E402
from ip_info.store.json_store import IPWriter  # noqa: E402
from ip_info.utils.verify_mapping import (  # noqa: E402
    extract_mappings_from_ip_data,
    format_report,
    parse_mappings_from_args,
    parse_mappings_from_file,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("verify_mapping")


def run_verify(mappings: list[dict], timeout: float, concurrency: int) -> list[dict]:
    """并发执行 DNS 验证。

    Args:
        mappings: 映射列表，每项包含 ip 和 domain。
        timeout: DNS 超时时间。
        concurrency: 并发数。

    Returns:
        验证结果列表，每项包含 domain、target_ip、status、resolved_ips、verify_time。
    """
    results: list[dict] = [None] * len(mappings)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {}
        for i, m in enumerate(mappings):
            future = executor.submit(verify_one, m["domain"], m["ip"], timeout)
            future_to_idx[future] = i
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
            except Exception as e:
                m = mappings[idx]
                result = {"domain": m["domain"], "status": "error", "resolved_ips": []}
                logger.warning("DNS验证异常: %s -> %s", m["domain"], e)
            result["target_ip"] = mappings[idx]["ip"]
            results[idx] = result
    return results


def save_output(results: list[dict], filepath: str) -> None:
    """将验证结果保存为 JSON 文件。"""
    output_data = {
        "verify_time": results[0].get("verify_time", "") if results else "",
        "total": len(results),
        "results": results,
    }
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    logger.info("结果已保存到: %s", filepath)


def update_ip_data(data_filepath: str, results: list[dict]) -> None:
    """将验证结果写回 ip_data.json 的 domain_verify 渠道。"""
    # 按 IP 分组
    ip_results: dict[str, list] = {}
    for r in results:
        ip = r["target_ip"]
        if ip not in ip_results:
            ip_results[ip] = []
        ip_results[ip].append(r)

    writer = IPWriter(data_filepath)
    for ip, items in ip_results.items():
        matched = sum(1 for r in items if r["status"] == "matched")
        changed = sum(1 for r in items if r["status"] == "changed")
        unresolved = sum(1 for r in items if r["status"] == "unresolved")
        timeout = sum(1 for r in items if r["status"] == "timeout")
        error = sum(1 for r in items if r["status"] == "error")
        verify_data = {
            "total_domains": len(items),
            "matched": matched,
            "changed": changed,
            "unresolved": unresolved,
            "timeout": timeout,
            "error": error,
            "results": [
                {
                    "domain": r["domain"],
                    "sources": [],
                    "status": r["status"],
                    "resolved_ips": r["resolved_ips"],
                    "verify_time": r.get("verify_time", ""),
                }
                for r in items
            ],
        }
        writer.add_or_update_ip(ip, "domain_verify", verify_data)
    logger.info("验证结果已写回: %s (%d 个 IP)", data_filepath, len(ip_results))


def main():
    parser = argparse.ArgumentParser(description="IP-域名映射验证脚本")
    parser.add_argument("pairs", nargs="*", help='IP-域名对，格式: "IP DOMAIN"')
    parser.add_argument("--file", help="从文本文件读取 IP-域名对（每行: IP DOMAIN）")
    parser.add_argument("--data", help="从 ip_data.json 提取映射并验证")
    parser.add_argument("--timeout", type=float, default=3.0, help="DNS 解析超时时间（秒），默认 3.0")
    parser.add_argument("--concurrency", type=int, default=10, help="并发验证数，默认 10")
    parser.add_argument("--output", help="将结果保存为 JSON 文件")
    parser.add_argument("--update", action="store_true", help="将结果写回源 ip_data.json 的 domain_verify 渠道")
    args = parser.parse_args()

    # 收集映射
    mappings: list[dict] = []

    if args.pairs:
        mappings.extend(parse_mappings_from_args(args.pairs))

    if args.file:
        file_mappings = parse_mappings_from_file(args.file)
        seen = {(m["ip"], m["domain"]) for m in mappings}
        for m in file_mappings:
            if (m["ip"], m["domain"]) not in seen:
                seen.add((m["ip"], m["domain"]))
                mappings.append(m)

    if args.data:
        data_mappings = extract_mappings_from_ip_data(args.data)
        seen = {(m["ip"], m["domain"]) for m in mappings}
        for m in data_mappings:
            if (m["ip"], m["domain"]) not in seen:
                seen.add((m["ip"], m["domain"]))
                mappings.append(m)

    if not mappings:
        logger.error("无有效映射，退出")
        sys.exit(1)

    logger.info("待验证映射: %d 个", len(mappings))

    # 执行验证
    results = run_verify(mappings, timeout=args.timeout, concurrency=args.concurrency)

    # 打印报告
    report = format_report(results)
    print(report)

    # 保存输出
    if args.output:
        save_output(results, args.output)

    # 写回 ip_data.json
    if args.update:
        if not args.data:
            logger.error("--update 需要配合 --data 参数使用")
            sys.exit(1)
        update_ip_data(args.data, results)


if __name__ == "__main__":
    main()
