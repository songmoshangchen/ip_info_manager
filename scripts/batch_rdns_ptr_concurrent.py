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
from scripts.logger_utils import get_batch_logger


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
        self.settings = Settings()
        self.ip_writer = ThreadSafeIPWriter()
        self.logger = get_batch_logger(channel_name)

        self.load_stats = {}
        self.pending_ips = self._load_pending_ips()

        self.lock = threading.Lock()
        self.stats = {
            'total': 0,
            'has_ptr': 0,
            'no_ptr': 0,
            'errors': 0
        }

    @property
    def progress_file(self):
        return f"{self.ip_writer.storage_file}.{self.channel_name}.progress"

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
            self.logger.error(f"找不到文件 {self.ip_file}")
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
        with self.lock:
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
        return fetch_channel(ip, timeout=self.settings.rdns_query_timeout)

    def _print_result(self, ip, data, thread_name, index):
        if data.get('has_ptr', False):
            hostname = data.get('hostname', 'N/A')
            aliases = data.get('aliases', [])
            alias_str = f" ({len(aliases)} 个别名)" if aliases else ""
            self.logger.info(f"[{thread_name}] [{index}/{self.load_stats['unique_count']}] {ip} ✅ {hostname}{alias_str}")
        else:
            error_msg = data.get('error_message', '无 PTR 记录')
            self.logger.info(f"[{thread_name}] [{index}/{self.load_stats['unique_count']}] {ip} ⚠️  {error_msg}")

    def _get_delay(self):
        return getattr(self.settings, 'rdns_query_delay', 0.1)

    def _process_ip(self, ip, index):
        try:
            thread_name = threading.current_thread().name
            query_start = time.time()

            self.logger.info(f"[{thread_name}] [{index}/{self.load_stats['unique_count']}] 正在查询: {ip}")

            rdns_data = self._query_ip(ip)

            query_elapsed = time.time() - query_start
            self.logger.debug(f"查询 {ip} 耗时: {query_elapsed:.3f}s")

            result = {
                'ip': ip,
                'index': index,
                'data': rdns_data
            }

            if isinstance(rdns_data, dict) and rdns_data.get('raw_error'):
                result['status'] = 'error'
                self.logger.warning(f"[{thread_name}] [{index}/{self.load_stats['unique_count']}] {ip} ❌ {rdns_data.get('error_message', 'Unknown')}")
            else:
                if rdns_data.get('has_ptr', False):
                    result['status'] = 'success'
                else:
                    result['status'] = 'no_ptr'
                self._print_result(ip, rdns_data, thread_name, index)

            self.ip_writer.add_update(ip, self.channel_name, rdns_data)
            self.logger.debug(f"已写入 {ip} 的 {self.channel_name} 数据")
            self._save_progress(ip)

            return result

        except Exception as e:
            thread_name = threading.current_thread().name
            self.logger.error(f"[{thread_name}] [{index}/{self.load_stats['unique_count']}] {ip} ❌ 异常: {str(e)}")
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
        pending_count = self.load_stats['pending_count']
        total_count = self.load_stats['unique_count']
        processed_count = self.load_stats['already_processed']

        self.logger.info("开始批量查询 RDNS PTR 信息（并发版本）")
        self.logger.info(f"IP 文件: {self.ip_file}")
        if self.load_stats['duplicate_count'] > 0:
            self.logger.info(f"IP 去重: 原始 {self.load_stats['raw_count']}, 去重后 {total_count}, 重复 {self.load_stats['duplicate_count']}")
        self.logger.info(f"总 IP 数: {total_count}")
        self.logger.info(f"已处理: {processed_count}")
        self.logger.info(f"待处理: {pending_count}")
        self.logger.info(f"并发线程数: {self.max_workers}")
        self.logger.info(f"查询超时: {self.settings.rdns_query_timeout} 秒")
        self.logger.info("-" * 60)

        if not self.pending_ips:
            self.logger.info("所有 IP 已处理完毕！")
            return

        ips_to_query = [(ip, idx + processed_count + 1) for idx, ip in enumerate(self.pending_ips)]

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
                        self.logger.error(f"处理 {ip} 时发生异常: {str(e)}")
                        with self.lock:
                            self.stats['total'] += 1
                            self.stats['errors'] += 1

            self.ip_writer.flush_updates()
            elapsed_time = time.time() - start_time

        except KeyboardInterrupt:
            self.ip_writer.flush_updates()
            self.logger.info("=" * 60)
            self.logger.info("查询已中断！")
            self.logger.info(f"已处理: {self.stats['total']} 个 IP")
            self.logger.info(f"有 PTR: {self.stats['has_ptr']} 个")
            self.logger.info(f"无 PTR: {self.stats['no_ptr']} 个")
            self.logger.info(f"错误: {self.stats['errors']} 个")
            self.logger.info(f"进度文件: {self.progress_file}")
            self.logger.info("=" * 60)
            sys.exit(0)

        self.logger.info("=" * 60)
        self.logger.info("批量查询完成！")
        self.logger.info(f"总共处理: {self.stats['total']} 个 IP")
        self.logger.info(f"有 PTR 记录: {self.stats['has_ptr']} 个")
        self.logger.info(f"无 PTR 记录: {self.stats['no_ptr']} 个")
        self.logger.info(f"查询错误: {self.stats['errors']} 个")
        self.logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        self.logger.info(f"平均速度: {self.stats['total'] / elapsed_time:.2f} IP/秒")
        self.logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询 RDNS PTR 信息（并发版本）')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')
    parser.add_argument('--workers', type=int, default=5, help='并发线程数（默认 5）')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('rdns_ptr')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = ConcurrentBatchRDNSQuery(args.ip_file, no_validate=args.no_validate, max_workers=args.workers)
    batch.run()


if __name__ == "__main__":
    main()
