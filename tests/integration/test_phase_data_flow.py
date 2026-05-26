from unittest.mock import MagicMock, patch

from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.filter_ips import filter_dynamic_ips, filter_ips_by_classification
from ip_info.pipeline.phases.phase1_basic import BasicCollectPhase
from ip_info.pipeline.phases.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.phases.phase3_deep import DeepQueryPhase
from ip_info.pipeline.phases.phase4_verify_scan import VerifyScanPhase
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


def _create_classifier_mock(writer, ips, classify_fn):
    mock = MagicMock()

    def fake_run():
        for ip in ips:
            result = classify_fn(ip)
            writer.add_or_update_ip(ip, "classifier", result)
        return BatchResult(success_count=len(ips))

    mock.run = fake_run
    return mock


def _create_tagger_mock(writer, ips):
    mock = MagicMock()

    def fake_run():
        for ip in ips:
            writer.add_or_update_ip(ip, "tagger", {"tags": ["tagged"]})
        return BatchResult(success_count=len(ips))

    mock.run = fake_run
    return mock


def _create_dns_mock(writer, ips):
    mock = MagicMock()

    def fake_run():
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

    mock.run = fake_run
    return mock


def _run_phase1(ips, writer, reader, tracker=None):
    phase = BasicCollectPhase(
        ips=ips,
        writer=writer,
        reader=reader,
        ipinfo_channel=FakeChannel(response={"country": "US", "org": "Test Corp"}),
        rdns_channel=FakeChannel(response={"ptr": "test.example.com"}),
        no_validate=True,
        progress_tracker=tracker,
    )
    return phase.run()


def _run_phase2(ips, writer, reader, classify_fn, tagger=True):
    with (
        patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
        patch("ip_info.pipeline.phases.phase2_classify.BatchTagger") as MockTagger,
    ):
        MockClassifier.return_value = _create_classifier_mock(writer, ips, classify_fn)
        if tagger:
            MockTagger.return_value = _create_tagger_mock(writer, ips)

        phase = ClassifyTagPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            rules_dir=RULES_DIR,
            tagger_config_dir=TAGGER_CONFIG_DIR,
            no_tagger=not tagger,
        )
        return phase.run()


def _run_phase3(ips, writer, reader, skip_ips=None, tracker=None):
    phase = DeepQueryPhase(
        ips=ips,
        writer=writer,
        reader=reader,
        aizhan_channel=FakeChannel(response={"domain": "aizhan.example.com"}),
        chinaz_channel=FakeChannel(response={"domain": "chinaz.example.com"}),
        fofa_channel=FakeChannel(response={"domain": "fofa.example.com"}),
        no_validate=True,
        skip_ips=skip_ips,
        progress_tracker=tracker,
    )
    return phase.run()


def _run_phase4(ips, writer, reader, skip_ips=None, tracker=None):
    with patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify") as MockDns:
        MockDns.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        phase = VerifyScanPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            nmap_channel=FakeChannel(response={"ports": [80, 443]}),
            no_validate=True,
            skip_ips=skip_ips,
            progress_tracker=tracker,
        )
        return phase.run()


