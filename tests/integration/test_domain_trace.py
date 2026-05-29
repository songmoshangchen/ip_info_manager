from datetime import datetime, timedelta, timezone

from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.trace_steps.phase3_deep import DeepQueryPhase
from ip_info.pipeline.trace_steps.phase4_verify_scan import VerifyScanPhase
from ip_info.processors.dns_verify.extractor import extract_domain_mappings
from ip_info.processors.dns_verify.runner import BatchDnsVerify
from ip_info.store.in_memory import InMemoryDomainCache, InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class FakeChannel(BaseChannelAdapter):
    channel_name = "fake"

    def __init__(self, *, disabled=False, default_delay=0, response=None):
        self.disabled = disabled
        self.default_delay = default_delay
        self._response = response or {"status": "ok"}

    def _validate_key(self):
        pass

    def _request(self, ip, **kwargs):
        return {"ip": ip, **self._response}

    def fetch(self, ip, **kwargs):
        raw = self._request(ip, **kwargs)
        result = self._parse(raw, ip)
        result.setdefault("query_time", "2024-01-01T00:00:00")
        return result


class FakeBatchStep:
    def __init__(self, name: str, result: BatchResult | None = None, writer=None, channel_name: str = ""):
        self._name = name
        self._result = result or BatchResult(success_count=1)
        self._writer = writer
        self._channel_name = channel_name or name
        self._run_fn = None

    @property
    def name(self) -> str:
        return self._name

    def run(self) -> BatchResult:
        if self._run_fn:
            self._run_fn()
            return self._result
        if self._writer:
            self._writer.add_or_update_ip("1.2.3.4", self._channel_name, {"data": "test"})
        return self._result


def _make_context(writer=None, reader=None, domain_cache=None):
    w = writer or InMemoryIPWriter()
    r = reader or InMemoryIPReader(data=w._store)
    return PipelineContext(
        writer=w,
        reader=r,
        progress_tracker=InMemoryProgressTracker(),
        domain_cache=domain_cache,
    )


def _make_aizhan_data(ip, domains):
    return {
        "query_ip": ip,
        "domains": [{"domain": d, "title": f"Site {d}"} for d in domains],
        "domain_count": len(domains),
    }


def _make_chinaz_data(ip, domains):
    return {
        "query_ip": ip,
        "domains": [{"domain": d, "start_time": "2024-01-01", "end_time": "2025-01-01"} for d in domains],
        "domain_count": len(domains),
    }


def _fake_batch_verify(mappings, **kwargs):
    results = []
    for m in mappings:
        domain = m["domain"]
        target_ip = m["target_ip"]
        if "timeout" in domain:
            results.append(
                {
                    "domain": domain,
                    "target_ip": target_ip,
                    "status": "timeout",
                    "resolved_ips": [],
                    "verify_time": datetime.now(timezone.utc).isoformat(),
                }
            )
        elif "unknown" in domain:
            results.append(
                {
                    "domain": domain,
                    "target_ip": target_ip,
                    "status": "unresolved",
                    "resolved_ips": [],
                    "verify_time": datetime.now(timezone.utc).isoformat(),
                }
            )
        elif "changed" in domain:
            results.append(
                {
                    "domain": domain,
                    "target_ip": target_ip,
                    "status": "changed",
                    "resolved_ips": ["9.9.9.9"],
                    "verify_time": datetime.now(timezone.utc).isoformat(),
                }
            )
        else:
            results.append(
                {
                    "domain": domain,
                    "target_ip": target_ip,
                    "status": "matched",
                    "resolved_ips": [target_ip],
                    "verify_time": datetime.now(timezone.utc).isoformat(),
                }
            )
    return results


class TestDomainExtraction:
    def test_extract_from_aizhan(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": _make_aizhan_data("1.2.3.4", ["example.com", "test.org"]),
        }
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 2
        domains = {m["domain"] for m in mappings}
        assert domains == {"example.com", "test.org"}
        assert all(m["target_ip"] == "1.2.3.4" for m in mappings)

    def test_extract_from_chinaz(self):
        ip_data = {
            "ip": "5.6.7.8",
            "chinaz": _make_chinaz_data("5.6.7.8", ["site.cn"]),
        }
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 1
        assert mappings[0]["domain"] == "site.cn"

    def test_extract_from_both_channels(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": _make_aizhan_data("1.2.3.4", ["shared.com", "aizhan-only.com"]),
            "chinaz": _make_chinaz_data("1.2.3.4", ["shared.com", "chinaz-only.com"]),
        }
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 4
        domain_sources = {}
        for m in mappings:
            domain_sources.setdefault(m["domain"], []).append(m["sources"][0])
        assert "shared.com" in domain_sources
        assert set(domain_sources["shared.com"]) == {"aizhan", "chinaz"}

    def test_no_domain_data(self):
        ip_data = {"ip": "1.2.3.4", "aizhan": {"query_ip": "1.2.3.4"}}
        mappings = extract_domain_mappings(ip_data)
        assert mappings == []


