#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 列表处理器

该脚本用于处理 IP 列表，包括验证 IP 格式、去重等功能，返回处理后的结果。
"""

import re
import sys
import argparse
from typing import List, Dict


def validate_ip(ip: str) -> bool:
    """
    验证 IP 地址格式是否正确（支持 IPv4 和 IPv6）

    Args:
        ip: 待验证的 IP 地址字符串

    Returns:
        bool: 如果 IP 地址格式正确返回 True，否则返回 False
    """
    # IPv4 地址验证
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(ipv4_pattern, ip):
        return True

    # IPv6 地址验证
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$"
    if re.match(ipv6_pattern, ip):
        return True

    # IPv6 压缩格式验证
    compressed_ipv6_pattern = r"^([0-9a-fA-F]{1,4}:)*(:[0-9a-fA-F]{1,4}){1,7}$"
    if re.match(compressed_ipv6_pattern, ip):
        return True

    return False


def process_ip_list(ip_list: List[str]) -> Dict:
    """
    处理 IP 列表

    Args:
        ip_list: 原始 IP 列表

    Returns:
        Dict: 处理结果，包含原始 IP 数量、有效 IP 数量、处理后的 IP 列表等信息
    """
    # 统计原始 IP 数量
    original_count = len(ip_list)

    # 去重
    unique_ips = list(set(ip_list))
    unique_count = len(unique_ips)

    # 验证 IP 格式并过滤
    valid_ips = [ip for ip in unique_ips if validate_ip(ip)]
    valid_count = len(valid_ips)

    # 排序
    valid_ips.sort()

    # 统计无效 IP
    invalid_ips = [ip for ip in unique_ips if not validate_ip(ip)]
    invalid_count = len(invalid_ips)

    return {
        "success": True,
        "original_count": original_count,
        "unique_count": unique_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "valid_ips": valid_ips,
        "invalid_ips": invalid_ips,
    }


def main(ip_string: str) -> Dict:
    """
    Args:
        ip_string: 原始 IP 字符串，一行一个 IP

    Returns:
        Dict: 处理结果
    """
    if not ip_string:
        return {
            "success": False,
            "error": "未提供 IP 列表",
            "original_count": 0,
            "unique_count": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "valid_ips": [],
            "invalid_ips": [],
        }

    # 解析字符串，按行分割并去除空白
    ip_list = [ip.strip() for ip in ip_string.split("\n") if ip.strip()]

    result = process_ip_list(ip_list)
    return result


def read_ip_from_file(file_path: str) -> str:
    """
    从文件中读取 IP 列表
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取文件时出错 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='IP 列表处理器 - 验证、去重和处理 IP 地址列表')
    parser.add_argument('file_path', help='包含 IP 列表的文件路径（每行一个 IP）')
    parser.add_argument('--show-valid', action='store_true', help='显示有效的 IP 地址列表')
    parser.add_argument('--show-invalid', action='store_true', help='显示无效的 IP 地址列表')
    parser.add_argument('--show-all', action='store_true', help='显示所有 IP 地址列表（有效和无效）')
    
    args = parser.parse_args()
    
    ip_string = read_ip_from_file(args.file_path)
    result = main(ip_string)
    
    print(f"处理结果:")
    print(f"原始 IP 数量: {result['original_count']}")
    print(f"去重后数量: {result['unique_count']}")
    print(f"有效 IP 数量: {result['valid_count']}")
    print(f"无效 IP 数量: {result['invalid_count']}")
    
    show_valid = args.show_valid or args.show_all
    show_invalid = args.show_invalid or args.show_all
    
    if show_valid and result['valid_ips']:
        print(f"\n有效的 IP 地址:")
        for ip in result['valid_ips']:
            print(f"  {ip}")
    
    if show_invalid and result['invalid_ips']:
        print(f"\n无效的 IP 地址:")
        for ip in result['invalid_ips']:
            print(f"  {ip}")
