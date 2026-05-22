import pytest

from ip_info.batch.query import BaseBatchQuery, BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class _FakeChannel(BaseChannelAdapter):
    channel_name = "test"

    def __init__(self):
        self.disabled = False
        self._results: dict[str, dict | Exception] = {}
        self._fetch_calls: list[tuple[str, dict]] = []
        self._validate_should_fail = False
        self._validate_called = False

    def _request(self, ip, **kwargs):
        return {}

    def fetch(self, ip, **kwargs):
        self._fetch_calls.append((ip, kwargs))
        if ip in self._results:
            result = self._results[ip]
            if isinstance(result, Exception):
                if isinstance(result, ChannelPermanentError):
                    self.disabled = True
                raise result
            return result
        return {"country": "CN", "ip": ip}

    def _validate_key(self):
        if self._validate_should_fail:
            raise RuntimeError("validation failed")

    def validate(self):
        self._validate_called = True
        return super().validate()


class _FakeWriter:
    def __init__(self):
        self.writes = []

    def add_or_update_ip(self, ip, channel, data):
        self.writes.append((ip, channel, data))
        return True


class _InMemoryProgressTracker:
    def __init__(self):
        self._processed: set[str] = set()

    def is_processed(self, ip: str) -> bool:
        return ip in self._processed

    def mark_processed(self, ip: str) -> None:
        self._processed.add(ip)


def _make_query(
    ips,
    *,
    delay=0,
    no_validate=False,
    progress_tracker=None,
    max_consecutive_network_failures=5,
    channel=None,
):
    ch = channel or _FakeChannel()
    return BaseBatchQuery(
        channel_name="test",
        channel=ch,
        writer=_FakeWriter(),
        ips=ips,
        delay=delay,
        no_validate=no_validate,
        progress_tracker=progress_tracker,
        max_consecutive_network_failures=max_consecutive_network_failures,
    )


class TestBatchResult:
    def test_defaults(self):
        result = BatchResult()
        assert result.success_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed == 0.0
        assert result.stopped_early is False
        assert result.stop_reason == ""


class TestBaseBatchQueryConstructor:
    def test_stores_channel_name(self):
        q = _make_query(["1.1.1.1"])
        assert q._channel_name == "test"

    def test_stores_delay(self):
        q = _make_query(["1.1.1.1"], delay=0.5)
        assert q._delay == 0.5

    def test_stores_no_validate(self):
        q = _make_query(["1.1.1.1"], no_validate=True)
        assert q._no_validate is True

    def test_stores_max_failures(self):
        q = _make_query(["1.1.1.1"], max_consecutive_network_failures=10)
        assert q._max_failures == 10


class TestIPDeduplication:
    def test_deduplicates_ips(self):
        q = _make_query(["1.1.1.1", "2.2.2.2", "1.1.1.1"])
        assert q.total_count == 2

    def test_preserves_order(self):
        q = _make_query(["3.3.3.3", "1.1.1.1", "2.2.2.2", "1.1.1.1"])
        assert q._all_ips == ["3.3.3.3", "1.1.1.1", "2.2.2.2"]


class TestTotalCount:
    def test_returns_count(self):
        q = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"])
        assert q.total_count == 3

    def test_empty_ips(self):
        q = _make_query([])
        assert q.total_count == 0


class TestPendingCount:
    def test_without_tracker(self):
        q = _make_query(["1.1.1.1", "2.2.2.2"])
        assert q.pending_count == 2

    def test_with_tracker_none_processed(self):
        tracker = _InMemoryProgressTracker()
        q = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 2

    def test_with_tracker_one_processed(self):
        tracker = _InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        q = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 1

    def test_with_tracker_all_processed(self):
        tracker = _InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        tracker.mark_processed("2.2.2.2")
        q = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 0


