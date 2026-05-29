from ip_info.pipeline.core.batch_factory import BatchFactory
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep
from ip_info.processors.classifier.runner import BatchClassifier
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


def _make_context():
    writer = InMemoryIPWriter()
    reader = InMemoryIPReader(data=writer._store)
    tracker = InMemoryProgressTracker()
    return writer, reader, tracker


class TestBatchFactoryTryCreateChannel:
    def test_create_aizhan_returns_channel_batch_step(self):
        writer, reader, tracker = _make_context()
        step = BatchFactory.try_create(
            "aizhan",
            ips=["1.2.3.4"],
            writer=writer,
            progress_tracker=tracker,
        )
        assert step is not None
        assert isinstance(step, ChannelBatchStep)
        assert step.name == "aizhan"

    def test_create_ipinfo_api_returns_channel_batch_step(self):
        writer, reader, tracker = _make_context()
        step = BatchFactory.try_create(
            "ipinfo_api",
            ips=["1.2.3.4"],
            writer=writer,
            progress_tracker=tracker,
        )
        assert step is not None
        assert isinstance(step, ChannelBatchStep)
        assert step.name == "ipinfo_api"

    def test_create_rdns_ptr_returns_channel_batch_step(self):
        writer, reader, tracker = _make_context()
        step = BatchFactory.try_create(
            "rdns_ptr",
            ips=["1.2.3.4"],
            writer=writer,
            progress_tracker=tracker,
        )
        assert step is not None
        assert isinstance(step, ChannelBatchStep)
        assert step.name == "rdns_ptr"


class TestBatchFactoryTryCreateProcessor:
    def test_create_classify_returns_batch_classifier(self):
        writer, reader, tracker = _make_context()
        step = BatchFactory.try_create(
            "classify",
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            rules_dir="config/classifier",
        )
        assert step is not None
        assert isinstance(step, BatchClassifier)
        assert step.name == "classifier"

    def test_create_classify_satisfies_batch_step(self):
        writer, reader, tracker = _make_context()
        step = BatchFactory.try_create(
            "classify",
            ips=["1.2.3.4"],
            writer=writer,
            reader=reader,
            rules_dir="config/classifier",
        )
        assert isinstance(step, BatchStep)


class TestBatchFactoryUnknownName:
    def test_unknown_name_returns_none(self):
        step = BatchFactory.try_create("nonexistent_channel")
        assert step is None

    def test_empty_name_returns_none(self):
        step = BatchFactory.try_create("")
        assert step is None


class TestBatchFactoryInitFailure:
    def test_channel_init_exception_returns_none(self):
        import unittest.mock

        with unittest.mock.patch(
            "ip_info.pipeline.core.batch_factory.importlib.import_module",
            side_effect=ImportError("no module"),
        ):
            step = BatchFactory.try_create("aizhan", ips=["1.2.3.4"])
            assert step is None


class TestBatchFactoryListNames:
    def test_list_channel_names(self):
        names = BatchFactory.list_channel_names()
        assert "aizhan" in names
        assert "ipinfo_api" in names
        assert "rdns_ptr" in names
        assert "chinaz" in names
        assert "fofa_host" in names
        assert "port_scan" in names

    def test_list_processor_names(self):
        names = BatchFactory.list_processor_names()
        assert "classify" in names
        assert "tagger" in names
        assert "dns_verify" in names

    def test_list_all_names(self):
        all_names = BatchFactory.list_all_names()
        channel_names = BatchFactory.list_channel_names()
        processor_names = BatchFactory.list_processor_names()
        for name in channel_names:
            assert name in all_names
        for name in processor_names:
            assert name in all_names
