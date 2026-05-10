import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from utils.pid_manager import PidManager


_HEARTBEAT_TIMEOUT = 120

_SEPARATOR = '\u2501' * 40


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f'{seconds:.0f}s'
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f'{minutes}min{secs:02d}s'
    hours = int(minutes // 60)
    mins = minutes % 60
    return f'{hours}h{mins:02d}min'


def _parse_iso_time(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _count_progress_lines(progress_file: str) -> int:
    if not os.path.exists(progress_file):
        return 0
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except IOError:
        return 0


def _check_phase_done(output_dir: str, prefix: str, marker_suffix: str) -> bool:
    marker = os.path.join(output_dir, f'{prefix}.{marker_suffix}')
    return os.path.exists(marker)


def _compute_eta(elapsed: float, done: int, total: int) -> str:
    if done <= 0 or total <= 0 or done >= total:
        return '--'
    avg = elapsed / done
    remaining = (total - done) * avg
    return _format_duration(remaining)


def _determine_status(pid_data: dict) -> str:
    if pid_data is None:
        return 'not_running'

    pid = pid_data.get('pid')
    if not pid or not PidManager.is_process_alive(pid):
        return 'crashed'

    last_hb_str = pid_data.get('last_heartbeat', '')
    last_hb = _parse_iso_time(last_hb_str)
    if last_hb:
        elapsed_hb = (datetime.now() - last_hb).total_seconds()
        if elapsed_hb > _HEARTBEAT_TIMEOUT:
            return 'hung'

    return 'running'


def _print_status_line(status: str, pid_data: dict = None):
    if status == 'running':
        pid = pid_data.get('pid', '?')
        start = _parse_iso_time(pid_data.get('start_time', ''))
        start_str = start.strftime('%H:%M:%S') if start else '?'
        elapsed = (datetime.now() - start).total_seconds() if start else 0
        print(f'\U0001f7e2 运行中 (PID: {pid}, 启动于 {start_str})')
        print(f'\u23f1\ufe0f 已运行: {_format_duration(elapsed)}')
    elif status == 'hung':
        pid = pid_data.get('pid', '?')
        print(f'\u23f3 疑似卡死 (PID: {pid}, 心跳超过 {_HEARTBEAT_TIMEOUT}s)')
    elif status == 'crashed':
        pid = pid_data.get('pid', '?')
        print(f'\u26a0\ufe0f 异常终止 (进程 {pid} 已不存在)')
    elif status == 'not_running':
        print(f'\u2b1c 未运行')


def _print_phase_status(done_phases: dict, current_phase=None):
    for phase_num, (label, done) in sorted(done_phases.items()):
        if done:
            icon = '\u2705'
        elif phase_num == current_phase:
            icon = '\u23f3'
        else:
            icon = '\u2b1c'
        print(f'  Phase {phase_num}: {icon} {label}')


def status_trace_ip():
    settings = Settings()
    project_name = settings.trace_ip_project_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'trace_ip', project_name)

    print(f'\U0001f4cb 溯源流水线状态 \u2014 项目: {project_name}')
    print(_SEPARATOR)

    if not os.path.exists(output_dir):
        print('\u2b1c 项目目录不存在')
        return

    pm = PidManager(output_dir, project_name)
    pid_data = pm.read_pid()
    status = _determine_status(pid_data)

    _print_status_line(status, pid_data)

    phase_names = {
        1: '\u57fa\u7840\u60c5\u62a5\u91c7\u96c6',
        2: '\u81ea\u52a8\u5206\u7c7b\u8fc7\u6ee4 + \u6807\u7b7e\u6253\u6807',
        3: '\u6df1\u5ea6\u67e5\u8be2',
        4: '\u6c47\u603b\u8f93\u51fa',
        5: '\u751f\u6210\u62a5\u544a\uff08Word + Excel\uff09',
    }

    done_phases = {}
    for p in range(1, 6):
        marker = f'trace_phase{p}_done'
        done_phases[p] = (phase_names.get(p, ''), _check_phase_done(output_dir, project_name, marker))

    current_phase = pid_data.get('current_phase') if pid_data else None

    if status == 'running' and current_phase:
        print(f'\U0001f4cd 当前阶段: Phase {current_phase} - {phase_names.get(current_phase, "")}')

    if pid_data:
        total_ips = pid_data.get('total_ips', 0)
        progress_file = os.path.join(output_dir, f'{project_name}.trace_phase1.progress')
        done_count = _count_progress_lines(progress_file)

        if status == 'running' and current_phase == 3:
            progress_file = os.path.join(output_dir, f'{project_name}.trace_phase3.progress')
            done_count = _count_progress_lines(progress_file)

        if total_ips > 0:
            pct = done_count / total_ips * 100
            print(f'\U0001f4ca 进度: {done_count}/{total_ips} ({pct:.1f}%)', end='')

            if status == 'running':
                start = _parse_iso_time(pid_data.get('start_time', ''))
                if start:
                    elapsed = (datetime.now() - start).total_seconds()
                    eta = _compute_eta(elapsed, done_count, total_ips)
                    print(f'  ETA: ~{eta}')
                else:
                    print()
            else:
                print()

        last_hb_str = pid_data.get('last_heartbeat', '')
        last_hb = _parse_iso_time(last_hb_str)
        if last_hb and status == 'running':
            hb_elapsed = (datetime.now() - last_hb).total_seconds()
            print(f'\U0001fafb 心跳: {_format_duration(hb_elapsed)}前')

    if status == 'crashed':
        print(f'\U0001f4a1 建议: 运行 python tools/status_tool.py cleanup trace_ip 清理')
        print(f'\U0001f4a1 可使用 --from-phase {current_phase or 1} 续查')

    print(_SEPARATOR)
    print('阶段完成情况:')
    _print_phase_status(done_phases, current_phase)


def status_ip_domain_lookup():
    settings = Settings()
    project_name = settings.ip_domain_lookup_project_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'ip_domain_lookup', project_name)

    print(f'\U0001f4cb IP域名反查状态 \u2014 项目: {project_name}')
    print(_SEPARATOR)

    if not os.path.exists(output_dir):
        print('\u2b1c 项目目录不存在')
        return

    pm = PidManager(output_dir, project_name)
    pid_data = pm.read_pid()
    status = _determine_status(pid_data)

    _print_status_line(status, pid_data)

    phase_names = {
        1: '\u57df\u540d\u6536\u96c6',
        2: 'DNS\u6b63\u5411\u9a8c\u8bc1',
        3: '\u6c47\u603b\u62a5\u544a',
        4: '\u751f\u6210 Word \u62a5\u544a',
    }

    done_phases = {}
    for p in range(1, 5):
        marker = f'domain_lookup_phase{p}_done'
        done_phases[p] = (phase_names.get(p, ''), _check_phase_done(output_dir, project_name, marker))

    current_phase = pid_data.get('current_phase') if pid_data else None

    if status == 'running' and current_phase:
        print(f'\U0001f4cd 当前阶段: Phase {current_phase} - {phase_names.get(current_phase, "")}')

    if pid_data:
        total_ips = pid_data.get('total_ips', 0)
        progress_file = os.path.join(output_dir, f'{project_name}.domain_lookup_phase1.progress')
        done_count = _count_progress_lines(progress_file)

        if status == 'running' and current_phase == 2:
            progress_file = os.path.join(output_dir, f'{project_name}.domain_lookup_phase2.progress')
            done_count = _count_progress_lines(progress_file)

        if total_ips > 0:
            pct = done_count / total_ips * 100
            print(f'\U0001f4ca 进度: {done_count}/{total_ips} ({pct:.1f}%)', end='')

            if status == 'running':
                start = _parse_iso_time(pid_data.get('start_time', ''))
                if start:
                    elapsed = (datetime.now() - start).total_seconds()
                    eta = _compute_eta(elapsed, done_count, total_ips)
                    print(f'  ETA: ~{eta}')
                else:
                    print()
            else:
                print()

        last_hb_str = pid_data.get('last_heartbeat', '')
        last_hb = _parse_iso_time(last_hb_str)
        if last_hb and status == 'running':
            hb_elapsed = (datetime.now() - last_hb).total_seconds()
            print(f'\U0001fafb 心跳: {_format_duration(hb_elapsed)}前')

    if status == 'crashed':
        print(f'\U0001f4a1 建议: 运行 python tools/status_tool.py cleanup ip_domain_lookup 清理')
        print(f'\U0001f4a1 可使用 --from-phase {current_phase or 1} 续查')

    print(_SEPARATOR)
    print('阶段完成情况:')
    _print_phase_status(done_phases, current_phase)