class TestFullPipelineDataFlow:
    def test_phase1_to_phase4_full_flow(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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
            assert writer.get_channel_data(ip, "ipinfo_api") is not None
            assert writer.get_channel_data(ip, "rdns_ptr") is not None

        r2 = _run_phase2(ips, writer, reader, classify_as_cloud)
        assert r2.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "classifier") is not None
            assert writer.get_channel_data(ip, "tagger") is not None

        filtered = filter_ips_by_classification(ips, reader)
        assert set(filtered) == set(ips)

        r3 = _run_phase3(filtered, writer, reader, tracker=tracker)
        assert r3.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "aizhan") is not None
            assert writer.get_channel_data(ip, "chinaz") is not None
            assert writer.get_channel_data(ip, "fofa_host") is not None

        r4 = _run_phase4(filtered, writer, reader, tracker=tracker)
        assert r4.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "domain_verify") is not None
            assert writer.get_channel_data(ip, "port_scan") is not None

        assert tracker.is_processed("1.2.3.4", "ipinfo_api")
        assert tracker.is_processed("1.2.3.4", "rdns_ptr")
        assert tracker.is_processed("1.2.3.4", "aizhan")
        assert tracker.is_processed("1.2.3.4", "port_scan")

    def test_classifier_result_carried_across_phases(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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

        classifier_data = writer.get_channel_data("1.2.3.4", "classifier")
        assert classifier_data["category"] == "cloud_provider"
        assert classifier_data["need_deep_query"] is True

        filtered = filter_ips_by_classification(ips, writer)
        assert "1.2.3.4" in filtered


class TestClassificationFilterFlow:
    def test_invalid_rdns_excluded_from_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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

        assert writer.get_channel_data("5.6.7.8", "classifier")["category"] == "invalid_rdns"

        filtered = filter_ips_by_classification(ips, writer)
        assert "1.2.3.4" in filtered
        assert "5.6.7.8" not in filtered

        _run_phase3(filtered, writer, reader)

        assert writer.get_channel_data("1.2.3.4", "aizhan") is not None
        assert writer.get_channel_data("5.6.7.8", "aizhan") is None

    def test_cdn_excluded_from_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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

        filtered = filter_ips_by_classification(ips, writer)
        assert len(filtered) == 0


class TestDynamicIpSkipFlow:
    def test_dynamic_ip_skipped_in_deep_query(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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

        dynamic_ips, non_dynamic_ips = filter_dynamic_ips(ips, writer)
        assert set(dynamic_ips) == {"5.6.7.8", "9.10.11.12"}
        assert non_dynamic_ips == ["1.2.3.4"]

        skip_set = set(dynamic_ips)
        _run_phase3(non_dynamic_ips, writer, reader, skip_ips=skip_set)

        assert writer.get_channel_data("1.2.3.4", "aizhan") is not None
        assert writer.get_channel_data("5.6.7.8", "aizhan") is None
        assert writer.get_channel_data("9.10.11.12", "aizhan") is None

    def test_dynamic_ip_dns_still_runs(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
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

        dynamic_ips, _ = filter_dynamic_ips(ips, writer)
        skip_set = set(dynamic_ips)

        _run_phase3(ips, writer, reader, skip_ips=skip_set)
        _run_phase4(ips, writer, reader, skip_ips=skip_set)

        assert writer.get_channel_data("5.6.7.8", "domain_verify") is not None
        assert writer.get_channel_data("5.6.7.8", "port_scan") is None
        assert writer.get_channel_data("1.2.3.4", "domain_verify") is not None
        assert writer.get_channel_data("1.2.3.4", "port_scan") is not None


class TestResumeFlow:
    def test_partial_data_only_processes_remaining(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ips = ["1.2.3.4", "5.6.7.8"]

        writer.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "US"})
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"ptr": "test.com"})

        r1 = _run_phase1(ips, writer, reader)
        assert r1.success is True

        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert writer.get_channel_data("5.6.7.8", "ipinfo_api") is not None
        assert writer.get_channel_data("5.6.7.8", "rdns_ptr") is not None

    def test_tracker_prevents_reprocessing(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()
        ips = ["1.2.3.4", "5.6.7.8"]

        tracker.mark_processed("1.2.3.4", "ipinfo_api")
        tracker.mark_processed("1.2.3.4", "rdns_ptr")

        _run_phase1(ips, writer, reader, tracker)

        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert writer.get_channel_data("5.6.7.8", "ipinfo_api") is not None
        assert writer.get_channel_data("5.6.7.8", "rdns_ptr") is not None

    def test_no_classifier_data_ip_kept_in_flow(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ips = ["1.2.3.4"]

        _run_phase1(ips, writer, reader)

        filtered = filter_ips_by_classification(ips, writer)
        assert "1.2.3.4" in filtered
