import pytest

from ip_info.batch.progress import InMemoryProgressTracker
from ip_info.batch.query import BaseBatchQuery, BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class _FakeChannel(BaseChannelAdapter):
    channel_name = "test"

    def __init__(self):
        self.disabled = False
        self._results: dict[str, dict | Exception] = {}
        self._validate_should_fail = False

    def _request(self, ip, **kwargs):
        return {}

    def fetch(self, ip, **kwargs):
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


class _FakeWriter:
    def __init__(self):
        self.writes = []

    def add_or_update_ip(self, ip, channel, data):
        self.writes.append((ip, channel, data))
        return True


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
    writer = _FakeWriter()
    return (
        BaseBatchQuery(
            channel_name="test",
            channel=ch,
            writer=writer,
            ips=ips,
            delay=delay,
            no_validate=no_validate,
            progress_tracker=progress_tracker,
            max_consecutive_network_failures=max_consecutive_network_failures,
        ),
        ch,
        writer,
    )


class TestBatchResult:
    def test_defaults(self):
        result = BatchResult()
        assert result.success_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed == 0.0
        assert result.stopped_early is False
        assert result.stop_reason == ""


class TestIPDeduplication:
    def test_deduplicates_ips(self):
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2", "1.1.1.1"])
        assert q.total_count == 2

    def test_preserves_order(self):
        q, ch, writer = _make_query(["3.3.3.3", "1.1.1.1", "2.2.2.2", "1.1.1.1"])
        q.run()
        written_ips = [w[0] for w in writer.writes]
        assert written_ips == ["3.3.3.3", "1.1.1.1", "2.2.2.2"]


class TestTotalCount:
    def test_returns_count(self):
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"])
        assert q.total_count == 3

    def test_empty_ips(self):
        q, _, _ = _make_query([])
        assert q.total_count == 0


