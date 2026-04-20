import socket
from datetime import datetime
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import WhoisSettings as Settings
try:
    from whois import whois as whois_query
except ImportError:
    whois_query = None


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


def fetch_whois(ip: str, timeout: float = 10.0) -> dict:
    """
    通过 Whois 查询 IP 或域名的注册信息
    适配 IP 管理器的 whois 渠道格式
    
    Args:
        ip: 要查询的 IP 地址或域名
        timeout: 查询超时时间（秒）
    
    Returns:
        包含 Whois 查询结果的字典
    """
    result = {
        "query_target": ip,
        "query_time": datetime.now().isoformat()
    }
    
    if whois_query is None:
        result.update({
            "has_whois": False,
            "error_type": "ImportError",
            "error_message": "whois 库未安装，请运行: pip install python-whois"
        })
        return result
    
    try:
        socket.setdefaulttimeout(timeout)
        w = whois_query(ip)
        
        if w is None:
            result.update({
                "has_whois": False,
                "error_message": "未找到 Whois 信息"
            })
            return result
        
        whois_data = {}
        
        if w.domain_name:
            whois_data["domain_name"] = w.domain_name if isinstance(w.domain_name, str) else (w.domain_name[0] if w.domain_name and len(w.domain_name) > 0 else None)
        
        if w.registrar:
            whois_data["registrar"] = w.registrar if isinstance(w.registrar, str) else (w.registrar[0] if w.registrar and len(w.registrar) > 0 else None)
        
        if w.org:
            whois_data["organization"] = w.org if isinstance(w.org, str) else (w.org[0] if w.org and len(w.org) > 0 else None)
        
        if w.country:
            whois_data["country"] = w.country if isinstance(w.country, str) else (w.country[0] if w.country and len(w.country) > 0 else None)
        
        if w.state:
            whois_data["state"] = w.state if isinstance(w.state, str) else (w.state[0] if w.state and len(w.state) > 0 else None)
        
        if w.city:
            whois_data["city"] = w.city if isinstance(w.city, str) else (w.city[0] if w.city and len(w.city) > 0 else None)
        
        if w.address:
            whois_data["address"] = w.address if isinstance(w.address, str) else (w.address[0] if w.address and len(w.address) > 0 else None)
        
        if w.name:
            whois_data["registrant_name"] = w.name if isinstance(w.name, str) else (w.name[0] if w.name and len(w.name) > 0 else None)
        
        if w.emails:
            whois_data["emails"] = w.emails if isinstance(w.emails, str) else (w.emails[0] if w.emails and len(w.emails) > 0 else None)
        
        if w.creation_date:
            creation_date = w.creation_date[0] if isinstance(w.creation_date, list) and len(w.creation_date) > 0 else w.creation_date
            whois_data["creation_date"] = creation_date.isoformat() if hasattr(creation_date, 'isoformat') else str(creation_date)
        
        if w.expiration_date:
            expiration_date = w.expiration_date[0] if isinstance(w.expiration_date, list) and len(w.expiration_date) > 0 else w.expiration_date
            whois_data["expiration_date"] = expiration_date.isoformat() if hasattr(expiration_date, 'isoformat') else str(expiration_date)
        
        if w.updated_date:
            updated_date = w.updated_date[0] if isinstance(w.updated_date, list) and len(w.updated_date) > 0 else w.updated_date
            whois_data["updated_date"] = updated_date.isoformat() if hasattr(updated_date, 'isoformat') else str(updated_date)
        
        if w.name_servers:
            whois_data["name_servers"] = w.name_servers if isinstance(w.name_servers, list) else ([w.name_servers] if w.name_servers else [])
        
        whois_data["status"] = w.status if isinstance(w.status, list) else ([w.status] if w.status else [])
        
        whois_data["dnssec"] = w.dnssec if hasattr(w, 'dnssec') else None
        
        result.update({
            "has_whois": True,
            "whois_data": whois_data
        })
        
    except socket.timeout:
        result.update({
            "has_whois": False,
            "error_type": "timeout",
            "error_message": f"查询超时（超过 {timeout} 秒）"
        })
        
    except Exception as e:
        result.update({
            "raw_error": True,
            "has_whois": False,
            "error_type": type(e).__name__,
            "error_message": str(e)
        })
    
    return result


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter()
    
    whois_data = fetch_whois(
        ip=ip,
        timeout=settings.whois_query_timeout
    )
    ip_writer.add_or_update_ip(
        ip=ip,
        channel="whois",
        data=whois_data
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python whois.py <IP地址或域名>")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    main(target_ip)
