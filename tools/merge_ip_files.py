import re
import sys
import argparse


def validate_ip(ip: str) -> bool:
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(ipv4_pattern, ip):
        return True

    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$"
    if re.match(ipv6_pattern, ip):
        return True

    compressed_ipv6_pattern = r"^([0-9a-fA-F]{1,4}:)*(:[0-9a-fA-F]{1,4}){1,7}$"
    if re.match(compressed_ipv6_pattern, ip):
        return True

    return False


def read_ips_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            ips = [line.strip() for line in f if line.strip()]
        return ips
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到文件 '{file_path}'")
    except Exception as e:
        raise IOError(f"读取文件 '{file_path}' 时出错: {e}")


def merge_and_dedup(file_paths):
    all_ips = []
    file_stats = {}

    for fp in file_paths:
        ips = read_ips_from_file(fp)
        file_stats[fp] = len(ips)
        all_ips.extend(ips)

    total_raw = len(all_ips)

    seen = set()
    unique_ips = []
    for ip in all_ips:
        if ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)

    valid_ips = []
    invalid_ips = []
    for ip in unique_ips:
        if validate_ip(ip):
            valid_ips.append(ip)
        else:
            invalid_ips.append(ip)

    valid_ips.sort()
    invalid_ips.sort()

    return {
        'total_raw': total_raw,
        'unique_count': len(unique_ips),
        'valid_count': len(valid_ips),
        'invalid_count': len(invalid_ips),
        'valid_ips': valid_ips,
        'invalid_ips': invalid_ips,
        'file_stats': file_stats,
    }


def append_to_file(base_file, source_files):
    base_ips = read_ips_from_file(base_file)
    base_set = set(base_ips)

    all_new = []
    source_stats = {}
    for fp in source_files:
        ips = read_ips_from_file(fp)
        source_stats[fp] = len(ips)
        all_new.extend(ips)

    seen = set()
    unique_new = []
    for ip in all_new:
        if ip not in seen:
            seen.add(ip)
            unique_new.append(ip)

    new_valid = []
    invalid_ips = []
    for ip in unique_new:
        if validate_ip(ip):
            new_valid.append(ip)
        else:
            invalid_ips.append(ip)

    to_append = [ip for ip in new_valid if ip not in base_set]

    return {
        'base_file': base_file,
        'base_count': len(base_ips),
        'source_stats': source_stats,
        'new_total': len(unique_new),
        'new_valid': len(new_valid),
        'invalid_count': len(invalid_ips),
        'invalid_ips': invalid_ips,
        'already_exists': len(new_valid) - len(to_append),
        'to_append': to_append,
        'append_count': len(to_append),
    }


def main():
    parser = argparse.ArgumentParser(description='合并/去重/验证 IP 文件，排除无效 IP 地址')
    parser.add_argument('files', nargs='+', help='IP 文件路径（支持多个文件合并，单文件时仅去重验证）')
    parser.add_argument('-o', '--output', help='输出文件路径（默认输出到屏幕）')
    parser.add_argument('--show-invalid', action='store_true', help='显示被排除的无效IP')
    parser.add_argument('--include-invalid', action='store_true', help='输出结果中包含无效IP（默认仅输出有效IP）')
    parser.add_argument('-a', '--append', action='store_true',
                        help='追加模式：将后续文件中不重复的有效IP追加到第一个文件末尾')

    args = parser.parse_args()

    if args.append and len(args.files) < 2:
        print("错误: 追加模式需要至少2个文件（目标文件 + 来源文件）")
        sys.exit(1)

    if args.append:
        base_file = args.files[0]
        source_files = args.files[1:]
        result = append_to_file(base_file, source_files)

        print("=" * 60)
        print("IP 追加模式报告")
        print("=" * 60)
        print(f"\n目标文件: {result['base_file']}")
        print(f"目标文件已有: {result['base_count']} 个IP")

        print(f"\n来源文件:")
        for fp, count in result['source_stats'].items():
            print(f"  {fp}: {count} 个IP")

        print(f"\n来源文件去重后有效IP: {result['new_valid']}")
        print(f"已在目标文件中存在:   {result['already_exists']}")
        print(f"需要追加的IP数量:     {result['append_count']}")
        print(f"被排除的无效IP:       {result['invalid_count']}")
        print("=" * 60)

        if args.show_invalid and result['invalid_ips']:
            print(f"\n被排除的无效IP ({result['invalid_count']} 个):")
            for ip in result['invalid_ips']:
                print(f"  {ip}")

        if result['to_append']:
            print(f"\n即将追加的IP:")
            print("-" * 40)
            for ip in result['to_append']:
                print(f"  {ip}")

            with open(base_file, 'a', encoding='utf-8') as f:
                for ip in result['to_append']:
                    f.write(ip + '\n')
            print(f"\n已追加 {result['append_count']} 个IP到 {base_file}")
            print(f"文件现有总数: {result['base_count'] + result['append_count']} 个IP")
        else:
            print("\n没有需要追加的新IP")

        return

    result = merge_and_dedup(args.files)

    print("=" * 60)
    if len(args.files) == 1:
        print("IP 去重验证报告")
    else:
        print("IP 合并去重报告")
    print("=" * 60)

    print(f"\n源文件:")
    for fp, count in result['file_stats'].items():
        print(f"  {fp}: {count} 个IP")

    print(f"\n合并后原始总数: {result['total_raw']}")
    print(f"去重后数量:     {result['unique_count']}")
    print(f"有效IP数量:     {result['valid_count']}")
    print(f"无效IP数量:     {result['invalid_count']}")
    print("=" * 60)

    if args.show_invalid and result['invalid_ips']:
        print(f"\n被排除的无效IP ({result['invalid_count']} 个):")
        for ip in result['invalid_ips']:
            print(f"  {ip}")

    output_ips = result['valid_ips']
    if args.include_invalid:
        output_ips = result['valid_ips'] + result['invalid_ips']

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            for ip in output_ips:
                f.write(ip + '\n')
        print(f"\n结果已写入: {args.output}")
    else:
        print(f"\n有效IP列表 ({len(output_ips)} 个):")
        print("-" * 40)
        for ip in output_ips:
            print(ip)


if __name__ == "__main__":
    main()
