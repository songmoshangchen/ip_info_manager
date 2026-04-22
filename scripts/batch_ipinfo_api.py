import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.ipinfo_api import IPWriter, Settings, fetch_channel, validate_channel_key
from scripts.logger_utils import get_batch_logger


class BatchIPInfoQuery:
    def __init__(self, ip_file, channel_name='ipinfo_api', no_validate=False, use_api=True):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.no_validate = no_validate
        self.use_api = use_api
        self.settings = Settings()
        self.ip_writer = IPWriter()
        self.logger = get_batch_logger(channel_name)

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
        return fetch_channel(ip, key=self.settings.ipinfo_access_token, use_api=self.use_api)

    def _print_result(self, ip, data):
        country = data.get('country', 'N/A')
        org = data.get('as_name', 'N/A')
        self.logger.info(f"✅ {country} - {org}")

    def _get_delay(self):
        return self.settings.ipinfo_query_delay

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.load_stats['pending_count']
        total_count = self.load_stats['unique_count']
        processed_count = self.load_stats['already_processed']
        mode = "API" if self.use_api else "非API"

        self.logger.info(f"开始批量查询 IPInfo 信息 ({mode} 模式)")
        self.logger.info(f"IP 文件: {self.ip_file}")
        if self.load_stats['duplicate_count'] > 0:
            self.logger.info(f"IP 去重: 原始 {self.load_stats['raw_count']}, 去重后 {total_count}, 重复 {self.load_stats['duplicate_count']}")
        self.logger.info(f"总 IP 数: {total_count}")
        self.logger.info(f"已处理: {processed_count}")
        self.logger.info(f"待处理: {pending_count}")
        self.logger.info(f"查询间隔: {delay} 秒")
        self.logger.info("-" * 60)

        current_count = processed_count
        success_count = 0
        fail_count = 0
        start_time = time.time()

        try:
            for ip in self.pending_ips:
                current_count += 1
                query_start = time.time()

                self.logger.info(f"[{current_count}/{total_count}] 正在查询: {ip}")

                data = self._query_ip(ip)

                query_elapsed = time.time() - query_start
                self.logger.debug(f"查询 {ip} 耗时: {query_elapsed:.3f}s")

                if isinstance(data, dict) and (data.get('raw_error') or data.get('error')):
                    self.logger.warning(f"[{current_count}/{total_count}] {ip} ❌ {data.get('error_message', data.get('error', 'Unknown'))}")
                    fail_count += 1
                else:
                    self._print_result(ip, data)
                    success_count += 1

                self.ip_writer.add_or_update_ip(ip, self.channel_name, data)
                self.logger.debug(f"已写入 {ip} 的 {self.channel_name} 数据")
                self._save_progress(ip)

                time.sleep(delay)

        except KeyboardInterrupt:
            total_elapsed = time.time() - start_time
            self.logger.info("=" * 60)
            self.logger.info("查询已中断！")
            self.logger.info(f"已处理: {current_count} 个 IP")
            self.logger.info(f"成功: {success_count} 个")
            self.logger.info(f"失败: {fail_count} 个")
            self.logger.info(f"总耗时: {total_elapsed:.2f}s")
            self.logger.info(f"进度文件: {self.progress_file}")
            self.logger.info("=" * 60)
            sys.exit(0)

        total_elapsed = time.time() - start_time
        self.logger.info("=" * 60)
        self.logger.info("批量查询完成！")
        self.logger.info(f"总共处理: {current_count} 个 IP")
        self.logger.info(f"成功: {success_count} 个")
        self.logger.info(f"失败: {fail_count} 个")
        self.logger.info(f"总耗时: {total_elapsed:.2f}s")
        self.logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询 IPInfo 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过 Token 有效性校验')
    parser.add_argument('--no-api', action='store_true', help='使用非 API 模式查询')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('ipinfo_api')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchIPInfoQuery(args.ip_file, no_validate=args.no_validate, use_api=not args.no_api)
    batch.run()


if __name__ == "__main__":
    main()
