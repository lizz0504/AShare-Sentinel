# -*- coding: utf-8 -*-
"""
AShare-Sentinel - A股热度分析工具
数据获取模块（增强版 v2.0）

本模块负责从 AkShare 获取实时行情数据
集成缓存、日志、验证等功能

稳定性升级 v2.0：
- 使用 tenacity 库实现专业级重试机制
- 仅在网络异常或超时时重试
- 记录 Warning 级别的重试日志
"""

import akshare as ak
import pandas as pd
import time
from pathlib import Path
from typing import Optional, Tuple
import warnings

# 尝试导入 tenacity，如果没有安装则使用简单重试
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_fixed,
        retry_if_exception_type,
        before_sleep_log
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

import logging

warnings.filterwarnings('ignore')

from ..config import DataFetch, FilterConfig, SectorConfig
from ..utils.logger import get_logger
from ..utils.cache import get_cache_manager, DataFrameCache
from ..utils.validator import DataValidator

logger = get_logger(__name__)


# =============================================================================
# 重试装饰器配置
# =============================================================================

if TENACITY_AVAILABLE:
    # 使用 tenacity 的专业重试装饰器
    # 仅在网络异常（RequestException）或超时时重试
    @retry(
        stop=stop_after_attempt(3),  # 最大重试 3 次
        wait=wait_fixed(2),  # 固定等待 2 秒
        retry=retry_if_exception_type(Exception),  # 任何异常都重试（包括网络超时）
        before_sleep=before_sleep_log(logger, logging.WARNING),  # 重试前记录 WARNING 日志
        reraise=True  # 重试失败后重新抛出异常
    )
    def _fetch_with_retry(func):
        """
        带重试的数据获取函数（使用 tenacity）

        Args:
            func: 要执行的获取函数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试3次后仍失败，抛出原始异常
        """
        return func()
