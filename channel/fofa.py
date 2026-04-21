import requests
from datetime import datetime
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import FofaSettings as Settings


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


def fetch_fofa_host_detail(ip: str, api_key: str) -> dict:
    """
    调用 Fofa API 获取 detail=true 的 host 数据
    适配 IP 管理器的 fofa 渠道格式
    """
    url = f"https://fofa.info/api/v1/host/{ip}"
    params = {
        "key": api_key,
        "detail": "true"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
        
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
            "query_time": datetime.now().isoformat()
        }


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter()
    
    fofa_data = fetch_fofa_host_detail(
        ip=ip,
        api_key=settings.fofa_api_key
    )
    ip_writer.add_or_update_ip(
        ip=ip,
        channel="fofa",
        data=fofa_data
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python fofa.py <IP地址>")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    main(target_ip)
