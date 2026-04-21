import json
import os
import argparse
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


def main():
    parser = argparse.ArgumentParser(description='IP 数据写入器')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    add_parser = subparsers.add_parser('add', help='添加或更新 IP 数据')
    add_parser.add_argument('ip', help='IP 地址')
    add_parser.add_argument('channel', help='渠道名称')
    add_parser.add_argument('data', nargs='+', help='数据键值对，格式为 key=value')
    
    delete_ip_parser = subparsers.add_parser('delete-ip', help='删除整个 IP')
    delete_ip_parser.add_argument('ip', help='IP 地址')
    
    delete_channel_parser = subparsers.add_parser('delete-channel', help='删除 IP 的某个渠道')
    delete_channel_parser.add_argument('ip', help='IP 地址')
    delete_channel_parser.add_argument('channel', help='渠道名称')
    
    args = parser.parse_args()
    writer = IPWriter()
    
    if args.command == 'add':
        try:
            data = {}
            for item in args.data:
                if '=' in item:
                    key, value = item.split('=', 1)
                    try:
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        elif value.isdigit():
                            value = int(value)
                        elif '.' in value and all(part.isdigit() for part in value.split('.')):
                            value = float(value)
                    except:
                        pass
                    data[key] = value
            if not data:
                print("错误: 请提供有效的数据键值对")
                return
            writer.add_or_update_ip(args.ip, args.channel, data)
            print(f"成功添加/更新 IP {args.ip} 的 {args.channel} 渠道数据")
        except Exception as e:
            print(f"错误: {e}")
    
    elif args.command == 'delete-ip':
        if writer.delete_ip(args.ip):
            print(f"成功删除 IP {args.ip}")
        else:
            print(f"错误: 未找到 IP {args.ip}")
    
    elif args.command == 'delete-channel':
        if writer.delete_channel(args.ip, args.channel):
            print(f"成功删除 IP {args.ip} 的 {args.channel} 渠道数据")
        else:
            print(f"错误: 未找到 IP {args.ip} 或渠道 {args.channel}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
