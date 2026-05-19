import os
import sys
import time
from abc import ABC, abstractmethod


class BaseBatchQuery(ABC):

    channel_name: str = ''

    def __init__(self, ip_file, channel_name=None, no_validate=False):
        self.ip_file = ip_file
        if channel_name:
            self.channel_name = channel_name
        self.no_validate = no_validate
        self.load_stats = {}
        self.pending_ips = self._load_pending_ips()

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
            print(f"找不到文件 {self.ip_file}")
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
            f.write(f"{ip}\n")

    def _load_pending_ips(self):
        unique_ips = self._load_ip_file()
        processed = self._load_progress()
        pending = [ip for ip in unique_ips if ip not in processed]
        self.load_stats['already_processed'] = len(processed)
        self.load_stats['pending_count'] = len(pending)
        return pending

    def _get_delay(self):
        attr = f'{self.channel_name}_query_delay'
        return getattr(self.settings, attr, 1.0)

    def _is_error(self, data):
        if not isinstance(data, dict):
            return False
        return bool(data.get('raw_error') or data.get('error'))

    def _do_validate(self):
        pass

    def run(self):
        if not self.no_validate:
            self._do_validate()

        delay = self._get_delay()
        total_count = self.load_stats.get('unique_count', 0)
        processed_count = self.load_stats.get('already_processed', 0)

        if hasattr(self, '_pid_mgr'):
            self._pid_mgr.write_pid(
                f'batch_{self.channel_name}', self.ip_file,
                total_count, current_phase=1)

        current_count = processed_count
        success_count = 0
        fail_count = 0
        start_time = time.time()
        new_count = 0

        try:
            for ip in self.pending_ips:
                current_count += 1
                new_count += 1

                data = self._query_ip(ip)

                if self._is_error(data):
                    self._print_result(ip, data)
                    fail_count += 1
                else:
                    self._print_result(ip, data)
                    success_count += 1

                self.ip_writer.add_or_update_ip(ip, self.channel_name, data)
                self._save_progress(ip)
                if hasattr(self, '_pid_mgr'):
                    self._pid_mgr.update_heartbeat(current_phase=1)

                if new_count > 0:
                    elapsed = time.time() - start_time
                    remaining = total_count - current_count
                    if remaining > 0:
                        avg = elapsed / new_count
                        eta_s = remaining * avg
                        eta_m = int(eta_s // 60)
                        eta_sec = int(eta_s % 60)
                        self.logger.info(f"  ETA: ~{eta_m}min{eta_sec:02d}s (剩余 {remaining} 个IP)")

                time.sleep(delay)

        except KeyboardInterrupt:
            if hasattr(self, '_pid_mgr'):
                self._pid_mgr.remove_pid()
            total_elapsed = time.time() - start_time
            self.logger.info("=" * 60)
            self.logger.info("查询已中断！")
            self.logger.info(f"已处理: {current_count} 个 IP")
            self.logger.info(f"成功: {success_count} 个")
            self.logger.info(f"失败: {fail_count} 个")
            self.logger.info(f"总耗时: {total_elapsed:.2f}s")
            self.logger.info("=" * 60)
            self.run_stats = {
                'success_count': success_count,
                'fail_count': fail_count,
                'total_elapsed': total_elapsed,
            }
            sys.exit(0)

        total_elapsed = time.time() - start_time
        if hasattr(self, '_pid_mgr'):
            self._pid_mgr.remove_pid()
        self.run_stats = {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_elapsed': total_elapsed,
        }

    @abstractmethod
    def _query_ip(self, ip):
        ...

    @abstractmethod
    def _print_result(self, ip, data):
        ...
