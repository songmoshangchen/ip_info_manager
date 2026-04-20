import os
import time
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.whois_query import IPWriter, Settings, fetch_whois


class BatchWhoisQuery:
    def __init__(self, ip_file: str, channel_name: str = 'whois'):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.progress_file = f"{ip_file}.{channel_name}.progress"
        self.settings = Settings()
        self.ip_writer = IPWriter()
        self.processed_ips = self._load_progress()
        self.total_ips = self._count_total_ips()
    
    def _count_total_ips(self):
        try:
            with open(self.ip_file, 'r', encoding='utf-8') as f:
                return sum(1 for line in f if line.strip())
        except FileNotFoundError:
            print(f"错误: 找不到文件 {self.ip_file}")
            sys.exit(1)
    
    def _load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()
    
    def _save_progress(self, ip: str):
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(ip + '\n')
    
    def _query_ip(self, ip: str):
        return fetch_whois(ip, self.settings.whois_query_timeout)
    
    def run(self):
        delay = getattr(self.settings, 'whois_query_delay', 1.0)
        print(f"开始批量查询 Whois 信息")
        print(f"IP 文件: {self.ip_file}")
        print(f"总 IP 数: {self.total_ips}")
        print(f"已处理: {len(self.processed_ips)}")
        print(f"待处理: {self.total_ips - len(self.processed_ips)}")
        print(f"查询间隔: {delay} 秒")
        print(f"超时时间: {self.settings.whois_query_timeout} 秒")
        print("-" * 60)
        
        current_count = len(self.processed_ips)
        has_whois_count = 0
        no_whois_count = 0
        
        try:
            with open(self.ip_file, 'r', encoding='utf-8') as f:
                for line in f:
                    ip = line.strip()
                    if not ip:
                        continue
                    
                    if ip in self.processed_ips:
                        continue
                    
                    current_count += 1
                    
                    print(f"[{current_count}/{self.total_ips}] 正在查询: {ip}", end=' ', flush=True)
                    
                    whois_data = self._query_ip(ip)
                    
                    if 'raw_error' in whois_data:
                        print(f"❌ 错误: {whois_data.get('error_message', 'Unknown error')}")
                    elif whois_data.get('has_whois', False):
                        whois_info = whois_data.get('whois_data', {})
                        registrar = whois_info.get('registrar', 'N/A')
                        org = whois_info.get('organization', 'N/A')
                        country = whois_info.get('country', 'N/A')
                        print(f"✅ {registrar} | {org} | {country}")
                        has_whois_count += 1
                    else:
                        error_msg = whois_data.get('error_message', '无 Whois 信息')
                        print(f"⚠️  {error_msg}")
                        no_whois_count += 1
                    
                    self.ip_writer.add_or_update_ip(ip, self.channel_name, whois_data)
                    self._save_progress(ip)
                    self.processed_ips.add(ip)
                    
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print(f"查询已中断！")
            print(f"已处理: {len(self.processed_ips)} 个 IP")
            print(f"有 Whois: {has_whois_count} 个")
            print(f"无 Whois: {no_whois_count} 个")
            print(f"进度文件: {self.progress_file}")
            print(f"下次运行将从第 {len(self.processed_ips) + 1} 个 IP 开始")
            print("=" * 60)
            sys.exit(0)
        
        print("\n" + "=" * 60)
        print(f"批量查询完成！")
        print(f"总共处理: {len(self.processed_ips)} 个 IP")
        print(f"有 Whois 信息: {has_whois_count} 个")
        print(f"无 Whois 信息: {no_whois_count} 个")
        print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python batch_whois.py <IP文件路径>")
        print("示例: python batch_whois.py ips.txt")
        sys.exit(1)
    
    ip_file = sys.argv[1]
    
    if not os.path.exists(ip_file):
        print(f"错误: 找不到文件 {ip_file}")
        sys.exit(1)
    
    batch_query = BatchWhoisQuery(ip_file)
    batch_query.run()


if __name__ == "__main__":
    main()