else:
    # 降级方案：使用简单的重试逻辑
    def _fetch_with_retry(func, max_retries: int = 3, delay: int = 2):
        """
        带重试的数据获取函数（降级方案）

        Args:
            func: 要执行的获取函数
            max_retries: 最大重试次数
            delay: 重试延迟（秒）

        Returns:
            函数执行结果或None

        Raises:
            Exception: 重试失败后抛出最后一次异常
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"获取数据失败，{delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"获取数据失败，已达最大重试次数: {e}")

        # 重新抛出最后一次异常
        if last_error:
            raise last_error

        return None


def fetch_realtime_data(
    filter_st: bool = True,
    use_cache: bool = True,
    validate: bool = True
) -> Tuple[pd.DataFrame, str]:
    """
    获取A股实时行情数据（增强版）
    非交易时间自动使用当日收盘价数据

    Args:
        filter_st: 是否过滤ST股票，默认为True
        use_cache: 是否使用缓存，默认为True
        validate: 是否验证数据，默认为True

    Returns:
        Tuple[pd.DataFrame, str]: (清洗后的实时行情数据, 更新时间字符串)
        DataFrame包含以下字段:
            - symbol: 股票代码
            - name: 股票名称
            - price: 最新价/收盘价
            - change_pct: 涨跌幅(%)
            - volume: 成交量(手)
            - amount: 成交额(元)
            - turnover: 换手率(%)
            - circ_mv: 流通市值(元)
            - total_mv: 总市值(元)
            - high: 最高价
            - low: 最低价
            - open: 今开价
            - close: 昨收价
        更新时间字符串格式: "YYYY-MM-DD HH:MM:SS"
    """
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    current_weekday = now.weekday()

    # 判断是否为交易时间（工作日9:00-15:00）
    is_trading_time = (current_weekday < 5) and (9 <= current_hour < 15)

    cache_key = "realtime_data"

    # 尝试从缓存获取
    if use_cache:
        cache_mgr = DataFrameCache()

        # 非交易时间使用更长缓存（24小时）
        if not is_trading_time:
            # 检查是否有任何缓存（无论是否过期）
            cache_path = Path(__file__).parent.parent / 'cache' / f"{cache_key}.pkl"
            if cache_path.exists():
                import pickle
                import time
                try:
                    with open(cache_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    # 非交易时间，缓存24小时有效
                    if time.time() - cache_data['timestamp'] < 86400:  # 24小时
                        logger.info(f"非交易时间，使用缓存数据: {len(cache_data['data'])} 只股票")
                        from datetime import datetime
                        update_time = datetime.fromtimestamp(cache_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        return cache_data['data'], update_time
                except Exception:
                    pass

        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None and not cached_data.empty:
            logger.info(f"从缓存获取实时数据: {len(cached_data)} 只股票")
            update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return cached_data, update_time
        elif cached_data is not None and cached_data.empty:
            logger.warning("缓存数据为空，将重新获取")
        # 如果cached_data是其他类型（如旧格式的元组），跳过缓存
        elif cached_data is not None:
            logger.warning(f"缓存数据格式异常: {type(cached_data)}，将重新获取")

    logger.info("正在获取A股实时行情数据...")

    # 定义获取函数
    def _fetch():
        return ak.stock_zh_a_spot_em()

    # 带重试的获取
    try:
        df = _fetch_with_retry(_fetch)
    except Exception as e:
        logger.error(f"获取实时行情数据失败（已重试3次）: {e}")
        return pd.DataFrame(), ""

    if df is None or df.empty:
        logger.error("获取实时行情数据失败")
        return pd.DataFrame(), ""

    logger.info(f"成功获取 {len(df)} 只股票的原始数据")

    # 字段名映射（中文 -> 英文）
    column_mapping = {
        '代码': 'symbol',
        '名称': 'name',
        '最新价': 'price',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amount',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude',
        '最高': 'high',
        '最低': 'low',
        '今开': 'open',
        '昨收': 'close',
        '换手率': 'turnover',
        '量比': 'volume_ratio',
        '市盈率-动态': 'pe_ttm',
        '市净率': 'pb',
        '总市值': 'total_mv',
        '流通市值': 'circ_mv'
    }

    # 重命名列
    df = df.rename(columns=column_mapping)

    # 数据清洗
    # 1. 判断是否为交易时间，如果不是则保留成交量为0的股票（使用收盘价）
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    current_weekday = now.weekday()

    # 周末全天非交易，工作日9:00-15:00为交易时间
    is_trading_time = (current_weekday < 5) and (9 <= current_hour < 15)

    if is_trading_time:
        # 交易时间：剔除成交量为0的股票（停牌或无交易）
        before_count = len(df)
        df = df[df['volume'] > 0]
        logger.info(f"剔除停牌股票: {before_count - len(df)} 只")
    else:
        # 非交易时间：保留成交量为0但有价格的股票（使用收盘价）
        before_count = len(df)
        df = df[df['price'] > 0]  # 只要有价格就保留
        logger.info(f"非交易时间，使用收盘价数据。保留有价格股票: {len(df)} 只（原{before_count}只）")

    # 2. 可选：过滤ST股票
    if filter_st:
        before_count = len(df)
        st_pattern = '|'.join(FilterConfig.ST_PATTERNS)
        df = df[~df['name'].str.contains(st_pattern, na=False)]
        logger.info(f"剔除ST股票: {before_count - len(df)} 只")

    # 3. 确保关键字段不为空
    before_count = len(df)
    df = df.dropna(subset=['price', 'change_pct'])
    logger.info(f"剔除关键字段为空的股票: {before_count - len(df)} 只")

    # 4. 数据类型转换
    numeric_columns = ['price', 'change_pct', 'volume', 'amount',
                      'turnover', 'volume_ratio', 'circ_mv', 'total_mv',
                      'high', 'low', 'open', 'close', 'amplitude', 'pe_ttm', 'pb']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 5. 数据验证
    if validate:
        validator = DataValidator()
        df = validator.clean_dataframe(df)

    # 6. 按涨跌幅排序（方便后续分析）
    df = df.sort_values('change_pct', ascending=False).reset_index(drop=True)

    logger.info(f"数据清洗完成，最终有效股票: {len(df)} 只")

    # 保存到缓存
    if use_cache:
        cache_mgr.set(cache_key, df)

    # 返回数据和时间戳
    update_time = now.strftime('%Y-%m-%d %H:%M:%S')
    return df, update_time


def fetch_sector_data(top_n: int = 10, use_cache: bool = True) -> pd.DataFrame:
    """
    获取行业板块涨跌数据（增强版）

    Args:
        top_n: 返回涨幅前N名的板块，默认为10
        use_cache: 是否使用缓存，默认为True

    Returns:
        pd.DataFrame: 行业板块数据，包含以下字段:
            - name: 板块名称
            - change_pct: 涨跌幅(%)
            - leading_stock: 领涨股票
            - stock_count: 板块内股票数量
    """
    cache_key = f"sector_data_{top_n}"

    # 尝试从缓存获取
    if use_cache:
        cache_mgr = DataFrameCache()
        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None:
            logger.info(f"从缓存获取板块数据: {len(cached_data)} 个板块")
            return cached_data

    logger.info("正在获取行业板块数据...")

    def _fetch():
        return ak.stock_board_industry_name_em()

    try:
        df = _fetch_with_retry(_fetch)
    except Exception as e:
        logger.error(f"获取板块数据失败（已重试3次）: {e}")
        return pd.DataFrame()

    if df is None or df.empty:
        logger.error("获取板块数据失败")
        return pd.DataFrame()

    # 字段名映射
    column_mapping = {
        '板块名称': 'name',
        '最新价': 'index_value',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amount',
        '成交量': 'volume',
        '成交额': 'amount',
        '换手率': 'turnover',
        '领涨股票': 'leading_stock',
        '代码': 'leading_code',
        '当前涨跌幅': 'leading_change_pct',
        '跌停': 'limit_down_count',
        '涨停': 'limit_up_count',
        '上涨': 'up_count',
        '下跌': 'down_count',
        '平盘': 'flat_count',
        '公司家数': 'stock_count'
    }

    df = df.rename(columns=column_mapping)

    # 数据类型转换
    numeric_columns = ['change_pct', 'index_value', 'volume', 'amount', 'turnover']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 按涨跌幅排序，取前N名
    df = df.sort_values('change_pct', ascending=False).head(top_n).reset_index(drop=True)

    logger.info(f"成功获取前 {top_n} 个领涨板块")

    # 保存到缓存
    if use_cache:
        cache_mgr.set(cache_key, df)

    return df


def fetch_concept_data(top_n: int = 10, use_cache: bool = True) -> pd.DataFrame:
    """
    获取概念板块涨跌数据（增强版）

    Args:
        top_n: 返回涨幅前N名的概念板块，默认为10
        use_cache: 是否使用缓存，默认为True

    Returns:
        pd.DataFrame: 概念板块数据
    """
    cache_key = f"concept_data_{top_n}"

    # 尝试从缓存获取
    if use_cache:
        cache_mgr = DataFrameCache()
        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None:
            logger.info(f"从缓存获取概念板块数据: {len(cached_data)} 个板块")
            return cached_data

    logger.info("正在获取概念板块数据...")

    def _fetch():
        return ak.stock_board_concept_name_em()

    try:
        df = _fetch_with_retry(_fetch)
    except Exception as e:
        logger.error(f"获取概念板块数据失败（已重试3次）: {e}")
        return pd.DataFrame()

    if df is None or df.empty:
        logger.error("获取概念板块数据失败")
        return pd.DataFrame()

    # 字段名映射
    column_mapping = {
        '板块名称': 'name',
        '最新价': 'index_value',
        '涨跌幅': 'change_pct',
        '领涨股票': 'leading_stock',
        '代码': 'leading_code',
        '当前涨跌幅': 'leading_change_pct',
        '公司家数': 'stock_count'
    }

    df = df.rename(columns=column_mapping)

    # 数据类型转换
    if 'change_pct' in df.columns:
        df['change_pct'] = pd.to_numeric(df['change_pct'], errors='coerce')

    df = df.sort_values('change_pct', ascending=False).head(top_n).reset_index(drop=True)

    logger.info(f"成功获取前 {top_n} 个领涨概念板块")

    # 保存到缓存
    if use_cache:
        cache_mgr.set(cache_key, df)

    return df


def get_hot_stocks_by_sector(
    sector_name: str,
    top_n: int = 5,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    获取指定板块的热门股票（增强版）

    Args:
        sector_name: 板块名称
        top_n: 返回前N只股票
        use_cache: 是否使用缓存，默认为True

    Returns:
        pd.DataFrame: 板块内热门股票数据
    """
    cache_key = f"sector_stocks_{sector_name}_{top_n}"

    # 尝试从缓存获取
    if use_cache:
        cache_mgr = DataFrameCache()
        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None:
            logger.info(f"从缓存获取 {sector_name} 板块股票: {len(cached_data)} 只")
            return cached_data

    logger.info(f"正在获取 {sector_name} 板块的热门股票...")

    def _fetch():
        return ak.stock_board_industry_cons_em(symbol=sector_name)

    try:
        df = _fetch_with_retry(_fetch)
    except Exception as e:
        logger.error(f"获取 {sector_name} 板块股票失败（已重试3次）: {e}")
        return pd.DataFrame()

    if df is None or df.empty:
        logger.error(f"获取 {sector_name} 板块股票失败")
        return pd.DataFrame()

    # 字段名映射
    column_mapping = {
        '代码': 'symbol',
        '名称': 'name',
        '最新价': 'price',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amount',
        '成交量': 'volume',
        '成交额': 'amount',
        '换手率': 'turnover',
        '市盈率-动态': 'pe_ttm',
        '市净率': 'pb'
    }

    df = df.rename(columns=column_mapping)

    # 数据类型转换
    numeric_columns = ['price', 'change_pct', 'volume', 'amount', 'turnover']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.sort_values('change_pct', ascending=False).head(top_n).reset_index(drop=True)

    logger.info(f"成功获取 {sector_name} 板块前 {top_n} 只热门股票")

    # 保存到缓存
    if use_cache:
        cache_mgr.set(cache_key, df)

    return df


