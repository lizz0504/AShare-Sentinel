# -*- coding: utf-8 -*-
"""
缓存管理模块
提供数据缓存功能，减少网络请求
"""

import pickle
import time
from pathlib import Path
from typing import Any, Optional, TypeVar

import pandas as pd

from ..config import CacheConfig, DataFetch, CACHE_DIR
from .logger import get_logger

T = TypeVar('T')

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: Optional[Path] = None, expire_seconds: int = 300):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录
            expire_seconds: 缓存过期时间（秒）
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.expire_seconds = expire_seconds
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logger

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.pkl"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.logger.debug(f"缓存未命中: {key}")
            return None

        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)

            # 检查是否过期
            if time.time() - cache_data['timestamp'] > self.expire_seconds:
                self.logger.info(f"缓存已过期: {key}")
                cache_path.unlink()  # 删除过期缓存
                return None

            self.logger.info(f"缓存命中: {key}")
            return cache_data['data']

        except Exception as e:
            self.logger.error(f"读取缓存失败 {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> None:
        """
        设置缓存数据

        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        cache_path = self._get_cache_path(key)

        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }

            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)

            self.logger.info(f"缓存已保存: {key}")

        except Exception as e:
            self.logger.error(f"保存缓存失败 {key}: {e}")

    def delete(self, key: str) -> None:
        """
        删除缓存

        Args:
            key: 缓存键
        """
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            self.logger.info(f"缓存已删除: {key}")

    def clear(self) -> None:
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        self.logger.info("所有缓存已清空")

    def is_enabled(self) -> bool:
        """检查缓存是否启用"""
        return CacheConfig.ENABLED


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(
            expire_seconds=DataFetch.CACHE_EXPIRE
        )
    return _cache_manager


def cached(key: str, ttl: int = 300):
    """
    缓存装饰器

    Args:
        key: 缓存键
        ttl: 缓存有效期（秒）

    Usage:
        @cached('realtime_data', ttl=300)
        def fetch_data():
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_mgr = get_cache_manager()

            if not cache_mgr.is_enabled():
                return func(*args, **kwargs)

            # 尝试从缓存获取
            cached_data = cache_mgr.get(key)
            if cached_data is not None:
                return cached_data

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_mgr.set(key, result)
            return result

        return wrapper

    return decorator


class DataFrameCache:
    """DataFrame专用缓存"""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or get_cache_manager()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """获取缓存的DataFrame"""
        data = self.cache_manager.get(key)
        if isinstance(data, pd.DataFrame):
            return data
        return None

    def set(self, key: str, df: pd.DataFrame) -> None:
        """保存DataFrame到缓存"""
        if isinstance(df, pd.DataFrame):
            self.cache_manager.set(key, df)
