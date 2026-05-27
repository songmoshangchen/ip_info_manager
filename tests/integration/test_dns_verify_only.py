from datetime import datetime, timezone
from unittest.mock import patch

from ip_info.processors.dns_verify.runner import BatchDnsVerify
from ip_info.store.in_memory import InMemoryDomainCache, InMemoryIPReader, InMemoryIPWriter


def _fake_batch_verify(mappings, **kwargs):
    results = []
    for m in mappings:
        results.append(
            {
                "domain": m["domain"],
                "target_ip": m["target_ip"],
                "status": "matched",
                "resolved_ips": [m["target_ip"]],
                "verify_time": datetime.now(timezone.utc).isoformat(),
            }
        )
    return results


class TestDnsVerifyIntegration:
    def test_single_ip_verify(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ip = "8.8.8.8"

        writer.add_or_update_ip(
            ip,
            "aizhan",
            {
                "query_ip": ip,
                "domains": [
                    {"domain": "dns.google", "title": "Google DNS"},
                    {"domain": "dns.google.com", "title": "Google DNS"},
                ],
                "domain_count": 2,
            },
        )

        with patch("ip_info.processors.dns_verify.runner.batch_verify", side_effect=_fake_batch_verify):
            runner = BatchDnsVerify(
                ips=[ip],
                writer=writer,
                reader=reader,
                max_age_days=7,
                force_days=0,
                timeout=3.0,
                concurrency=5,
            )
            result = runner.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data is not None
        assert verify_data["total_domains"] >= 2
        assert verify_data["matched"] >= 2
        for r in verify_data["results"]:
            assert r["verify_time"] is not None
            assert len(r["verify_time"]) > 0

    def test_verify_with_domain_cache(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        cache = InMemoryDomainCache()
        ip = "8.8.8.8"

        writer.add_or_update_ip(
            ip,
            "aizhan",
            {
                "query_ip": ip,
                "domains": [{"domain": "cached.example.com"}, {"domain": "new.example.com"}],
                "domain_count": 2,
            },
        )

        cache.set(
            "cached.example.com",
            {
                "domain": "cached.example.com",
                "status": "matched",
                "resolved_ips": [ip],
                "verify_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        with patch("ip_info.processors.dns_verify.runner.batch_verify", side_effect=_fake_batch_verify):
            runner = BatchDnsVerify(
                ips=[ip],
                writer=writer,
                reader=reader,
                domain_cache=cache,
                max_age_days=7,
                force_days=0,
            )
            result = runner.run()

        assert result.success_count == 1
        new_cached = cache.get("new.example.com")
        assert new_cached is not None
        assert new_cached["status"] == "matched"

    def test_verify_no_domain_data(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ip = "1.2.3.4"

        writer.add_or_update_ip(ip, "ipinfo_api", {"country": "US"})

        with patch("ip_info.processors.dns_verify.runner.batch_verify", side_effect=_fake_batch_verify):
            runner = BatchDnsVerify(
                ips=[ip],
                writer=writer,
                reader=reader,
                max_age_days=7,
                force_days=0,
            )
            result = runner.run()

        assert result.success_count == 0
        assert result.skip_count >= 1

    def test_each_domain_has_verify_time(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ip = "1.2.3.4"

        writer.add_or_update_ip(
            ip,
            "aizhan",
            {
                "query_ip": ip,
                "domains": [
                    {"domain": "a.com"},
                    {"domain": "b.com"},
                    {"domain": "c.com"},
                ],
                "domain_count": 3,
            },
        )

        with patch("ip_info.processors.dns_verify.runner.batch_verify", side_effect=_fake_batch_verify):
            runner = BatchDnsVerify(
                ips=[ip],
                writer=writer,
                reader=reader,
                max_age_days=7,
                force_days=0,
            )
            runner.run()

        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert len(verify_data["results"]) == 3
        verify_times = [r["verify_time"] for r in verify_data["results"]]
        assert all(vt for vt in verify_times)
