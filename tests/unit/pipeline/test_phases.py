from unittest.mock import MagicMock, patch

from ip_info.batch.core.query import BatchResult
from ip_info.pipeline.phase import Phase
from ip_info.pipeline.phases.phase1_basic import BasicCollectPhase
from ip_info.pipeline.phases.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.phases.phase3_deep import DeepQueryPhase
from ip_info.pipeline.phases.phase4_verify_scan import VerifyScanPhase
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker

RULES_DIR = "config/classifier"
TAGGER_CONFIG_DIR = "config/ip_tagger"


def _make_channel(disabled: bool = False, default_delay: float = 1.0) -> MagicMock:
    """创建一个 mock 渠道，默认不禁用"""
    ch = MagicMock()
    ch.disabled = disabled
    ch.default_delay = default_delay
    ch.validate.return_value = not disabled
    ch.fetch.return_value = {"data": "mock"}
    return ch


class TestDeepQueryPhase:
    """DeepQueryPhase (Phase 3) 单元测试"""

    def test_normal_execution(self):
        """正常执行：mock 三个渠道的 fetch/validate，验证 BaseBatchQuery 被三个渠道调用"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()
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

        mock_batch_result = BatchResult(success_count=2, fail_count=0, skip_count=0, total_elapsed=0.1)

        with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
            mock_run.return_value = mock_batch_result
            result = phase.run()

        assert result.success is True
        assert mock_run.call_count == 3
        call_channel_names = [c.kwargs.get("channel_name") for c in mock_run.call_args_list]
        assert "aizhan" in call_channel_names
        assert "chinaz" in call_channel_names
        assert "fofa_host" in call_channel_names

    def test_empty_input(self):
        """空输入：ips=[] → PhaseResult(success=True, message="无 IP 需深度查询")"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()

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
        """部分渠道验证失败：aizhan 渠道 disabled → 跳过 aizhan，chinaz 和 fofa_host 正常执行"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel(disabled=True)
        chinaz = _make_channel()
        fofa = _make_channel()
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

        mock_batch_result = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
            mock_run.return_value = mock_batch_result
            result = phase.run()

        # aizhan 被跳过，只有 chinaz 和 fofa_host 两个渠道执行
        assert mock_run.call_count == 2
        call_channel_names = [c.kwargs.get("channel_name") for c in mock_run.call_args_list]
        assert "aizhan" not in call_channel_names
        assert "chinaz" in call_channel_names
        assert "fofa_host" in call_channel_names
        assert result.success is True
        assert result.data["aizhan"] is None
        assert result.data["chinaz"] is not None
        assert result.data["fofa_host"] is not None

    def test_phase_protocol(self):
        """Phase Protocol 检查：isinstance(phase, Phase) == True"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()

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
        """delay 自动传递：run_concurrent 被调用时 delay=channel.default_delay"""
        aizhan = _make_channel(default_delay=2.0)
        chinaz = _make_channel(default_delay=2.0)
        fofa = _make_channel(default_delay=2.0)
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            aizhan_channel=aizhan,
            chinaz_channel=chinaz,
            fofa_channel=fofa,
            no_validate=True,
        )

        mock_batch_result = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
            mock_run.return_value = mock_batch_result
            phase.run()

        for call in mock_run.call_args_list:
            assert call.kwargs["delay"] == 2.0

    def test_progress_tracker_passed(self):
        """progress_tracker 传递：run_concurrent 被调用时 progress_tracker=提供的 tracker"""
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

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

        mock_batch_result = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
            mock_run.return_value = mock_batch_result
            phase.run()

        for call in mock_run.call_args_list:
            assert call.kwargs["progress_tracker"] is tracker

    def test_disabled_channel_logs_pending_count(self, caplog):
        """aizhan 渠道禁用时，日志显示待查询 IP 数量"""
        aizhan = _make_channel(disabled=True)
        chinaz = _make_channel()
        fofa = _make_channel()
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

        # aizhan 渠道禁用，应包含 "共 3 个 IP, 已有结果 0, 剩余 3 未查询"
        assert any(
            "aizhan" in r.message
            and "共 3 个 IP" in r.message
            and "已有结果 0" in r.message
            and "剩余 3 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_with_existing_results(self, caplog):
        """渠道禁用时，已有部分结果，日志显示正确的待查询数量"""
        aizhan = _make_channel(disabled=True)
        chinaz = _make_channel()
        fofa = _make_channel()
        writer = InMemoryIPWriter()
        # reader 中已有 1.2.3.4 的 aizhan 数据
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

        # aizhan 渠道禁用，应包含 "共 3 个 IP, 已有结果 1, 剩余 2 未查询"
        assert any(
            "aizhan" in r.message
            and "共 3 个 IP" in r.message
            and "已有结果 1" in r.message
            and "剩余 2 未查询" in r.message
            for r in caplog.records
        )

    def test_skip_ips_excludes_from_all_channels(self):
        """skip_ips: 指定的 IP 不进入任何渠道查询"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()
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

        mock_batch_result = BatchResult(success_count=2, fail_count=0, skip_count=0, total_elapsed=0.1)

        with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
            mock_run.return_value = mock_batch_result
            result = phase.run()

        assert result.success is True
        for call in mock_run.call_args_list:
            assert "5.6.7.8" not in call.kwargs["ips"]
            assert "1.2.3.4" in call.kwargs["ips"]
            assert "9.10.11.12" in call.kwargs["ips"]

    def test_skip_ips_logs_count(self, caplog):
        """skip_ips: 日志显示跳过的动态 IP 数量"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        aizhan = _make_channel()
        chinaz = _make_channel()
        fofa = _make_channel()
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

        mock_batch_result = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        with caplog.at_level("INFO"):
            with patch("ip_info.pipeline.phases.phase3_deep.run_concurrent") as mock_run:
                mock_run.return_value = mock_batch_result
                phase.run()

        assert any("跳过 2 个动态 IP" in r.message for r in caplog.records)


class TestVerifyScanPhase:
    """VerifyScanPhase (Phase 4) 单元测试"""

    def _make_phase(self, ips=None, domain_cache=None, **kwargs):
        """构造 VerifyScanPhase 实例，自动 mock 依赖"""
        return VerifyScanPhase(
            ips=ips if ips is not None else ["1.1.1.1", "2.2.2.2"],
            writer=MagicMock(),
            reader=MagicMock(),
            nmap_channel=MagicMock(),
            domain_cache=domain_cache,
            **kwargs,
        )

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_dns_and_nmap_run_in_parallel(self, MockBatchDnsVerify, mock_run_concurrent):
        """DNS 验证 + Nmap 端口扫描并行执行，writer 写入了两个渠道数据"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=2)
        MockBatchDnsVerify.return_value = mock_dns_instance

        mock_run_concurrent.return_value = BatchResult(success_count=2)

        writer = MagicMock()
        phase = VerifyScanPhase(
            ips=["1.1.1.1", "2.2.2.2"],
            writer=writer,
            reader=MagicMock(),
            nmap_channel=MagicMock(),
        )
        result = phase.run()

        # 验证 BatchDnsVerify 被正确构造和调用
        MockBatchDnsVerify.assert_called_once()
        call_kwargs = MockBatchDnsVerify.call_args
        assert call_kwargs.kwargs["ips"] == ["1.1.1.1", "2.2.2.2"]
        assert call_kwargs.kwargs["writer"] is writer
        mock_dns_instance.run.assert_called_once()

        # 验证 run_concurrent 被正确调用
        mock_run_concurrent.assert_called_once()
        rc_kwargs = mock_run_concurrent.call_args.kwargs
        assert rc_kwargs["ips"] == ["1.1.1.1", "2.2.2.2"]
        assert rc_kwargs["channel_name"] == "port_scan"
        assert rc_kwargs["writer"] is writer

        # 验证结果
        assert result.success is True
        assert "DNS验证: 2成功" in result.message
        assert "Nmap扫描: 2成功" in result.message

    def test_empty_ip_list(self):
        """空 IP 列表 → PhaseResult(success=True, message='无 IP 需验证/扫描')"""
        phase = self._make_phase(ips=[])
        result = phase.run()

        assert result.success is True
        assert result.message == "无 IP 需验证/扫描"

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_no_domain_cache(self, MockBatchDnsVerify, mock_run_concurrent):
        """domain_cache=None → BatchDnsVerify 构造时不传入缓存"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=1)
        MockBatchDnsVerify.return_value = mock_dns_instance
        mock_run_concurrent.return_value = BatchResult(success_count=1)

        phase = self._make_phase(ips=["1.1.1.1"], domain_cache=None)
        phase.run()

        call_kwargs = MockBatchDnsVerify.call_args.kwargs
        assert call_kwargs["domain_cache"] is None

    def test_phase_protocol(self):
        """VerifyScanPhase 满足 Phase Protocol"""
        phase = self._make_phase(ips=[])
        assert isinstance(phase, Phase)

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_delay_auto_passed(self, MockBatchDnsVerify, mock_run_concurrent):
        """delay 自动传递：run_concurrent 被调用时 delay=nmap_channel.default_delay"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=1)
        MockBatchDnsVerify.return_value = mock_dns_instance
        mock_run_concurrent.return_value = BatchResult(success_count=1)

        nmap_channel = MagicMock()
        nmap_channel.default_delay = 0.5
        nmap_channel.disabled = False

        phase = VerifyScanPhase(
            ips=["1.1.1.1"],
            writer=MagicMock(),
            reader=MagicMock(),
            nmap_channel=nmap_channel,
            no_validate=True,
        )
        phase.run()

        rc_kwargs = mock_run_concurrent.call_args.kwargs
        assert rc_kwargs["delay"] == 0.5

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_progress_tracker_passed(self, MockBatchDnsVerify, mock_run_concurrent):
        """progress_tracker 传递：run_concurrent 被调用时 progress_tracker=提供的 tracker"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=1)
        MockBatchDnsVerify.return_value = mock_dns_instance
        mock_run_concurrent.return_value = BatchResult(success_count=1)

        tracker = InMemoryProgressTracker()
        nmap_channel = MagicMock()
        nmap_channel.default_delay = 0
        nmap_channel.disabled = False

        phase = VerifyScanPhase(
            ips=["1.1.1.1"],
            writer=MagicMock(),
            reader=MagicMock(),
            nmap_channel=nmap_channel,
            no_validate=True,
            progress_tracker=tracker,
        )
        phase.run()

        rc_kwargs = mock_run_concurrent.call_args.kwargs
        assert rc_kwargs["progress_tracker"] is tracker

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_skip_ips_excludes_from_port_scan_only(self, MockBatchDnsVerify, mock_run_concurrent):
        """skip_ips: 动态 IP 只跳过 port_scan，DNS 验证仍对所有 IP 执行"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=3)
        MockBatchDnsVerify.return_value = mock_dns_instance
        mock_run_concurrent.return_value = BatchResult(success_count=1)

        nmap_channel = MagicMock()
        nmap_channel.default_delay = 0
        nmap_channel.disabled = False

        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}

        phase = VerifyScanPhase(
            ips=ips,
            writer=MagicMock(),
            reader=MagicMock(),
            nmap_channel=nmap_channel,
            no_validate=True,
            skip_ips=skip,
        )
        result = phase.run()

        dns_kwargs = MockBatchDnsVerify.call_args.kwargs
        assert dns_kwargs["ips"] == ips

        rc_kwargs = mock_run_concurrent.call_args.kwargs
        assert rc_kwargs["ips"] == ["1.1.1.1"]
        assert "2.2.2.2" not in rc_kwargs["ips"]
        assert "3.3.3.3" not in rc_kwargs["ips"]

        assert result.success is True

    @patch("ip_info.pipeline.phases.phase4_verify_scan.run_concurrent")
    @patch("ip_info.pipeline.phases.phase4_verify_scan.BatchDnsVerify")
    def test_skip_ips_logs_count(self, MockBatchDnsVerify, mock_run_concurrent, caplog):
        """skip_ips: 日志显示跳过的动态 IP 数量"""
        mock_dns_instance = MagicMock()
        mock_dns_instance.run.return_value = BatchResult(success_count=1)
        MockBatchDnsVerify.return_value = mock_dns_instance
        mock_run_concurrent.return_value = BatchResult(success_count=1)

        nmap_channel = MagicMock()
        nmap_channel.default_delay = 0
        nmap_channel.disabled = False

        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        skip = {"2.2.2.2", "3.3.3.3"}

        phase = VerifyScanPhase(
            ips=ips,
            writer=MagicMock(),
            reader=MagicMock(),
            nmap_channel=nmap_channel,
            no_validate=True,
            skip_ips=skip,
        )

        with caplog.at_level("INFO"):
            phase.run()

        assert any("跳过 2 个动态 IP" in r.message for r in caplog.records)


class TestBasicCollectPhase:
    """BasicCollectPhase 单元测试"""

    def _make_channels(self):
        """创建 mock 的 ipinfo 和 rdns 渠道"""
        ipinfo_channel = MagicMock()
        ipinfo_channel.disabled = False
        ipinfo_channel.fetch.return_value = {"ip": "1.2.3.4", "data": "ipinfo_test"}
        ipinfo_channel.validate.return_value = True

        rdns_channel = MagicMock()
        rdns_channel.disabled = False
        rdns_channel.fetch.return_value = {"ip": "1.2.3.4", "data": "rdns_test"}
        rdns_channel.validate.return_value = True

        return ipinfo_channel, rdns_channel

    def test_normal_execution(self):
        """正常执行：两个渠道都成功，writer 中写入对应渠道数据"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

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
        """空输入：ips=[] → PhaseResult(success=True, message='无 IP 需处理')"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

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
        """渠道验证失败：ipinfo_channel.validate() 后 disabled=True → 跳过 ipinfo_api，rdns_ptr 正常执行"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        # mock validate 设置 disabled
        def disable_ipinfo():
            ipinfo_channel.disabled = True

        ipinfo_channel.validate.side_effect = disable_ipinfo

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
        """两渠道都失败：两个渠道都 disabled → PhaseResult(success=False)"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        def disable_ipinfo():
            ipinfo_channel.disabled = True

        def disable_rdns():
            rdns_channel.disabled = True

        ipinfo_channel.validate.side_effect = disable_ipinfo
        rdns_channel.validate.side_effect = disable_rdns

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
        """Phase Protocol 检查：isinstance(phase, Phase) == True"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
        )
        assert isinstance(phase, Phase)

    @patch("ip_info.pipeline.phases.phase1_basic.run_concurrent")
    def test_delay_auto_passed(self, mock_run):
        """delay 自动传递：run_concurrent 被调用时 delay=channel.default_delay"""
        ipinfo_channel = _make_channel(default_delay=1.2)
        rdns_channel = _make_channel(default_delay=0.1)
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
        )

        mock_run.return_value = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        phase.run()

        # 验证两次 run_concurrent 调用的 delay 分别对应各自渠道的 default_delay
        delays = {call.kwargs["channel_name"]: call.kwargs["delay"] for call in mock_run.call_args_list}
        assert delays["ipinfo_api"] == 1.2
        assert delays["rdns_ptr"] == 0.1

    @patch("ip_info.pipeline.phases.phase1_basic.run_concurrent")
    def test_progress_tracker_passed(self, mock_run):
        """progress_tracker 传递：run_concurrent 被调用时 progress_tracker=提供的 tracker"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            ipinfo_channel=ipinfo_channel,
            rdns_channel=rdns_channel,
            no_validate=True,
            progress_tracker=tracker,
        )

        mock_run.return_value = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        phase.run()

        for call in mock_run.call_args_list:
            assert call.kwargs["progress_tracker"] is tracker

    @patch("ip_info.pipeline.phases.phase1_basic.run_concurrent")
    def test_channel_level_resume(self, mock_run):
        """分渠道断点续传：ipinfo_api 已处理但 rdns_ptr 未处理，rdns_ptr 仍会执行"""
        ipinfo_channel, rdns_channel = self._make_channels()
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        # 模拟 ipinfo_api 已处理
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

        mock_run.return_value = BatchResult(success_count=1, fail_count=0, skip_count=0, total_elapsed=0.1)

        phase.run()

        # 验证 run_concurrent 被调用两次，各自带正确的 channel_name
        calls_by_channel = {call.kwargs["channel_name"]: call for call in mock_run.call_args_list}
        assert "ipinfo_api" in calls_by_channel
        assert "rdns_ptr" in calls_by_channel
        # 两次调用都传了同一个 tracker
        assert calls_by_channel["ipinfo_api"].kwargs["progress_tracker"] is tracker
        assert calls_by_channel["rdns_ptr"].kwargs["progress_tracker"] is tracker

    def test_disabled_channel_logs_pending_count_ipinfo(self, caplog):
        """ipinfo_api 渠道禁用时，日志显示待查询 IP 数量"""
        ipinfo_channel = _make_channel(disabled=True)
        rdns_channel = _make_channel()
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

        # 应包含 "共 3 个 IP, 已有结果 0, 剩余 3 未查询"
        assert any(
            "共 3 个 IP" in r.message and "已有结果 0" in r.message and "剩余 3 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_with_existing_results(self, caplog):
        """ipinfo_api 渠道禁用时，已有部分结果，日志显示正确的待查询数量"""
        ipinfo_channel = _make_channel(disabled=True)
        rdns_channel = _make_channel()
        writer = InMemoryIPWriter()
        # reader 中已有 1.2.3.4 的 ipinfo_api 数据
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

        # 应包含 "共 3 个 IP, 已有结果 1, 剩余 2 未查询"
        assert any(
            "共 3 个 IP" in r.message and "已有结果 1" in r.message and "剩余 2 未查询" in r.message
            for r in caplog.records
        )

    def test_disabled_channel_logs_pending_count_rdns(self, caplog):
        """rdns_ptr 渠道禁用时，日志显示待查询 IP 数量"""
        ipinfo_channel = _make_channel()
        rdns_channel = _make_channel(disabled=True)
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

        # rdns_ptr 渠道禁用，应包含 "共 2 个 IP, 已有结果 0, 剩余 2 未查询"
        assert any(
            "共 2 个 IP" in r.message and "已有结果 0" in r.message and "剩余 2 未查询" in r.message
            for r in caplog.records
        )


class TestClassifyTagPhase:
    """ClassifyTagPhase 的单元测试。"""

    def test_normal_execution(self):
        """正常执行：验证 writer 中写入了 classifier 和 tagger 渠道数据。"""
        ips = ["1.2.3.4", "5.6.7.8"]
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger") as MockTagger,
        ):
            mock_classifier = MagicMock()
            mock_classifier.run.return_value = BatchResult(success_count=2)
            MockClassifier.return_value = mock_classifier

            mock_tagger = MagicMock()
            mock_tagger.run.return_value = BatchResult(success_count=2)
            MockTagger.return_value = mock_tagger

            phase = ClassifyTagPhase(
                ips=ips,
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
            )
            result = phase.run()

        # 验证 BatchClassifier 被正确调用
        MockClassifier.assert_called_once_with(
            ips=ips,
            writer=writer,
            reader=reader,
            rules_dir=RULES_DIR,
        )
        mock_classifier.run.assert_called_once()

        # 验证 BatchTagger 被正确调用
        MockTagger.assert_called_once_with(
            ips=ips,
            writer=writer,
            config_dir=TAGGER_CONFIG_DIR,
            level=None,
        )
        mock_tagger.run.assert_called_once()

        # 验证结果
        assert result.success is True
        assert "分类" in result.message
        assert "标签" in result.message
        assert result.data["classify_result"].success_count == 2
        assert result.data["tagger_result"].success_count == 2

    def test_no_tagger(self):
        """no_tagger=True：只执行分类，不执行标签打标，验证 writer 中只有 classifier 数据无 tagger 数据。"""
        ips = ["1.2.3.4", "5.6.7.8"]
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger") as MockTagger,
        ):
            mock_classifier = MagicMock()
            mock_classifier.run.return_value = BatchResult(success_count=2)
            MockClassifier.return_value = mock_classifier

            phase = ClassifyTagPhase(
                ips=ips,
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
                no_tagger=True,
            )
            result = phase.run()

        # 验证 BatchClassifier 被调用
        MockClassifier.assert_called_once()
        mock_classifier.run.assert_called_once()

        # 验证 BatchTagger 未被调用
        MockTagger.assert_not_called()

        # 验证结果中 tagger_result 为 None
        assert result.success is True
        assert result.data["tagger_result"] is None
        assert result.data["classify_result"].success_count == 2

    def test_empty_input(self):
        """空输入：ips=[] → PhaseResult(success=True, message='无 IP 需分类')。"""
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        with (
            patch("ip_info.pipeline.phases.phase2_classify.BatchClassifier") as MockClassifier,
            patch("ip_info.pipeline.phases.phase2_classify.BatchTagger") as MockTagger,
        ):
            phase = ClassifyTagPhase(
                ips=[],
                writer=writer,
                reader=reader,
                rules_dir=RULES_DIR,
                tagger_config_dir=TAGGER_CONFIG_DIR,
            )
            result = phase.run()

        # 验证 BatchClassifier 和 BatchTagger 都未被调用
        MockClassifier.assert_not_called()
        MockTagger.assert_not_called()

        # 验证结果
        assert result.success is True
        assert result.message == "无 IP 需分类"

    def test_phase_protocol(self):
        """Phase Protocol 检查：isinstance(phase, Phase) == True。"""
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
