import json
import os
from unittest.mock import patch

import pytest

from ip_info.store.json_store import IPWriter, IPReader
from ip_info.store.protocols import IPDataReader


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "json_store"


@pytest.fixture
def file_writer(storage_dir):
    storage_file = str(storage_dir / "test.json")
    return IPWriter(storage_file=storage_file)


@pytest.fixture
def file_reader(storage_dir, file_writer):
    storage_file = str(storage_dir / "test.json")
    return IPReader(storage_file=storage_file)


def _populate_writer(writer):
    writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN", "org": "ISP-A"})
    writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})
    writer.add_or_update_ip("5.6.7.8", "ipinfo", {"country": "US", "org": "ISP-B"})
    writer.add_or_update_ip("5.6.7.8", "fofa", {"title": "Web Server"})
    writer.add_or_update_ip("10.0.0.1", "rdns", {"ptr": "internal.local"})


class TestIPReaderProtocol:

    def test_满足_IPDataReader_协议(self, file_reader):
        assert isinstance(file_reader, IPDataReader)


class TestIPReaderGetIPData:

    def test_get_ip_data_returns_record(self, file_writer, file_reader):
        _populate_writer(file_writer)
        record = file_reader.get_ip_data("1.2.3.4")
        assert record is not None
        assert record["ip"] == "1.2.3.4"
        assert record["ipinfo"] == {"country": "CN", "org": "ISP-A"}
        assert record["rdns"] == {"ptr": "host.example.com"}

    def test_get_ip_data_returns_none_for_nonexistent(self, file_reader):
        assert file_reader.get_ip_data("99.99.99.99") is None


class TestIPReaderGetChannelData:

    def test_get_channel_data_returns_dict(self, file_writer, file_reader):
        _populate_writer(file_writer)
        data = file_reader.get_channel_data("1.2.3.4", "ipinfo")
        assert data == {"country": "CN", "org": "ISP-A"}


class TestIPReaderListAllIPs:

    def test_list_all_ips_returns_keys(self, file_writer, file_reader):
        _populate_writer(file_writer)
        ips = file_reader.list_all_ips()
        assert set(ips) == {"1.2.3.4", "5.6.7.8", "10.0.0.1"}


class TestIPReaderFileNotExist:

    def test_file_not_exist_returns_empty(self, tmp_path):
        storage_file = str(tmp_path / "nonexistent" / "missing.json")
        reader = IPReader(storage_file=storage_file)
        assert reader.get_ip_data("1.2.3.4") is None
        assert reader.list_all_ips() == []


class TestIPReaderEndToEnd:

    def test_end_to_end_write_read(self, storage_dir):
        storage_file = str(storage_dir / "e2e.json")
        writer = IPWriter(storage_file=storage_file)
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})

        reader = IPReader(storage_file=storage_file)
        record = reader.get_ip_data("1.2.3.4")
        assert record is not None
        assert record["ipinfo"] == {"country": "CN"}

    def test_end_to_end_batch_query(self, storage_dir):
        storage_file = str(storage_dir / "batch.json")
        writer = IPWriter(storage_file=storage_file)
        writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN"})
        writer.add_or_update_ip("5.6.7.8", "ipinfo", {"country": "US"})
        writer.add_or_update_ip("10.0.0.1", "rdns", {"ptr": "internal.local"})

        reader = IPReader(storage_file=storage_file)
        batch = reader.get_ips_data(["1.2.3.4", "5.6.7.8", "99.99.99.99"])
        assert len(batch) == 2
        assert "1.2.3.4" in batch
        assert "5.6.7.8" in batch
        assert "99.99.99.99" not in batch

        all_data = reader.list_all_ips_data()
        assert len(all_data) == 3

        all_data_excluded = reader.list_all_ips_data(exclude_ips=["10.0.0.1"])
        assert len(all_data_excluded) == 2
        assert "10.0.0.1" not in all_data_excluded


class TestIPReaderIOError:

    def test_io_error_on_read_propagates(self, file_reader):
        with patch("builtins.open", side_effect=PermissionError("拒绝访问")):
            with pytest.raises(PermissionError, match="拒绝访问"):
                file_reader.get_ip_data("1.2.3.4")
