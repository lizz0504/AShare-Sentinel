# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录接口
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from ..config import LogConfig


# 日志记录器缓存
_loggers = {}


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，通常使用 __name__
        level: 日志级别，如果不指定则使用配置文件中的设置

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 如果已经创建过，直接返回
    if name in _loggers:
        return _loggers[name]

    # 创建新的日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level or getattr(LogConfig, 'LEVEL', 'INFO'))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        getattr(LogConfig, 'FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # 添加文件处理器
    log_file = Path(getattr(LogConfig, 'FILE', 'logs/ashare_sentinel.log'))
    log_file.parent.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=getattr(LogConfig, 'MAX_BYTES', 10) * 1024 * 1024,
        backupCount=getattr(LogConfig, 'BACKUP_COUNT', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 添加控制台处理器
    if getattr(LogConfig, 'CONSOLE_OUTPUT', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 缓存日志记录器
    _loggers[name] = logger

    return logger


def set_level(level: str) -> None:
    """
    设置全局日志级别

    Args:
        level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    for logger in _loggers.values():
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)


class LoggerMixin:
    """
    日志混入类
    为类提供便捷的日志记录功能
    """

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
