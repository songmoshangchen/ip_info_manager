from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.store.json_store import IPReader, IPWriter
from ip_info.store.protocols import IPDataReader, IPDataWriter


class TestIPWriterProtocolConformance:
    def test_ipwriter_is_ipdatawriter(self, tmp_path):
        writer = IPWriter(storage_file=str(tmp_path / "test.json"))
        assert isinstance(writer, IPDataWriter)

    def test_in_memory_writer_is_ipdatawriter(self):
        writer = InMemoryIPWriter()
        assert isinstance(writer, IPDataWriter)


class TestIPReaderProtocolConformance:
    def test_ipreader_is_ipdatareader(self, tmp_path):
        reader = IPReader(storage_file=str(tmp_path / "test.json"))
        assert isinstance(reader, IPDataReader)

    def test_in_memory_reader_is_ipdatareader(self):
        reader = InMemoryIPReader()
        assert isinstance(reader, IPDataReader)


class TestInMemoryWriterAlsoReader:
    def test_in_memory_writer_is_also_ipdatareader(self):
        writer = InMemoryIPWriter()
        assert isinstance(writer, IPDataReader)


class TestImportFromPackage:
    def test_import_from_store_init(self):
        from ip_info.store import (
            InMemoryIPReader,
            InMemoryIPWriter,
            IPDataReader,
            IPDataWriter,
            IPReader,
            IPWriter,
        )

        assert IPDataWriter is not None
        assert IPDataReader is not None
        assert IPWriter is not None
        assert IPReader is not None
        assert InMemoryIPWriter is not None
        assert InMemoryIPReader is not None
