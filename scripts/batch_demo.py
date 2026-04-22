import argparse
import os
import random
import sys
import time


class MockIPWriter:
    def __init__(self):
        self._store = {}

    def add_or_update_ip(self, ip, channel, data):
        if ip not in self._store:
            self._store[ip] = {'ip': ip}
        self._store[ip][channel] = data
        print(f"  [MockIPWriter] 已写入 {ip} ({channel})")


class MockSettings:
    demo_query_delay = 0.3


def validate_channel_key():
    print("[Mock] 校验通过")


MOCK_DATA = [
    {"country": "United States", "org": "Google LLC"},
    {"country": "Australia", "org": "Cloudflare, Inc."},
    {"country": "China", "org": "Zenlayer Inc"},
    {"country": "Japan", "org": "NTT Communications"},
    {"country": "Germany", "org": "Deutsche Telekom"},
]


def fetch_channel(ip, **kwargs):
    if random.random() < 0.2:
        return {"raw_error": True, "error_message": f"模拟查询失败: {ip}"}
    data = random.choice(MOCK_DATA).copy()
    data['ip'] = ip
    return data


class BatchDemoQuery:
    def __init__(self, ip_file, channel_name='demo', no_validate=False):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.no_validate = no_validate
        self.settings = MockSettings()
        self.ip_writer = MockIPWriter()

        self.load_stats = {}
        self.pending_ips = self._load_pending_ips()

    @property
    def progress_file(self):
        return f"{self.ip_file}.{self.channel_name}.progress"

    def _load_ip_file(self):
        seen = set()
        unique_ips = []
        raw_count = 0

        try:
            with open(self.ip_file, 'r', encoding='utf-8') as f:
                for line in f:
                    ip = line.strip()
                    if not ip:
                        continue
                    raw_count += 1
                    if ip not in seen:
                        seen.add(ip)
                        unique_ips.append(ip)
        except FileNotFoundError:
            print(f"错误: 找不到文件 {self.ip_file}")
            sys.exit(1)

        self.load_stats['raw_count'] = raw_count
        self.load_stats['unique_count'] = len(unique_ips)
        self.load_stats['duplicate_count'] = raw_count - len(unique_ips)

        return unique_ips

    def _load_progress(self):
        if not os.path.exists(self.progress_file):
            return set()
        with open(self.progress_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())

    def _save_progress(self, ip):
        with open(self.progress_file, 'a', encoding='utf-8') as f:
            f.write(ip + '\n')

    def _load_pending_ips(self):
        unique_ips = self._load_ip_file()
        processed = self._load_progress()

        pending = [ip for ip in unique_ips if ip not in processed]

        self.load_stats['already_processed'] = len(processed)
        self.load_stats['pending_count'] = len(pending)

        return pending

    def _query_ip(self, ip):
        return fetch_channel(ip)

    def _print_result(self, ip, data):
        country = data.get('country', 'N/A')
        org = data.get('org', 'N/A')
        print(f"✅ {country} - {org}")

    def _get_delay(self):
        return self.settings.demo_query_delay

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.load_stats['pending_count']
        total_count = self.load_stats['unique_count']
        processed_count = self.load_stats['already_processed']

        print(f"开始批量查询 Demo 信息")
        print(f"IP 文件: {self.ip_file}")
        if self.load_stats['duplicate_count'] > 0:
            print(f"IP 去重: 原始 {self.load_stats['raw_count']}, 去重后 {total_count}, 重复 {self.load_stats['duplicate_count']}")
        print(f"总 IP 数: {total_count}")
        print(f"已处理: {processed_count}")
        print(f"待处理: {pending_count}")
        print(f"查询间隔: {delay} 秒")
        print("-" * 60)

        current_count = processed_count
        success_count = 0
        fail_count = 0

        try:
            for ip in self.pending_ips:
                current_count += 1

                print(f"[{current_count}/{total_count}] 正在查询: {ip}", end=' ', flush=True)

                data = self._query_ip(ip)

                if isinstance(data, dict) and (data.get('raw_error') or data.get('error')):
                    print(f"❌ {data.get('error_message', data.get('error', 'Unknown'))}")
                    fail_count += 1
                else:
                    self._print_result(ip, data)
                    success_count += 1

                self.ip_writer.add_or_update_ip(ip, self.channel_name, data)
                self._save_progress(ip)

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
    parser = argparse.ArgumentParser(description='批量查询 Demo 信息（模拟）')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchDemoQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
