from ip_info.batch.core.query import BatchResult
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import Phase
from ip_info.pipeline.trace_steps.phase1_basic import BasicCollectPhase
from ip_info.pipeline.trace_steps.phase2_classify import ClassifyTagPhase
from ip_info.pipeline.trace_steps.phase3_deep import DeepQueryPhase
from ip_info.pipeline.trace_steps.phase4_verify_scan import VerifyScanPhase
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class FakeBatchStep:
    def __init__(self, name: str, result: BatchResult | None = None, writer=None, channel_name: str = ""):
        self._name = name
        self._result = result or BatchResult(success_count=1)
        self._writer = writer
        self._channel_name = channel_name or name
        self._run_count = 0

    @property
    def name(self) -> str:
        return self._name

    def run(self) -> BatchResult:
        self._run_count += 1
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


class TestPhase1WithBatchSteps:
    def test_runs_steps_in_parallel(self):
        ctx = _make_context()
        ipinfo_step = FakeBatchStep("ipinfo_api", writer=ctx.writer, channel_name="ipinfo_api")
        rdns_step = FakeBatchStep("rdns_ptr", writer=ctx.writer, channel_name="rdns_ptr")

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            steps=[ipinfo_step, rdns_step],
        )
        result = phase.run()

        assert result.success is True
        assert ipinfo_step._run_count == 1
        assert rdns_step._run_count == 1

    def test_empty_steps(self):
        ctx = _make_context()
        phase = BasicCollectPhase(ips=["1.2.3.4"], context=ctx, steps=[])
        result = phase.run()
        assert result.success is True

    def test_empty_ips(self):
        ctx = _make_context()
        step = FakeBatchStep("ipinfo_api")
        phase = BasicCollectPhase(ips=[], context=ctx, steps=[step])
        result = phase.run()
        assert result.success is True
        assert "无 IP" in result.message

    def test_satisfies_phase_protocol(self):
        ctx = _make_context()
        phase = BasicCollectPhase(ips=[], context=ctx, steps=[])
        assert isinstance(phase, Phase)
        assert phase.name == "基础情报采集"

    def test_result_message_contains_step_names(self):
        ctx = _make_context()
        ipinfo_step = FakeBatchStep(
            "ipinfo_api",
            BatchResult(success_count=2),
            writer=ctx.writer,
            channel_name="ipinfo_api",
        )
        rdns_step = FakeBatchStep(
            "rdns_ptr",
            BatchResult(success_count=3),
            writer=ctx.writer,
            channel_name="rdns_ptr",
        )

        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            context=ctx,
            steps=[ipinfo_step, rdns_step],
        )
        result = phase.run()

        assert "ipinfo_api" in result.message
        assert "rdns_ptr" in result.message


class TestPhase2WithBatchSteps:
    def test_runs_classify_then_tagger(self):
        ctx = _make_context()
        classify_step = FakeBatchStep(
            "classifier",
            BatchResult(success_count=2),
            writer=ctx.writer,
            channel_name="classifier",
        )
        tagger_step = FakeBatchStep(
            "tagger",
            BatchResult(success_count=2),
            writer=ctx.writer,
            channel_name="tagger",
        )

        phase = ClassifyTagPhase(
            ips=["1.2.3.4"],
            context=ctx,
            classify_step=classify_step,
            tagger_step=tagger_step,
        )
        result = phase.run()

        assert result.success is True
        assert classify_step._run_count == 1
        assert tagger_step._run_count == 1

    def test_no_tagger(self):
        ctx = _make_context()
        classify_step = FakeBatchStep(
            "classifier",
            BatchResult(success_count=1),
            writer=ctx.writer,
            channel_name="classifier",
        )

        phase = ClassifyTagPhase(
            ips=["1.2.3.4"],
            context=ctx,
            classify_step=classify_step,
            tagger_step=None,
        )
        result = phase.run()

        assert result.success is True
        assert classify_step._run_count == 1

    def test_empty_ips(self):
        ctx = _make_context()
        classify_step = FakeBatchStep("classifier")
        tagger_step = FakeBatchStep("tagger")

        phase = ClassifyTagPhase(
            ips=[],
            context=ctx,
            classify_step=classify_step,
            tagger_step=tagger_step,
        )
        result = phase.run()
        assert result.success is True
        assert "无 IP" in result.message

    def test_satisfies_phase_protocol(self):
        ctx = _make_context()
        phase = ClassifyTagPhase(ips=[], context=ctx, classify_step=FakeBatchStep("c"), tagger_step=FakeBatchStep("t"))
        assert isinstance(phase, Phase)
        assert phase.name == "分类与标签"