def print_market_summary(realtime_df: pd.DataFrame, sector_df: pd.DataFrame) -> None:
    """
    打印市场概况摘要

    Args:
        realtime_df: 实时行情数据
        sector_df: 板块数据
    """
    print("\n" + "="*60)
    print("A股市场概况")
    print("="*60)

    if not realtime_df.empty:
        up_count = len(realtime_df[realtime_df['change_pct'] > 0])
        down_count = len(realtime_df[realtime_df['change_pct'] < 0])
        limit_up_count = len(realtime_df[realtime_df['change_pct'] >= 9.9])
        limit_down_count = len(realtime_df[realtime_df['change_pct'] <= -9.9])

        print(f"\n市场统计:")
        print(f"  交易股票总数: {len(realtime_df)}")
        print(f"  上涨: {up_count} ({up_count/len(realtime_df)*100:.1f}%)")
        print(f"  下跌: {down_count} ({down_count/len(realtime_df)*100:.1f}%)")
        print(f"  涨停: {limit_up_count}")
        print(f"  跌停: {limit_down_count}")

        print(f"\n涨停榜 TOP 5:")
        top_stocks = realtime_df.nlargest(5, 'change_pct')[['symbol', 'name', 'price', 'change_pct', 'turnover']]
        for idx, row in top_stocks.iterrows():
            print(f"  {row['symbol']} {row['name']:8s} | "
                  f"价格: {row['price']:7.2f} | "
                  f"涨幅: {row['change_pct']:6.2f}% | "
                  f"换手: {row['turnover']:5.2f}%")

    if not sector_df.empty:
        print(f"\n领涨板块 TOP 5:")
        for idx, row in sector_df.head(5).iterrows():
            print(f"  {row['name']:12s} | 涨幅: {row['change_pct']:6.2f}%")

    print("="*60 + "\n")


