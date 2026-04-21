import json
import os
from config import Settings


class IPWriter:
    def __init__(self):
        self.settings = Settings()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        storage_dir = self.settings.storage_dir
        if not os.path.isabs(storage_dir):
            storage_dir = os.path.join(script_dir, storage_dir)
        
        self.storage_file = os.path.join(storage_dir, self.settings.storage_name + '.json')
        
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
        
        self._init_storage()
    
    def _init_storage(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_data(self):
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    
    def _save_data(self, data):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_or_update_ip(self, ip, channel, data):
        all_data = self._load_data()
        
        if ip not in all_data:
            all_data[ip] = {"ip": ip}
        
        all_data[ip][channel] = data
        self._save_data(all_data)
        return True
    
    def delete_ip(self, ip):
        all_data = self._load_data()
        if ip in all_data:
            del all_data[ip]
            self._save_data(all_data)
            return True
        return False
    
    def delete_channel(self, ip, channel):
        all_data = self._load_data()
        if ip in all_data and channel in all_data[ip]:
            del all_data[ip][channel]
            self._save_data(all_data)
            return True
        return False


ip_writer = IPWriter()

ip_writer.add_or_update_ip(
    ip="192.168.1.100",
    channel="channel_name",
    data={
        "key1": "value1",
        "key2": 123,
        "key3": True,
        "key4": False
    }
)

ip_writer.add_or_update_ip(
    ip="192.168.1.100",
    channel="another_channel",
    data={
        "status": "active",
        "count": 5
    }
)

ip_writer.add_or_update_ip(
    ip="192.168.1.200",
    channel="channel_name",
    data={
        "name": "test",
        "enabled": True
    }
)
