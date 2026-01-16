# -*- coding: utf-8 -*-
"""
AShare-Sentinel 统一数据库管理器
支持 SQLite 和 PostgreSQL 无缝切换
"""

import os
import sqlite3
from typing import Optional, Union, Dict, Any, List
from contextlib import contextmanager

import pandas as pd

# 尝试导入 SQLAlchemy（如果安装了 PostgreSQL）
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# 尝试导入 tenacity（用于重试机制）
try:
    from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseConfig:
    """数据库配置"""

    # SQLite 配置
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sentinel.db")

    # PostgreSQL 配置
    POSTGRES_USER = os.getenv("POSTGRES_USER", "quant")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "sentinel")

    @classmethod
    def get_database_type(cls) -> str:
        """获取当前数据库类型"""
        return os.getenv("DATABASE_TYPE", "sqlite").lower()

    @classmethod
    def get_sqlite_url(cls) -> str:
        """获取 SQLite 连接 URL"""
        return f"sqlite:///{cls.SQLITE_PATH}"

    @classmethod
    def get_postgres_url(cls) -> str:
        """获取 PostgreSQL 连接 URL"""
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    @classmethod
    def get_connection_url(cls) -> str:
        """获取当前数据库连接 URL"""
        db_type = cls.get_database_type()
        if db_type == "postgresql":
            return cls.get_postgres_url()
        else:
            return cls.get_sqlite_url()


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, database_type: str = "sqlite"):
        """
        初始化数据库管理器

        Args:
            database_type: 数据库类型 ('sqlite' 或 'postgresql')
        """
        self.database_type = database_type.lower()
        self._engine = None
        self._session_factory = None

        logger.info(f"初始化数据库管理器: {self.database_type}")

    def get_engine(self):
        """获取数据库引擎"""
        if self._engine is None:
            if self.database_type == "postgresql":
                if not SQLALCHEMY_AVAILABLE:
                    raise ImportError("SQLAlchemy 未安装，请运行: pip install sqlalchemy")
                from sqlalchemy import create_engine
                from sqlalchemy.pool import QueuePool

                self._engine = create_engine(
                    DatabaseConfig.get_postgres_url(),
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                )
            else:
                # SQLite
                from sqlalchemy import create_engine
                self._engine = create_engine(
                    DatabaseConfig.get_sqlite_url(),
                    connect_args={"check_same_thread": False}
                )

        return self._engine

    @contextmanager
    def get_session(self):
        """获取数据库会话"""
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy 未安装，请运行: pip install sqlalchemy")

        if self._session_factory is None:
            from sqlalchemy.orm import sessionmaker
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.get_engine()
            )

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话出错: {e}")
            raise
        finally:
            session.close()

    def execute(self, query: str, params: Optional[Dict] = None) -> int:
        """
        执行 SQL 语句

        Args:
            query: SQL 语句
            params: 参数

        Returns:
            影响的行数
        """
        if self.database_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH)
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()
        else:
            with self.get_engine().connect() as conn:
                result = conn.execute(text(query), params or {})
                conn.commit()
                return result.rowcount

    def fetch_all(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        查询所有数据

        Args:
            query: SQL 查询
            params: 参数

        Returns:
            查询结果列表
        """
        if self.database_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()
        else:
            with self.get_engine().connect() as conn:
                result = conn.execute(text(query), params or {})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]

    def _robust_sqlite_read(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        带重试机制的 SQLite 读取（使用 WAL 模式提升并发性能）

        Args:
            query: SQL 查询
            params: 参数

        Returns:
            DataFrame

        Raises:
            sqlite3.OperationalError: 重试 5 次后仍失败
        """
        if TENACITY_AVAILABLE:
            # 使用 tenacity 重试装饰器
            @retry(
                stop=stop_after_attempt(5),
                wait=wait_fixed(0.5),
                retry=retry_if_exception_type(sqlite3.OperationalError),
                before_sleep=before_sleep_log(logger, logger.level),
                reraise=True
            )
            def _read_with_retry():
                conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH, timeout=30.0)
                try:
                    # 启用 WAL 模式（提升并发性能）
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA busy_timeout=30000')  # 30秒超时
                    return pd.read_sql_query(query, conn, params=params)
                finally:
                    conn.close()

            return _read_with_retry()
        else:
            # 降级方案：不使用重试
            logger.warning("tenacity 未安装，SQLite 读取将无重试保护")
            conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH, timeout=30.0)
            try:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=30000')
                return pd.read_sql_query(query, conn, params=params)
            finally:
                conn.close()

    def fetch_df(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        查询并返回 DataFrame

        Args:
            query: SQL 查询
            params: 参数

        Returns:
            DataFrame
        """
        if self.database_type == "sqlite":
            # 使用带重试机制的健壮读取方法
            return self._robust_sqlite_read(query, params)
        else:
            return pd.read_sql_query(query, self.get_engine(), params=params)

    def insert_df(self, df: pd.DataFrame, table_name: str, if_exists: str = "append") -> int:
        """
        将 DataFrame 写入数据库

        Args:
            df: DataFrame
            table_name: 表名
            if_exists: 表存在时的处理方式

        Returns:
            写入的行数
        """
        if self.database_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH)
            try:
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                return len(df)
            finally:
                conn.close()
        else:
            df.to_sql(table_name, self.get_engine(), if_exists=if_exists, index=False)
            return len(df)

    def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            是否连接成功
        """
        try:
            if self.database_type == "sqlite":
                import sqlite3
                conn = sqlite3.connect(DatabaseConfig.SQLITE_PATH)
                conn.close()
                logger.info("SQLite 连接成功")
                return True
            else:
                with self.get_engine().connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("PostgreSQL 连接成功")
                return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("数据库连接已关闭")


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    获取全局数据库管理器实例

    Returns:
        DatabaseManager 实例
    """
    global _db_manager

    if _db_manager is None:
        db_type = DatabaseConfig.get_database_type()
        _db_manager = DatabaseManager(db_type)

    return _db_manager


# 便捷函数（兼容现有代码）

def get_db_engine():
    """获取数据库引擎（兼容旧代码）"""
    return get_db_manager().get_engine()


@contextmanager
def get_db_session():
    """获取数据库会话（兼容旧代码）"""
    with get_db_manager().get_session() as session:
        yield session


def read_sql_to_df(query: str, params: Optional[Dict] = None) -> pd.DataFrame:
    """读取 SQL 到 DataFrame（兼容旧代码）"""
    return get_db_manager().fetch_df(query, params)


def execute_sql(query: str, params: Optional[Dict] = None) -> int:
    """执行 SQL（兼容旧代码）"""
    return get_db_manager().execute(query, params)


def test_connection() -> bool:
    """测试数据库连接（兼容旧代码）"""
    return get_db_manager().test_connection()


if __name__ == "__main__":
    """测试数据库管理器"""
    print("=" * 60)
    print("统一数据库管理器测试")
    print("=" * 60)

    # 测试 SQLite
    print("\n[1] 测试 SQLite...")
    db = DatabaseManager("sqlite")
    if db.test_connection():
        print("✅ SQLite 连接成功")

        # 查询测试
        try:
            df = db.fetch_df("SELECT COUNT(*) as count FROM stock_analysis")
            print(f"   stock_analysis 表有 {df['count'].iloc[0]} 条记录")
        except Exception as e:
            print(f"   ℹ️  查询测试: {e}")

    # 测试切换数据库
    print("\n[2] 测试数据库切换...")
    os.environ["DATABASE_TYPE"] = "postgresql"
    print(f"   当前数据库类型: {DatabaseConfig.get_database_type()}")
    print(f"   连接 URL: {DatabaseConfig.get_connection_url()}")

    print("\n✅ 所有测试完成！")
