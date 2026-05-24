"""测试 run_concurrent() 并发批量查询"""

import threading

import pytest

from ip_info.batch.core.concurrent import run_concurrent
from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.utils.progress import InMemoryProgressTracker


class _FakeChannel(BaseChannelAdapter):
    channel_name = "test"

    def __init__(self):
        self.disabled = False
        self._results: dict[str, dict | Exception] = {}
        self._validate_should_fail = False
        self._fetch_delay_records: list[float] = []

    def _request(self, ip, **kwargs):
        return {}

    def fetch(self, ip, **kwargs):
        if "delay" in kwargs:
            self._fetch_delay_records.append(kwargs["delay"])
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
        self._lock = threading.Lock()

    def add_or_update_ip(self, ip, channel, data):
        with self._lock:
            self.writes.append((ip, channel, data))
        return True


def _run(
    ips,
    *,
    workers=1,
    delay=0,
    no_validate=False,
    progress_tracker=None,
    max_consecutive_network_failures=5,
    channel=None,
):
    ch = channel or _FakeChannel()
    writer = _FakeWriter()
    result = run_concurrent(
        ips=ips,
        channel=ch,
        writer=writer,
        channel_name="test",
        workers=workers,
        delay=delay,
        no_validate=no_validate,
        progress_tracker=progress_tracker,
        max_consecutive_network_failures=max_consecutive_network_failures,
    )
    return result, ch, writer


class TestRunConcurrentBasic:
    def test_returns_batch_result(self):
        result, _, _ = _run(["1.1.1.1"])
        assert isinstance(result, BatchResult)
        assert result.success_count == 1
        assert result.fail_count == 0
        assert result.total_elapsed >= 0

    def test_writes_all_ips(self):
        result, _, writer = _run(["1.1.1.1", "2.2.2.2", "3.3.3.3"])
        assert result.success_count == 3
        written_ips = {w[0] for w in writer.writes}
        assert written_ips == {"1.1.1.1", "2.2.2.2", "3.3.3.3"}

    def test_deduplicates_ips(self):
        result, _, _ = _run(["1.1.1.1", "2.2.2.2", "1.1.1.1"])
        assert result.success_count == 2

    def test_empty_ips(self):
        result, _, _ = _run([])
        assert result.success_count == 0
        assert result.fail_count == 0

    def test_writes_correct_channel_name(self):
        _, _, writer = _run(["1.1.1.1"])
        assert writer.writes[0][1] == "test"


class TestRunConcurrentWorkers1Degeneration:
    def test_workers_1_same_as_base_query(self):
        """workers=1 应退化为 BaseBatchQuery.run()"""
        result, _, _ = _run(["1.1.1.1", "2.2.2.2"], workers=1)
        assert result.success_count == 2
        assert result.fail_count == 0

    def test_workers_0_same_as_base_query(self):
        """workers=0 应退化为 BaseBatchQuery.run()"""
        result, _, _ = _run(["1.1.1.1"], workers=0)
        assert result.success_count == 1