class TestPendingCount:
    def test_without_tracker(self):
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"])
        assert q.pending_count == 2

    def test_with_tracker_none_processed(self):
        tracker = InMemoryProgressTracker()
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 2

    def test_with_tracker_one_processed(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 1

    def test_with_tracker_all_processed(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        tracker.mark_processed("2.2.2.2")
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        assert q.pending_count == 0


class TestRun:
    def test_run_returns_batch_result(self):
        q, _, _ = _make_query(["1.1.1.1"])
        result = q.run()
        assert isinstance(result, BatchResult)
        assert result.success_count == 1
        assert result.fail_count == 0
        assert result.total_elapsed >= 0

    def test_run_writes_all_ips_to_store(self):
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"])
        q.run()
        written_ips = {w[0] for w in writer.writes}
        assert written_ips == {"1.1.1.1", "2.2.2.2", "3.3.3.3"}

    def test_run_writes_correct_channel_name(self):
        q, _, writer = _make_query(["1.1.1.1"])
        q.run()
        assert writer.writes[0][1] == "test"

    def test_run_writes_data_for_each_ip(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = {"country": "US"}
        ch._results["2.2.2.2"] = {"country": "JP"}
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2"], channel=ch)
        q.run()
        assert writer.writes[0][2] == {"country": "US"}
        assert writer.writes[1][2] == {"country": "JP"}

    def test_run_empty_pending_does_nothing(self):
        q, _, _ = _make_query([])
        result = q.run()
        assert result.success_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed >= 0

    def test_run_delay_is_passed_to_channel(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = {"country": "CN"}
        q, _, writer = _make_query(["1.1.1.1"], delay=2.0, channel=ch)
        result = q.run()
        assert result.success_count == 1
        assert len(writer.writes) == 1


class TestRunProgressTracking:
    def test_run_no_tracker_processes_all(self):
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"])
        result = q.run()
        assert result.success_count == 2
        assert result.fail_count == 0

    def test_run_tracker_excludes_processed(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        result = q.run()
        assert result.success_count == 1
        written_ips = [w[0] for w in writer.writes]
        assert "1.1.1.1" not in written_ips
        assert "2.2.2.2" in written_ips

    def test_run_success_marks_progress(self):
        tracker = InMemoryProgressTracker()
        q, _, _ = _make_query(["1.1.1.1", "2.2.2.2"], progress_tracker=tracker)
        q.run()
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is True

    def test_run_channel_error_no_progress(self):
        tracker = InMemoryProgressTracker()
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        q, _, _ = _make_query(["1.1.1.1"], progress_tracker=tracker, channel=ch)
        q.run()
        assert tracker.is_processed("1.1.1.1") is False

    def test_run_permanent_error_no_progress(self):
        tracker = InMemoryProgressTracker()
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("permanent")
        q, _, _ = _make_query(["1.1.1.1"], progress_tracker=tracker, channel=ch)
        q.run()
        assert tracker.is_processed("1.1.1.1") is False


class TestRunErrorHandling:
    def test_run_success_writes_to_store(self):
        q, _, writer = _make_query(["1.1.1.1"])
        q.run()
        assert len(writer.writes) == 1
        assert writer.writes[0][0] == "1.1.1.1"

    def test_run_channel_error_does_not_write(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        q, _, writer = _make_query(["1.1.1.1"], channel=ch)
        q.run()
        assert len(writer.writes) == 0

    def test_run_permanent_error_stops_loop(self):
        ch = _FakeChannel()
        ch._results["2.2.2.2"] = ChannelPermanentError("permanent")
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"], channel=ch)
        result = q.run()
        assert result.stopped_early is True
        assert result.stop_reason == "permanent_error"
        assert result.fail_count == 1

    def test_run_permanent_error_skips_remaining(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("permanent")
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2", "3.3.3.3"], channel=ch)
        q.run()
        written_ips = [w[0] for w in writer.writes]
        assert "2.2.2.2" not in written_ips
        assert "3.3.3.3" not in written_ips

    def test_run_non_channel_error_propagates(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = RuntimeError("unexpected")
        q, _, _ = _make_query(["1.1.1.1"], channel=ch)
        with pytest.raises(RuntimeError, match="unexpected"):
            q.run()


class TestRunCircuitBreaking:
    def test_run_circuit_break_after_5_failures(self):
        ch = _FakeChannel()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5", "6.6.6.6"]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        q, _, _ = _make_query(ips, channel=ch)
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
        q, _, writer = _make_query(ips, channel=ch)
        result = q.run()
        assert result.success_count == 1
        assert result.fail_count == 7
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"
        written_ips = [w[0] for w in writer.writes]
        assert "3.3.3.3" in written_ips

    def test_run_custom_circuit_threshold(self):
        ch = _FakeChannel()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        q, _, _ = _make_query(ips, channel=ch, max_consecutive_network_failures=3)
        result = q.run()
        assert result.fail_count == 3
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"


class TestRunDependencyCheck:
    def test_run_disabled_skips_all(self):
        ch = _FakeChannel()
        ch.disabled = True
        q, _, writer = _make_query(["1.1.1.1", "2.2.2.2"], channel=ch, no_validate=True)
        result = q.run()
        assert result.success_count == 0
        assert result.fail_count == 0
        assert len(writer.writes) == 0

    def test_run_validate_failure_skips_all_queries(self):
        ch = _FakeChannel()
        ch._validate_should_fail = True
        q, _, writer = _make_query(["1.1.1.1"], channel=ch, no_validate=False)
        result = q.run()
        assert result.success_count == 0
        assert len(writer.writes) == 0

    def test_run_no_validate_true_allows_disabled_channel(self):
        ch = _FakeChannel()
        ch.disabled = True
        q, _, writer = _make_query(["1.1.1.1"], channel=ch, no_validate=True)
        result = q.run()
        assert result.success_count == 0
        assert len(writer.writes) == 0

    def test_run_no_validate_false_with_valid_channel_queries_normally(self):
        ch = _FakeChannel()
        q, _, writer = _make_query(["1.1.1.1"], channel=ch, no_validate=False)
        result = q.run()
        assert result.success_count == 1
        assert len(writer.writes) == 1
