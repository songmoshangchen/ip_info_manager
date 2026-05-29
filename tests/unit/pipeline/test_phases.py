from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import Phase
from ip_info.pipeline.trace_steps.phase1_basic import BasicCollectPhase
from ip_info.pipeline.trace_steps.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.trace_steps.phase3_deep import DeepQueryPhase
from ip_info.pipeline.trace_steps.phase4_verify_scan import VerifyScanPhase
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class FakeBatchStep:
    def __init__(
        self,
        name: str,
        result: BatchResult | None = None,
        writer=None,
        channel_name: str = "",
    ):
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


class FakeChannel(BaseChannelAdapter):
    channel_name = "fake"

    def __init__(self, *, disabled=False, default_delay=0, response=None, fail_validation=False):
        self.disabled = disabled
        self.default_delay = default_delay
        self._response = response or {"status": "ok"}
        self._fail_validation = fail_validation

    def _validate_key(self):
        if self._fail_validation:
            raise RuntimeError("validation failed")

    def _request(self, ip, **kwargs):
        return {"ip": ip, **self._response}

    def fetch(self, ip, **kwargs):
        raw = self._request(ip, **kwargs)
        result = self._parse(raw, ip)
        result.setdefault("query_time", "2024-01-01T00:00:00")
        return result


def _make_context(writer=None, reader=None, tracker=None, domain_cache=None):
    w = writer or InMemoryIPWriter()
    r = reader or InMemoryIPReader(data=w._store)
    return PipelineContext(
        writer=w,
        reader=r,
        progress_tracker=tracker or InMemoryProgressTracker(),
        domain_cache=domain_cache,
    )


