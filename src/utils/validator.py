# -*- coding: utf-8 -*-
"""
数据验证模块
提供数据有效性检查功能
"""

import pandas as pd
from typing import List, Optional, Tuple

from ..config import DataValidation
from .logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """数据验证器"""

    def __init__(self, validation_config=None):
        """
        初始化数据验证器

        Args:
            validation_config: 验证配置，默认使用DataValidation
        """
        self.config = validation_config or DataValidation
        self.logger = logger

    def validate_price(self, price: float) -> bool:
        """
        验证价格是否在合理范围内

        Args:
            price: 股票价格

        Returns:
            bool: 价格是否有效
        """
        if pd.isna(price):
            return False
        return self.config.MIN_PRICE <= price <= self.config.MAX_PRICE

    def validate_change_pct(self, change_pct: float) -> bool:
        """
        验证涨跌幅是否在合理范围内

        Args:
            change_pct: 涨跌幅百分比

        Returns:
            bool: 涨跌幅是否有效
        """
        if pd.isna(change_pct):
            return False
        return self.config.MIN_CHANGE_PCT <= change_pct <= self.config.MAX_CHANGE_PCT

    def validate_turnover(self, turnover: float) -> bool:
        """
        验证换手率是否在合理范围内

        Args:
            turnover: 换手率百分比

        Returns:
            bool: 换手率是否有效
        """
        if pd.isna(turnover):
            return True  # 换手率可以为空
        return self.config.MIN_TURNOVER <= turnover <= self.config.MAX_TURNOVER

    def validate_volume(self, volume: float) -> bool:
        """
        验证成交量是否有效

        Args:
            volume: 成交量（手）

        Returns:
            bool: 成交量是否有效
        """
        if pd.isna(volume):
            return False
        return volume >= self.config.MIN_VOLUME

    def validate_row(self, row: pd.Series) -> Tuple[bool, List[str]]:
        """
        验证单行数据

        Args:
            row: 数据行

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 检查价格
        if 'price' in row.index:
            if not self.validate_price(row['price']):
                errors.append(f"价格异常: {row.get('price', 'N/A')}")

        # 检查涨跌幅
        if 'change_pct' in row.index:
            if not self.validate_change_pct(row['change_pct']):
                errors.append(f"涨跌幅异常: {row.get('change_pct', 'N/A')}")

        # 检查换手率
        if 'turnover' in row.index and pd.notna(row['turnover']):
            if not self.validate_turnover(row['turnover']):
                errors.append(f"换手率异常: {row.get('turnover', 'N/A')}")

        # 检查成交量
        if 'volume' in row.index:
            if not self.validate_volume(row['volume']):
                errors.append(f"成交量异常: {row.get('volume', 'N/A')}")

        return len(errors) == 0, errors

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        验证并分割DataFrame为有效数据和无效数据（优化版，使用向量化操作）

        Args:
            df: 要验证的DataFrame

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (有效数据, 无效数据)
        """
        if df.empty:
            return df, pd.DataFrame()

        # 创建有效标志，初始为True
        valid_mask = pd.Series([True] * len(df), index=df.index)

        # 向量化验证价格
        if 'price' in df.columns:
            price_valid = (df['price'].notna()) & \
                         (df['price'] >= self.config.MIN_PRICE) & \
                         (df['price'] <= self.config.MAX_PRICE)
            valid_mask &= price_valid

        # 向量化验证涨跌幅
        if 'change_pct' in df.columns:
            change_valid = (df['change_pct'].notna()) & \
                          (df['change_pct'] >= self.config.MIN_CHANGE_PCT) & \
                          (df['change_pct'] <= self.config.MAX_CHANGE_PCT)
            valid_mask &= change_valid

        # 向量化验证换手率（如果存在）
        if 'turnover' in df.columns:
            turnover_valid = (df['turnover'].isna()) | \
                            ((df['turnover'] >= self.config.MIN_TURNOVER) & \
                             (df['turnover'] <= self.config.MAX_TURNOVER))
            valid_mask &= turnover_valid

        # 向量化验证成交量
        if 'volume' in df.columns:
            volume_valid = (df['volume'].notna()) & \
                          (df['volume'] >= self.config.MIN_VOLUME)
            valid_mask &= volume_valid

        # 分割数据
        valid_df = df[valid_mask].copy()
        invalid_df = df[~valid_mask].copy()

        # 记录验证结果
        total = len(df)
        valid_count = len(valid_df)
        invalid_count = len(invalid_df)

        if invalid_count > 0:
            self.logger.warning(
                f"数据验证完成: 有效 {valid_count}/{total} "
                f"({valid_count/total*100:.1f}%), "
                f"无效 {invalid_count} ({invalid_count/total*100:.1f}%)"
            )

        return valid_df, invalid_df

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗DataFrame，移除无效数据

        Args:
            df: 要清洗的DataFrame

        Returns:
            pd.DataFrame: 清洗后的DataFrame
        """
        valid_df, invalid_df = self.validate_dataframe(df)

        if not invalid_df.empty:
            self.logger.info(f"已移除 {len(invalid_df)} 条无效数据")

        return valid_df

    def get_validation_summary(self, df: pd.DataFrame) -> dict:
        """
        获取数据验证摘要

        Args:
            df: 要分析的DataFrame

        Returns:
            dict: 验证摘要信息
        """
        if df.empty:
            return {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'valid_rate': 0.0
            }

        valid_df, invalid_df = self.validate_dataframe(df)

        return {
            'total': len(df),
            'valid': len(valid_df),
            'invalid': len(invalid_df),
            'valid_rate': len(valid_df) / len(df) * 100 if len(df) > 0 else 0.0,
            'invalid_samples': invalid_df.head(5).to_dict('records') if not invalid_df.empty else []
        }


def quick_validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    快速验证DataFrame（便捷函数）

    Args:
        df: 要验证的DataFrame

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (有效数据, 无效数据)
    """
    validator = DataValidator()
    return validator.validate_dataframe(df)
