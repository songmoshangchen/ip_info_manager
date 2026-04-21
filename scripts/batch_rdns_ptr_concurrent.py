import argparse
import os
import sys
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.rdns_ptr import Settings, fetch_channel, validate_channel_key


class ThreadSafeIPWriter:
    def __init__(self):
        self.settings = Settings()
        self.lock = threading.Lock()
        self.pending_updates = {}
        self.pending_lock = threading.Lock()

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
        with self.lock:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)

    def _save_data(self, data):
        with self.lock:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def add_update(self, ip, channel, data):
        with self.pending_lock:
            self.pending_updates[ip] = {channel: data}

    def flush_updates(self):
        with self.pending_lock:
            if not self.pending_updates:
                return

            updates = self.pending_updates.copy()
            self.pending_updates.clear()

        all_data = self._load_data()

        for ip, channel_data in updates.items():
            if ip not in all_data:
                all_data[ip] = {"ip": ip}

            for channel, data in channel_data.items():
                all_data[ip][channel] = data

        self._save_data(all_data)


class ConcurrentBatchRDNSQuery:
    def __init__(self, ip_file, channel_name='rdns_ptr', no_validate=False, max_workers=5):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.no_validate = no_validate
        self.max_workers = max_workers
        self.progress_file = f"{ip_file}.{channel_name}.progress"
        self.settings = Settings()
        self.ip_writer = ThreadSafeIPWriter()
        self.processed_ips = self._load_progress()
        self.total_ips = self._count_total_ips()

        self.lock = threading.Lock()
        self.stats = {
            'total': 0,
            'has_ptr': 0,
            'no_ptr': 0,
            'errors': 0
        }
        self.print_lock = threading.Lock()

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
        with self.lock:
            with open(self.progress_file, 'a', encoding='utf-8') as f:
                f.write(ip + '\n')

    def _query_ip(self, ip):
        return fetch_channel(ip, timeout=self.settings.rdns_query_timeout)

    def _print_result(self, ip, data, thread_name, index):
        if data.get('has_ptr', False):
            hostname = data.get('hostname', 'N/A')
            aliases = data.get('aliases', [])
            alias_str = f" ({len(aliases)} 个别名)" if aliases else ""
            print(f"[{thread_name}] [{index}/{self.total_ips}] {ip} ✅ {hostname}{alias_str}")
        else:
            error_msg = data.get('error_message', '无 PTR 记录')
            print(f"[{thread_name}] [{index}/{self.total_ips}] {ip} ⚠️  {error_msg}")

    def _get_delay(self):
        return getattr(self.settings, 'rdns_query_delay', 0.1)

    def _process_ip(self, ip, index):
        if ip in self.processed_ips:
            return None

        try:
            thread_name = threading.current_thread().name
            with self.print_lock:
                print(f"[{thread_name}] [{index}/{self.total_ips}] 正在查询: {ip}", flush=True)

            rdns_data = self._query_ip(ip)

            result = {
                'ip': ip,
                'index': index,
                'data': rdns_data
            }

            if isinstance(rdns_data, dict) and rdns_data.get('raw_error'):
                result['status'] = 'error'
                with self.print_lock:
                    print(f"[{thread_name}] [{index}/{self.total_ips}] {ip} ❌ {rdns_data.get('error_message', 'Unknown')}")
            else:
                if rdns_data.get('has_ptr', False):
                    result['status'] = 'success'
                else:
                    result['status'] = 'no_ptr'
                with self.print_lock:
                    self._print_result(ip, rdns_data, thread_name, index)

            self.ip_writer.add_update(ip, self.channel_name, rdns_data)
            self._save_progress(ip)

            return result

        except Exception as e:
            thread_name = threading.current_thread().name
            with self.print_lock:
                print(f"[{thread_name}] [{index}/{self.total_ips}] {ip} ❌ 异常: {str(e)}")
            return {
                'ip': ip,
                'index': index,
                'status': 'exception',
                'error': str(e)
            }

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.total_ips - len(self.processed_ips)

        print(f"开始批量查询 RDNS PTR 信息（并发版本）")
        print(f"IP 文件: {self.ip_file}")
        print(f"总 IP 数: {self.total_ips}")
        print(f"已处理: {len(self.processed_ips)}")
        print(f"待处理: {pending_count}")
        print(f"并发线程数: {self.max_workers}")
        print(f"查询超时: {self.settings.rdns_query_timeout} 秒")
        print("-" * 60)

        ips_to_query = []
        with open(self.ip_file, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                ip = line.strip()
                if ip and ip not in self.processed_ips:
                    ips_to_query.append((ip, idx))

        if not ips_to_query:
            print("所有 IP 已处理完毕！")
            return

        try:
            start_time = time.time()
            completed_count = 0

            with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='RDNS') as executor:
                futures = {
                    executor.submit(self._process_ip, ip, idx): (ip, idx)
                    for ip, idx in ips_to_query
                }

                for future in as_completed(futures):
                    ip, idx = futures[future]
                    try:
                        result = future.result()
                        if result:
                            with self.lock:
                                self.stats['total'] += 1
                                completed_count += 1
                                if result['status'] == 'success':
                                    self.stats['has_ptr'] += 1
                                elif result['status'] == 'no_ptr':
                                    self.stats['no_ptr'] += 1
                                else:
                                    self.stats['errors'] += 1

                            if completed_count % 5 == 0:
                                self.ip_writer.flush_updates()

                    except Exception as e:
                        with self.print_lock:
                            print(f"处理 {ip} 时发生异常: {str(e)}")
                        with self.lock:
                            self.stats['total'] += 1
                            self.stats['errors'] += 1

            self.ip_writer.flush_updates()
            elapsed_time = time.time() - start_time

        except KeyboardInterrupt:
            self.ip_writer.flush_updates()
            print("\n\n" + "=" * 60)
            print(f"查询已中断！")
            print(f"已处理: {self.stats['total']} 个 IP")
            print(f"有 PTR: {self.stats['has_ptr']} 个")
            print(f"无 PTR: {self.stats['no_ptr']} 个")
            print(f"错误: {self.stats['errors']} 个")
            print(f"进度文件: {self.progress_file}")
            print("=" * 60)
            sys.exit(0)

        print("\n" + "=" * 60)
        print(f"批量查询完成！")
        print(f"总共处理: {self.stats['total']} 个 IP")
        print(f"有 PTR 记录: {self.stats['has_ptr']} 个")
        print(f"无 PTR 记录: {self.stats['no_ptr']} 个")
        print(f"查询错误: {self.stats['errors']} 个")
        print(f"总耗时: {elapsed_time:.2f} 秒")
        print(f"平均速度: {self.stats['total'] / elapsed_time:.2f} IP/秒")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询 RDNS PTR 信息（并发版本）')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')
    parser.add_argument('--workers', type=int, default=5, help='并发线程数（默认 5）')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = ConcurrentBatchRDNSQuery(args.ip_file, no_validate=args.no_validate, max_workers=args.workers)
    batch.run()


if __name__ == "__main__":
    main()
