import time
from datetime import datetime


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    result = dict(data)
    result.setdefault('query_time', datetime.now().isoformat())
    return result


_NETWORK_ERROR_KEYWORDS = [
    'timeout', 'timed out', 'connectionerror', 'connection refused',
    '网络', '连接', 'rate limit',
]


def is_network_error(data) -> bool:
    if not isinstance(data, dict):
        return False
    if not (data.get('raw_error') or data.get('error')):
        return False
    msg = data.get('error_message', '').lower()
    return any(kw in msg for kw in _NETWORK_ERROR_KEYWORDS)
