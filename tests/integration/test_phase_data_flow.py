from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.filter_ips import filter_dynamic_ips, filter_ips_by_classification
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


def _run_phase1(ips, writer, reader, tracker=None):
    ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
    phase = BasicCollectPhase(
        ips=ips,
        context=ctx,
        ipinfo_channel=FakeChannel(response={"country": "US", "org": "Test Corp"}),
        rdns_channel=FakeChannel(response={"ptr": "test.example.com"}),
        no_validate=True,
    )
    return phase.run()


def _run_phase2(ips, writer, reader, classify_fn, tagger=True):
    ctx = _make_context(writer=writer, reader=reader)

    def classify_run():
        for ip in ips:
            result = classify_fn(ip)
            writer.add_or_update_ip(ip, "classifier", result)
        return BatchResult(success_count=len(ips))

    classify_step = FakeBatchStep("classifier", BatchResult(success_count=len(ips)))
    classify_step._run_fn = classify_run

    tagger_step = None
    if tagger:

        def tagger_run():
            for ip in ips:
                writer.add_or_update_ip(ip, "tagger", {"tags": ["tagged"]})
            return BatchResult(success_count=len(ips))

        tagger_step = FakeBatchStep("tagger", BatchResult(success_count=len(ips)))
        tagger_step._run_fn = tagger_run

    phase = ClassifyTagPhase(
        ips=ips,
        context=ctx,
        classify_step=classify_step,
        tagger_step=tagger_step,
    )
    return phase.run()


def _run_phase3(ips, writer, reader, skip_ips=None, tracker=None):
    ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
    phase = DeepQueryPhase(
        ips=ips,
        context=ctx,
        aizhan_channel=FakeChannel(response={"domain": "aizhan.example.com"}),
        chinaz_channel=FakeChannel(response={"domain": "chinaz.example.com"}),
        fofa_channel=FakeChannel(response={"domain": "fofa.example.com"}),
        no_validate=True,
        skip_ips=skip_ips,
    )
    return phase.run()


def _run_phase4(ips, writer, reader, skip_ips=None, tracker=None):
    ctx = _make_context(writer=writer, reader=reader, tracker=tracker)
    scan_ips = [ip for ip in ips if ip not in (skip_ips or set())]

    def dns_run():
        for ip in ips:
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
        return BatchResult(success_count=len(ips))

    dns_step = FakeBatchStep("domain_verify", BatchResult(success_count=len(ips)))
    dns_step._run_fn = dns_run

    def port_scan_run():
        for ip in scan_ips:
            writer.add_or_update_ip(ip, "port_scan", {"ports": [80, 443]})
            if tracker:
                tracker.mark_processed(ip, "port_scan")
        return BatchResult(success_count=len(scan_ips))

    port_step = FakeBatchStep("port_scan", BatchResult(success_count=len(scan_ips)))
    port_step._run_fn = port_scan_run

    phase = VerifyScanPhase(
        ips=ips,
        context=ctx,
        steps=[dns_step, port_step],
        skip_ips=skip_ips,
    )
    return phase.run()


