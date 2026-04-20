import json
import os
import argparse
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    storage_dir: str = Field(default='data', description='存储目录')
    storage_filename: str = Field(default='ip_data.json', description='存储文件名')
    
    class Config:
        env_prefix = 'IP_'
        env_file = '.env'
        extra = 'ignore'


class IPReader:
    def __init__(self):
        self.settings = Settings()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        storage_dir = self.settings.storage_dir
        if not os.path.isabs(storage_dir):
            storage_dir = os.path.join(script_dir, storage_dir)
        
        self.storage_file = os.path.join(storage_dir, self.settings.storage_filename)
    
    def _load_data(self):
        if not os.path.exists(self.storage_file):
            return {}
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    
    def get_ip_data(self, ip):
        all_data = self._load_data()
        return all_data.get(ip, None)
    
    def get_channel_data(self, ip, channel):
        ip_data = self.get_ip_data(ip)
        if ip_data and channel in ip_data:
            return ip_data[channel]
        return None
    
    def list_all_ips(self):
        all_data = self._load_data()
        return list(all_data.keys())
    
    def list_ip_channels(self, ip):
        ip_data = self.get_ip_data(ip)
        if ip_data:
            channels = [key for key in ip_data.keys() if key != 'ip']
            return channels
        return []
    
    def search_ips_by_channel(self, channel, key=None, value=None):
        all_data = self._load_data()
        result = []
        for ip, data in all_data.items():
            if channel in data:
                if key is None and value is None:
                    result.append(ip)
                elif key in data[channel]:
                    if value is None or data[channel][key] == value:
                        result.append(ip)
        return result


def main():
    parser = argparse.ArgumentParser(description='IP 数据读取器')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    get_parser = subparsers.add_parser('get', help='获取 IP 数据')
    get_parser.add_argument('ip', help='IP 地址')
    
    get_channel_parser = subparsers.add_parser('get-channel', help='获取 IP 的指定渠道数据')
    get_channel_parser.add_argument('ip', help='IP 地址')
    get_channel_parser.add_argument('channel', help='渠道名称')
    
    list_parser = subparsers.add_parser('list', help='列出所有 IP')
    list_parser.add_argument('--limit', type=int, help='仅显示前 N 个 IP')
    list_parser.add_argument('--start', type=int, help='起始位置（从 1 开始）')
    list_parser.add_argument('--end', type=int, help='结束位置')
    list_parser.add_argument('--detail', action='store_true', help='显示 IP 的详细内容')
    list_parser.add_argument('--output', type=str, help='输出到指定文件（同时也会在控制台显示）')
    list_parser.add_argument('--include-channel', action='append', help='仅显示包含指定渠道的 IP（可多次使用）')
    list_parser.add_argument('--exclude-channel', action='append', help='排除包含指定渠道的 IP（可多次使用）')
    list_parser.add_argument('--export-excel', type=str, help='导出为 Excel 文件（指定输出文件路径）')
    
    list_channels_parser = subparsers.add_parser('list-channels', help='列出 IP 的所有渠道')
    list_channels_parser.add_argument('ip', help='IP 地址')
    
    search_parser = subparsers.add_parser('search', help='按渠道搜索 IP')
    search_parser.add_argument('channel', help='渠道名称')
    search_parser.add_argument('--key', help='数据键（可选）')
    search_parser.add_argument('--value', help='数据值（可选，需要配合 --key 使用）')
    
    args = parser.parse_args()
    reader = IPReader()
    
    if args.command == 'get':
        data = reader.get_ip_data(args.ip)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"错误: 未找到 IP {args.ip}")
    
    elif args.command == 'get-channel':
        data = reader.get_channel_data(args.ip, args.channel)
        if data is not None:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"错误: 未找到 IP {args.ip} 或渠道 {args.channel}")
    
    elif args.command == 'list':
        # 验证互斥参数
        include_channel = getattr(args, 'include_channel', None)
        exclude_channel = getattr(args, 'exclude_channel', None)
        
        if include_channel and exclude_channel:
            print("错误: --include-channel 和 --exclude-channel 不能同时使用")
            return
        
        ips = reader.list_all_ips()
        if not ips:
            print("暂无存储的 IP 数据")
            return
        
        # 应用范围限制
        start = 0
        end = len(ips)
        
        if hasattr(args, 'limit') and args.limit:
            end = min(args.limit, len(ips))
        
        if hasattr(args, 'start') and args.start:
            if args.start < 1:
                print("错误: --start 参数必须大于等于 1")
                return
            start = args.start - 1  # 转换为 0-based 索引
        
        if hasattr(args, 'end') and args.end:
            end = min(args.end, len(ips))
        
        # 确保范围有效
        if start >= end:
            print("错误: 起始位置必须小于结束位置")
            return
        
        if start >= len(ips):
            print(f"错误: 起始位置超出范围（总共 {len(ips)} 个 IP）")
            return
        
        selected_ips = ips[start:end]
        
        # 检查是否显示详细信息
        show_detail = hasattr(args, 'detail') and args.detail
        output_file = hasattr(args, 'output') and args.output
        
        # 收集输出内容
        output_lines = []
        
        if show_detail:
            header = f"已存储的 IP (显示 {start + 1}-{end}, 共 {len(selected_ips)} 个):"
            output_lines.append(header)
            for ip in selected_ips:
                output_lines.append(f"\nIP: {ip}")
                ip_data = reader.get_ip_data(ip)
                if ip_data:
                    # 应用渠道过滤到输出内容
                    if include_channel:
                        filtered_data = {'ip': ip_data.get('ip', ip)}
                        for ch in include_channel:
                            if ch in ip_data:
                                filtered_data[ch] = ip_data[ch]
                        output_lines.append(json.dumps(filtered_data, ensure_ascii=False, indent=2))
                    elif exclude_channel:
                        filtered_data = {k: v for k, v in ip_data.items() if k not in exclude_channel}
                        output_lines.append(json.dumps(filtered_data, ensure_ascii=False, indent=2))
                    else:
                        output_lines.append(json.dumps(ip_data, ensure_ascii=False, indent=2))
        else:
            header = f"已存储的 IP (显示 {start + 1}-{end}，共 {len(selected_ips)} 个):"
            output_lines.append(header)
            for ip in selected_ips:
                output_lines.append(f"- {ip}")
        
        # 合并为完整输出
        full_output = '\n'.join(output_lines)
        
        # 导出 Excel（如果指定）
        export_excel = getattr(args, 'export_excel', None)
        if export_excel:
            from exporter import IPExcelExporter
            exporter = IPExcelExporter(reader)
            exporter.export_to_excel(
                selected_ips,
                include_channel=include_channel,
                exclude_channel=exclude_channel,
                output_file=export_excel
            )
            return
        
        # 输出到文件（如果指定）
        if output_file:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(full_output)
                print(f"已将结果保存到文件: {args.output}")
            except Exception as e:
                print(f"错误: 无法写入文件 - {e}")
                return
        
        # 输出到控制台
        print(full_output)
    
    elif args.command == 'list-channels':
        channels = reader.list_ip_channels(args.ip)
        if channels:
            print(f"IP {args.ip} 的渠道:")
            for channel in channels:
                print(f"- {channel}")
        else:
            print(f"IP {args.ip} 暂无渠道数据")
    
    elif args.command == 'search':
        result = reader.search_ips_by_channel(args.channel, args.key, args.value)
        if result:
            print(f"找到 {len(result)} 个匹配的 IP:")
            for ip in result:
                print(f"- {ip}")
        else:
            print(f"未找到匹配的 IP")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
