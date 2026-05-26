"""单独测试 domain_verify 渠道，验证每个域名有独立的 verify_time。"""

import json
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))

from ip_info.processors.dns_verify.runner import BatchDnsVerify  # noqa: E402
from ip_info.store.json_store import IPReader, IPWriter  # noqa: E402
from ip_info.store.sqlite_cache import SqliteDomainCache  # noqa: E402

reader = IPReader("data/integration_test_data.json")
writer = IPWriter("data/integration_test_data.json")
cache = SqliteDomainCache("data/integration_domain_cache.db")

# 只对 8.8.8.8 运行 DNS 验证（force_days=0 强制重新验证）
runner = BatchDnsVerify(
    ips=["8.8.8.8"],
    writer=writer,
    reader=reader,
    domain_cache=cache,
    max_age_days=7,
    force_days=0,
    timeout=3.0,
    concurrency=5,
)
result = runner.run()
print(f"结果: success={result.success_count}, skip={result.skip_count}")

# 查看写入的数据
data = json.load(open("data/integration_test_data.json", "r", encoding="utf-8"))
dv = data["8.8.8.8"]["domain_verify"]
print(f"total_domains: {dv['total_domains']}")
print(f"IP级 verify_time: {dv.get('verify_time', '无（已移除）')}")
print("results 前3个:")
for r in dv["results"][:3]:
    print(
        f"  domain={r['domain']}, status={r['status']}, "
        f"verify_time={r.get('verify_time', '无')}, "
        f"sources={r.get('sources', [])}"
    )
