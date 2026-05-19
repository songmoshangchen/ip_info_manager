import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import IPDataWriter, IPDataReader
from writer import IPWriter
from reader import IPReader


@pytest.fixture
def storage_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def file_writer(storage_dir):
    return IPWriter(storage_dir=storage_dir)


@pytest.fixture
def file_reader(storage_dir, file_writer):
    return IPReader(storage_dir=storage_dir)


class TestIPWriterProtocolConformance:

    def test_ipwriter_is_ipdatawriter(self, file_writer):
        assert isinstance(file_writer, IPDataWriter)

    def test_ipwriter_has_required_methods(self):
        assert hasattr(IPWriter, 'add_or_update_ip')
        assert hasattr(IPWriter, 'delete_ip')
        assert hasattr(IPWriter, 'delete_channel')


class TestIPReaderProtocolConformance:

    def test_ipreader_is_ipdatareader(self, file_reader):
        assert isinstance(file_reader, IPDataReader)

    def test_ipreader_has_required_methods(self):
        assert hasattr(IPReader, 'get_ip_data')
        assert hasattr(IPReader, 'get_channel_data')
        assert hasattr(IPReader, 'list_all_ips')
        assert hasattr(IPReader, 'list_ip_channels')
        assert hasattr(IPReader, 'search_ips_by_channel')


class TestIPWriterThroughProtocol:

    def test_write_through_protocol_interface(self, file_writer, file_reader):
        writer: IPDataWriter = file_writer
        writer.add_or_update_ip('10.0.0.1', 'test_ch', {'key': 'val'})

        reader: IPDataReader = file_reader
        assert reader.get_channel_data('10.0.0.1', 'test_ch') == {'key': 'val'}

    def test_delete_ip_through_protocol_interface(self, file_writer, file_reader):
        writer: IPDataWriter = file_writer
        writer.add_or_update_ip('10.0.0.1', 'ch1', {'a': 1})
        writer.add_or_update_ip('10.0.0.2', 'ch1', {'b': 2})

        assert writer.delete_ip('10.0.0.1') is True

        reader: IPDataReader = file_reader
        assert reader.get_ip_data('10.0.0.1') is None
        assert reader.get_ip_data('10.0.0.2') is not None

    def test_delete_channel_through_protocol_interface(self, file_writer, file_reader):
        writer: IPDataWriter = file_writer
        writer.add_or_update_ip('10.0.0.1', 'ch1', {'a': 1})
        writer.add_or_update_ip('10.0.0.1', 'ch2', {'b': 2})

        assert writer.delete_channel('10.0.0.1', 'ch1') is True

        reader: IPDataReader = file_reader
        assert reader.get_channel_data('10.0.0.1', 'ch1') is None
        assert reader.get_channel_data('10.0.0.1', 'ch2') == {'b': 2}


class TestIPReaderThroughProtocol:

    def test_read_through_protocol_interface(self, file_writer, file_reader):
        file_writer.add_or_update_ip('10.0.0.1', 'rdns', {'host': 'test.com'})
        file_writer.add_or_update_ip('10.0.0.2', 'rdns', {'host': 'other.com'})

        reader: IPDataReader = file_reader
        assert reader.get_ip_data('10.0.0.1')['rdns']['host'] == 'test.com'
        assert reader.get_channel_data('10.0.0.1', 'rdns') == {'host': 'test.com'}
        assert sorted(reader.list_all_ips()) == ['10.0.0.1', '10.0.0.2']
        assert reader.list_ip_channels('10.0.0.1') == ['rdns']
        assert reader.search_ips_by_channel('rdns', 'host', 'test.com') == ['10.0.0.1']
