import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from channel.xxx import IPWriter, Settings, fetch_xxx, validate_channel_key
from utils.ip_loader import load_pending_ips, save_progress


class BatchXxxQuery:
    def __init__(self, ip_file, channel_name='xxx', no_validate=False):
        self.ip_file = ip_file
        self.channel_name = channel_name
        self.no_validate = no_validate
        self.settings = Settings()
        self.ip_writer = IPWriter()

        self.pending_ips, self.load_stats = load_pending_ips(ip_file, self.progress_file)

    @property
    def progress_file(self):
        return f"{self.ip_file}.{self.channel_name}.progress"

    def _query_ip(self, ip):
        """
        【各渠道自定义】调用 channel 的 fetch 函数，传入渠道特有参数。

        示例:
          fofa:    return fetch_fofa(ip, self.settings.fofa_api_key)
          aizhan:  return fetch_aizhan(ip, self.settings.aizhan_cookie, delay=0)
          rdns:    return fetch_rdns_ptr(ip, self.settings.rdns_query_timeout)
        """
        pass

    def _print_result(self, ip, data):
        """
        【各渠道自定义】展示单条查询结果。

        示例:
          fofa:    print(f"✅ {data.get('country_name')} - {data.get('org')}")
          aizhan:  print(f"✅ {data.get('location')} - {data.get('domain_count')} 个域名")
          rdns:    print(f"✅ {data.get('hostname')}")
        """
        pass

    def _get_delay(self):
        """
        【各渠道自定义】从 Settings 获取查询间隔。
        """
        return getattr(self.settings, 'xxx_query_delay', 1.0)

    def run(self):
        if not self.no_validate:
            validate_channel_key()

        delay = self._get_delay()
        pending_count = self.load_stats['pending_count']
        total_count = self.load_stats['unique_count']
        processed_count = self.load_stats['already_processed']

        print(f"开始批量查询 XXX 信息")
        print(f"IP 文件: {self.ip_file}")
        if self.load_stats['duplicate_count'] > 0:
            print(f"IP 去重: 原始 {self.load_stats['raw_count']}, 去重后 {total_count}, 重复 {self.load_stats['duplicate_count']}")
        print(f"总 IP 数: {total_count}")
        print(f"已处理: {processed_count}")
        print(f"待处理: {pending_count}")
        print(f"查询间隔: {delay} 秒")
        print("-" * 60)

        current_count = processed_count
        success_count = 0
        fail_count = 0

        try:
            for ip in self.pending_ips:
                current_count += 1

                print(f"[{current_count}/{total_count}] 正在查询: {ip}", end=' ', flush=True)

                data = self._query_ip(ip)

                if isinstance(data, dict) and (data.get('raw_error') or data.get('error')):
                    print(f"❌ {data.get('error_message', data.get('error', 'Unknown'))}")
                    fail_count += 1
                else:
                    self._print_result(ip, data)
                    success_count += 1

                self.ip_writer.add_or_update_ip(ip, self.channel_name, data)
                save_progress(self.progress_file, ip)

                time.sleep(delay)

        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print(f"查询已中断！")
            print(f"已处理: {current_count} 个 IP")
            print(f"成功: {success_count} 个")
            print(f"失败: {fail_count} 个")
            print(f"进度文件: {self.progress_file}")
            print("=" * 60)
            sys.exit(0)

        print("\n" + "=" * 60)
        print(f"批量查询完成！")
        print(f"总共处理: {current_count} 个 IP")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='批量查询 XXX 信息')
    parser.add_argument('ip_file', help='IP 文件路径')
    parser.add_argument('--no-validate', action='store_true', help='跳过 Key 有效性校验')

    args = parser.parse_args()

    if not os.path.exists(args.ip_file):
        print(f"错误: 找不到文件 {args.ip_file}")
        sys.exit(1)

    batch = BatchXxxQuery(args.ip_file, no_validate=args.no_validate)
    batch.run()


if __name__ == "__main__":
    main()
