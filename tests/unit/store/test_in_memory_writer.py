import pytest

from ip_info.store.in_memory import InMemoryIPWriter
from ip_info.store.protocols import IPDataWriter


class TestInMemoryIPWriter:

    @pytest.fixture
    def writer(self):
        return InMemoryIPWriter()

    def test_满足_IPDataWriter_协议(self, writer):
        assert isinstance(writer, IPDataWriter)

    def test_add_or_update_ip_creates_new_ip_record(self, writer):
        result = writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        store = writer.get_all()

        assert "1.2.3.4" in store
        assert store["1.2.3.4"]["ip"] == "1.2.3.4"
        assert store["1.2.3.4"]["ipinfo"] == {"country": "CN"}

    def test_add_or_update_ip_appends_channel_to_existing_ip(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})

        store = writer.get_all()
        assert store["1.2.3.4"]["ipinfo"] == {"country": "CN"}
        assert store["1.2.3.4"]["rdns"] == {"ptr": "host.example.com"}

    def test_add_or_update_ip_overwrites_existing_channel(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN", "org": "Old"})
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "US"})

        store = writer.get_all()
        assert store["1.2.3.4"]["ipinfo"] == {"country": "US"}
        assert "org" not in store["1.2.3.4"]["ipinfo"]

    def test_add_or_update_ip_returns_true(self, writer):
        result = writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        assert result is True

    def test_delete_ip_removes_entire_record(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("5.6.7.8", "rdns", {"ptr": "other.example.com"})

        result = writer.delete_ip("1.2.3.4")

        assert result is True
        assert "1.2.3.4" not in writer.get_all()
        assert "5.6.7.8" in writer.get_all()

    def test_delete_ip_returns_false_for_nonexistent(self, writer):
        result = writer.delete_ip("99.99.99.99")
        assert result is False

    def test_delete_channel_removes_only_specified_channel(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})

        result = writer.delete_channel("1.2.3.4", "rdns")

        assert result is True
        store = writer.get_all()
        assert "rdns" not in store["1.2.3.4"]
        assert store["1.2.3.4"]["ipinfo"] == {"country": "CN"}

    def test_delete_channel_returns_false_for_nonexistent_ip(self, writer):
        result = writer.delete_channel("99.99.99.99", "ipinfo")
        assert result is False

    def test_delete_channel_returns_false_for_nonexistent_channel(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        result = writer.delete_channel("1.2.3.4", "nonexistent")
        assert result is False