class TestRunConcurrentMultiWorkers:
    def test_multi_workers_writes_all(self):
        result, _, writer = _run(
            ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"],
            workers=4,
        )
        assert result.success_count == 4
        written_ips = {w[0] for w in writer.writes}
        assert written_ips == {"1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"}

    def test_multi_workers_custom_data(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = {"country": "US"}
        ch._results["2.2.2.2"] = {"country": "JP"}
        result, _, writer = _run(["1.1.1.1", "2.2.2.2"], workers=2, channel=ch)
        assert result.success_count == 2
        data_map = {w[0]: w[2] for w in writer.writes}
        assert data_map["1.1.1.1"] == {"country": "US"}
        assert data_map["2.2.2.2"] == {"country": "JP"}


class TestRunConcurrentProgressTracking:
    def test_tracker_excludes_processed(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        result, _, writer = _run(
            ["1.1.1.1", "2.2.2.2"],
            workers=2,
            progress_tracker=tracker,
        )
        assert result.success_count == 1
        written_ips = [w[0] for w in writer.writes]
        assert "1.1.1.1" not in written_ips
        assert "2.2.2.2" in written_ips

    def test_success_marks_progress(self):
        tracker = InMemoryProgressTracker()
        _run(["1.1.1.1", "2.2.2.2"], workers=2, progress_tracker=tracker)
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is True

    def test_channel_error_no_progress(self):
        tracker = InMemoryProgressTracker()
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        _run(["1.1.1.1"], workers=2, progress_tracker=tracker, channel=ch)
        assert tracker.is_processed("1.1.1.1") is False


class TestRunConcurrentErrorHandling:
    def test_channel_error_does_not_write(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelError("temp")
        result, _, writer = _run(["1.1.1.1"], workers=2, channel=ch)
        assert result.fail_count == 1
        assert len(writer.writes) == 0

    def test_permanent_error_stops_early(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("permanent")
        result, _, _ = _run(
            ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
            workers=2,
            channel=ch,
        )
        assert result.stopped_early is True
        assert result.stop_reason == "permanent_error"

    def test_non_channel_error_propagates(self):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = RuntimeError("unexpected")
        with pytest.raises(RuntimeError, match="unexpected"):
            _run(["1.1.1.1"], workers=2, channel=ch)


class TestRunConcurrentCircuitBreaking:
    def test_circuit_break_after_threshold(self):
        ch = _FakeChannel()
        ips = [f"{i}.{i}.{i}.{i}" for i in range(1, 7)]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        result, _, _ = _run(ips, workers=2, channel=ch)
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"

    def test_custom_circuit_threshold(self):
        ch = _FakeChannel()
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        result, _, _ = _run(ips, workers=2, channel=ch, max_consecutive_network_failures=3)
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"

    def test_success_resets_circuit_counter(self):
        ch = _FakeChannel()
        # 2 个失败，1 个成功，再 5 个失败 -> 不应该在第 5 个失败时熔断
        # 因为成功重置了计数器
        ch._results["1.1.1.1"] = ChannelError("fail")
        ch._results["2.2.2.2"] = ChannelError("fail")
        # 3.3.3.3 成功（默认）
        ch._results["4.4.4.4"] = ChannelError("fail")
        ch._results["5.5.5.5"] = ChannelError("fail")
        ch._results["6.6.6.6"] = ChannelError("fail")
        ch._results["7.7.7.7"] = ChannelError("fail")
        ch._results["8.8.8.8"] = ChannelError("fail")
        ips = [
            "1.1.1.1",
            "2.2.2.2",
            "3.3.3.3",
            "4.4.4.4",
            "5.5.5.5",
            "6.6.6.6",
            "7.7.7.7",
            "8.8.8.8",
        ]
        result, _, writer = _run(ips, workers=1, channel=ch)
        assert result.success_count == 1
        assert result.stopped_early is True
        assert result.stop_reason == "circuit_break"


class TestRunConcurrentProgressLogging:
    def test_success_logs_progress_counter(self, caplog):
        result, _, _ = _run(["1.1.1.1", "2.2.2.2", "3.3.3.3"], workers=2)
        assert result.success_count == 3
        with caplog.at_level("INFO"):
            _run(["1.1.1.1", "2.2.2.2", "3.3.3.3"], workers=2)
        progress_logs = [r for r in caplog.records if "进度" in r.message]
        assert len(progress_logs) == 3
        assert "1/3" in progress_logs[0].message
        assert "2/3" in progress_logs[1].message
        assert "3/3" in progress_logs[2].message

    def test_failure_logs_progress_counter(self, caplog):
        ch = _FakeChannel()
        ch._results["2.2.2.2"] = ChannelError("fail")
        with caplog.at_level("INFO"):
            _run(["1.1.1.1", "2.2.2.2", "3.3.3.3"], workers=2, channel=ch)
        fail_warnings = [r for r in caplog.records if r.levelname == "WARNING" and "查询失败" in r.message]
        assert len(fail_warnings) >= 1
        for record in fail_warnings:
            assert "2.2.2.2" in record.message


class TestRunConcurrentWarningLogging:
    def test_permanent_error_logs_warning(self, caplog):
        ch = _FakeChannel()
        ch._results["1.1.1.1"] = ChannelPermanentError("key invalid")
        with caplog.at_level("WARNING"):
            _run(["1.1.1.1", "2.2.2.2"], workers=2, channel=ch)
        assert any("永久错误" in r.message for r in caplog.records)

    def test_circuit_break_logs_warning(self, caplog):
        ch = _FakeChannel()
        ips = [f"{i}.{i}.{i}.{i}" for i in range(1, 7)]
        for ip in ips:
            ch._results[ip] = ChannelError("fail")
        with caplog.at_level("WARNING"):
            _run(ips, workers=2, channel=ch)
        assert any("熔断" in r.message for r in caplog.records)


class TestRunConcurrentDependencyCheck:
    def test_disabled_channel_returns_empty(self, caplog):
        ch = _FakeChannel()
        ch.disabled = True
        with caplog.at_level("WARNING"):
            result, _, writer = _run(
                ["1.1.1.1", "2.2.2.2"],
                workers=2,
                channel=ch,
                no_validate=True,
            )
        assert result.success_count == 0
        assert result.fail_count == 2
        assert len(writer.writes) == 0
        assert "渠道已禁用" in caplog.text

    def test_validate_failure_skips_queries(self):
        ch = _FakeChannel()
        ch._validate_should_fail = True
        result, _, writer = _run(
            ["1.1.1.1"],
            workers=2,
            channel=ch,
            no_validate=False,
        )
        assert result.success_count == 0
        assert len(writer.writes) == 0