class TestDeepQueryPhase:
    def test_normal_execution(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel(response={"source": "aizhan"})
        chinaz = FakeChannel(response={"source": "chinaz"})
        fofa = FakeChannel(response={"source": "fofa"})
        ips = ["1.2.3.4", "5.6.7.8"]

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "aizhan") is not None
            assert reader.get_channel_data(ip, "chinaz") is not None
            assert reader.get_channel_data(ip, "fofa_host") is not None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=[],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )

        result = phase.run()
        assert result.success is True
        assert "无 IP 需深度查询" in result.message

    def test_partial_channel_disabled(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel(disabled=True, response={"source": "aizhan"})
        chinaz = FakeChannel(response={"source": "chinaz"})
        fofa = FakeChannel(response={"source": "fofa"})
        ips = ["1.2.3.4"]

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.2.3.4", "aizhan") is None
        assert reader.get_channel_data("1.2.3.4", "chinaz") is not None
        assert reader.get_channel_data("1.2.3.4", "fofa_host") is not None

    def test_phase_protocol(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
        )

        assert isinstance(phase, Phase)
        assert phase.name == "深度查询"

    def test_delay_auto_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel(default_delay=2.0)
        chinaz = FakeChannel(default_delay=2.0)
        fofa = FakeChannel(default_delay=2.0)

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.2.3.4", "aizhan") is not None
        assert reader.get_channel_data("1.2.3.4", "chinaz") is not None
        assert reader.get_channel_data("1.2.3.4", "fofa_host") is not None

    def test_progress_tracker_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        phase.run()

        assert tracker.is_processed("1.2.3.4", "aizhan")
        assert tracker.is_processed("1.2.3.4", "chinaz")
        assert tracker.is_processed("1.2.3.4", "fofa_host")

    def test_disabled_channel_logs_pending_count(self, caplog):
        aizhan = FakeChannel(disabled=True)
        chinaz = FakeChannel()
        fofa = FakeChannel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "aizhan" in r.message
            and "共 3 个 IP" in r.message
            and "已有结果 0" in r.message
            and "剩余 3 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_with_existing_results(self, caplog):
        aizhan = FakeChannel(disabled=True)
        chinaz = FakeChannel()
        fofa = FakeChannel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.2.3.4", "aizhan")
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "aizhan" in r.message and "已有结果 1" in r.message and "剩余 2 未查询" in r.message for r in caplog.records
        )

    def test_skip_ips_excludes_from_all_channels(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
        skip = {"5.6.7.8"}

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
            skip_ips=skip,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("5.6.7.8", "aizhan") is None
        assert reader.get_channel_data("5.6.7.8", "chinaz") is None
        assert reader.get_channel_data("5.6.7.8", "fofa_host") is None
        assert reader.get_channel_data("1.2.3.4", "aizhan") is not None
        assert reader.get_channel_data("9.10.11.12", "aizhan") is not None

    def test_skip_ips_logs_count(self, caplog):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
        skip = {"5.6.7.8", "9.10.11.12"}

        phase = DeepQueryPhase(
            ips=ips,
            context=ctx,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
            skip_ips=skip,
        )

        with caplog.at_level("INFO"):
            phase.run()

        assert any("跳过 2 个动态 IP" in r.message for r in caplog.records)


class TestVerifyScanPhase:
    def test_dns_and_nmap_run_in_parallel(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.1.1.1", "2.2.2.2"]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=len(ips)))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=len(ips)))
        port_step._run_fn = lambda: [writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]}) for ip in ips]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step, port_step])
        result = phase.run()

        assert result.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "domain_verify") is not None
            assert reader.get_channel_data(ip, "port_scan") is not None

    def test_empty_ip_list(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        phase = VerifyScanPhase(ips=[], context=ctx, steps=[FakeBatchStep("domain_verify")])
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需验证/扫描"

    def test_no_domain_cache(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader, domain_cache=None)
        ips = ["1.1.1.1"]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=1))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step])
        phase.run()

        assert reader.get_channel_data("1.1.1.1", "domain_verify") is not None

    def test_phase_protocol(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        phase = VerifyScanPhase(ips=[], context=ctx, steps=[FakeBatchStep("domain_verify")])
        assert isinstance(phase, Phase)

    def test_delay_auto_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.1.1.1"]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=1))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=1))
        port_step._run_fn = lambda: [writer.add_or_update_ip(ip, "port_scan", {"ports": [80]}) for ip in ips]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step, port_step])
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.1.1.1", "port_scan") is not None

    def test_progress_tracker_passed(self):
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()
        ctx = _make_context(writer=writer, tracker=tracker)
        ips = ["1.1.1.1"]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=1))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=1))
        port_step._run_fn = lambda: [
            (
                writer.add_or_update_ip(ip, "port_scan", {"ports": [80]}),
                tracker.mark_processed(ip, "port_scan"),
            )
            for ip in ips
        ]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step, port_step])
        phase.run()

        assert tracker.is_processed("1.1.1.1", "port_scan")

    def test_skip_ips_excludes_from_port_scan_only(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}
        scan_ips = [ip for ip in ips if ip not in skip]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=len(ips)))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=len(scan_ips)))
        port_step._run_fn = lambda: [writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]}) for ip in scan_ips]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step, port_step], skip_ips=skip)
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.1.1.1", "domain_verify") is not None
        assert reader.get_channel_data("2.2.2.2", "domain_verify") is not None
        assert reader.get_channel_data("3.3.3.3", "domain_verify") is not None
        assert reader.get_channel_data("1.1.1.1", "port_scan") is not None
        assert reader.get_channel_data("2.2.2.2", "port_scan") is None
        assert reader.get_channel_data("3.3.3.3", "port_scan") is None

    def test_skip_ips_logs_count(self, caplog):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}
        scan_ips = [ip for ip in ips if ip not in skip]

        dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=len(ips)))
        dns_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "domain_verify",
                {
                    "ip": ip,
                    "matched": 1,
                    "changed": 0,
                    "unresolved": 0,
                    "results": [{"domain": "example.com", "verify_time": "2024-01-01T00:00:00"}],
                },
            )
            for ip in ips
        ]

        port_step = FakeBatchStep("port_scan", BatchResult(success_count=len(scan_ips)))
        port_step._run_fn = lambda: [writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]}) for ip in scan_ips]

        phase = VerifyScanPhase(ips=ips, context=ctx, steps=[dns_step, port_step], skip_ips=skip)

        with caplog.at_level("INFO"):
            phase.run()

        assert any("跳过 2 个动态 IP" in r.message for r in caplog.records)


