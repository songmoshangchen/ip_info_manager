from unittest.mock import MagicMock, patch

from ip_info.batch.core.query import BatchResult
from ip_info.pipeline.phase import Phase
from ip_info.pipeline.phases.phase1_basic import BasicCollectPhase
from ip_info.pipeline.phases.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.phases.phase3_deep import DeepQueryPhase
from ip_info.pipeline.phases.phase4_verify_scan import VerifyScanPhase
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter

RULES_DIR = "config/classifier"
TAGGER_CONFIG_DIR = "config/ip_tagger"


def _make_channel(disabled: bool = False) -> MagicMock:
    """创建一个 mock 渠道，默认不禁用"""
    ch = MagicMock()
    ch.disabled = disabled
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