class TestDomainTraceEndToEnd:
    def test_full_trace_aizhan_to_verify(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ip = "1.2.3.4"

        aizhan = FakeChannel(response=_make_aizhan_data(ip, ["example.com", "test.org"]))
        phase3 = DeepQueryPhase(
            ips=[ip],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=FakeChannel(),
            fofa_channel=FakeChannel(),
            no_validate=True,
        )
        phase3.run()

        aizhan_data = reader.get_channel_data(ip, "aizhan")
        assert aizhan_data is not None
        assert len(aizhan_data["domains"]) == 2

        ip_data = reader.get_ip_data(ip)
        ip_data["ip"] = ip
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 2

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            max_age_days=7,
            force_days=0,
            batch_verify_fn=_fake_batch_verify,
        )
        result = verifier.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data is not None
        assert verify_data["matched"] >= 1

    def test_full_trace_both_channels_to_verify(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ip = "1.2.3.4"

        aizhan = FakeChannel(response=_make_aizhan_data(ip, ["shared.com", "a-only.com"]))
        chinaz = FakeChannel(response=_make_chinaz_data(ip, ["shared.com", "c-only.com"]))
        phase3 = DeepQueryPhase(
            ips=[ip],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=FakeChannel(),
            no_validate=True,
        )
        phase3.run()

        ip_data = reader.get_ip_data(ip)
        ip_data["ip"] = ip
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 4

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            max_age_days=7,
            force_days=0,
            batch_verify_fn=_fake_batch_verify,
        )
        result = verifier.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data["matched"] >= 1


class TestDomainVerifyStatuses:
    def test_matched_changed_unresolved_timeout(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ip = "1.2.3.4"

        writer.add_or_update_ip(
            ip,
            "aizhan",
            _make_aizhan_data(
                ip,
                [
                    "normal.com",
                    "changed-site.com",
                    "unknown-site.org",
                    "timeout-site.net",
                ],
            ),
        )

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            max_age_days=7,
            force_days=0,
            batch_verify_fn=_fake_batch_verify,
        )
        result = verifier.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data["matched"] >= 1
        assert verify_data["changed"] >= 1
        assert verify_data["unresolved"] >= 1


class TestDomainCacheIntegration:
    def test_cached_domain_used_in_result(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        cache = InMemoryDomainCache()
        ip = "1.2.3.4"

        writer.add_or_update_ip(ip, "aizhan", _make_aizhan_data(ip, ["cached.com", "new.com"]))

        cached_time = datetime.now(timezone.utc).isoformat()
        cache.set(
            "cached.com",
            {
                "domain": "cached.com",
                "status": "matched",
                "resolved_ips": [ip],
                "verify_time": cached_time,
            },
        )

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            domain_cache=cache,
            max_age_days=7,
            batch_verify_fn=_fake_batch_verify,
        )
        result = verifier.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data is not None
        assert verify_data["matched"] >= 1
        cached_entry = cache.get("new.com")
        assert cached_entry is not None
        assert cached_entry["status"] == "matched"

    def test_expired_cache_reverified(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        cache = InMemoryDomainCache()
        ip = "1.2.3.4"

        writer.add_or_update_ip(ip, "aizhan", _make_aizhan_data(ip, ["stale.com"]))

        expired_time = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cache.set(
            "stale.com",
            {
                "domain": "stale.com",
                "status": "matched",
                "resolved_ips": [ip],
                "verify_time": expired_time,
            },
        )

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            domain_cache=cache,
            max_age_days=7,
            batch_verify_fn=_fake_batch_verify,
        )
        result = verifier.run()

        assert result.success_count == 1
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data is not None

    def test_new_domain_written_to_cache(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        cache = InMemoryDomainCache()
        ip = "1.2.3.4"

        writer.add_or_update_ip(ip, "aizhan", _make_aizhan_data(ip, ["fresh.com"]))

        verifier = BatchDnsVerify(
            ips=[ip],
            writer=writer,
            reader=reader,
            domain_cache=cache,
            max_age_days=7,
            force_days=0,
            batch_verify_fn=_fake_batch_verify,
        )
        verifier.run()

        cached = cache.get("fresh.com")
        assert cached is not None
        assert cached["status"] == "matched"


class TestDomainTraceViaPhase4:
    def test_phase4_dns_verify_reads_phase3_data(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ip = "1.2.3.4"

        aizhan = FakeChannel(response=_make_aizhan_data(ip, ["example.com"]))
        phase3 = DeepQueryPhase(
            ips=[ip],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=FakeChannel(),
            fofa_channel=FakeChannel(),
            no_validate=True,
        )
        phase3.run()

        assert reader.get_channel_data(ip, "aizhan") is not None

        def dns_run_fn():
            from ip_info.processors.dns_verify.runner import BatchDnsVerify as RealDns

            real = RealDns(
                ips=[ip],
                writer=writer,
                reader=reader,
                max_age_days=7,
                force_days=0,
                batch_verify_fn=_fake_batch_verify,
            )
            real.run()

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=1))
        dns_step._run_fn = dns_run_fn

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=1))

        phase4 = VerifyScanPhase(
            ips=[ip],
            context=ctx,
            steps=[dns_step, port_step],
        )
        r4 = phase4.run()

        assert r4.success is True
        verify_data = reader.get_channel_data(ip, "domain_verify")
        assert verify_data is not None
        assert verify_data["matched"] >= 1