class TestRun:
    def test_run_returns_batch_result(self):
        q = _make_query(["1.1.1.1"])
        result = q.run()
        assert isinstance(result, BatchResult)
        assert result.success_count == 1
        assert result.fail_count == 0
        assert result.total_elapsed >= 0

    def test_run_queries_all_pending_ips(self):
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        q = _make_query(ips)
        q.run()
        assert len(q._channel._fetch_calls) == 3

    def test_run_writes_correct_channel_name(self):
        q = _make_query(["1.1.1.1"])
        q.run()
        assert q._writer.writes[0][1] == "test"

    def test_run_writes_data_for_each_ip(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = {"country": "US"}
        ch._results["2.2.2.2"] = {"country": "JP"}
        q = _make_query(["1.1.1.1", "2.2.2.2"], channel=ch)
        q.run()
        assert q._writer.writes[0][2] == {"country": "US"}
        assert q._writer.writes[1][2] == {"country": "JP"}

    def test_run_passes_delay_to_fetch(self):
        q = _make_query(["1.1.1.1"], delay=0.5)
        q.run()
        assert q._channel._fetch_calls[0][1].get("delay") == 0.5

    def test_run_empty_pending_does_nothing(self):
        q = _make_query([])
        result = q.run()
        assert result.success_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed >= 0


class TestRunProgressTracking:
    def test_run_no_tracker_processes_all(self):
        q = _make_query(["1.1.1.1", "2.2.2.2"])
        result = q.run()
        assert result.success_count == 2
        assert result.fail_count == 0

    def test_run_tracker_excludes_processed(self):
        tracker = _InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        q = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        result = q.run()
        assert result.success_count == 1

    def test_run_success_marks_progress(self):
        tracker = _InMemoryProgressTracker()
        q = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        q.run()
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is True

    def test_run_channel_error_no_progress(self):
        tracker = _InMemoryProgressTracker()
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        q = _make_query(["1.1.1.1"], progress_tracker=tracker, channel=ch)
        q.run()
        assert tracker.is_processed("1.1.1.1") is False

    def test_run_permanent_error_no_progress(self):
        tracker = _InMemoryProgressTracker()
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("permanent")
        q = _make_query(["1.1.1.1"], progress_tracker=tracker, channel=ch)
        q.run()
        assert tracker.is_processed("1.1.1.1") is False


class TestRunErrorHandling:
    def test_run_success_writes_to_store(self):
        q = _make_query(["1.1.1.1"])
        q.run()
        assert len(q._writer.writes) == 1
        assert q._writer.writes[0][0] == "1.1.1.1"

    def test_run_channel_error_does_not_write(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        q = _make_query(["1.1.1.1"], channel=ch)
        q.run()
        assert len(q._writer.writes) == 0

    def test_run_permanent_error_stops_loop(self):
        ch = _FakeChannel()
        ch._results["2.2.2.2"] = ChannelPermanentError("permanent")
        q = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"], channel=ch)
        result = q.run()
        assert result.stopped_early is True
        assert result.stop_reason == "permanent_error"
        assert result.fail_count == 1

    def test_run_permanent_error_skips_remaining(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("permanent")
        q = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"], channel=ch)
        q.run()
        assert len(ch._fetch_calls) == 1

    def test_run_non_channel_error_propagates(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = RuntimeError("unexpected")
        q = _make_query(["1.1.1.1"], channel=ch)
        with pytest.raises(RuntimeError, match="unexpected"):
            q.run()


class TestRunCircuitBreaking:
    def test_run_circuit_break_after_5_failures(self):
        ch = _FakeChannel()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5", "6.6.6.6"]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        q = _make_query(ips, channel=ch)
        result = q.run()
        assert result.fail_count == 5
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"

    def test_run_success_resets_circuit_counter(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("fail")
        ch._results["2.2.2.2"] = ChannelError("fail")
        ch._results["4.4.4.4"] = ChannelError("fail")
        ch._results["5.5.5.5"] = ChannelError("fail")
        ch._results["6.6.6.6"] = ChannelError("fail")
        ch._results["7.7.7.7"] = ChannelError("fail")
        ch._results["8.8.8.8"] = ChannelError("fail")
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5", "6.6.6.6", "7.7.7.7", "8.8.8.8"]
        q = _make_query(ips, channel=ch)
        result = q.run()
        assert result.success_count == 1
        assert result.fail_count == 7
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"

    def test_run_custom_circuit_threshold(self):
        ch = _FakeChannel()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        q = _make_query(ips, channel=ch, max_consecutive_network_failures=3)
        result = q.run()
        assert result.fail_count == 3
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"


class TestRunDependencyCheck:
    def test_run_disabled_skips_all(self):
        ch = _FakeChannel()
        ch.disabled = True
        q = _make_query(["1.1.1.1", "2.2.2.2"], channel=ch, no_validate=True)
        result = q.run()
        assert result.success_count == 0
        assert result.fail_count == 0

    def test_run_no_validate_false_calls_validate(self):
        ch = _FakeChannel()
        q = _make_query(["1.1.1.1"], no_validate=False, channel=ch)
        q.run()
        assert ch._validate_called is True

    def test_run_no_validate_true_skips_validate(self):
        ch = _FakeChannel()
        q = _make_query(["1.1.1.1"], no_validate=True, channel=ch)
        q.run()
        assert ch._validate_called is False

    def test_run_validate_failure_sets_disabled(self):
        ch = _FakeChannel()
        ch._validate_should_fail = True
        q = _make_query(["1.1.1.1"], channel=ch, no_validate=False)
        result = q.run()
        assert result.success_count == 0
        assert ch.disabled is True
