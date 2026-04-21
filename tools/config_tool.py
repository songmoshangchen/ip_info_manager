import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import ENV_FILE


REQUIRED_PREFIX = 'IP_'


class EnvManager:

    def __init__(self, env_path=None):
        self.env_path = env_path or ENV_FILE

    def _parse_lines(self):
        if not os.path.exists(self.env_path):
            return []
        with open(self.env_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_lines(self, lines):
        with open(self.env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def list_all(self):
        lines = self._parse_lines()
        result = {}
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, _, value = stripped.partition('=')
                key = key.strip()
                if key.startswith(REQUIRED_PREFIX):
                    result[key] = value
        return result

    def get(self, key):
        self._validate_key(key)
        all_items = self.list_all()
        if key not in all_items:
            return None
        return all_items[key]

    def set(self, key, value):
        self._validate_key(key)
        lines = self._parse_lines()
        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                existing_key, _, _ = stripped.partition('=')
                if existing_key.strip() == key:
                    lines[i] = f'{key}={value}\n'
                    found = True
                    break
        if not found:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] = lines[-1] + '\n'
            lines.append(f'{key}={value}\n')
        self._write_lines(lines)
        return True

    def delete(self, key):
        self._validate_key(key)
        lines = self._parse_lines()
        new_lines = []
        found = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue
            if '=' in stripped:
                existing_key, _, _ = stripped.partition('=')
                if existing_key.strip() == key:
                    found = True
                    continue
            new_lines.append(line)
        if found:
            self._write_lines(new_lines)
        return found

    def bulk_set(self, items):
        for key, value in items.items():
            self.set(key, value)
        return len(items)

    def _validate_key(self, key):
        if not key.startswith(REQUIRED_PREFIX):
            print(f"错误: Key 必须以 '{REQUIRED_PREFIX}' 开头，收到: {key}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='.env 配置管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    subparsers.add_parser('list', help='列出所有配置项')

    get_parser = subparsers.add_parser('get', help='获取配置值')
    get_parser.add_argument('key', help='配置键名')

    set_parser = subparsers.add_parser('set', help='设置配置值')
    set_parser.add_argument('key', help='配置键名')
    set_parser.add_argument('value', help='配置值')

    delete_parser = subparsers.add_parser('delete', help='删除配置项')
    delete_parser.add_argument('key', help='配置键名')

    bulk_parser = subparsers.add_parser('bulk-set', help='批量设置配置项')
    bulk_parser.add_argument('items', nargs='+', help='键值对，格式: KEY=VALUE')

    args = parser.parse_args()
    mgr = EnvManager()

    if args.command == 'list':
        items = mgr.list_all()
        if not items:
            print(f"配置文件为空或不存在: {mgr.env_path}")
            return
        max_key_len = max(len(k) for k in items)
        print(f"配置文件: {mgr.env_path}")
        print(f"{'Key'.ljust(max_key_len)}  Value")
        print('-' * (max_key_len + 40))
        for key in sorted(items):
            value = items[key]
            display_value = value[:50] + '...' if len(value) > 50 else value
            print(f"{key.ljust(max_key_len)}  {display_value}")
        print(f"\n共 {len(items)} 个配置项")

    elif args.command == 'get':
        value = mgr.get(args.key)
        if value is None:
            print(f"未找到: {args.key}")
            sys.exit(1)
        print(value)

    elif args.command == 'set':
        mgr.set(args.key, args.value)
        print(f"已设置: {args.key}={args.value[:30]}{'...' if len(args.value) > 30 else ''}")

    elif args.command == 'delete':
        if mgr.delete(args.key):
            print(f"已删除: {args.key}")
        else:
            print(f"未找到: {args.key}")
            sys.exit(1)

    elif args.command == 'bulk-set':
        items = {}
        for item in args.items:
            if '=' not in item:
                print(f"错误: 格式无效 '{item}'，应为 KEY=VALUE")
                sys.exit(1)
            key, _, value = item.partition('=')
            items[key] = value
        count = mgr.bulk_set(items)
        print(f"已批量设置 {count} 个配置项")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
