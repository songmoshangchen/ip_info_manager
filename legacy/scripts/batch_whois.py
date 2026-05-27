import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from channel.whois_query import IPWriter, Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchWhoisQuery(BaseBatchQuery):
    channel_name = 'whois'

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
        return fetch_channel(ip, timeout=self.settings.whois_query_timeout)

    def _print_result(self, ip, data):
        if data.get('has_whois', False):
            whois_info = data.get('whois_data', {})
            registrar = whois_info.get('registrar', 'N/A')
            org = whois_info.get('organization', 'N/A')
            country = whois_info.get('country', 'N/A')
            self.logger.info(f"✅ {registrar} | {org} | {country}")
        else:
            error_msg = data.get('error_message', '无 Whois 信息')
            self.logger.info(f"⚠️  {error_msg}")

    def _get_delay(self):
        return getattr(self.settings, 'whois_query_delay', 1.0)


def main():
    parser = argparse.ArgumentParser(description='批量查询 Whois 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('whois')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchWhoisQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
