"""Phase 1-4 集成测试（Mock 模式）。

使用 FakeChannel + InMemory 组件验证全流程编排逻辑。
真实模式可通过 `python tests/integration/test_phase_full_run.py --live` 手动运行。
"""

import sys

import pytest

from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.filter_ips import filter_ips_by_classification
from ip_info.pipeline.trace_steps.phase1_basic import BasicCollectPhase
from ip_info.pipeline.trace_steps.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.trace_steps.phase3_deep import DeepQueryPhase
from ip_info.pipeline.trace_steps.phase4_verify_scan import VerifyScanPhase
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker

RULES_DIR = "config/classifier"
TAGGER_CONFIG_DIR = "config/ip_tagger"


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


def _make_context(writer=None, reader=None, tracker=None):
    w = writer or InMemoryIPWriter()
    r = reader or InMemoryIPReader(data=w._store)
    return PipelineContext(
        writer=w,
        reader=r,
        progress_tracker=tracker or InMemoryProgressTracker(),
    )


class TestFullPipelineMockMode:
    def test_phase1_through_phase4(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        ips = ["8.8.8.8", "1.1.1.1"]

        phase1 = BasicCollectPhase(
            ips=ips,
            context=ctx,
            ipinfo_channel=FakeChannel(response={"country": "US", "org": "Google"}),
            rdns_channel=FakeChannel(response={"ptr": "dns.google"}),
            no_validate=True,
        )
        r1 = phase1.run()
        assert r1.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "ipinfo_api") is not None
            assert reader.get_channel_data(ip, "rdns_ptr") is not None

        def classify_run_fn():
            for ip in ips:
                writer.add_or_update_ip(
                    ip,
                    "classifier",
                    {
                        "ip": ip,
                        "category": "cloud_provider",
                        "label": "Cloud Provider",
                        "need_deep_query": True,
                        "matched_by": [{"field": "org", "pattern": "Cloud"}],
                    },
                )

        classify_step = FakeBatchStep("classifier", BatchResult(success_count=len(ips)))
        classify_step._run_fn = classify_run_fn

        def tagger_run_fn():
            for ip in ips:
                writer.add_or_update_ip(ip, "tagger", {"tags": ["cloud"]})

        tagger_step = FakeBatchStep("tagger", BatchResult(success_count=len(ips)))
        tagger_step._run_fn = tagger_run_fn

        phase2 = ClassifyTagPhase(
            ips=ips,
            context=ctx,
            classify_step=classify_step,
            tagger_step=tagger_step,
        )
        r2 = phase2.run()

        assert r2.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "classifier") is not None
            assert reader.get_channel_data(ip, "tagger") is not None

        filtered = filter_ips_by_classification(ips, reader)
        assert set(filtered) == set(ips)

        phase3 = DeepQueryPhase(
            ips=filtered,
            context=ctx,
            aizhan_channel=FakeChannel(
                response={
                    "query_ip": "8.8.8.8",
                    "domains": [{"domain": "dns.google", "title": "Google DNS"}],
                    "domain_count": 1,
                }
            ),
            chinaz_channel=FakeChannel(
                response={
                    "query_ip": "8.8.8.8",
                    "domains": [{"domain": "dns.google"}],
                    "domain_count": 1,
                }
            ),
            fofa_channel=FakeChannel(),
            no_validate=True,
        )
        r3 = phase3.run()
        assert r3.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "aizhan") is not None
            assert reader.get_channel_data(ip, "chinaz") is not None

        def dns_run_fn():
            for ip in filtered:
                writer.add_or_update_ip(
                    ip,
                    "domain_verify",
                    {
                        "ip": ip,
                        "matched": 1,
                        "changed": 0,
                        "unresolved": 0,
                        "total_domains": 1,
                        "results": [
                            {
                                "domain": "example.com",
                                "status": "matched",
                                "verify_time": "2024-01-01T00:00:00",
                            },
                        ],
                    },
                )

        dns_step = FakeBatchStep(
            "domain_verify",
            BatchResult(success_count=len(filtered)),
        )
        dns_step._run_fn = dns_run_fn

        def port_scan_run_fn():
            for ip in filtered:
                writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]})
                if tracker:
                    tracker.mark_processed(ip, "port_scan")

        port_step = FakeBatchStep(
            "port_scan",
            BatchResult(success_count=len(filtered)),
        )
        port_step._run_fn = port_scan_run_fn

        phase4 = VerifyScanPhase(
            ips=filtered,
            context=ctx,
            steps=[dns_step, port_step],
        )
        r4 = phase4.run()

        assert r4.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "domain_verify") is not None
            assert reader.get_channel_data(ip, "port_scan") is not None

        assert tracker.is_processed("8.8.8.8", "ipinfo_api")
        assert tracker.is_processed("8.8.8.8", "aizhan")
        assert tracker.is_processed("8.8.8.8", "port_scan")

    def test_phase_execution_order(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.2.3.4"]
        execution_order = []

        phase1 = BasicCollectPhase(
            ips=ips,
            context=ctx,
            ipinfo_channel=FakeChannel(),
            rdns_channel=FakeChannel(),
            no_validate=True,
        )
        r1 = phase1.run()
        execution_order.append("phase1")
        assert r1.success is True

        def classify_run_fn():
            for ip in ips:
                writer.add_or_update_ip(
                    ip,
                    "classifier",
                    {
                        "ip": ip,
                        "category": "cloud_provider",
                        "label": "Cloud Provider",
                        "need_deep_query": True,
                        "matched_by": [{"field": "org", "pattern": "Cloud"}],
                    },
                )

        classify_step = FakeBatchStep(
            "classifier",
            BatchResult(success_count=len(ips)),
        )
        classify_step._run_fn = classify_run_fn

        def tagger_run_fn():
            for ip in ips:
                writer.add_or_update_ip(ip, "tagger", {"tags": ["cloud"]})

        tagger_step = FakeBatchStep(
            "tagger",
            BatchResult(success_count=len(ips)),
        )
        tagger_step._run_fn = tagger_run_fn

        phase2 = ClassifyTagPhase(
            ips=ips,
            context=ctx,
            classify_step=classify_step,
            tagger_step=tagger_step,
        )
        r2 = phase2.run()
        execution_order.append("phase2")
        assert r2.success is True

        phase3 = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=FakeChannel(),
            chinaz_channel=FakeChannel(),
            fofa_channel=FakeChannel(),
            no_validate=True,
        )
        r3 = phase3.run()
        execution_order.append("phase3")
        assert r3.success is True

        def dns_run_fn():
            for ip in ips:
                writer.add_or_update_ip(
                    ip,
                    "domain_verify",
                    {
                        "ip": ip,
                        "matched": 1,
                        "changed": 0,
                        "unresolved": 0,
                        "total_domains": 1,
                        "results": [
                            {
                                "domain": "example.com",
                                "status": "matched",
                                "verify_time": "2024-01-01T00:00:00",
                            },
                        ],
                    },
                )

        dns_step = FakeBatchStep(
            "domain_verify",
            BatchResult(success_count=len(ips)),
        )
        dns_step._run_fn = dns_run_fn

        def port_scan_run_fn():
            for ip in ips:
                writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]})

        port_step = FakeBatchStep(
            "port_scan",
            BatchResult(success_count=len(ips)),
        )
        port_step._run_fn = port_scan_run_fn

        phase4 = VerifyScanPhase(
            ips=ips,
            context=ctx,
            steps=[dns_step, port_step],
        )
        r4 = phase4.run()
        execution_order.append("phase4")
        assert r4.success is True

        assert execution_order == ["phase1", "phase2", "phase3", "phase4"]

    def test_data_accumulation_across_phases(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ip = "1.2.3.4"

        BasicCollectPhase(
            ips=[ip],
            context=ctx,
            ipinfo_channel=FakeChannel(),
            rdns_channel=FakeChannel(),
            no_validate=True,
        ).run()
        assert set(reader.list_ip_channels(ip)) == {"ipinfo_api", "rdns_ptr"}

        def classify_run_fn():
            writer.add_or_update_ip(
                ip,
                "classifier",
                {
                    "ip": ip,
                    "category": "cloud_provider",
                    "label": "Cloud Provider",
                    "need_deep_query": True,
                    "matched_by": [{"field": "org", "pattern": "Cloud"}],
                },
            )

        classify_step = FakeBatchStep("classifier", BatchResult(success_count=1))
        classify_step._run_fn = classify_run_fn

        def tagger_run_fn():
            writer.add_or_update_ip(ip, "tagger", {"tags": ["cloud"]})

        tagger_step = FakeBatchStep("tagger", BatchResult(success_count=1))
        tagger_step._run_fn = tagger_run_fn

        ClassifyTagPhase(
            ips=[ip],
            context=ctx,
            classify_step=classify_step,
            tagger_step=tagger_step,
        ).run()
        channels = set(reader.list_ip_channels(ip))
        assert "classifier" in channels
        assert "tagger" in channels

        DeepQueryPhase(
            ips=[ip],
            context=ctx,
            aizhan_channel=FakeChannel(),
            chinaz_channel=FakeChannel(),
            fofa_channel=FakeChannel(),
            no_validate=True,
        ).run()
        channels = set(reader.list_ip_channels(ip))
        assert "aizhan" in channels
        assert "chinaz" in channels
        assert "fofa_host" in channels

        def dns_run_fn():
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "total_domains": 1,
                    "results": [{"domain": "example.com", "status": "matched", "verify_time": "2024-01-01T00:00:00"}],
                },
            )

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=1))
        dns_step._run_fn = dns_run_fn

        def port_scan_run_fn():
            writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]})

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=1))
        port_step._run_fn = port_scan_run_fn

        VerifyScanPhase(
            ips=[ip],
            context=ctx,
            steps=[dns_step, port_step],
        ).run()
        channels = set(reader.list_ip_channels(ip))
        assert "domain_verify" in channels
        assert "port_scan" in channels

        ip_data = reader.get_ip_data(ip)
        assert len([k for k in ip_data if k != "ip"]) >= 8


