import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.base_batch import BaseBatchQuery
from writer import IPWriter
from channel.ssl_cert import Settings, fetch_channel, validate_channel_key
from utils.logger_utils import get_batch_logger
from utils.pid_manager import PidManager


class BatchSslCertQuery(BaseBatchQuery):
    channel_name = 'ssl_cert'

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
        return fetch_channel(
            ip=ip,
            port=self.settings.ssl_cert_port,
            timeout=self.settings.ssl_cert_timeout,
            openssl_timeout=self.settings.ssl_cert_openssl_timeout,
        )

    def _print_result(self, ip, data):
        if data.get('error'):
            self.logger.info(f"  ❌ {ip}: {data.get('error')}")
            return
        domains = data.get('domains', [])
        self.logger.info(f"  ✅ {ip}: 提取到 {len(domains)} 个域名")

    def _get_delay(self):
        return self.settings.ssl_cert_query_delay


def main():
    parser = argparse.ArgumentParser(description='批量获取 SSL 证书域名')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        logger = get_batch_logger('ssl_cert')
        logger.error(f"找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchSslCertQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
