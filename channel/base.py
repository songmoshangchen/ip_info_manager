import time
from datetime import datetime


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    result = dict(data)
    result.setdefault('query_time', datetime.now().isoformat())
    return result
