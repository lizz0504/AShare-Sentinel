"""
短线策略筛选模块
用于从行情数据中筛选短线机会
"""

import sys
from pathlib import Path
# 将项目根目录添加到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyScanner:
    """
    策略扫描器
    从全量股票数据中筛选短线机会
    """

    # 单位转换常量
    UNIT_YI = 100_000_000  # 1亿

    # 策略A: 放量突破参数
    VOL_BREAKOUT_MIN_CHANGE = 5.0
    VOL_BREAKOUT_MAX_CHANGE = 8.0
    VOL_BREAKOUT_MIN_TURNOVER = 7.0
    VOL_BREAKOUT_MAX_TURNOVER = 15.0
    VOL_BREAKOUT_MIN_MV = 10 * UNIT_YI
    VOL_BREAKOUT_MAX_MV = 200 * UNIT_YI
    VOL_BREAKOUT_MIN_PRICE = 5.0
    VOL_BREAKOUT_MAX_PRICE = 1000.0

    # 策略B: 准涨停参数
    LIMIT_CANDIDATE_MIN_CHANGE = 8.0
    LIMIT_CANDIDATE_MAX_CHANGE = 20.0
    LIMIT_CANDIDATE_MIN_TURNOVER = 8.0

    # 策略C: 低位潜伏参数
    TURTLE_MIN_CHANGE = 2.0
    TURTLE_MAX_CHANGE = 5.0
    TURTLE_MIN_TURNOVER = 6.0

    # 统一输出列（AI 分析需要）
    OUTPUT_COLUMNS = ['symbol', 'name', 'price', 'change_pct', 'turnover', 'volume_ratio']

    def __init__(self, df: pd.DataFrame):
        """
        初始化策略扫描器

        Args:
            df: 包含股票数据的DataFrame
        """
        self.df = df.copy() if df is not None else pd.DataFrame()

        # 确保 volume_ratio 列存在
        if not self.df.empty and 'volume_ratio' not in self.df.columns:
            self.df['volume_ratio'] = 1.0

        # 填充 volume_ratio 空值为 1.0，并确保为 float 类型
        if not self.df.empty:
            self.df['volume_ratio'] = self.df['volume_ratio'].fillna(1.0).astype(float)

        if self.df.empty:
            logger.warning("输入的DataFrame为空，策略扫描将返回空结果")
        else:
            logger.info(f"策略扫描器初始化完成，数据量: {len(self.df)}")

    def _validate_columns(self) -> bool:
        """
        验证DataFrame是否包含必要的列

        Returns:
            bool: 是否包含必要列
        """
        required_columns = ['symbol', 'name', 'price', 'change_pct', 'turnover', 'volume_ratio']

        if self.df.empty:
            return False

        missing_columns = [col for col in required_columns if col not in self.df.columns]

        if missing_columns:
            logger.error(f"DataFrame缺少必要列: {missing_columns}")
            return False

        return True

    def _standardize_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化输出：只保留指定列，确保数据类型正确

        Args:
            df: 待处理的DataFrame

        Returns:
            标准化后的DataFrame
        """
        if df.empty:
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

        # 确保所有输出列都存在
        for col in self.OUTPUT_COLUMNS:
            if col not in df.columns:
                if col == 'volume_ratio':
                    df[col] = 1.0
                else:
                    df[col] = None

        # 只保留指定列，按固定顺序
        result = df[self.OUTPUT_COLUMNS].copy()

        # 确保 volume_ratio 为 float 类型
        result['volume_ratio'] = result['volume_ratio'].fillna(1.0).astype(float)

        return result

    def scan_volume_breakout(self, limit: int = 10) -> pd.DataFrame:
        """
        策略A: 强势中军/主升浪

        逻辑: 寻找正在拉升且人气聚集的股票，适合潜伏或追涨

        筛选条件:
        1. 涨幅: 5% <= x <= 8% (去掉3-5%的杂毛，只看强势股)
        2. 换手率: 7% <= x <= 15% (提高换手门槛，确保资金关注度极高)
        3. 流通市值: 10亿 <= x <= 200亿 (中小盘股)
        4. 价格: 5元 <= x <= 2000元

        排序: 严格按换手率降序（谁资金博弈最激烈，谁排第一）

        Args:
            limit: 返回前N条结果，默认10

        Returns:
            符合条件的股票DataFrame (统一输出格式)
        """
        logger.info("=" * 50)
        logger.info("执行策略A: 强势中军/主升浪")

        if not self._validate_columns():
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

        try:
            # 市值阈值
            min_mv = 10 * 10**8
            max_mv = 200 * 10**8

            # 构建筛选条件
            mask = (
                (self.df['change_pct'] >= 5.0) &
                (self.df['change_pct'] <= 8.0) &
                (self.df['turnover'] >= 7.0) &
                (self.df['turnover'] <= 15.0) &
                (self.df['circ_mv'] >= min_mv) &
                (self.df['circ_mv'] <= max_mv) &
                (self.df['price'] >= 5.0) &
                (self.df['price'] <= 2000.0)
            )

            result = self.df[mask].copy()

            # 标准化输出
            result = self._standardize_output(result)

            # 严格按换手率降序排列
            result = result.sort_values('turnover', ascending=False).reset_index(drop=True)

            # 限制返回数量
            if len(result) > limit:
                result = result.head(limit).copy()
                logger.info(f"策略A筛选完成，找到 {len(result)} 只股票（限制前{limit}条）")
            else:
                logger.info(f"策略A筛选完成，找到 {len(result)} 只股票")

            logger.info(f"  涨幅范围: 5.0% - 8.0%")
            logger.info(f"  换手率范围: 7.0% - 15.0%")
            logger.info(f"  市值范围: 10亿 - 200亿")
            logger.info(f"  价格范围: 5.0元 - 2000.0元")
            logger.info(f"  排序: 按换手率降序")

            return result

        except Exception as e:
            logger.error(f"策略A执行出错: {e}")
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

    def scan_limit_candidates(self, limit: int = 10) -> pd.DataFrame:
        """
        策略B: 冲击涨停/20cm博弈

        逻辑: 寻找即将封板的股票（兼容创业板/科创板20cm涨停）

        筛选条件:
        1. 涨幅: 8% <= x <= 20% (兼容20cm涨停)
        2. 换手率: > 8% (必须有充分换手)

        排序: 严格按涨幅降序（谁离涨停最近，谁排第一）

        Args:
            limit: 返回前N条结果，默认10

        Returns:
            符合条件的股票DataFrame (统一输出格式)
        """
        logger.info("=" * 50)
        logger.info("执行策略B: 冲击涨停/20cm博弈")

        if not self._validate_columns():
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

        try:
            # 构建筛选条件
            mask = (
                (self.df['change_pct'] >= 8.0) &
                (self.df['change_pct'] <= 20.0) &
                (self.df['turnover'] > 8.0)
            )

            result = self.df[mask].copy()

            # 标准化输出
            result = self._standardize_output(result)

            # 严格按涨幅降序排列
            result = result.sort_values('change_pct', ascending=False).reset_index(drop=True)

            # 限制返回数量
            if len(result) > limit:
                result = result.head(limit).copy()
                logger.info(f"策略B筛选完成，找到 {len(result)} 只股票（限制前{limit}条）")
            else:
                logger.info(f"策略B筛选完成，找到 {len(result)} 只股票")

            logger.info(f"  涨幅范围: 8.0% - 20.0%")
            logger.info(f"  换手率: > 8.0%")
            logger.info(f"  排序: 按涨幅降序")

            return result

        except Exception as e:
            logger.error(f"策略B执行出错: {e}")
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

    def scan_turtle_stocks(self, limit: int = 10) -> pd.DataFrame:
        """
        策略C: 温和放量/趋势股

        逻辑: 涨幅较小但有成交量的股票（可能在吸筹）

        筛选条件:
        1. 涨幅: 2% <= x <= 5%
        2. 换手率: > 6% (温和上涨但换手不低，说明有主力吸筹)

        排序: 严格按换手率降序（谁资金运作活跃，谁排第一）

        Args:
            limit: 返回前N条结果，默认10

        Returns:
            符合条件的股票DataFrame (统一输出格式)
        """
        logger.info("=" * 50)
        logger.info("执行策略C: 温和放量/趋势股")

        if not self._validate_columns():
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

        try:
            # 构建筛选条件
            mask = (
                (self.df['change_pct'] >= 2.0) &
                (self.df['change_pct'] <= 5.0) &
                (self.df['turnover'] > 6.0)
            )

            result = self.df[mask].copy()

            # 标准化输出
            result = self._standardize_output(result)

            # 严格按换手率降序排列
            result = result.sort_values('turnover', ascending=False).reset_index(drop=True)

            # 限制返回数量
            if len(result) > limit:
                result = result.head(limit).copy()
                logger.info(f"策略C筛选完成，找到 {len(result)} 只股票（限制前{limit}条）")
            else:
                logger.info(f"策略C筛选完成，找到 {len(result)} 只股票")

            logger.info(f"  涨幅范围: 2.0% - 5.0%")
            logger.info(f"  换手率: > 6.0%")
            logger.info(f"  排序: 按换手率降序")

            return result

        except Exception as e:
            logger.error(f"策略C执行出错: {e}")
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

    def format_output(self, df: pd.DataFrame, top_n: Optional[int] = None) -> str:
        """
        格式化输出策略结果（统一6列格式）

        Args:
            df: 策略筛选结果
            top_n: 只显示前N只，None表示全部显示

        Returns:
            格式化的字符串
        """
        if df.empty:
            return "暂无符合条件的股票\n"

        # 限制显示数量
        if top_n is not None:
            display_df = df.head(top_n).copy()
        else:
            display_df = df.copy()

        # 构建输出字符串（6列格式）
        lines = []
        lines.append(f"{'代码':<10}{'名称':<12}{'价格':<10}{'涨幅%':<10}{'换手%':<10}{'量比':<10}")
        lines.append("-" * 62)

        for _, row in display_df.iterrows():
            lines.append(
                f"{row['symbol']:<10}"
                f"{row['name']:<12}"
                f"{row['price']:<10.2f}"
                f"{row['change_pct']:<10.2f}"
                f"{row['turnover']:<10.2f}"
                f"{row['volume_ratio']:<10.2f}"
            )

        return "\n".join(lines)


def format_strategy_header(strategy_name: str, description: str) -> str:
    """
    格式化策略标题

    Args:
        strategy_name: 策略名称
        description: 策略描述

    Returns:
        格式化的标题字符串
    """
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append(f"  {strategy_name}")
    lines.append(f"  {description}")
    lines.append("=" * 70)
    return "\n".join(lines)


if __name__ == "__main__":
    from src.data.data_loader import fetch_realtime_data

    print("=" * 70)
    print(" " * 20 + "短线策略扫描器测试")
    print("=" * 70)
    print("\n正在获取A股实时数据...")

    df, _ = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if df.empty:
        print("错误: 未能获取到有效数据")
    else:
        print(f"成功获取 {len(df)} 只股票数据\n")

        scanner = StrategyScanner(df)

        # 策略A: 放量突破
        print(format_strategy_header(
            "策略A: 强势中军",
            "寻找正在拉升且人气聚集的股票 (涨幅5-8%, 换手7-15%, 市值10-200亿)"
        ))
        result_a = scanner.scan_volume_breakout()
        print(scanner.format_output(result_a, top_n=10))
        print(f"总计: {len(result_a)} 只股票\n")

        # 策略B: 准涨停
        print(format_strategy_header(
            "策略B: 冲击涨停",
            "寻找即将封板的股票 (涨幅8-20%, 换手>8%)"
        ))
        result_b = scanner.scan_limit_candidates()
        print(scanner.format_output(result_b, top_n=10))
        print(f"总计: {len(result_b)} 只股票\n")

        # 策略C: 低位潜伏
        print(format_strategy_header(
            "策略C: 低位潜伏",
            "寻找涨幅小但换手高的吸筹股 (涨幅2-5%, 换手>6%)"
        ))
        result_c = scanner.scan_turtle_stocks()
        print(scanner.format_output(result_c, top_n=10))
        print(f"总计: {len(result_c)} 只股票\n")

        # 汇总统计
        print("=" * 70)
        print("策略扫描汇总")
        print("=" * 70)
        print(f"  总股票数: {len(df)}")
        print(f"  策略A (强势中军): {len(result_a)} 只")
        print(f"  策略B (冲击涨停): {len(result_b)} 只")
        print(f"  策略C (低位潜伏): {len(result_c)} 只")
        print(f"  合计机会: {len(result_a) + len(result_b) + len(result_c)} 只")
        print("=" * 70)