def clear_cache() -> None:
    """清空所有缓存"""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    logger.info("所有缓存已清空")


def get_stock_sector(symbol: str) -> str:
    """
    获取单只股票的所属板块/行业

    Args:
        symbol: 股票代码（如 "300059" 或 "000001"）

    Returns:
        str: 板块/行业名称，失败返回 "未知"
    """
    try:
        # 使用 AkShare 获取个股信息
        info_df = ak.stock_individual_info_em(symbol=symbol)

        if info_df is None or info_df.empty:
            logger.warning(f"获取股票 {symbol} 信息失败: 无数据")
            return "未知"

        # 转换为字典方便查找
        info_dict = dict(zip(info_df['item'], info_df['value']))

        # 尝试获取行业字段
        sector = info_dict.get('行业') or info_dict.get('板块') or info_dict.get('所属行业') or info_dict.get('所属板块')

        if sector and sector != '-':
            return str(sector).strip()

        return "未知"

    except Exception as e:
        logger.warning(f"获取股票 {symbol} 板块信息失败: {e}")
        return "未知"


def calculate_technical_indicators(symbol: str, current_price: float, current_volume: float) -> dict:
    """
    计算技术指标（均线、量能等）

    Args:
        symbol: 股票代码
        current_price: 当前价格
        current_volume: 当前成交量（手）

    Returns:
        dict: 技术指标字典，包含 MA5, MA10, MA20, MA60, 量比等
    """
    try:
        # 获取历史数据（最近 60 个交易日）
        hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101", adjust="qfq")

        if hist_df is None or len(hist_df) < 20:
            # 数据不足，返回默认值
            return {
                'ma5': None,
                'ma10': None,
                'ma20': None,
                'ma60': None,
                'ma5_volume': None,
                'volume_ratio': None,
                'is_above_ma5': False,
                'is_above_ma20': False,
                'is_above_ma60': False,
                'trend_status': '未知',
                'volume_status': '未知'
            }

        # 计算价格均线
        hist_df['MA5'] = hist_df['收盘'].rolling(window=5).mean()
        hist_df['MA10'] = hist_df['收盘'].rolling(window=10).mean()
        hist_df['MA20'] = hist_df['收盘'].rolling(window=20).mean()
        hist_df['MA60'] = hist_df['收盘'].rolling(window=60).mean()

        # 计算量能均线
        hist_df['MA5_Volume'] = hist_df['成交量'].rolling(window=5).mean()

        # 获取最新的均线值
        latest = hist_df.iloc[-1]
        ma5 = latest['MA5'] if not pd.isna(latest['MA5']) else None
        ma10 = latest['MA10'] if not pd.isna(latest['MA10']) else None
        ma20 = latest['MA20'] if not pd.isna(latest['MA20']) else None
        ma60 = latest['MA60'] if not pd.isna(latest['MA60']) else None
        ma5_volume = latest['MA5_Volume'] if not pd.isna(latest['MA5_Volume']) else None

        # 计算量比
        if ma5_volume and ma5_volume > 0:
            volume_ratio = current_volume / ma5_volume
        else:
            volume_ratio = None

        # 判断趋势状态
        is_above_ma5 = ma5 and current_price > ma5
        is_above_ma20 = ma20 and current_price > ma20
        is_above_ma60 = ma60 and current_price > ma60

        # 趋势判断
        if is_above_ma5 and is_above_ma20 and is_above_ma60:
            trend_status = "多头排列"
        elif is_above_ma5 and is_above_ma20:
            trend_status = "中期上涨"
        elif is_above_ma5:
            trend_status = "短期强势"
        else:
            trend_status = "弱势调整"

        # 量能状态
        if volume_ratio:
            if volume_ratio >= 2.0:
                volume_status = "放量"
            elif volume_ratio >= 1.2:
                volume_status = "温和放量"
            elif volume_ratio < 0.8:
                volume_status = "缩量"
            else:
                volume_status = "正常"
        else:
            volume_status = "未知"

        return {
            'ma5': round(ma5, 2) if ma5 else None,
            'ma10': round(ma10, 2) if ma10 else None,
            'ma20': round(ma20, 2) if ma20 else None,
            'ma60': round(ma60, 2) if ma60 else None,
            'ma5_volume': int(ma5_volume) if ma5_volume else None,
            'volume_ratio': round(volume_ratio, 2) if volume_ratio else None,
            'is_above_ma5': is_above_ma5,
            'is_above_ma20': is_above_ma20,
            'is_above_ma60': is_above_ma60,
            'trend_status': trend_status,
            'volume_status': volume_status
        }

    except Exception as e:
        logger.warning(f"计算 {symbol} 技术指标失败: {e}")
        return {
            'ma5': None,
            'ma10': None,
            'ma20': None,
            'ma60': None,
            'ma5_volume': None,
            'volume_ratio': None,
            'is_above_ma5': False,
            'is_above_ma20': False,
            'is_above_ma60': False,
            'trend_status': '未知',
            'volume_status': '未知'
        }


