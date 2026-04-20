import sys
import argparse


def read_ips(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ips = set(line.strip() for line in f if line.strip())
        return ips
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{file_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取文件 '{file_path}' 时出错: {e}")
        sys.exit(1)


def compare_ip_files(file_a, file_b):
    print(f"正在读取文件 A: {file_a}")
    ips_a = read_ips(file_a)
    print(f"文件 A 中共有 {len(ips_a)} 个IP\n")

    print(f"正在读取文件 B: {file_b}")
    ips_b = read_ips(file_b)
    print(f"文件 B 中共有 {len(ips_b)} 个IP\n")

    common_ips = ips_a & ips_b
    only_in_a = ips_a - ips_b
    only_in_b = ips_b - ips_a

    print("=" * 50)
    print(f"重复的IP（同时在A和B中）: {len(common_ips)} 个")
    print("=" * 50)
    if common_ips:
        for ip in sorted(common_ips):
            print(ip)
    else:
        print("(无)")

    print("\n" + "=" * 50)
    print(f"只在A中的IP: {len(only_in_a)} 个")
    print("=" * 50)
    if only_in_a:
        for ip in sorted(only_in_a):
            print(ip)
    else:
        print("(无)")

    print("\n" + "=" * 50)
    print(f"只在B中的IP: {len(only_in_b)} 个")
    print("=" * 50)
    if only_in_b:
        for ip in sorted(only_in_b):
            print(ip)
    else:
        print("(无)")


def main():
    parser = argparse.ArgumentParser(description='比较两个IP文件，找出重复和差异IP')
    parser.add_argument('file_a', help='文件A路径')
    parser.add_argument('file_b', help='文件B路径')

    args = parser.parse_args()

    compare_ip_files(args.file_a, args.file_b)


if __name__ == "__main__":
    main()
