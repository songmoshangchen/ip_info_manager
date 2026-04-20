import socket
from datetime import datetime
import json
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    storage_dir: str = Field(default='data', description='存储目录')
    storage_filename: str = Field(default='ip_data.json', description='存储文件名')
    rdns_query_timeout: float = Field(default=3.0, description='RDNS 查询超时时间（秒）')
    rdns_query_delay: float = Field(default=0.5, description='RDNS 批量查询间隔（秒）')
    
    class Config:
        env_prefix = 'IP_'
        env_file = [
            '.env',
            '../.env'
        ]
        extra = 'ignore'


class IPWriter:
    def __init__(self):
        self.settings = Settings()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        storage_dir = self.settings.storage_dir
        if not os.path.isabs(storage_dir):
            storage_dir = os.path.join(script_dir, storage_dir)
        
        self.storage_file = os.path.join(storage_dir, self.settings.storage_filename)
        
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


def fetch_rdns_ptr(ip: str, timeout: float = 3.0) -> dict:
    """
    通过 DNS PTR 记录查询反向域名（RDNS）
    适配 IP 管理器的 rdns_ptr 渠道格式
    
    Args:
        ip: 要查询的 IP 地址
        timeout: 查询超时时间（秒）
    
    Returns:
        包含 RDNS 查询结果的字典
    """
    result = {
        "query_ip": ip,
        "query_time": datetime.now().isoformat()
    }
    
    try:
        socket.setdefaulttimeout(timeout)
        
        ptr_records = socket.gethostbyaddr(ip)
        
        result.update({
            "hostname": ptr_records[0],
            "aliases": ptr_records[1],
            "ip_addresses": ptr_records[2],
            "ptr_count": len(ptr_records[1]) + 1,
            "has_ptr": True
        })
        
    except socket.herror as e:
        result.update({
            "has_ptr": False,
            "error_type": "herror",
            "error_code": e.errno if hasattr(e, 'errno') else None,
            "error_message": str(e)
        })
        
    except socket.gaierror as e:
        result.update({
            "has_ptr": False,
            "error_type": "gaierror",
            "error_code": e.errno if hasattr(e, 'errno') else None,
            "error_message": str(e)
        })
        
    except socket.timeout:
        result.update({
            "has_ptr": False,
            "error_type": "timeout",
            "error_message": f"查询超时（超过 {timeout} 秒）"
        })
        
    except Exception as e:
        result.update({
            "raw_error": True,
            "has_ptr": False,
            "error_type": type(e).__name__,
            "error_message": str(e)
        })
    
    return result


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter()
    
    rdns_data = fetch_rdns_ptr(
        ip=ip,
        timeout=settings.rdns_query_timeout
    )
    ip_writer.add_or_update_ip(
        ip=ip,
        channel="rdns_ptr",
        data=rdns_data
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python rdns_ptr.py <IP地址>")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    main(target_ip)
