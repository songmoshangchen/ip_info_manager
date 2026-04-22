import logging
import os
from logging.handlers import RotatingFileHandler

_SCRIPTS_LOGGER_PREFIX = 'ip_info_manager.scripts'
_CHANNEL_LOGGER_PREFIX = 'ip_info_manager.channel'

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'logs')

_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 3

_CONSOLE_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
_CONSOLE_DATE_FORMAT = '%H:%M:%S'

_FILE_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
_FILE_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_initialized_loggers = set()


def _ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


def get_batch_logger(channel_name):
    logger_name = f'{_SCRIPTS_LOGGER_PREFIX}.{channel_name}'

    if logger_name in _initialized_loggers:
        return logging.getLogger(logger_name)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT, _CONSOLE_DATE_FORMAT))
        logger.addHandler(console_handler)

        _ensure_log_dir()
        log_file = os.path.join(_LOG_DIR, f'{channel_name}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, _FILE_DATE_FORMAT))
        logger.addHandler(file_handler)

    _initialized_loggers.add(logger_name)
    return logger


def get_channel_logger(channel_name):
    logger_name = f'{_CHANNEL_LOGGER_PREFIX}.{channel_name}'

    if logger_name in _initialized_loggers:
        return logging.getLogger(logger_name)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        _ensure_log_dir()
        log_file = os.path.join(_LOG_DIR, f'{channel_name}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, _FILE_DATE_FORMAT))
        logger.addHandler(file_handler)

    _initialized_loggers.add(logger_name)
    return logger
