import json
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def load_json(json_file):
    if not os.path.exists(json_file):
        print(f"错误: 找不到文件 {json_file}")
        sys.exit(1)
    with open(json_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)


def load_progress(progress_file):
    if not os.path.exists(progress_file):
        return []
    with open(progress_file, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def save_progress(progress_file, ips):
    dir_path = os.path.dirname(progress_file)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    with open(progress_file, 'w', encoding='utf-8') as f:
        for ip in ips:
            f.write(ip + '\n')


def generate(json_file, channel, output=None):
    data = load_json(json_file)

    total = len(data)
    ips = [ip for ip, entry in data.items() if isinstance(entry, dict) and channel in entry]

    if output is None:
        output = f"{json_file}.{channel}.progress"

    save_progress(output, ips)

    print(f"JSON 文件: {json_file}")
    print(f"总 IP 数: {total}")
    print(f"含渠道 '{channel}' 的 IP 数: {len(ips)}")
    print(f"已生成: {output}")


def remove(progress_file, ips_to_remove):
    if not os.path.exists(progress_file):
        print(f"错误: 找不到文件 {progress_file}")
        sys.exit(1)

    original = load_progress(progress_file)
    original_set = set(original)
    remove_set = set(ips_to_remove)

    kept = [ip for ip in original if ip not in remove_set]
    actually_removed = original_set & remove_set

    save_progress(progress_file, kept)

    print(f"Progress 文件: {progress_file}")
    print(f"原数量: {len(original)}")
    print(f"删除数量: {len(actually_removed)}")
    print(f"剩余数量: {len(kept)}")


def main():
    parser = argparse.ArgumentParser(description='Progress 文件管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    gen_parser = subparsers.add_parser('generate', help='从 JSON 数据生成 progress 文件')
    gen_parser.add_argument('json_file', help='JSON 数据文件路径')
    gen_parser.add_argument('--channel', required=True, help='渠道名称')
    gen_parser.add_argument('-o', '--output', help='输出路径（默认: <json_file>.<channel>.progress）')

    rm_parser = subparsers.add_parser('remove', help='从 progress 文件中删除指定 IP')
    rm_parser.add_argument('progress_file', help='Progress 文件路径')
    rm_parser.add_argument('ips', nargs='*', help='要删除的 IP 地址')
    rm_parser.add_argument('--from-file', help='从文件读取要删除的 IP（每行一个）')

    args = parser.parse_args()

    if args.command == 'generate':
        generate(args.json_file, args.channel, args.output)

    elif args.command == 'remove':
        ips_to_remove = list(args.ips or [])
        if args.from_file:
            file_ips = load_progress(args.from_file)
            ips_to_remove.extend(file_ips)
        if not ips_to_remove:
            print("错误: 请提供要删除的 IP（命令行参数或 --from-file）")
            sys.exit(1)
        remove(args.progress_file, ips_to_remove)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
