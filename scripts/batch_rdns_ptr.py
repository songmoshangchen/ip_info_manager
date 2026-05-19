import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from channel.rdns_ptr import IPWriter, Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchRDNSQuery(BaseBatchQuery):
    channel_name = 'rdns_ptr'

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
        return fetch_channel(ip, timeout=self.settings.rdns_query_timeout)

    def _print_result(self, ip, data):
        if data.get('has_ptr', False):
            hostname = data.get('hostname', 'N/A')
            aliases = data.get('aliases', [])
            alias_str = f" ({len(aliases)} 个别名)" if aliases else ""
            self.logger.info(f"✅ {hostname}{alias_str}")
        else:
            error_msg = data.get('error_message', '无 PTR 记录')
            self.logger.info(f"⚠️  {error_msg}")

    def _get_delay(self):
        return getattr(self.settings, 'rdns_query_delay', 0.5)


def main():
    parser = argparse.ArgumentParser(description='批量查询 RDNS PTR 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('rdns_ptr')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchRDNSQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