def status_batch():
    settings = Settings()
    storage_dir = settings.storage_dir
    storage_name = settings.storage_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if storage_dir:
        data_dir = os.path.join(project_root, 'data', storage_dir)
    else:
        data_dir = os.path.join(project_root, 'data')

    print(f'\U0001f4cb 批量查询状态 \u2014 存储: {storage_name}')
    print(_SEPARATOR)

    if not os.path.exists(data_dir):
        print('\u2b1c 数据目录不存在')
        return

    pm = PidManager(data_dir, storage_name)
    pid_data = pm.read_pid()
    status = _determine_status(pid_data)

    _print_status_line(status, pid_data)

    if pid_data:
        total_ips = pid_data.get('total_ips', 0)
        channel = pid_data.get('task_type', '').replace('batch_', '')
        progress_file = os.path.join(data_dir, f'{storage_name}.{channel}.progress')
        done_count = _count_progress_lines(progress_file)

        if total_ips > 0:
            pct = done_count / total_ips * 100
            print(f'\U0001f4ca 进度: {done_count}/{total_ips} ({pct:.1f}%)', end='')

            if status == 'running':
                start = _parse_iso_time(pid_data.get('start_time', ''))
                if start:
                    elapsed = (datetime.now() - start).total_seconds()
                    eta = _compute_eta(elapsed, done_count, total_ips)
                    print(f'  ETA: ~{eta}')
                else:
                    print()
            else:
                print()

    if status == 'crashed':
        print(f'\U0001f4a1 建议: 运行 python tools/status_tool.py cleanup batch 清理')

    print(_SEPARATOR)


