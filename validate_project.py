#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AShare-Sentinel 项目验证脚本
全面检查项目功能和潜在的Bug
"""

import sys
sys.path.insert(0, 'src')

import pandas as pd
from data.data_loader import (
    fetch_realtime_data,
    fetch_sector_data,
    fetch_concept_data,
    get_hot_stocks_by_sector,
    print_market_summary
)


def check_dataframe_integrity(df, func_name):
    """检查DataFrame完整性"""
    issues = []

    if df.empty:
        return [f"{func_name}: 返回空DataFrame"]

    # 检查是否有NaN值
    nan_counts = df.isnull().sum()
    cols_with_nan = nan_counts[nan_counts > 0].tolist()
    if cols_with_nan:
        issues.append(f"{func_name}: 部分列包含NaN值")

    # 检查数据类型
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                pd.to_numeric(df[col], errors='raise')
            except:
                pass  # 非数值列是正常的

    return issues


def test_fetch_realtime_data():
    """测试实时行情数据获取"""
    print("\n" + "="*60)
    print("测试 1: fetch_realtime_data()")
    print("="*60)

    issues = []

    # 测试默认参数
    print("\n1.1 测试默认参数 (filter_st=True)...")
    df = fetch_realtime_data()
    issues.extend(check_dataframe_integrity(df, "fetch_realtime_data"))

    if not df.empty:
        # 检查必需字段
        required_cols = ['symbol', 'name', 'price', 'change_pct', 'volume', 'turnover', 'circ_mv']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"缺少必需字段: {missing_cols}")
        else:
            print("   必需字段完整")

        # 检查数据清洗效果
        st_stocks = df[df['name'].str.contains('ST|st', na=False)]
        if not st_stocks.empty:
            issues.append(f"存在 {len(st_stocks)} 只ST股票未被过滤")

        zero_volume = df[df['volume'] == 0]
        if not zero_volume.empty:
            issues.append(f"存在 {len(zero_volume)} 只成交量为0的股票")

        print(f"   数据行数: {len(df)}")
        print(f"   列数: {len(df.columns)}")
    else:
        issues.append("返回空DataFrame")

    # 测试不过滤ST
    print("\n1.2 测试 filter_st=False...")
    df_no_filter = fetch_realtime_data(filter_st=False)
    if not df_no_filter.empty:
        st_count = len(df_no_filter[df_no_filter['name'].str.contains('ST|st', na=False)])
        print(f"   ST股票数量: {st_count}")
        if len(df_no_filter) <= len(df):
            issues.append("filter_st参数未生效")

    return issues


def test_fetch_sector_data():
    """测试行业板块数据获取"""
    print("\n" + "="*60)
    print("测试 2: fetch_sector_data()")
    print("="*60)

    issues = []

    print("\n2.1 测试默认参数 (top_n=10)...")
    df = fetch_sector_data()
    issues.extend(check_dataframe_integrity(df, "fetch_sector_data"))

    if not df.empty:
        if len(df) != 10:
            issues.append(f"返回行数不正确: 期望10, 实际{len(df)}")

        # 检查是否按涨跌幅降序排列
        if not df['change_pct'].is_monotonic_decreasing:
            issues.append("数据未按涨跌幅降序排列")

        print(f"   返回行数: {len(df)}")

    # 测试自定义top_n
    print("\n2.2 测试 top_n=5...")
    df_5 = fetch_sector_data(top_n=5)
    if not df_5.empty and len(df_5) != 5:
        issues.append(f"top_n参数未生效: 期望5, 实际{len(df_5)}")

    return issues


def test_fetch_concept_data():
    """测试概念板块数据获取"""
    print("\n" + "="*60)
    print("测试 3: fetch_concept_data()")
    print("="*60)

    issues = []

    print("\n3.1 测试默认参数...")
    df = fetch_concept_data()
    issues.extend(check_dataframe_integrity(df, "fetch_concept_data"))

    if not df.empty:
        print(f"   返回行数: {len(df)}")
    else:
        issues.append("返回空DataFrame")

    return issues


def test_get_hot_stocks_by_sector():
    """测试获取板块热门股票"""
    print("\n" + "="*60)
    print("测试 4: get_hot_stocks_by_sector()")
    print("="*60)

    issues = []

    # 先获取一个有效的板块名称
    sector_df = fetch_sector_data(top_n=1)
    if sector_df.empty:
        issues.append("无法获取板块数据进行测试")
        return issues

    sector_name = sector_df.iloc[0]['name']
    print(f"\n4.1 测试板块: {sector_name}")

    stocks_df = get_hot_stocks_by_sector(sector_name, top_n=5)
    issues.extend(check_dataframe_integrity(stocks_df, "get_hot_stocks_by_sector"))

    if not stocks_df.empty:
        if len(stocks_df) != 5:
            issues.append(f"返回股票数量不正确: 期望5, 实际{len(stocks_df)}")
        print(f"   返回股票数: {len(stocks_df)}")
    else:
        issues.append("返回空DataFrame")

    # 测试无效板块名称
    print("\n4.2 测试无效板块名称...")
    invalid_df = get_hot_stocks_by_sector("不存在的板块名称123")
    if not invalid_df.empty:
        issues.append("无效板块名称应返回空DataFrame")

    return issues


def test_print_market_summary():
    """测试市场概况打印"""
    print("\n" + "="*60)
    print("测试 5: print_market_summary()")
    print("="*60)

    issues = []

    print("\n5.1 测试正常数据...")
    df = fetch_realtime_data()
    sector_df = fetch_sector_data(top_n=5)

    try:
        print_market_summary(df, sector_df)
        print("   正常输出")
    except Exception as e:
        issues.append(f"打印出错: {e}")

    # 测试空DataFrame
    print("\n5.2 测试空DataFrame...")
    try:
        print_market_summary(pd.DataFrame(), pd.DataFrame())
        print("   空数据处理正常")
    except Exception as e:
        issues.append(f"空数据处理出错: {e}")

    return issues


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*60)
    print("测试 6: 边界情况")
    print("="*60)

    issues = []

    # 测试top_n=0
    print("\n6.1 测试 top_n=0...")
    try:
        df = fetch_sector_data(top_n=0)
        if not df.empty:
            issues.append("top_n=0应返回空DataFrame")
    except Exception as e:
        issues.append(f"top_n=0抛出异常: {e}")

    # 测试top_n为负数
    print("\n6.2 测试 top_n=-1...")
    try:
        df = fetch_sector_data(top_n=-1)
        if not df.empty:
            print(f"   返回{len(df)}行")
    except Exception as e:
        issues.append(f"top_n=-1抛出异常: {e}")

    return issues


def main():
    """主测试函数"""
    print("="*60)
    print("AShare-Sentinel 项目全面验证")
    print("="*60)

    all_issues = []

    # 运行所有测试
    all_issues.extend(test_fetch_realtime_data())
    all_issues.extend(test_fetch_sector_data())
    all_issues.extend(test_fetch_concept_data())
    all_issues.extend(test_get_hot_stocks_by_sector())
    all_issues.extend(test_print_market_summary())
    all_issues.extend(test_edge_cases())

    # 汇总结果
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)

    if not all_issues:
        print("\n✓ 所有测试通过！未发现Bug")
        return 0
    else:
        print(f"\n✗ 发现 {len(all_issues)} 个问题:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
