from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep
from ip_info.processors.classifier.runner import BatchClassifier
from ip_info.processors.core.base import BaseProcessor
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class FakeChannel(BaseChannelAdapter):
    channel_name = "fake"
    default_delay = 0.5

    def __init__(self, *, disabled=False, response=None):
        self.disabled = disabled
        self._response = response or {"status": "ok"}

    def _validate_key(self):
        pass

    def _request(self, ip, **kwargs):
        return {"ip": ip, **self._response}

    def fetch(self, ip, **kwargs):
        result = self._parse(self._request(ip, **kwargs), ip)
        result.setdefault("query_time", "2024-01-01T00:00:00")
        return result


class TestBatchStepProtocol:
    def test_simple_object_satisfies_batch_step(self):
        class SimpleStep:
            @property
            def name(self) -> str:
                return "test_step"

            def run(self) -> BatchResult:
                return BatchResult(success_count=1)

        step = SimpleStep()
        assert isinstance(step, BatchStep)

    def test_simple_step_name(self):
        class SimpleStep:
            @property
            def name(self) -> str:
                return "my_step"

            def run(self) -> BatchResult:
                return BatchResult()

        step = SimpleStep()
        assert step.name == "my_step"

    def test_simple_step_run_returns_batch_result(self):
        class SimpleStep:
            @property
            def name(self) -> str:
                return "step"

            def run(self) -> BatchResult:
                return BatchResult(success_count=5, fail_count=1)

        step = SimpleStep()
        result = step.run()
        assert isinstance(result, BatchResult)
        assert result.success_count == 5
        assert result.fail_count == 1


class TestBaseProcessorName:
    def test_name_returns_channel_name(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()

        class TestProcessor(BaseProcessor):
            channel_name = "test_proc"

            def _process(self) -> BatchResult:
                return BatchResult()

        proc = TestProcessor(ips=["1.2.3.4"], writer=writer, reader=reader)
        assert proc.name == "test_proc"

    def test_name_property_is_readable(self):
        writer = InMemoryIPWriter()

        class TestProcessor(BaseProcessor):
            channel_name = "classifier"

            def _process(self) -> BatchResult:
                return BatchResult()

        proc = TestProcessor(ips=[], writer=writer)
        assert proc.name == "classifier"


class TestBatchClassifierSatisfiesBatchStep:
    def test_batch_classifier_is_batch_step(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            rules_dir="config/classifier",
        )
        assert isinstance(classifier, BatchStep)

    def test_batch_classifier_name(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            rules_dir="config/classifier",
        )
        assert classifier.name == "classifier"


class TestChannelBatchStep:
    def test_satisfies_batch_step_protocol(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        step = ChannelBatchStep(
            channel_name="aizhan",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
        )
        assert isinstance(step, BatchStep)

    def test_name_returns_channel_name(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        step = ChannelBatchStep(
            channel_name="chinaz",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
        )
        assert step.name == "chinaz"

    def test_run_returns_batch_result(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        step = ChannelBatchStep(
            channel_name="fake",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
            no_validate=True,
        )
        result = step.run()
        assert isinstance(result, BatchResult)
        assert result.success_count == 1

    def test_default_delay_from_channel(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        step = ChannelBatchStep(
            channel_name="fake",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
            no_validate=True,
        )
        assert step.delay == 0.5

    def test_custom_delay_overrides_default(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        step = ChannelBatchStep(
            channel_name="fake",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
            delay=1.0,
            no_validate=True,
        )
        assert step.delay == 1.0

    def test_run_writes_data_via_writer(self):
        ch = FakeChannel(response={"source": "test"})
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader(data=writer._store)
        step = ChannelBatchStep(
            channel_name="fake",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
            no_validate=True,
        )
        step.run()
        data = reader.get_channel_data("1.2.3.4", "fake")
        assert data is not None
        assert data["source"] == "test"

    def test_progress_tracker_passed(self):
        ch = FakeChannel()
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()
        step = ChannelBatchStep(
            channel_name="fake",
            channel=ch,
            ips=["1.2.3.4"],
            writer=writer,
            progress_tracker=tracker,
            no_validate=True,
        )
        step.run()
        assert tracker.is_processed("1.2.3.4", "fake")
