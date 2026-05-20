import ctypes
import json
import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger('ip_info_manager.utils.pid_manager')


class PidManager:

    def __init__(self, output_dir: str, prefix: str):
        self._output_dir = output_dir
        self._prefix = prefix
        self._pid_file = os.path.join(output_dir, f'{prefix}.pid')
        self._pid_data = None

    @property
    def pid_file(self) -> str:
        return self._pid_file

    def write_pid(self, task_type: str, ip_file: str,
                  total_ips: int, **kwargs):
        self._pid_data = {
            'pid': os.getpid(),
            'start_time': datetime.now().isoformat(),
            'last_heartbeat': datetime.now().isoformat(),
            'task_type': task_type,
            'ip_file': ip_file,
            'total_ips': total_ips,
            'current_phase': kwargs.get('current_phase'),
            'from_phase': kwargs.get('from_phase'),
            'only_phase': kwargs.get('only_phase'),
        }
        self._flush_pid()
        logger.debug("PID 文件已写入: %s", self._pid_file)

    def update_heartbeat(self, current_phase: int = None):
        if self._pid_data is None:
            return
        self._pid_data['last_heartbeat'] = datetime.now().isoformat()
        if current_phase is not None:
            self._pid_data['current_phase'] = current_phase
        self._flush_pid()

    def remove_pid(self):
        if os.path.exists(self._pid_file):
            try:
                os.remove(self._pid_file)
                logger.debug("PID 文件已删除: %s", self._pid_file)
            except OSError as e:
                logger.warning("删除 PID 文件失败: %s", e)
        self._pid_data = None

    def read_pid(self) -> dict | None:
        if not os.path.exists(self._pid_file):
            return None
        try:
            with open(self._pid_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("读取 PID 文件失败: %s", e)
            return None

    @staticmethod
    def is_process_alive(pid: int) -> bool:
        if sys.platform == 'win32':
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def _flush_pid(self):
        os.makedirs(self._output_dir, exist_ok=True)
        with open(self._pid_file, 'w', encoding='utf-8') as f:
            json.dump(self._pid_data, f, ensure_ascii=False, indent=2)
