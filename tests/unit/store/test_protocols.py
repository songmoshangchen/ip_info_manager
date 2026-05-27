from ip_info.store.protocols import IPDataReader, IPDataWriter


class StubWriter:
    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool:
        return True

    def delete_ip(self, ip: str) -> bool:
        return True

    def delete_channel(self, ip: str, channel: str) -> bool:
        return True


class StubReader:
    def get_ip_data(self, ip: str) -> dict | None:
        return None

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        return None

    def list_all_ips(self) -> list[str]:
        return []

    def list_ip_channels(self, ip: str) -> list[str]:
        return []

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        return []

    def get_ips_data(self, ips: list[str]) -> dict[str, dict]:
        return {}

    def list_all_ips_data(self, exclude_ips: list[str] | None = None) -> dict[str, dict]:
        return {}


class IncompleteWriter:
    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool:
        return True


class TestIPDataWriterProtocol:
    def test_stub_writer_is_instance(self):
        stub = StubWriter()
        assert isinstance(stub, IPDataWriter)

    def test_incomplete_writer_is_not_instance(self):
        stub = IncompleteWriter()
        assert not isinstance(stub, IPDataWriter)


class TestIPDataReaderProtocol:
    def test_stub_reader_is_instance(self):
        stub = StubReader()
        assert isinstance(stub, IPDataReader)

    def test_incomplete_class_is_not_reader_instance(self):
        stub = IncompleteWriter()
        assert not isinstance(stub, IPDataReader)
