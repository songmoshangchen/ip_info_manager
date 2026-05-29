from ip_info.pipeline.core.context import PipelineContext
from ip_info.store.in_memory import InMemoryDomainCache, InMemoryIPReader, InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


class TestPipelineContext:
    def test_stores_writer_reader_tracker(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker)

        assert ctx.writer is writer
        assert ctx.reader is reader
        assert ctx.progress_tracker is tracker

    def test_domain_cache_optional(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker)

        assert ctx.domain_cache is None

    def test_domain_cache_provided(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()
        cache = InMemoryDomainCache()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker, domain_cache=cache)

        assert ctx.domain_cache is cache

    def test_config_optional(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker)

        assert ctx.config is None

    def test_config_provided(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker, config={"key": "value"})

        assert ctx.config == {"key": "value"}

    def test_is_frozen_dataclass(self):
        writer = InMemoryIPWriter()
        reader = InMemoryIPReader()
        tracker = InMemoryProgressTracker()

        ctx = PipelineContext(writer=writer, reader=reader, progress_tracker=tracker)

        import dataclasses

        assert dataclasses.is_dataclass(ctx)
