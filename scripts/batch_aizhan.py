import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.aizhan import IPWriter, Settings, fetch_channel, validate_channel_key


class BatchAizhanQuery:
    def __init__(self, ip_file, channel_name='aizhan', no_validate=False):
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
        return fetch_channel(ip, cookie=self.settings.aizhan_cookie)

    def _print_result(self, ip, data):
        domain_count = data.get("domain_count", 0)
        location = data.get("location", "N/A")
        print(f"✅ {location} - {domain_count} 个域名")

    def _get_delay(self):
        return self.settings.aizhan_query_delay

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.total_ips - len(self.processed_ips)

        print(f"开始批量查询爱站网 IP 反查域名信息")
        print(f"IP 文件: {self.ip_file}")
        print(f"总 IP 数: {self.total_ips}")
        print(f"已处理: {len(self.processed_ips)}")
        print(f"待处理: {pending_count}")
        print(f"查询间隔: {delay} 秒")
        print("-" * 60)

        current_count = len(self.processed_ips)
        success_count = 0
        fail_count = 0

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

                    if isinstance(data, dict) and (data.get('raw_error') or data.get('error')):
                        print(f"❌ {data.get('error_message', data.get('error', 'Unknown'))}")
                        fail_count += 1
                    else:
                        self._print_result(ip, data)
                        success_count += 1

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
            print(f"进度文件: {self.progress_file}")
            print("=" * 60)
            sys.exit(0)

        print("\n" + "=" * 60)
        print(f"批量查询完成！")
        print(f"总共处理: {current_count} 个 IP")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询爱站网 IP 反查域名信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过 Cookie 有效性校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchAizhanQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
