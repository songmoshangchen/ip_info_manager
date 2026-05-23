import json
import os
from unittest.mock import patch

import pytest

from ip_info.store.json_store import IPWriter
from ip_info.store.protocols import IPDataWriter


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "json_store"


@pytest.fixture
def writer(storage_dir):
    storage_file = str(storage_dir / "test.json")
    return IPWriter(storage_file=storage_file)


class TestIPWriterProtocol:
    def test_满足_IPDataWriter_协议(self, writer):
        assert isinstance(writer, IPDataWriter)


class TestIPWriterFileCreation:
    def test_creates_file_and_dir_when_not_exist(self, tmp_path):
        storage_file = str(tmp_path / "deep" / "nested" / "data.json")
        IPWriter(storage_file=storage_file)
        assert os.path.isfile(storage_file)
        with open(storage_file, encoding="utf-8") as f:
            assert json.load(f) == {}


class TestIPWriterAddOrUpdate:
    def test_add_or_update_ip_writes_to_file(self, writer, storage_dir):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})

        file_path = storage_dir / "test.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "1.2.3.4" in data
        assert data["1.2.3.4"]["ip"] == "1.2.3.4"
        assert data["1.2.3.4"]["ipinfo"] == {"country": "CN"}

    def test_add_or_update_ip_appends_channel(self, writer, storage_dir):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})

        file_path = storage_dir / "test.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["1.2.3.4"]["ipinfo"] == {"country": "CN"}
        assert data["1.2.3.4"]["rdns"] == {"ptr": "host.example.com"}

    def test_add_or_update_ip_overwrites_channel(self, writer, storage_dir):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN", "org": "Old"})
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "US"})

        file_path = storage_dir / "test.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["1.2.3.4"]["ipinfo"] == {"country": "US"}
        assert "org" not in data["1.2.3.4"]["ipinfo"]


class TestIPWriterDeleteIP:
    def test_delete_ip_removes_from_file(self, writer, storage_dir):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("5.6.7.8", "rdns", {"ptr": "other.example.com"})

        result = writer.delete_ip("1.2.3.4")

        assert result is True
        file_path = storage_dir / "test.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "1.2.3.4" not in data
        assert "5.6.7.8" in data

    def test_delete_ip_returns_false_for_nonexistent(self, writer):
        result = writer.delete_ip("99.99.99.99")
        assert result is False


class TestIPWriterDeleteChannel:
    def test_delete_channel_removes_from_file(self, writer, storage_dir):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})

        result = writer.delete_channel("1.2.3.4", "rdns")

        assert result is True
        file_path = storage_dir / "test.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "rdns" not in data["1.2.3.4"]
        assert data["1.2.3.4"]["ipinfo"] == {"country": "CN"}

    def test_delete_channel_returns_false_for_nonexistent(self, writer):
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        assert writer.delete_channel("1.2.3.4", "nonexistent") is False
        assert writer.delete_channel("99.99.99.99", "ipinfo") is False


class TestIPWriterIOError:
    def test_io_error_on_write_propagates(self, writer):
        with patch("builtins.open", side_effect=PermissionError("拒绝访问")):
            with pytest.raises(PermissionError, match="拒绝访问"):
                writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
