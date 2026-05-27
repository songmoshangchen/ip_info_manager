from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.builder import PipelineBuilder
from ip_info.pipeline.context import PipelineContext
from ip_info.pipeline.phases.phase1_basic import BasicCollectPhase
from ip_info.pipeline.phases.phase3_deep import DeepQueryPhase
from ip_info.pipeline.pipeline import Pipeline, PipelineResult
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class FakeChannel(BaseChannelAdapter):
    channel_name = "fake"

    def __init__(self, *, disabled=False, response=None):
        self.disabled = disabled
        self._response = response or {"status": "ok"}

    def _validate_key(self):
        pass

    def _request(self, ip, **kwargs):
        return {"ip": ip, **self._response}

    def fetch(self, ip, **kwargs):
        return {"ip": ip, **self._response, "query_time": "2024-01-01T00:00:00"}


def _make_context():
    writer = InMemoryIPWriter()
    reader = InMemoryIPReader()
    tracker = InMemoryProgressTracker()
    return PipelineContext(writer=writer, reader=reader, progress_tracker=tracker)


class TestPipelineBuilder:
    def test_fluent_api_returns_self(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx)
        result = builder.with_ips(["1.2.3.4"])
        assert result is builder

    def test_with_ips_stores_ips(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx).with_ips(["1.2.3.4", "5.6.7.8"])
        assert builder.ips == ["1.2.3.4", "5.6.7.8"]

    def test_with_channel_registers(self):
        ctx = _make_context()
        ch = FakeChannel()
        builder = PipelineBuilder(ctx).with_channel("test", ch)
        assert builder.get_channel("test") is ch

    def test_skip_channel_marks_disabled(self):
        ctx = _make_context()
        ch = FakeChannel()
        builder = PipelineBuilder(ctx).with_channel("test", ch).skip_channel("test")
        assert builder.get_channel("test").disabled is True

    def test_add_phase_registers(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx)
        phase = BasicCollectPhase(
            ips=["1.2.3.4"],
            ipinfo_channel=FakeChannel(),
            rdns_channel=FakeChannel(),
            context=ctx,
        )
        builder.add_phase(phase)
        assert len(builder.phases) == 1

    def test_build_returns_pipeline(self):
        ctx = _make_context()
        builder = (
            PipelineBuilder(ctx)
            .with_ips(["1.2.3.4"])
            .with_channel("ipinfo_api", FakeChannel())
            .with_channel("rdns_ptr", FakeChannel())
        )
        builder.add_phase(
            BasicCollectPhase(
                ips=["1.2.3.4"],
                ipinfo_channel=builder.get_channel("ipinfo_api"),
                rdns_channel=builder.get_channel("rdns_ptr"),
                context=ctx,
                no_validate=True,
            )
        )
        pipeline = builder.build()
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline._phases) == 1

    def test_pipeline_run_executes_phases(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx).with_ips(["1.2.3.4"])
        builder.add_phase(
            BasicCollectPhase(
                ips=["1.2.3.4"],
                ipinfo_channel=FakeChannel(),
                rdns_channel=FakeChannel(),
                context=ctx,
                no_validate=True,
            )
        )
        pipeline = builder.build()
        result = pipeline.run()
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.phase_results) == 1

    def test_multiple_phases_sequential(self):
        ctx = _make_context()
        ips = ["1.2.3.4"]

        builder = PipelineBuilder(ctx).with_ips(ips)
        builder.add_phase(
            BasicCollectPhase(
                ips=ips,
                ipinfo_channel=FakeChannel(),
                rdns_channel=FakeChannel(),
                context=ctx,
                no_validate=True,
            )
        )
        builder.add_phase(
            DeepQueryPhase(
                ips=ips,
                aizhan_channel=FakeChannel(),
                chinaz_channel=FakeChannel(),
                fofa_channel=FakeChannel(),
                context=ctx,
                no_validate=True,
            )
        )

        pipeline = builder.build()
        result = pipeline.run()
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.phase_results) == 2


class TestWithFilter:
    def test_with_filter_returns_self(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx)

        def my_filter(ips, context):
            return ips

        result = builder.with_filter("分类与标签", my_filter)
        assert result is builder

    def test_with_filter_stores_filter(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx)

        def my_filter(ips, context):
            return ips

        builder.with_filter("分类与标签", my_filter)
        assert len(builder._filters) == 1
        assert builder._filters[0] == ("分类与标签", my_filter)

    def test_with_filter_multiple_filters(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx)

        def filter_a(ips, context):
            return ips

        def filter_b(ips, context):
            return ips

        builder.with_filter("分类与标签", filter_a)
        builder.with_filter("分类与标签", filter_b)
        assert len(builder._filters) == 2

    def test_build_passes_filters_to_pipeline(self):
        ctx = _make_context()
        builder = PipelineBuilder(ctx).with_ips(["1.2.3.4"])

        def my_filter(ips, context):
            return ips

        builder.with_filter("分类与标签", my_filter)
        builder.add_phase(
            BasicCollectPhase(
                ips=["1.2.3.4"],
                ipinfo_channel=FakeChannel(),
                rdns_channel=FakeChannel(),
                context=ctx,
                no_validate=True,
            )
        )
        pipeline = builder.build()
        assert "分类与标签" in pipeline._filters
        assert len(pipeline._filters["分类与标签"]) == 1
