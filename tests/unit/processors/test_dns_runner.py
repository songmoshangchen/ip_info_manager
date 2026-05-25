from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from ip_info.batch.core.query import BatchResult
from ip_info.batch.core.runner import BatchRunner
from ip_info.processors.dns_verify.runner import (
    CHANNEL_NAME,
    BatchDnsVerify,
    _is_expired,
)
from ip_info.store.in_memory import InMemoryDomainCache, InMemoryIPWriter


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


class TestIsExpired:
    def test_old_time_is_expired(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        assert _is_expired({"verify_time": old_time}, 7) is True

    def test_recent_time_not_expired(self):
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert _is_expired({"verify_time": recent_time}, 7) is False

    def test_no_time_is_expired(self):
        assert _is_expired({}, 7) is True

    def test_invalid_time_is_expired(self):
        assert _is_expired({"verify_time": "not-a-date"}, 7) is True


class TestDefaultExpiredBehavior:
    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_expired_verify_warning_only_not_reverified(self, mock_batch_verify):
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

        assert result.success_count == 0
        assert result.skip_count == 1
        mock_batch_verify.assert_not_called()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_expired_verify_with_force_days_none_not_reverified(self, mock_batch_verify):
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

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, force_days=None)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 1
        mock_batch_verify.assert_not_called()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_recent_verify_still_skipped(self, mock_batch_verify):
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


class TestForceDaysBehavior:
    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_force_days_7_reverify_old_ips(self, mock_batch_verify):
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

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, force_days=7)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_force_days_0_reverify_all_ips(self, mock_batch_verify):
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

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, force_days=0)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_force_days_5_not_reverify_slightly_expired(self, mock_batch_verify):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})
        slightly_old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        writer.add_or_update_ip(
            "1.2.3.4",
            CHANNEL_NAME,
            {
                "matched": 1,
                "verify_time": slightly_old,
            },
        )

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, max_age_days=2, force_days=5)
        result = runner.run()

        assert result.success_count == 0
        assert result.skip_count == 1
        mock_batch_verify.assert_not_called()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_force_days_no_verify_data_verifies_normally(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, force_days=7)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()


class TestParameterValidation:
    def test_max_age_days_zero_raises_value_error(self):
        writer = InMemoryIPWriter()
        with pytest.raises(ValueError, match="max_age_days"):
            BatchDnsVerify(ips=[], writer=writer, reader=writer, max_age_days=0)

    def test_max_age_days_negative_raises_value_error(self):
        writer = InMemoryIPWriter()
        with pytest.raises(ValueError, match="max_age_days"):
            BatchDnsVerify(ips=[], writer=writer, reader=writer, max_age_days=-1)

    def test_force_days_negative_raises_value_error(self):
        writer = InMemoryIPWriter()
        with pytest.raises(ValueError, match="force_days"):
            BatchDnsVerify(ips=[], writer=writer, reader=writer, force_days=-1)

    def test_max_age_days_one_is_valid(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer, max_age_days=1)
        assert runner._max_age_days == 1

    def test_force_days_zero_is_valid(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer, force_days=0)
        assert runner._force_days == 0

    def test_force_days_none_is_valid(self):
        writer = InMemoryIPWriter()
        runner = BatchDnsVerify(ips=[], writer=writer, reader=writer, force_days=None)
        assert runner._force_days is None


class TestInMemoryDomainCache:
    def test_get_returns_none_for_missing(self):
        cache = InMemoryDomainCache()
        assert cache.get("example.com") is None

    def test_set_and_get(self):
        cache = InMemoryDomainCache()
        cache.set("example.com", {"status": "matched"})
        assert cache.get("example.com") == {"status": "matched"}

    def test_set_overwrites(self):
        cache = InMemoryDomainCache()
        cache.set("example.com", {"status": "matched"})
        cache.set("example.com", {"status": "changed"})
        assert cache.get("example.com") == {"status": "changed"}


class TestDomainCacheIntegration:
    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_cached_domains_skipped(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "b.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["a.com", "b.com"]})

        cache = InMemoryDomainCache()
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cache.set("a.com", {"status": "matched", "resolved_ips": ["1.2.3.4"], "verify_time": recent_time})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, domain_cache=cache)
        result = runner.run()

        assert result.success_count == 1
        assert mock_batch_verify.call_count == 1

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_verified_domains_are_cached(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})

        cache = InMemoryDomainCache()
        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, domain_cache=cache)
        runner.run()

        cached = cache.get("example.com")
        assert cached is not None
        assert cached["status"] == "matched"

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_no_domain_cache_verifies_all(self, mock_batch_verify):
        mock_batch_verify.return_value = [
            {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]},
        ]
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["example.com"]})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_called_once()

    @patch("ip_info.processors.dns_verify.runner.batch_verify")
    def test_all_domains_cached_skips_batch_verify(self, mock_batch_verify):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "aizhan", {"domains": ["a.com", "b.com"]})

        cache = InMemoryDomainCache()
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cache.set("a.com", {"status": "matched", "resolved_ips": ["1.2.3.4"], "verify_time": recent_time})
        cache.set("b.com", {"status": "changed", "resolved_ips": ["9.9.9.9"], "verify_time": recent_time})

        runner = BatchDnsVerify(ips=["1.2.3.4"], writer=writer, reader=writer, domain_cache=cache)
        result = runner.run()

        assert result.success_count == 1
        mock_batch_verify.assert_not_called()
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data["matched"] == 1
        assert channel_data["changed"] == 1