class TestFullPipelineDataFlow:
    def test_phase1_to_phase4_full_flow(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ips = ["1.2.3.4", "5.6.7.8"]

        def classify_as_cloud(ip):
            return {
                "ip": ip,
                "category": "cloud_provider",
                "label": "Cloud Provider",
                "need_deep_query": True,
                "matched_by": [{"field": "org", "pattern": "Test Corp"}],
            }

        r1 = _run_phase1(ips, writer, reader, tracker)
        assert r1.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "ipinfo_api") is not None
            assert reader.get_channel_data(ip, "rdns_ptr") is not None

        r2 = _run_phase2(ips, writer, reader, classify_as_cloud)
        assert r2.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "classifier") is not None
            assert reader.get_channel_data(ip, "tagger") is not None

        filtered = filter_ips_by_classification(ips, reader)
        assert set(filtered) == set(ips)

        r3 = _run_phase3(filtered, writer, reader, tracker=tracker)
        assert r3.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "aizhan") is not None
            assert reader.get_channel_data(ip, "chinaz") is not None
            assert reader.get_channel_data(ip, "fofa_host") is not None

        r4 = _run_phase4(filtered, writer, reader, tracker=tracker)
        assert r4.success is True
        for ip in ips:
            assert reader.get_channel_data(ip, "domain_verify") is not None
            assert reader.get_channel_data(ip, "port_scan") is not None

        assert tracker.is_processed("1.2.3.4", "ipinfo_api")
        assert tracker.is_processed("1.2.3.4", "rdns_ptr")
        assert tracker.is_processed("1.2.3.4", "aizhan")
        assert tracker.is_processed("1.2.3.4", "port_scan")

    def test_classifier_result_carried_across_phases(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4"]

        _run_phase1(ips, writer, reader)

        def classify_as_cloud(ip):
            return {
                "ip": ip,
                "category": "cloud_provider",
                "label": "Cloud Provider",
                "need_deep_query": True,
                "matched_by": [{"field": "org", "pattern": "Cloud"}],
            }

        _run_phase2(ips, writer, reader, classify_as_cloud)

        classifier_data = reader.get_channel_data("1.2.3.4", "classifier")
        assert classifier_data["category"] == "cloud_provider"
        assert classifier_data["need_deep_query"] is True

        filtered = filter_ips_by_classification(ips, reader)
        assert "1.2.3.4" in filtered


class TestClassificationFilterFlow:
    def test_invalid_rdns_excluded_from_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4", "5.6.7.8"]

        _run_phase1(ips, writer, reader)

        def classify_mixed(ip):
            if ip == "1.2.3.4":
                return {
                    "ip": ip,
                    "category": "cloud_provider",
                    "label": "Cloud",
                    "need_deep_query": True,
                    "matched_by": [],
                }
            return {
                "ip": ip,
                "category": "invalid_rdns",
                "label": "Invalid RDNS",
                "need_deep_query": False,
                "matched_by": [],
            }

        _run_phase2(ips, writer, reader, classify_mixed)

        assert reader.get_channel_data("5.6.7.8", "classifier")["category"] == "invalid_rdns"

        filtered = filter_ips_by_classification(ips, reader)
        assert "1.2.3.4" in filtered
        assert "5.6.7.8" not in filtered

        _run_phase3(filtered, writer, reader)

        assert reader.get_channel_data("1.2.3.4", "aizhan") is not None
        assert reader.get_channel_data("5.6.7.8", "aizhan") is None

    def test_cdn_excluded_from_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.1.1.1"]

        _run_phase1(ips, writer, reader)

        def classify_as_cdn(ip):
            return {
                "ip": ip,
                "category": "cdn",
                "label": "CDN",
                "need_deep_query": False,
                "matched_by": [],
            }

        _run_phase2(ips, writer, reader, classify_as_cdn)

        filtered = filter_ips_by_classification(ips, reader)
        assert len(filtered) == 0


class TestDynamicIpSkipFlow:
    def test_dynamic_ip_skipped_in_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        _run_phase1(ips, writer, reader)

        def classify_with_dynamic(ip):
            if ip == "5.6.7.8":
                return {
                    "ip": ip,
                    "category": "residential",
                    "label": "Dynamic",
                    "need_deep_query": True,
                    "matched_by": [{"field": "ptr", "pattern": "dynamic-broadband.isp.com"}],
                }
            if ip == "9.10.11.12":
                return {
                    "ip": ip,
                    "category": "residential",
                    "label": "Dynamic",
                    "need_deep_query": True,
                    "matched_by": [{"field": "ptr", "pattern": "pppoe-pool.provider.net"}],
                }
            return {
                "ip": ip,
                "category": "cloud_provider",
                "label": "Cloud",
                "need_deep_query": True,
                "matched_by": [],
            }

        _run_phase2(ips, writer, reader, classify_with_dynamic)

        dynamic_ips, non_dynamic_ips = filter_dynamic_ips(ips, reader)
        assert set(dynamic_ips) == {"5.6.7.8", "9.10.11.12"}
        assert non_dynamic_ips == ["1.2.3.4"]

        skip_set = set(dynamic_ips)
        _run_phase3(non_dynamic_ips, writer, reader, skip_ips=skip_set)

        assert reader.get_channel_data("1.2.3.4", "aizhan") is not None
        assert reader.get_channel_data("5.6.7.8", "aizhan") is None
        assert reader.get_channel_data("9.10.11.12", "aizhan") is None

    def test_dynamic_ip_dns_still_runs(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4", "5.6.7.8"]

        _run_phase1(ips, writer, reader)

        def classify_one_dynamic(ip):
            if ip == "5.6.7.8":
                return {
                    "ip": ip,
                    "category": "residential",
                    "label": "Dynamic",
                    "need_deep_query": True,
                    "matched_by": [{"field": "ptr", "pattern": "dhcp-pool.isp.com"}],
                }
            return {
                "ip": ip,
                "category": "cloud_provider",
                "label": "Cloud",
                "need_deep_query": True,
                "matched_by": [],
            }

        _run_phase2(ips, writer, reader, classify_one_dynamic)

        dynamic_ips, _ = filter_dynamic_ips(ips, reader)
        skip_set = set(dynamic_ips)

        _run_phase3(ips, writer, reader, skip_ips=skip_set)
        _run_phase4(ips, writer, reader, skip_ips=skip_set)

        assert reader.get_channel_data("5.6.7.8", "domain_verify") is not None
        assert reader.get_channel_data("5.6.7.8", "port_scan") is None
        assert reader.get_channel_data("1.2.3.4", "domain_verify") is not None
        assert reader.get_channel_data("1.2.3.4", "port_scan") is not None


class TestResumeFlow:
    def test_partial_data_only_processes_remaining(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4", "5.6.7.8"]

        writer.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "US"})
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"ptr": "test.com"})

        r1 = _run_phase1(ips, writer, reader)
        assert r1.success is True

        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert reader.get_channel_data("5.6.7.8", "ipinfo_api") is not None
        assert reader.get_channel_data("5.6.7.8", "rdns_ptr") is not None

    def test_tracker_prevents_reprocessing(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        tracker = InMemoryProgressTracker()
        ips = ["1.2.3.4", "5.6.7.8"]

        tracker.mark_processed("1.2.3.4", "ipinfo_api")
        tracker.mark_processed("1.2.3.4", "rdns_ptr")

        _run_phase1(ips, writer, reader, tracker)

        assert reader.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert reader.get_channel_data("5.6.7.8", "ipinfo_api") is not None
        assert reader.get_channel_data("5.6.7.8", "rdns_ptr") is not None

    def test_no_classifier_data_ip_kept_in_flow(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        ips = ["1.2.3.4"]

        _run_phase1(ips, writer, reader)

        filtered = filter_ips_by_classification(ips, reader)
        assert "1.2.3.4" in filtered
