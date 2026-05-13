import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime

# TODO: 未来支持 fscan 引擎
# - 配置项: IP_PORT_SCAN_ENGINE=fscan
# - 路径配置: IP_PORT_SCAN_FSCAN_PATH
# - 输出解析: fscan 文本输出解析
# - 参考: https://github.com/shadow1ng/fscan

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import TraceIPSettings
from writer import IPWriter
from utils.logger_utils import get_channel_logger

_logger = get_channel_logger('port_scan')


def load_port_list(port_list_path: str) -> list:
    if not os.path.isabs(port_list_path):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        port_list_path = os.path.join(project_root, port_list_path)

    if not os.path.exists(port_list_path):
        _logger.warning("端口列表文件不存在: %s", port_list_path)
        return []

    with open(port_list_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    ports = []
    for part in content.replace('\n', ',').split(','):
        p = part.strip()
        if p.isdigit():
            ports.append(int(p))
    return sorted(set(ports))


def extract_historical_ports(ip_data: dict) -> list:
    ports = set()

    fofa = ip_data.get('fofa_host', {})
    if fofa and not fofa.get('error'):
        for p in fofa.get('ports', []):
            port_val = p.get('port')
            if isinstance(port_val, int):
                ports.add(port_val)
            elif isinstance(port_val, str) and port_val.isdigit():
                ports.add(int(port_val))

    zoomeye = ip_data.get('zoomeye', {})
    if zoomeye and zoomeye.get('data'):
        for item in zoomeye['data']:
            port_val = item.get('port')
            if isinstance(port_val, int):
                ports.add(port_val)
            elif isinstance(port_val, str) and port_val.isdigit():
                ports.add(int(port_val))

    return sorted(ports)


def build_port_string(historical_ports: list, top_ports: list) -> str:
    all_ports = sorted(set(historical_ports + top_ports))
    return ','.join(str(p) for p in all_ports)


def validate_engine(nmap_path: str) -> bool:
    if os.path.isabs(nmap_path):
        if not os.path.isfile(nmap_path):
            _logger.error("nmap 路径不存在: %s", nmap_path)
            return False
        return True

    try:
        result = subprocess.run(
            [nmap_path, '--version'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            _logger.debug("nmap 版本: %s", result.stdout.strip().split('\n')[0])
            return True
        return False
    except FileNotFoundError:
        _logger.error("找不到 nmap: %s", nmap_path)
        return False
    except subprocess.TimeoutExpired:
        _logger.error("nmap 版本检测超时")
        return False
    except Exception as e:
        _logger.error("nmap 检测异常: %s", e)
        return False


def request_channel(ip: str, nmap_path: str = 'nmap', port_string: str = '',
                    timeout: int = 30, **kwargs) -> dict:
    cmd = [nmap_path, '-sT', '-T4', '-Pn', '--open', '-oX', '-']

    if port_string:
        cmd.extend(['-p', port_string])

    cmd.append(ip)

    _logger.debug("执行命令: %s", ' '.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=timeout,
        )
        return {
            'xml_output': result.stdout,
            'returncode': result.returncode,
            'stderr': result.stderr,
        }
    except FileNotFoundError:
        _logger.error("nmap 命令不存在: %s", nmap_path)
        return {'raw_error': True, 'error_message': f'nmap not found: {nmap_path}'}
    except subprocess.TimeoutExpired:
        _logger.warning("nmap 扫描超时: %s (%ds)", ip, timeout)
        return {'raw_error': True, 'error_message': f'nmap timeout after {timeout}s'}
    except Exception as e:
        _logger.error("nmap 扫描异常: %s, error: %s", ip, e)
        return {'raw_error': True, 'error_message': str(e)}


def parse_nmap_xml(xml_output: str, historical_ports: list) -> dict:
    result = {
        'host_alive': False,
        'open_ports': [],
        'total_scanned': 0,
        'open_count': 0,
        'historical_ports_verified': [],
        'historical_ports_closed': [],
    }

    historical_set = set(historical_ports)

    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        _logger.debug("XML 解析失败: %s", e)
        return result

    host_elem = root.find('host')
    if host_elem is None:
        return result

    status_elem = host_elem.find('status')
    if status_elem is not None:
        result['host_alive'] = status_elem.get('state') == 'up'

    ports_elem = host_elem.find('ports')
    if ports_elem is not None:
        open_ports = []
        for port_elem in ports_elem.findall('port'):
            port_id = port_elem.get('portid')
            protocol = port_elem.get('protocol', 'tcp')
            state_elem = port_elem.find('state')
            service_elem = port_elem.find('service')

            if state_elem is not None and state_elem.get('state') == 'open':
                port_info = {
                    'port': int(port_id),
                    'protocol': protocol,
                    'state': 'open',
                }
                if service_elem is not None:
                    port_info['service'] = service_elem.get('name', '')
                    port_info['product'] = service_elem.get('product', '')
                    port_info['version'] = service_elem.get('version', '')
                open_ports.append(port_info)

                if int(port_id) in historical_set:
                    result['historical_ports_verified'].append(int(port_id))

        result['open_ports'] = open_ports
        result['open_count'] = len(open_ports)

        all_scanned = ports_elem.findall('port')
        result['total_scanned'] = len(all_scanned)

        verified_set = set(result['historical_ports_verified'])
        for hp in historical_ports:
            if hp not in verified_set:
                result['historical_ports_closed'].append(hp)

    return result


def fetch_channel(ip: str, nmap_path: str = 'nmap', port_string: str = '',
                  timeout: int = 30, historical_ports: list = None,
                  delay: float = 0, **kwargs) -> dict:
    apply_delay(delay)

    _logger.debug("fetch_channel 开始: ip=%s", ip)

    raw = request_channel(ip, nmap_path=nmap_path, port_string=port_string,
                          timeout=timeout, **kwargs)

    if raw.get('raw_error'):
        return format_output_error(ip, raw.get('error_message', 'Unknown'))

    parsed = parse_nmap_xml(raw.get('xml_output', ''), historical_ports or [])

    return format_output(ip, parsed, raw.get('returncode', -1))


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output_error(ip: str, error_message: str) -> dict:
    return {
        'ip': ip,
        'engine': 'nmap',
        'scan_time': datetime.now().isoformat(),
        'error': error_message,
        'host_alive': False,
        'open_ports': [],
        'open_count': 0,
    }


def format_output(ip: str, parsed: dict, returncode: int) -> dict:
    result = {
        'ip': ip,
        'engine': 'nmap',
        'scan_time': datetime.now().isoformat(),
        'host_alive': parsed.get('host_alive', False),
        'open_ports': parsed.get('open_ports', []),
        'total_scanned': parsed.get('total_scanned', 0),
        'open_count': parsed.get('open_count', 0),
        'historical_ports_verified': parsed.get('historical_ports_verified', []),
        'historical_ports_closed': parsed.get('historical_ports_closed', []),
    }

    if returncode != 0:
        result['nmap_returncode'] = returncode

    return result


def main(ip: str):
    settings = TraceIPSettings()
    ip_writer = IPWriter(settings=settings)

    top_ports = load_port_list(settings.port_scan_port_list)
    port_string = ','.join(str(p) for p in top_ports) if top_ports else ''

    data = fetch_channel(
        ip=ip,
        nmap_path=settings.port_scan_nmap_path,
        port_string=port_string,
        timeout=settings.port_scan_timeout,
        delay=settings.port_scan_query_delay,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="port_scan", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python port_scan.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