def generate_position_desc(current_price: float, indicators: dict) -> str:
    """
    生成价格相对位置的描述

    Args:
        current_price: 当前价格
        indicators: 技术指标字典

    Returns:
        str: 位置描述
    """
    ma5 = indicators.get('ma5')
    ma20 = indicators.get('ma20')
    ma60 = indicators.get('ma60')

    desc_parts = []

    if ma5:
        if current_price > ma5:
            desc_parts.append(f"站在5日线({ma5:.2f})之上")
        else:
            desc_parts.append(f"跌破5日线({ma5:.2f})")

    if ma20:
        if current_price > ma20:
            desc_parts.append("在中期均线上方")
        else:
            desc_parts.append("受20日线压制")

    if ma60:
        if current_price > ma60:
            desc_parts.append("长期趋势向上")
        else:
            desc_parts.append("处于长期下降趋势")

    return "；".join(desc_parts) if desc_parts else "位置未明"


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("AShare-Sentinel 数据获取模块测试（增强版 v2.0）")
    print("="*60)

    if not TENACITY_AVAILABLE:
        print("\n[提示] tenacity 库未安装，使用简单重试机制")
        print("安装命令: pip install tenacity\n")

    # 1. 获取实时行情数据
    realtime_data, update_time = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if not realtime_data.empty:
        print(f"\n更新时间: {update_time}")
        print("\n实时行情数据预览 (前5行):")
        print("-"*60)
        display_columns = ['symbol', 'name', 'price', 'change_pct', 'volume',
                          'turnover', 'circ_mv']
        print(realtime_data[display_columns].head())
    else:
        print("未获取到实时行情数据")

    # 2. 获取行业板块数据
    sector_data = fetch_sector_data(top_n=10)

    if not sector_data.empty:
        print("\n行业板块数据预览 (前5行):")
        print("-"*60)
        print(sector_data.head())
    else:
        print("未获取到板块数据")

    # 3. 打印市场概况
    print_market_summary(realtime_data, sector_data)

    # 4. 获取概念板块数据
    concept_data = fetch_concept_data(top_n=5)
    if not concept_data.empty:
        print("\n领涨概念板块 TOP 5:")
        print("-"*60)
        for idx, row in concept_data.head(5).iterrows():
            print(f"  {row['name']:15s} | 涨幅: {row['change_pct']:6.2f}%")

    print("\n测试完成！")
    print(f"日志文件位置: logs/ashare_sentinel.log")
