from unittest.mock import MagicMock, patch

from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.phase import Phase
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


def _create_dns_mock(writer, ips):
    mock = MagicMock()

    def fake_run():
        for ip in ips:
            writer.add_or_update_ip(ip, "domain_verify", {"ip": ip, "verified": True})
        return BatchResult(success_count=len(ips))

    mock.run = fake_run
    return mock


def _create_classifier_mock(writer, ips):
    mock = MagicMock()

    def fake_run():
        for ip in ips:
            writer.add_or_update_ip(ip, "classifier", {"ip": ip, "category": "test"})
        return BatchResult(success_count=len(ips))

    mock.run = fake_run
    return mock


def _create_tagger_mock(writer, ips):
    mock = MagicMock()

    def fake_run():
        for ip in ips:
            writer.add_or_update_ip(ip, "tagger", {"ip": ip, "tags": ["test"]})
        return BatchResult(success_count=len(ips))

    mock.run = fake_run
    return mock


class TestDeepQueryPhase:
    def test_normal_execution(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel(response={"source": "aizhan"})
        chinaz = FakeChannel(response={"source": "chinaz"})
        fofa = FakeChannel(response={"source": "fofa"})
        ips = ["1.2.3.4", "5.6.7.8"]

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "aizhan") is not None
            assert writer.get_channel_data(ip, "chinaz") is not None
            assert writer.get_channel_data(ip, "fofa_host") is not None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=[],
            writer=writer,
            reader=reader,
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
        reader = InMemoryIPReader()
        aizhan = FakeChannel(disabled=True, response={"source": "aizhan"})
        chinaz = FakeChannel(response={"source": "chinaz"})
        fofa = FakeChannel(response={"source": "fofa"})
        ips = ["1.2.3.4"]

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.2.3.4", "aizhan") is None
        assert writer.get_channel_data("1.2.3.4", "chinaz") is not None
        assert writer.get_channel_data("1.2.3.4", "fofa_host") is not None

    def test_phase_protocol(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
        )

        assert isinstance(phase, Phase)
        assert phase.name == "深度查询"

    def test_delay_auto_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel(default_delay=2.0)
        chinaz = FakeChannel(default_delay=2.0)
        fofa = FakeChannel(default_delay=2.0)

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.2.3.4", "aizhan") is not None
        assert writer.get_channel_data("1.2.3.4", "chinaz") is not None
        assert writer.get_channel_data("1.2.3.4", "fofa_host") is not None

    def test_progress_tracker_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
            progress_tracker=tracker,
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
        reader = InMemoryIPReader()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
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
        reader = InMemoryIPReader(
            data={
                "1.2.3.4": {"ip": "1.2.3.4", "aizhan": {"data": "test"}},
            }
        )
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
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
            and "已有结果 1" in r.message
            and "剩余 2 未查询" in r.message
            for r in caplog.records
        )

    def test_skip_ips_excludes_from_all_channels(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
        skip = {"5.6.7.8"}

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
            skip_ips=skip,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("5.6.7.8", "aizhan") is None
        assert writer.get_channel_data("5.6.7.8", "chinaz") is None
        assert writer.get_channel_data("5.6.7.8", "fofa_host") is None
        assert writer.get_channel_data("1.2.3.4", "aizhan") is not None
        assert writer.get_channel_data("9.10.11.12", "aizhan") is not None

    def test_skip_ips_logs_count(self, caplog):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = FakeChannel()
        chinaz = FakeChannel()
        fofa = FakeChannel()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
        skip = {"5.6.7.8", "9.10.11.12"}

        phase = DeepQueryPhase(
            ips=ips,
            writer=writer,
            reader=reader,
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
    def _make_phase(self, ips=None, writer=None, nmap_channel=None, **kwargs):
        return VerifyScanPhase(
            ips=ips if ips is not None else ["1.1.1.1", "2.2.2.2"],
            writer=writer or InMemoryIPWriter(),
            reader=InMemoryIPReader(),
            nmap_channel=nmap_channel or FakeChannel(),
            **kwargs,
        )

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_dns_and_nmap_run_in_parallel(self, MockBatchDnsVerify):
        writer = InMemoryIPWriter()
        ips = ["1.1.1.1", "2.2.2.2"]

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        nmap_channel = FakeChannel(response={"ports": [80, 443]})
        phase = self._make_phase(ips=ips, writer=writer, nmap_channel=nmap_channel, no_validate=True)
        result = phase.run()

        assert result.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "domain_verify") is not None
            assert writer.get_channel_data(ip, "port_scan") is not None

    def test_empty_ip_list(self):
        phase = self._make_phase(ips=[])
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需验证/扫描"

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_no_domain_cache(self, MockBatchDnsVerify):
        writer = InMemoryIPWriter()

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        phase = self._make_phase(ips=["1.1.1.1"], writer=writer, domain_cache=None, no_validate=True)
        phase.run()

        assert writer.get_channel_data("1.1.1.1", "domain_verify") is not None

    def test_phase_protocol(self):
        phase = self._make_phase(ips=[])
        assert isinstance(phase, Phase)

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_delay_auto_passed(self, MockBatchDnsVerify):
        writer = InMemoryIPWriter()

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        nmap_channel = FakeChannel(default_delay=0.5, response={"ports": [80]})
        phase = self._make_phase(ips=["1.1.1.1"], writer=writer, nmap_channel=nmap_channel, no_validate=True)
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.1.1.1", "port_scan") is not None

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_progress_tracker_passed(self, MockBatchDnsVerify):
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        nmap_channel = FakeChannel()
        phase = self._make_phase(
            ips=["1.1.1.1"],
            writer=writer,
            nmap_channel=nmap_channel,
            no_validate=True,
            progress_tracker=tracker,
        )
        phase.run()

        assert tracker.is_processed("1.1.1.1", "port_scan")

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_skip_ips_excludes_from_port_scan_only(self, MockBatchDnsVerify):
        writer = InMemoryIPWriter()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        nmap_channel = FakeChannel()
        phase = self._make_phase(
            ips=ips,
            writer=writer,
            nmap_channel=nmap_channel,
            no_validate=True,
            skip_ips=skip,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.1.1.1", "domain_verify") is not None
        assert writer.get_channel_data("2.2.2.2", "domain_verify") is not None
        assert writer.get_channel_data("3.3.3.3", "domain_verify") is not None
        assert writer.get_channel_data("1.1.1.1", "port_scan") is not None
        assert writer.get_channel_data("2.2.2.2", "port_scan") is None
        assert writer.get_channel_data("3.3.3.3", "port_scan") is None

    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_skip_ips_logs_count(self, MockBatchDnsVerify, caplog):
        writer = InMemoryIPWriter()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}

        MockBatchDnsVerify.side_effect = lambda *a, **kw: _create_dns_mock(writer, kw.get("ips", []))

        nmap_channel = FakeChannel()
        phase = self._make_phase(
            ips=ips,
            writer=writer,
            nmap_channel=nmap_channel,
            no_validate=True,
            skip_ips=skip,
        )

        with caplog.at_level("INFO"):
            phase.run()

        assert any("跳过 2 个动态 IP" in r.message for r in caplog.records)


class TestBasicCollectPhase:
    def test_normal_execution(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert writer.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=[],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需处理"

    def test_one_channel_disabled(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel(fail_validation=True)
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert writer.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_both_channels_disabled(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel(fail_validation=True)
        rdns_channel = FakeChannel(fail_validation=True)

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        result = phase.run()

        assert result.success is False

    def test_phase_protocol_conformance(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        assert isinstance(phase, Phase)

    def test_delay_auto_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ipinfo_channel = FakeChannel(default_delay=1.2)
        rdns_channel = FakeChannel(default_delay=0.1)

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )
        result = phase.run()

        assert result.success is True
        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is not None
        assert writer.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_progress_tracker_passed(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
            progress_tracker=tracker,
        )
        phase.run()

        assert tracker.is_processed("1.2.3.4", "ipinfo_api")
        assert tracker.is_processed("1.2.3.4", "rdns_ptr")

    def test_channel_level_resume(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel()

        tracker.mark_processed("1.2.3.4", "ipinfo_api")

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
            progress_tracker=tracker,
        )
        phase.run()

        assert writer.get_channel_data("1.2.3.4", "ipinfo_api") is None
        assert writer.get_channel_data("1.2.3.4", "rdns_ptr") is not None

    def test_disabled_channel_logs_pending_count_ipinfo(self, caplog):
        ipinfo_channel = FakeChannel(disabled=True)
        rdns_channel = FakeChannel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = BasicCollectPhase(
            ips=ips,
            writer=writer,
            reader=reader,
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
        reader = InMemoryIPReader(
            data={
                "1.2.3.4": {"ip": "1.2.3.4", "ipinfo_api": {"country": "US"}},
            }
        )
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

        phase = BasicCollectPhase(
            ips=ips,
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )

        with caplog.at_level("WARNING"):
            phase.run()

        assert any(
            "共 3 个 IP" in r.message and "已有结果 1" in r.message and "剩余 2 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_rdns(self, caplog):
        ipinfo_channel = FakeChannel()
        rdns_channel = FakeChannel(disabled=True)
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        ips = ["1.2.3.4", "5.6.7.8"]

        phase = BasicCollectPhase(
            ips=ips,
            writer=writer,
            reader=reader,
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
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger") as MockTagger,
        ):
            MockClassifier.return_value = _create_classifier_mock(writer, ips)
            MockTagger.return_value = _create_tagger_mock(writer, ips)

            phase = ClassifyTagPhase(
                ips=ips,
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
            )
            result = phase.run()

        assert result.success is True
        assert "分类" in result.message
        assert "标签" in result.message
        for ip in ips:
            assert writer.get_channel_data(ip, "classifier") is not None
            assert writer.get_channel_data(ip, "tagger") is not None

    def test_no_tagger(self):
        ips = ["1.2.3.4", "5.6.7.8"]
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger"),
        ):
            MockClassifier.return_value = _create_classifier_mock(writer, ips)

            phase = ClassifyTagPhase(
                ips=ips,
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
                no_tagger=True,
            )
            result = phase.run()

        assert result.success is True
        for ip in ips:
            assert writer.get_channel_data(ip, "classifier") is not None
            assert writer.get_channel_data(ip, "tagger") is None
        assert result.data["tagger_result"] is None

    def test_empty_input(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier"),
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger"),
        ):
            phase = ClassifyTagPhase(
                ips=[],
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
            )
            result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需分类"
        assert len(writer.list_all_ips()) == 0

    def test_phase_protocol(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        phase = ClassifyTagPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            rules_dir=RULES_DIR,
            tagger_config_dir=TAGGER_CONFIG_DIR,
        )

        assert isinstance(phase, Phase)
        assert phase.name == "分类与标签"