class TestBasicCollectPhase:
    def test_normal_execution(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert reader.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=[],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需处理"

    def test_one_channel_disabled(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel(fail_validation=True)
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert reader.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_both_channels_disabled(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel(fail_validation=True)
        rdns_channel = FakeChannel(fail_validation=True)

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is False

    def test_phase_protocol_conformance(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        assert isinstance(phase, Phase)

    def test_delay_auto_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ipinfo_channel = FakeChannel(default_delay=1.2)
        rdns_channel = FakeChannel(default_delay=0.1)

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert reader.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_progress_tracker_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )
        phase.run()

        assert tracker.is_processed("1.2.3.4", "ipinfo_api")
        assert tracker.is_processed("1.2.3.4", "rdns_ptr")

    def test_channel_level_resume(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        tracker.mark_processed("1.2.3.4", "ipinfo_api")

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )
        phase.run()

        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert reader.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_disabled_channel_logs_pending_count_ipinfo(self, caplog):
        ipinfo_channel = FakeChannel(disabled=True)
        rdns_channel = FakeChannel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = BasicCollectPhase(
            ips=ips,
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "共 3 个 IP" in r.message and "已有结果 0" in r.message and "剩余 3 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_with_existing_results(self, caplog):
        ipinfo_channel = FakeChannel(disabled=True)
        rdns_channel = FakeChannel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.2.3.4", "ipinfo_api")
        ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = BasicCollectPhase(
            ips=ips,
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "ipinfo_api" in r.message and "已有结果 1" in r.message and "剩余 2 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_rdns(self, caplog):
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel(disabled=True)
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)
        ips = ["1.2.3.4", "5.6.7.8"]

        phase = BasicCollectPhase(
            ips=ips,
            context=ctx,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "共 2 个 IP" in r.message and "已有结果 0" in r.message and "剩余 2 未查询" in r.message
            for r in caplog.records
        )


class TestClassifyTagPhase:
    def test_normal_execution(self):
        ips = ["1.2.3.4", "5.6.7.8"]
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        classify_step = FakeBatchStep("classifier", BatchResult(success_count=len(ips)))
        classify_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "classifier",
                {
                    "ip": ip,
                    "category": "cloud_provider",
                    "label": "Cloud",
                    "need_deep_query": True,
                    "matched_by": [],
                },
            )
            for ip in ips
        ]

        tagger_step = FakeBatchStep("tagger", BatchResult(success_count=len(ips)))
        tagger_step._run_fn = lambda: [writer.add_or_update_ip(ip, "tagger", {"tags": ["cloud"]}) for ip in ips]

        phase = ClassifyTagPhase(ips=ips, context=ctx, classify_step=classify_step, tagger_step=tagger_step)
        result = phase.run()

        assert result.success is True
        assert "分类" in result.message
        assert "标签" in result.message
        for ip in ips:
            assert reader.get_channel_data(ip, "classifier") is not None
            assert reader.get_channel_data(ip, "tagger") is not None

    def test_no_tagger(self):
        ips = ["1.2.3.4", "5.6.7.8"]
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        classify_step = FakeBatchStep("classifier", BatchResult(success_count=len(ips)))
        classify_step._run_fn = lambda: [
            writer.add_or_update_ip(
                ip,
                "classifier",
                {
                    "ip": ip,
                    "category": "cloud_provider",
                    "label": "Cloud",
                    "need_deep_query": True,
                    "matched_by": [],
                },
            )
            for ip in ips
        ]

        phase = ClassifyTagPhase(
            ips=ips,
            context=ctx,
            classify_step=classify_step,
            tagger_step=None,
            no_tagger=True,
        )
        result = phase.run()

        assert result.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "classifier") is not None
            assert reader.get_channel_data(ip, "tagger") is None
        assert result.data["tagger_result"] is None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        classify_step = FakeBatchStep("classifier")
        tagger_step = FakeBatchStep("tagger")

        phase = ClassifyTagPhase(ips=[], context=ctx, classify_step=classify_step, tagger_step=tagger_step)
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需分类"
        assert len(reader.list_all_ips()) == 0

    def test_phase_protocol(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ctx = _make_context(writer=writer, reader=reader)

        phase = ClassifyTagPhase(
            ips=["1.2.3.4"],
            context=ctx,
            classify_step=FakeBatchStep("classifier"),
            tagger_step=FakeBatchStep("tagger"),
        )

        assert isinstance(phase, Phase)
        assert phase.name == "分类与标签"
