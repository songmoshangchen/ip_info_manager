import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import ChannelFetcher


class TestChannelFetcherProtocolConformance:

    def test_fetch_channel_functions_satisfy_protocol(self):
        from channel.rdns_ptr import fetch_channel

        assert isinstance(fetch_channel, ChannelFetcher)

    def test_channel_fetcher_protocol_defines_callable(self):
        assert hasattr(ChannelFetcher, '__call__')


class TestChannelBaseApplyDelay:

    def test_apply_delay_returns_immediately_for_zero(self):
        from channel.base import apply_delay

        import time
        start = time.monotonic()
        apply_delay(0)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    def test_apply_delay_sleeps_for_positive_delay(self):
        from channel.base import apply_delay

        import time
        start = time.monotonic()
        apply_delay(0.1)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.09

    def test_apply_delay_does_not_sleep_for_negative(self):
        from channel.base import apply_delay

        import time
        start = time.monotonic()
        apply_delay(-1)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1


class TestChannelBaseFormatOutput:

    def test_format_output_adds_query_time(self):
        from channel.base import format_output

        data = {'country': 'CN'}
        result = format_output(data)
        assert 'query_time' in result
        assert result['country'] == 'CN'

    def test_format_output_does_not_overwrite_existing_query_time(self):
        from channel.base import format_output

        data = {'query_time': '2024-01-01T00:00:00', 'country': 'CN'}
        result = format_output(data)
        assert result['query_time'] == '2024-01-01T00:00:00'

    def test_format_output_preserves_all_fields(self):
        from channel.base import format_output

        data = {'hostname': 'test.com', 'has_ptr': True, 'ttl': 300}
        result = format_output(data)
        assert result['hostname'] == 'test.com'
        assert result['has_ptr'] is True
        assert result['ttl'] == 300

    def test_format_output_handles_empty_dict(self):
        from channel.base import format_output

        result = format_output({})
        assert 'query_time' in result
        assert len(result) == 1

    def test_format_output_handles_error_dict(self):
        from channel.base import format_output

        data = {'raw_error': True, 'error_message': 'timeout'}
        result = format_output(data)
        assert result['raw_error'] is True
        assert result['error_message'] == 'timeout'
        assert 'query_time' in result

    def test_format_output_does_not_mutate_input(self):
        from channel.base import format_output

        data = {'country': 'CN'}
        format_output(data)
        assert 'query_time' not in data
