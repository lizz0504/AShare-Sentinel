# -*- coding: utf-8 -*-
"""
AShare-Sentinel 配置文件
集中管理项目的各种常量和配置参数
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# 确保目录存在
for dir_path in [DATA_DIR, LOG_DIR, CACHE_DIR]:
    dir_path.mkdir(exist_ok=True)


# 数据验证配置
class DataValidation:
    """数据验证规则"""

    # 价格范围（元）
    MIN_PRICE = 0.01
    MAX_PRICE = 1000.0

    # 涨跌幅范围（%）
    MIN_CHANGE_PCT = -20.0
    MAX_CHANGE_PCT = 20.0

    # 换手率范围（%）
    MIN_TURNOVER = 0.0
    MAX_TURNOVER = 200.0

    # 最小成交量（手）
    MIN_VOLUME = 0


# 数据获取配置
class DataFetch:
    """数据获取配置"""

    # 请求超时时间（秒）
    TIMEOUT = 30

    # 重试次数
    MAX_RETRIES = 3

    # 重试延迟（秒）
    RETRY_DELAY = 2

    # 缓存有效期（秒）
    CACHE_EXPIRE = 300  # 5分钟


# 缓存配置
class CacheConfig:
    """缓存配置"""

    # 是否启用缓存
    ENABLED = True

    # 缓存文件路径
    REALTIME_CACHE = CACHE_DIR / "realtime_cache.pkl"
    SECTOR_CACHE = CACHE_DIR / "sector_cache.pkl"
    CONCEPT_CACHE = CACHE_DIR / "concept_cache.pkl"


# 日志配置
class LogConfig:
    """日志配置"""

    # 日志级别
    LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # 日志文件路径
    FILE = LOG_DIR / "ashare_sentinel.log"

    # 日志格式
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 是否输出到控制台
    CONSOLE_OUTPUT = True

    # 日志文件最大大小（MB）
    MAX_BYTES = 10

    # 保留的日志文件数量
    BACKUP_COUNT = 5


# 数据过滤配置
class FilterConfig:
    """数据过滤配置"""

    # 是否默认过滤ST股票
    FILTER_ST = True

    # 是否默认过滤停牌股票
    FILTER_SUSPENDED = True

    # ST股票匹配模式（正则表达式需要转义*）
    ST_PATTERNS = ['ST', 'st', r'\*ST', r'\*st']

    # 最小流通市值（元）- 过滤小微盘股
    MIN_CIRC_MV = 0  # 0表示不过滤

    # 最大流通市值（元）- 过滤权重股
    MAX_CIRC_MV = 0  # 0表示不过滤


# 板块配置
class SectorConfig:
    """板块配置"""

    # 默认获取板块数量
    DEFAULT_TOP_N = 10

    # 最大板块数量
    MAX_TOP_N = 50


# 导出所有配置类
__all__ = [
    'PROJECT_ROOT',
    'DATA_DIR',
    'LOG_DIR',
    'CACHE_DIR',
    'DataValidation',
    'DataFetch',
    'CacheConfig',
    'LogConfig',
    'FilterConfig',
    'SectorConfig',
]