def cleanup_trace_ip():
    settings = Settings()
    project_name = settings.trace_ip_project_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'trace_ip', project_name)

    pm = PidManager(output_dir, project_name)
    if os.path.exists(pm.pid_file):
        pm.remove_pid()
        print(f'已清理溯源流水线 PID 文件: {pm.pid_file}')
    else:
        print('未发现残留 PID 文件')


def cleanup_ip_domain_lookup():
    settings = Settings()
    project_name = settings.ip_domain_lookup_project_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'ip_domain_lookup', project_name)

    pm = PidManager(output_dir, project_name)
    if os.path.exists(pm.pid_file):
        pm.remove_pid()
        print(f'已清理域名反查 PID 文件: {pm.pid_file}')
    else:
        print('未发现残留 PID 文件')


def cleanup_batch():
    settings = Settings()
    storage_dir = settings.storage_dir
    storage_name = settings.storage_name
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if storage_dir:
        data_dir = os.path.join(project_root, 'data', storage_dir)
    else:
        data_dir = os.path.join(project_root, 'data')

    pm = PidManager(data_dir, storage_name)
    if os.path.exists(pm.pid_file):
        pm.remove_pid()
        print(f'已清理批量查询 PID 文件: {pm.pid_file}')
    else:
        print('未发现残留 PID 文件')


def main():
    parser = argparse.ArgumentParser(description='任务状态查询工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    subparsers.add_parser('trace_ip', help='查看溯源流水线状态')
    subparsers.add_parser('ip_domain_lookup', help='查看IP域名反查状态')
    subparsers.add_parser('batch', help='查看批量查询状态')

    cleanup_parser = subparsers.add_parser('cleanup', help='清理残留 PID 文件')
    cleanup_parser.add_argument(
        'target', choices=['trace_ip', 'ip_domain_lookup', 'batch'],
        help='要清理的场景')

    args = parser.parse_args()

    if args.command == 'trace_ip':
        status_trace_ip()
    elif args.command == 'ip_domain_lookup':
        status_ip_domain_lookup()
    elif args.command == 'batch':
        status_batch()
    elif args.command == 'cleanup':
        if args.target == 'trace_ip':
            cleanup_trace_ip()
        elif args.target == 'ip_domain_lookup':
            cleanup_ip_domain_lookup()
        elif args.target == 'batch':
            cleanup_batch()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
