from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ip_info.batch.core.query import BatchResult
from ip_info.batch.core.runner import BatchRunner
from ip_info.processors.dns_verify.runner import (
    CHANNEL_NAME,
    BatchDnsVerify,
    _is_verify_expired,
)
from ip_info.store.in_memory import InMemoryIPWriter


class TestBatchRunnerProtocolConformance:
    def test_isinstance_batch_runner(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer)
        assert isinstance(runner, BatchRunner)

    def test_has_run_method(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer)
        assert hasattr(runner, "run")
        assert callable(runner.run)


class TestNormalFlow:
    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_ip_with_domain_data_verified_and_written(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data is not None
        assert channel_data["matched"] == 1
        assert channel_data["total_domains"] == 1

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_writer_called_with_domain_verify_channel(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "chinaz", {"domains": [{"domain": "example.com"}]})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        runner.run()

        ip_data = writer.get_ip_data("1.2.3.4")
        assert ip_data is not None
        assert CHANNEL_NAME in ip_data

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_multiple_ips(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
            {"domain": "b.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.1.1.1", "aizhan", {"domains": ["a.com"]})
        writer.add_or_update_ip("2.2.2.2", "chinaz", {"domains": [{"domain": "b.com"}]})

        runner = BatchDnsVerify(ips=["1.1.1.1", "2.2.2.2"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 2
        assert result.skip_count == 0

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_verify_data_has_stats(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
            {"domain": "b.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.1.1.1", "aizhan", {"domains": ["a.com", "b.com"]})

        runner = BatchDnsVerify(ips=["1.1.1.1"], writer=writer, reader=writer)
        runner.run()

        channel_data = writer.get_channel_data("1.1.1.1", CHANNEL_NAME)
        assert channel_data["total_domains"] == 2
        assert channel_data["matched"] == 1
        assert channel_data["changed"] == 1
        assert channel_data["unresolved"] == 0
        assert channel_data["timeout"] == 0
        assert channel_data["error"] == 0
        assert "verify_time" in channel_data
        assert len(channel_data["results"]) == 2


class TestSkipIPsWithNoData:
    def test_ip_without_data_is_skipped(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=["10.0.0.1"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 1
        assert writer.get_channel_data("10.0.0.1", CHANNEL_NAME) is None

    def test_ip_with_data_but_no_domains_is_skipped(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": []})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 1

    def test_mixed_ips_skip_only_no_data(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["a.com"]})

        with patch("ip_info.processors.dns_verify.runner.batch_verify") as mock_batch_verify:
            mock_batch_verify.return_value = [
                {"domain": "a.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
            ]
            runner = BatchDnsVerify(ips=["1.2.3.4", "10.0.0.1"], writer=writer, reader=writer)
            result = runner.run()

        assert result.success_count == 1
        assert result.skip_count == 1


class TestEmptyInput:
    def test_empty_ip_list_returns_zero_counts(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 0
        assert isinstance(result, BatchResult)

    def test_empty_ip_list_total_elapsed_positive(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer)
        result = runner.run()

        assert result.total_elapsed >= 0


class TestFullReprocessing:
    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_expired_verify_data_is_reverified(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        writer.add_or_update_ip(
            "1.2.3.4",
            CHANNEL_NAME,
            {
                "matched": 100,
                "changed": 0,
                "total_domains": 100,
                "verify_time": old_time,
            },
        )

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data["matched"] == 0
        assert channel_data["changed"] == 1
        assert channel_data["total_domains"] == 1


class TestVerifyExpiry:
    def test_is_verify_expired_with_old_time(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        assert _is_verify_expired({"verify_time": old_time}, 7) is True

    def test_is_verify_expired_with_recent_time(self):
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert _is_verify_expired({"verify_time": recent_time}, 7) is False

    def test_is_verify_expired_with_no_time(self):
        assert _is_verify_expired({}, 7) is True

    def test_is_verify_expired_with_invalid_time(self):
        assert _is_verify_expired({"verify_time": "not-a-date"}, 7) is True

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_recent_verify_skipped(self, mock_batch_verify):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        writer.add_or_update_ip(
            "1.2.3.4",
            CHANNEL_NAME,
            {
                "matched": 1,
                "verify_time": recent_time,
            },
        )

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 1
        mock_batch_verify.assert_not_called()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_expired_verify_triggers_reverify(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        writer.add_or_update_ip(
            "1.2.3.4",
            CHANNEL_NAME,
            {
                "matched": 0,
                "verify_time": old_time,
            },
        )

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_max_age_days_zero_always_reverify(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})
        recent_time = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        writer.add_or_update_ip(
            "1.2.3.4",
            CHANNEL_NAME,
            {
                "matched": 1,
                "verify_time": recent_time,
            },
        )

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, max_age_days=0)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()
