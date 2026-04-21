import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.rdns_ptr import IPWriter, Settings, fetch_channel, validate_channel_key


class BatchRDNSQuery:
    def __init__(self, ip_file, channel_name='rdns_ptr', no_validate=False):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.no_validate = no_validate
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

    def _save_progress(self, ip):
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(ip + '\n')

    def _query_ip(self, ip):
        return fetch_channel(ip, timeout=self.settings.rdns_query_timeout)

    def _print_result(self, ip, data):
        if data.get('has_ptr', False):
            hostname = data.get('hostname', 'N/A')
            aliases = data.get('aliases', [])
            alias_str = f" ({len(aliases)} 个别名)" if aliases else ""
            print(f"✅ {hostname}{alias_str}")
        else:
            error_msg = data.get('error_message', '无 PTR 记录')
            print(f"⚠️  {error_msg}")

    def _get_delay(self):
        return getattr(self.settings, 'rdns_query_delay', 0.5)

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.total_ips - len(self.processed_ips)

        print(f"开始批量查询 RDNS PTR 信息")
        print(f"IP 文件: {self.ip_file}")
        print(f"总 IP 数: {self.total_ips}")
        print(f"已处理: {len(self.processed_ips)}")
        print(f"待处理: {pending_count}")
        print(f"查询间隔: {delay} 秒")
        print(f"超时时间: {self.settings.rdns_query_timeout} 秒")
        print("-" * 60)

        current_count = len(self.processed_ips)
        success_count = 0
        fail_count = 0
        has_ptr_count = 0
        no_ptr_count = 0

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

                    data = self._query_ip(ip)

                    if isinstance(data, dict) and data.get('raw_error'):
                        print(f"❌ {data.get('error_message', 'Unknown')}")
                        fail_count += 1
                    else:
                        if data.get('has_ptr', False):
                            has_ptr_count += 1
                            success_count += 1
                        else:
                            no_ptr_count += 1
                            success_count += 1
                        self._print_result(ip, data)

                    self.ip_writer.add_or_update_ip(ip, self.channel_name, data)
                    self._save_progress(ip)
                    self.processed_ips.add(ip)

                    time.sleep(delay)

        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print(f"查询已中断！")
            print(f"已处理: {current_count} 个 IP")
            print(f"成功: {success_count} 个")
            print(f"失败: {fail_count} 个")
            print(f"有 PTR: {has_ptr_count} 个")
            print(f"无 PTR: {no_ptr_count} 个")
            print(f"进度文件: {self.progress_file}")
            print("=" * 60)
            sys.exit(0)

        print("\n" + "=" * 60)
        print(f"批量查询完成！")
        print(f"总共处理: {current_count} 个 IP")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")
        print(f"有 PTR 记录: {has_ptr_count} 个")
        print(f"无 PTR 记录: {no_ptr_count} 个")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询 RDNS PTR 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchRDNSQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
