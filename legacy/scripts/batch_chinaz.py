import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from channel.chinaz import IPWriter, Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchChinazQuery(BaseBatchQuery):
    channel_name = 'chinaz'

    def __init__(self, ip_file, channel_name=None, no_validate=False):
        self.settings = Settings()
        self.ip_writer = IPWriter(settings=self.settings)
        self.logger = get_batch_logger(self.channel_name)
        self._pid_mgr = PidManager(
            os.path.dirname(self.ip_writer.storage_file),
            os.path.basename(self.ip_writer.storage_file).replace('.json', '')
        )
        super().__init__(ip_file, channel_name=channel_name, no_validate=no_validate)

    def _do_validate(self):
        validate_channel_key()

    def _query_ip(self, ip):
        return fetch_channel(ip, cookie=self.settings.chinaz_cookie, timeout=self.settings.chinaz_query_timeout)

    def _print_result(self, ip, data):
        domain_count = len(data.get("domains", []))
        location = data.get("location", "N/A")
        self.logger.info(f"✅ {location} - {domain_count} 个域名")

    def _get_delay(self):
        return self.settings.chinaz_query_delay


def main():
    parser = argparse.ArgumentParser(description='批量查询站长之家 IP 反查域名信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过 Cookie 有效性校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('chinaz')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchChinazQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