def _run_live():
    import logging
    import os
    import time

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )

    from ip_info.channel.chinaz import ChinazChannel
    from ip_info.channel.ipinfo_api import IpinfoApiChannel
    from ip_info.channel.port_scan import PortScanChannel
    from ip_info.channel.rdns_ptr import RdnsPtrChannel
    from ip_info.store.json_store import IPReader, IPWriter
    from ip_info.store.sqlite_cache import SqliteDomainCache
    from ip_info.utils.load_ips import load_ips
    from ip_info.utils.progress import SqliteProgressTracker

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ip_file = os.path.join(project_root, "data", "live_test_ips.txt")
    storage = os.path.join(project_root, "data", "live_test_data.json")
    cache_db = os.path.join(project_root, "data", "live_domain_cache.db")
    progress_db = os.path.join(project_root, "data", "live_progress.db")

    os.makedirs(os.path.dirname(ip_file), exist_ok=True)
    with open(ip_file, "w") as f:
        f.write("8.8.8.8\n1.1.1.1\n")

    ips = load_ips(ip_file)
    writer = IPWriter(storage)
    reader = IPReader(storage)
    domain_cache = SqliteDomainCache(cache_db)
    tracker = SqliteProgressTracker(progress_db)

    ctx = PipelineContext(
        writer=writer,
        reader=reader,
        progress_tracker=tracker,
        domain_cache=domain_cache,
    )

    start = time.time()

    BasicCollectPhase(
        ips=ips,
        context=ctx,
        ipinfo_channel=IpinfoApiChannel(),
        rdns_channel=RdnsPtrChannel(),
    ).run()

    ClassifyTagPhase(ips=ips, context=ctx, rules_dir=RULES_DIR, tagger_config_dir=TAGGER_CONFIG_DIR).run()

    filtered = filter_ips_by_classification(ips, reader)
    if filtered:
        DeepQueryPhase(
            ips=filtered,
            context=ctx,
            aizhan_channel=ChinazChannel(),
            chinaz_channel=ChinazChannel(),
            fofa_channel=ChinazChannel(),
        ).run()
        VerifyScanPhase(
            ips=filtered,
            context=ctx,
            nmap_channel=PortScanChannel(),
        ).run()

    elapsed = time.time() - start
    print(f"\n全流程完成! 耗时: {elapsed:.1fs}")
    for ip in reader.list_all_ips():
        print(f"  {ip}: {reader.list_ip_channels(ip)}")

    for f in [ip_file, storage, cache_db, progress_db]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    if "--live" in sys.argv:
        _run_live()
    else:
        pytest.main([__file__, "-v"])
