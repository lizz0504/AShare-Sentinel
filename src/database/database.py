# -*- coding: utf-8 -*-
"""
AShare-Sentinel 数据库模块
使用 SQLite 存储分析结果
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / 'sentinel.db'


def init_db():
    """
    初始化数据库，创建表结构
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建分析结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL,
            change_pct REAL,
            turnover REAL,
            volume_ratio REAL DEFAULT 1.0,
            sector TEXT,
            strategy TEXT,
            ai_score INTEGER,
            ai_reason TEXT,
            ai_suggestion TEXT,
            status TEXT DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol
        ON stock_analysis(symbol)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_created_at
        ON stock_analysis(created_at DESC)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_created
        ON stock_analysis(symbol, created_at DESC)
    ''')

    # 检查并添加 status 列（用于兼容旧数据库）
    cursor.execute("PRAGMA table_info(stock_analysis)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute('ALTER TABLE stock_analysis ADD COLUMN status TEXT DEFAULT "New"')
        logger.info("数据库升级: 添加 status 列")

    conn.commit()
    conn.close()

    logger.info(f"数据库初始化完成: {DB_PATH}")


def save_analysis(data: Dict[str, Any]) -> int:
    """
    保存分析结果到数据库

    Args:
        data: 包含分析数据的字典，必须包含以下字段:
            - symbol: 股票代码
            - name: 股票名称
            - price: 价格
            - change_pct: 涨跌幅
            - turnover: 换手率
            - volume_ratio: 量比（可选，默认1.0）
            - sector: 板块（可选）
            - strategy: 策略名称（可选）
            - ai_score: AI评分
            - ai_reason: AI分析理由
            - ai_suggestion: AI建议

    Returns:
        int: 插入记录的ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO stock_analysis (
                symbol, name, price, change_pct, turnover, volume_ratio,
                sector, strategy, ai_score, ai_reason, ai_suggestion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['symbol'],
            data['name'],
            data.get('price'),
            data.get('change_pct'),
            data.get('turnover'),
            data.get('volume_ratio', 1.0),
            data.get('sector'),
            data.get('strategy'),
            data.get('ai_score'),
            data.get('ai_reason'),
            data.get('ai_suggestion')
        ))

        record_id = cursor.lastrowid
        conn.commit()

        logger.debug(f"保存分析结果: {data['symbol']} - ID: {record_id}")
        return record_id

    except Exception as e:
        conn.rollback()
        logger.error(f"保存分析结果失败: {e}")
        raise
    finally:
        conn.close()


def get_analysis_today(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取今天的分析记录

    Args:
        symbol: 股票代码，如果为None则返回所有今天的记录

    Returns:
        List[Dict]: 分析记录列表
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 获取今天的日期（SQLite格式）
        today = datetime.now().strftime('%Y-%m-%d')

        if symbol:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE symbol = ?
                AND DATE(created_at) = ?
                ORDER BY created_at DESC
            ''', (symbol, today))
        else:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE DATE(created_at) = ?
                ORDER BY created_at DESC
            ''', (today,))

        rows = cursor.fetchall()
        results = [dict(row) for row in rows]

        logger.debug(f"获取今天分析记录: {len(results)} 条")
        return results

    finally:
        conn.close()


def get_latest_analysis(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取指定股票的最新分析记录

    Args:
        symbol: 股票代码

    Returns:
        Dict: 最新的分析记录，如果不存在返回None
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM stock_analysis
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (symbol,))

        row = cursor.fetchone()

        if row:
            result = dict(row)
            logger.debug(f"获取最新分析记录: {symbol}")
            return result
        else:
            logger.debug(f"未找到分析记录: {symbol}")
            return None

    finally:
        conn.close()


def get_all_analyses(
    symbol: Optional[str] = None,
    limit: int = 100,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    获取分析记录

    Args:
        symbol: 股票代码，如果为None则返回所有股票
        limit: 最多返回的记录数
        days: 查询最近N天的记录

    Returns:
        List[Dict]: 分析记录列表
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if symbol:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE symbol = ?
                AND DATE(created_at) >= DATE('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                LIMIT ?
            ''', (symbol, days, limit))
        else:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                LIMIT ?
            ''', (days, limit))

        rows = cursor.fetchall()
        results = [dict(row) for row in rows]

        logger.debug(f"获取分析记录: {len(results)} 条")
        return results

    finally:
        conn.close()


def delete_analysis(record_id: int) -> bool:
    """
    删除指定的分析记录

    Args:
        record_id: 记录ID

    Returns:
        bool: 是否删除成功
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM stock_analysis WHERE id = ?', (record_id,))
        conn.commit()

        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"删除分析记录: ID {record_id}")
        else:
            logger.warning(f"未找到要删除的记录: ID {record_id}")

        return deleted

    except Exception as e:
        conn.rollback()
        logger.error(f"删除分析记录失败: {e}")
        raise
    finally:
        conn.close()


def get_statistics(days: int = 7) -> Dict[str, Any]:
    """
    获取数据库统计信息

    Args:
        days: 统计最近N天

    Returns:
        Dict: 统计信息
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 总记录数
        cursor.execute('''
            SELECT COUNT(*) FROM stock_analysis
            WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
        ''', (days,))
        total_count = cursor.fetchone()[0]

        # 不同股票数量
        cursor.execute('''
            SELECT COUNT(DISTINCT symbol) FROM stock_analysis
            WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
        ''', (days,))
        unique_symbols = cursor.fetchone()[0]

        # 平均评分
        cursor.execute('''
            SELECT AVG(ai_score) FROM stock_analysis
            WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
            AND ai_score IS NOT NULL
        ''', (days,))
        avg_score = cursor.fetchone()[0] or 0

        # 按建议分类统计
        cursor.execute('''
            SELECT ai_suggestion, COUNT(*) as count
            FROM stock_analysis
            WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
            GROUP BY ai_suggestion
            ORDER BY count DESC
        ''', (days,))
        suggestions = dict(cursor.fetchall())

        return {
            'total_count': total_count,
            'unique_symbols': unique_symbols,
            'avg_score': round(avg_score, 2),
            'suggestions': suggestions,
            'days': days
        }

    finally:
        conn.close()


def update_status(record_id: int, status: str) -> bool:
    """
    更新分析记录的状态

    Args:
        record_id: 记录ID
        status: 新状态 (New/Watchlist/Ignored)

    Returns:
        bool: 是否更新成功
    """
    valid_statuses = ['New', 'Watchlist', 'Ignored']
    if status not in valid_statuses:
        logger.error(f"无效的状态: {status}，有效值为: {valid_statuses}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE stock_analysis
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, record_id))
        conn.commit()

        updated = cursor.rowcount > 0
        if updated:
            logger.debug(f"更新状态: ID {record_id} -> {status}")
        else:
            logger.warning(f"未找到要更新的记录: ID {record_id}")

        return updated

    except Exception as e:
        conn.rollback()
        logger.error(f"更新状态失败: {e}")
        raise
    finally:
        conn.close()


def get_records_by_status(
    status: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    根据状态获取分析记录

    Args:
        status: 状态筛选 (New/Watchlist/Ignored/None表示全部)
        date: 日期筛选 (格式: YYYY-MM-DD，None表示今天)
        limit: 最多返回的记录数

    Returns:
        List[Dict]: 分析记录列表
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 默认查询今天
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 构建查询条件
        if status:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE status = ?
                AND DATE(created_at) = ?
                ORDER BY ai_score DESC, created_at DESC
                LIMIT ?
            ''', (status, date, limit))
        else:
            cursor.execute('''
                SELECT * FROM stock_analysis
                WHERE DATE(created_at) = ?
                ORDER BY ai_score DESC, created_at DESC
                LIMIT ?
            ''', (date, limit))

        rows = cursor.fetchall()
        results = [dict(row) for row in rows]

        logger.debug(f"根据状态获取记录: {len(results)} 条 (status={status}, date={date})")
        return results

    finally:
        conn.close()


def get_records(
    date: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取指定日期的分析记录（全部状态）

    Args:
        date: 日期筛选 (格式: YYYY-MM-DD，None表示今天)
        limit: 最多返回的记录数

    Returns:
        List[Dict]: 分析记录列表
    """
    return get_records_by_status(status=None, date=date, limit=limit)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("数据库模块测试")
    print("=" * 60)

    # 初始化数据库
    init_db()

    # 测试保存
    test_data = {
        'symbol': '300059',
        'name': '东方财富',
        'price': 28.50,
        'change_pct': 10.0,
        'turnover': 12.3,
        'volume_ratio': 2.0,
        'sector': '证券',
        'strategy': '测试策略',
        'ai_score': 85,
        'ai_reason': '测试理由',
        'ai_suggestion': '买入'
    }

    record_id = save_analysis(test_data)
    print(f"保存测试记录: ID {record_id}")

    # 测试查询
    latest = get_latest_analysis('300059')
    if latest:
        print(f"查询最新记录: {latest['name']} - 评分: {latest['ai_score']}")

    # 测试统计
    stats = get_statistics(days=7)
    print(f"统计信息: {stats}")

    print("数据库模块测试完成！")
