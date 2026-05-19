import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from writer import IPWriter
from channel.fofa_search import Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchFofaSearchQuery(BaseBatchQuery):
    channel_name = 'fofa_search'

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
        return fetch_channel(ip, key=self.settings.fofa_api_key, timeout=self.settings.fofa_query_timeout)

    def _print_result(self, ip, data):
        if data.get('raw_error'):
            self.logger.info(f"  ❌ {ip}: 查询失败 - {data.get('error_message', 'Unknown')}")
            return
        size = data.get('size', 0)
        results = data.get('results', [])
        self.logger.info(f"  ✅ {ip}: Fofa Search 返回 {size} 条结果, {len(results)} 条记录")

    def _get_delay(self):
        return self.settings.fofa_query_delay


def main():
    parser = argparse.ArgumentParser(description='批量查询 Fofa Search 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过 Key 有效性校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('fofa_search')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchFofaSearchQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
