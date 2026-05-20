import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from writer import IPWriter
from channel.ipinfo_api import Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchIPInfoQuery(BaseBatchQuery):
    channel_name = 'ipinfo_api'

    def __init__(self, ip_file, channel_name=None, no_validate=False, use_api=True):
        self.use_api = use_api
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
        return fetch_channel(ip, key=self.settings.ipinfo_access_token, use_api=self.use_api, timeout=self.settings.ipinfo_query_timeout)

    def _print_result(self, ip, data):
        country = data.get('country', 'N/A')
        org = data.get('as_name', 'N/A')
        self.logger.info(f"✅ {country} - {org}")

    def _get_delay(self):
        return self.settings.ipinfo_query_delay


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
