# -*- coding: utf-8 -*-
"""
日志工具模块
提供统一的日志记录接口

可维护性升级 v2.0：
- 使用 RotatingFileHandler 实现日志自动轮转
- 单个日志文件最大限制：10MB
- 保留备份文件数量：5个
- 日志格式包含时间戳、日志级别和模块名
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

    日志轮转配置：
        - 单个日志文件最大：10MB
        - 保留备份文件：5个（ashare_sentinel.log.1, .log.2, ..., .log.5）
        - 当日志文件达到10MB时，自动轮转到下一个备份文件
        - 最旧的备份文件（.log.5）会被自动删除

    日志格式：
        YYYY-MM-DD HH:MM:SS - 模块名 - 级别 - 消息内容
        例如: 2026-01-13 15:30:45 - src.data.data_loader - INFO - 正在获取A股实时行情数据...
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

    # 创建格式化器（包含时间戳、模块名、日志级别）
    formatter = logging.Formatter(
        getattr(LogConfig, 'FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # 添加文件处理器（带轮转功能）
    log_file = Path(getattr(LogConfig, 'FILE', 'logs/ashare_sentinel.log'))
    log_file.parent.mkdir(exist_ok=True)

    # RotatingFileHandler 配置：
    # - maxBytes: 单个日志文件最大 10MB
    # - backupCount: 保留 5 个备份文件
    # - 当文件达到 10MB 时，自动轮转：
    #   ashare_sentinel.log -> ashare_sentinel.log.1
    #   ashare_sentinel.log.1 -> ashare_sentinel.log.2
    #   ...
    #   ashare_sentinel.log.5 -> 删除
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=getattr(LogConfig, 'MAX_BYTES', 10) * 1024 * 1024,  # 10MB
        backupCount=getattr(LogConfig, 'BACKUP_COUNT', 5),  # 保留5个备份
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

    日志级别说明：
        - DEBUG: 详细信息，用于调试
        - INFO: 一般信息，确认程序正常运行
        - WARNING: 警告信息，表示发生了意外情况
        - ERROR: 错误信息，表示程序出现了严重问题
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    for logger in _loggers.values():
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)


def get_log_files() -> list:
    """
    获取所有日志文件列表

    Returns:
        list: 日志文件路径列表（包括主日志文件和备份文件）

    返回示例：
        [
            'logs/ashare_sentinel.log',
            'logs/ashare_sentinel.log.1',
            'logs/ashare_sentinel.log.2',
            ...
        ]
    """
    log_file = Path(getattr(LogConfig, 'FILE', 'logs/ashare_sentinel.log'))
    log_dir = log_file.parent

    if not log_dir.exists():
        return []

    # 获取所有相关的日志文件
    log_files = []
    base_name = log_file.name

    # 主日志文件
    if log_file.exists():
        log_files.append(str(log_file))

    # 备份日志文件
    for i in range(1, getattr(LogConfig, 'BACKUP_COUNT', 5) + 1):
        backup_file = log_dir / f"{base_name}.{i}"
        if backup_file.exists():
            log_files.append(str(backup_file))

    return log_files


class LoggerMixin:
    """
    日志混入类
    为类提供便捷的日志记录功能

    使用示例：
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("开始执行任务...")
                try:
                    # 业务逻辑
                    self.logger.info("任务执行成功")
                except Exception as e:
                    self.logger.error(f"任务执行失败: {e}")
    """

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


if __name__ == "__main__":
    # 测试日志功能
    print("="*60)
    print("日志工具模块测试")
    print("="*60)

    # 测试基本日志功能
    test_logger = get_logger("test")

    print("\n测试不同级别的日志：")
    test_logger.debug("这是 DEBUG 级别的日志")
    test_logger.info("这是 INFO 级别的日志")
    test_logger.warning("这是 WARNING 级别的日志")
    test_logger.error("这是 ERROR 级别的日志")

    # 测试日志轮转信息
    print("\n当前日志文件列表：")
    log_files = get_log_files()
    for file in log_files:
        print(f"  - {file}")

    # 测试 LoggerMixin
    print("\n测试 LoggerMixin：")
    class TestService(LoggerMixin):
        def run(self):
            self.logger.info("TestService 启动")
            self.logger.warning("这是一个警告")
            self.logger.error("这是一个错误")

    service = TestService()
    service.run()

    print("\n日志文件位置:")
    print(f"  主日志: {getattr(LogConfig, 'FILE', 'logs/ashare_sentinel.log')}")
    print(f"  最大大小: {getattr(LogConfig, 'MAX_BYTES', 10)}MB")
    print(f"  备份数量: {getattr(LogConfig, 'BACKUP_COUNT', 5)}个")
    print("\n测试完成！")