class TestPhase3WithBatchSteps:
    def test_runs_steps_in_parallel(self):
        ctx = _make_context()
        aizhan_step = FakeBatchStep("aizhan", writer=ctx.writer, channel_name="aizhan")
        chinaz_step = FakeBatchStep("chinaz", writer=ctx.writer, channel_name="chinaz")
        fofa_step = FakeBatchStep("fofa_host", writer=ctx.writer, channel_name="fofa_host")

        phase = DeepQueryPhase(
            ips=["1.2.3.4"],
            context=ctx,
            steps=[aizhan_step, chinaz_step, fofa_step],
        )
        result = phase.run()

        assert result.success is True
        assert aizhan_step._run_count == 1
        assert chinaz_step._run_count == 1
        assert fofa_step._run_count == 1

    def test_empty_ips(self):
        ctx = _make_context()
        step = FakeBatchStep("aizhan")
        phase = DeepQueryPhase(ips=[], context=ctx, steps=[step])
        result = phase.run()
        assert result.success is True
        assert "无 IP" in result.message

    def test_satisfies_phase_protocol(self):
        ctx = _make_context()
        phase = DeepQueryPhase(ips=[], context=ctx, steps=[])
        assert isinstance(phase, Phase)
        assert phase.name == "深度查询"

    def test_skip_ips(self):
        ctx = _make_context()
        step = FakeBatchStep("aizhan", writer=ctx.writer, channel_name="aizhan")

        phase = DeepQueryPhase(
            ips=["1.2.3.4", "5.6.7.8"],
            context=ctx,
            steps=[step],
            skip_ips={"5.6.7.8"},
        )
        result = phase.run()
        assert result.success is True


class TestPhase4WithBatchSteps:
    def test_runs_steps_in_parallel(self):
        ctx = _make_context()
        dns_step = FakeBatchStep("domain_verify", writer=ctx.writer, channel_name="domain_verify")
        scan_step = FakeBatchStep("port_scan", writer=ctx.writer, channel_name="port_scan")

        phase = VerifyScanPhase(
            ips=["1.2.3.4"],
            context=ctx,
            steps=[dns_step, scan_step],
        )
        result = phase.run()

        assert result.success is True
        assert dns_step._run_count == 1
        assert scan_step._run_count == 1

    def test_empty_ips(self):
        ctx = _make_context()
        step = FakeBatchStep("port_scan")
        phase = VerifyScanPhase(ips=[], context=ctx, steps=[step])
        result = phase.run()
        assert result.success is True
        assert "无 IP" in result.message

    def test_satisfies_phase_protocol(self):
        ctx = _make_context()
        phase = VerifyScanPhase(ips=[], context=ctx, steps=[])
        assert isinstance(phase, Phase)
        assert phase.name == "验证与扫描"

    def test_skip_ips(self):
        ctx = _make_context()
        step = FakeBatchStep("port_scan", writer=ctx.writer, channel_name="port_scan")

        phase = VerifyScanPhase(
            ips=["1.2.3.4", "5.6.7.8"],
            context=ctx,
            steps=[step],
            skip_ips={"5.6.7.8"},
        )
        result = phase.run()
        assert result.success is True
