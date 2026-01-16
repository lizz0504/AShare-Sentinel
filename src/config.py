# -*- coding: utf-8 -*-
"""
AShare-Sentinel 配置文件
集中管理项目的各种常量和配置参数

安全性升级 v2.0：
- 所有敏感信息从环境变量读取
- 使用 python-dotenv 加载 .env 文件
- 提供默认值确保系统可运行
"""

import os
from pathlib import Path
from typing import Optional

# 尝试加载 python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果没有安装 dotenv，直接使用系统环境变量

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# 确保目录存在
for dir_path in [DATA_DIR, LOG_DIR, CACHE_DIR]:
    dir_path.mkdir(exist_ok=True)


# =============================================================================
# 环境变量配置类
# =============================================================================

class EnvConfig:
    """
    环境变量配置

    优先级：环境变量 > .env 文件 > 默认值
    """

    # ========== 数据库配置 ==========
    @staticmethod
    def get_database_type() -> str:
        """获取数据库类型 (sqlite/postgresql)"""
        return os.getenv("DATABASE_TYPE", "sqlite").lower()

    @staticmethod
    def get_postgres_user() -> str:
        """PostgreSQL 用户名"""
        return os.getenv("POSTGRES_USER", "quant")

    @staticmethod
    def get_postgres_password() -> str:
        """PostgreSQL 密码"""
        return os.getenv("POSTGRES_PASSWORD", "password")

    @staticmethod
    def get_postgres_host() -> str:
        """PostgreSQL 主机"""
        return os.getenv("POSTGRES_HOST", "localhost")

    @staticmethod
    def get_postgres_port() -> str:
        """PostgreSQL 端口"""
        return os.getenv("POSTGRES_PORT", "5432")

    @staticmethod
    def get_postgres_database() -> str:
        """PostgreSQL 数据库名"""
        return os.getenv("POSTGRES_DB", "sentinel")

    # ========== AI API 配置 ==========
    @staticmethod
    def get_dashscope_api_key() -> Optional[str]:
        """通义千问 API Key"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            return None
        return api_key

    # ========== 邮件配置（预留） ==========
    @staticmethod
    def get_email_smtp_host() -> Optional[str]:
        """SMTP 服务器地址"""
        return os.getenv("EMAIL_SMTP_HOST")

    @staticmethod
    def get_email_smtp_port() -> int:
        """SMTP 服务器端口"""
        return int(os.getenv("EMAIL_SMTP_PORT", "587"))

    @staticmethod
    def get_email_user() -> Optional[str]:
        """邮件用户名"""
        return os.getenv("EMAIL_USER")

    @staticmethod
    def get_email_password() -> Optional[str]:
        """邮件授权码"""
        return os.getenv("EMAIL_PASSWORD")

    @staticmethod
    def get_email_from() -> Optional[str]:
        """发件人地址"""
        return os.getenv("EMAIL_FROM")

    # ========== 其他配置 ==========
    @staticmethod
    def get_log_level() -> str:
        """日志级别"""
        return os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def get_cache_enabled() -> bool:
        """是否启用缓存"""
        return os.getenv("CACHE_ENABLED", "true").lower() == "true"

    @staticmethod
    def get_api_timeout() -> int:
        """API 请求超时时间（秒）"""
        return int(os.getenv("API_TIMEOUT", "30"))


# =============================================================================
# 原有配置类（保持兼容）
# =============================================================================

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

    # 请求超时时间（秒）- 从环境变量读取
    TIMEOUT = EnvConfig.get_api_timeout()

    # 重试次数
    MAX_RETRIES = 3

    # 重试延迟（秒）
    RETRY_DELAY = 2

    # 缓存有效期（秒）
    CACHE_EXPIRE = 300  # 5分钟


# 缓存配置
class CacheConfig:
    """缓存配置"""

    # 是否启用缓存 - 从环境变量读取
    ENABLED = EnvConfig.get_cache_enabled()

    # 缓存文件路径
    REALTIME_CACHE = CACHE_DIR / "realtime_cache.pkl"
    SECTOR_CACHE = CACHE_DIR / "sector_cache.pkl"
    CONCEPT_CACHE = CACHE_DIR / "concept_cache.pkl"


# 日志配置
class LogConfig:
    """日志配置"""

    # 日志级别 - 从环境变量读取
    LEVEL = EnvConfig.get_log_level()

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


# 模拟盘交易配置
class PortfolioConfig:
    """模拟盘交易配置"""

    # 初始资金（元）
    INITIAL_CASH = 1000000  # 100万

    # 单笔买入金额（元）
    TRADE_AMOUNT_PER_POS = 50000  # 5万

    # 连榜触发阈值
    STREAK_THRESHOLD = 2  # 连续2次上榜触发买入

    # 是否启用自动交易
    AUTO_TRADE_ENABLED = True


# 导出所有配置类
__all__ = [
    'PROJECT_ROOT',
    'DATA_DIR',
    'LOG_DIR',
    'CACHE_DIR',
    'EnvConfig',
    'DataValidation',
    'DataFetch',
    'CacheConfig',
    'LogConfig',
    'FilterConfig',
    'SectorConfig',
    'PortfolioConfig',
]
