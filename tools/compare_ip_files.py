import sys
from pathlib import Path


def read_ips(file_path):
    """读取文件中的IP地址列表"""
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
    """比较两个IP文件"""
    print(f"正在读取文件 A: {file_a}")
    ips_a = read_ips(file_a)
    print(f"文件 A 中共有 {len(ips_a)} 个IP\n")

    print(f"正在读取文件 B: {file_b}")
    ips_b = read_ips(file_b)
    print(f"文件 B 中共有 {len(ips_b)} 个IP\n")

    # 找出重复的IP（同时在a和b中的IP）
    common_ips = ips_a & ips_b

    # 找出在b但不在a的IP
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
    print(f"只在B中的IP: {len(only_in_b)} 个")
    print("=" * 50)
    if only_in_b:
        for ip in sorted(only_in_b):
            print(ip)
    else:
        print("(无)")


def main():
    if len(sys.argv) != 3:
        print("使用方法: python compare_ip_files.py <文件A路径> <文件B路径>")
        print("\n示例:")
        print("  python compare_ip_files.py ips_a.txt ips_b.txt")
        print("\n说明:")
        print("  - 文件中每行一个IP地址")
        print("  - 会显示两个文件中重复的IP")
        print("  - 会显示只在文件B中但不在文件A中的IP")
        sys.exit(1)

    file_a = sys.argv[1]
    file_b = sys.argv[2]

    compare_ip_files(file_a, file_b)


if __name__ == "__main__":
    main()
