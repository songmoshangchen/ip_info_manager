import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import InMemoryIPWriter


@pytest.fixture
def writer():
    return InMemoryIPWriter()


class TestInMemoryIPWriter:

    def test_add_or_update_ip_creates_new_ip_record(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {
            'hostname': 'example.com',
            'has_ptr': True,
        })

        stored = writer.get_all()
        assert '1.2.3.4' in stored
        assert stored['1.2.3.4']['ip'] == '1.2.3.4'
        assert stored['1.2.3.4']['rdns_ptr']['hostname'] == 'example.com'

    def test_add_or_update_ip_appends_channel_to_existing_ip(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True})
        writer.add_or_update_ip('1.2.3.4', 'ipinfo_api', {'country': 'CN'})

        stored = writer.get_all()
        assert 'rdns_ptr' in stored['1.2.3.4']
        assert 'ipinfo_api' in stored['1.2.3.4']
        assert stored['1.2.3.4']['ipinfo_api']['country'] == 'CN'

    def test_add_or_update_ip_overwrites_existing_channel(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {
            'has_ptr': False,
            'old_field': 'should_be_removed',
        })
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True, 'hostname': 'new.com'})

        stored = writer.get_all()
        assert stored['1.2.3.4']['rdns_ptr'] == {'has_ptr': True, 'hostname': 'new.com'}
        assert 'old_field' not in stored['1.2.3.4']['rdns_ptr']

    def test_add_or_update_ip_returns_true(self, writer):
        result = writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True})
        assert result is True

    def test_delete_ip_removes_entire_record(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True})
        writer.add_or_update_ip('5.6.7.8', 'rdns_ptr', {'has_ptr': False})

        result = writer.delete_ip('1.2.3.4')
        assert result is True
        assert '1.2.3.4' not in writer.get_all()
        assert '5.6.7.8' in writer.get_all()

    def test_delete_ip_returns_false_for_nonexistent(self, writer):
        result = writer.delete_ip('9.9.9.9')
        assert result is False

    def test_delete_channel_removes_only_specified_channel(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True})
        writer.add_or_update_ip('1.2.3.4', 'ipinfo_api', {'country': 'CN'})

        result = writer.delete_channel('1.2.3.4', 'rdns_ptr')
        assert result is True
        stored = writer.get_all()
        assert 'rdns_ptr' not in stored['1.2.3.4']
        assert 'ipinfo_api' in stored['1.2.3.4']

    def test_delete_channel_returns_false_for_nonexistent_ip(self, writer):
        result = writer.delete_channel('9.9.9.9', 'rdns_ptr')
        assert result is False

    def test_delete_channel_returns_false_for_nonexistent_channel(self, writer):
        writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'has_ptr': True})
        result = writer.delete_channel('1.2.3.4', 'ipinfo_api')
        assert result is False
