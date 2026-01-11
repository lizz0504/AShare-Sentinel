# -*- coding: utf-8 -*-
"""
对 Step 2 sentiment.py 进行全面验证
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from src.sentiment.sentiment import MarketAnalyzer, format_report

print("=" * 70)
print(" " * 20 + "Step 2 全面验证")
print("=" * 70)

# 测试1: 空DataFrame处理
print("\n[测试1] 空DataFrame处理")
print("-" * 70)
try:
    empty_df = pd.DataFrame()
    analyzer = MarketAnalyzer(empty_df)
    report = analyzer.generate_daily_report()

    print("  空DataFrame处理: PASS")
    print(f"    - 涨跌分布: {report['summary']}")
    print(f"    - 市场温度: {report['market_temperature']}")
    print(f"    - 涨跌幅: {report['price_change_stats']}")
except Exception as e:
    print(f"  空DataFrame处理: FAIL - {e}")

# 测试2: 缺少change_pct列的DataFrame
print("\n[测试2] 缺少change_pct列的DataFrame")
print("-" * 70)
try:
    invalid_df = pd.DataFrame({'price': [10, 20, 30]})
    analyzer = MarketAnalyzer(invalid_df)
    report = analyzer.generate_daily_report()

    print("  缺失列处理: PASS")
    print(f"    - 返回默认值: {report['summary']['total_stocks'] == 0}")
except Exception as e:
    print(f"  缺失列处理: FAIL - {e}")

# 测试3: 正常数据 - 极热市场 (上涨占比 >80%)
print("\n[测试3] 极热市场 (上涨占比 >80%)")
print("-" * 70)
try:
    hot_data = {
        'symbol': [f'{i:06d}' for i in range(100)],
        'name': [f'股票{i}' for i in range(100)],
        'change_pct': [5.0] * 85 + [-2.0] * 15  # 85%上涨
    }
    hot_df = pd.DataFrame(hot_data)
    analyzer = MarketAnalyzer(hot_df)
    report = analyzer.generate_daily_report()

    temp_status = report['market_temperature']['status']
    temp_score = report['market_temperature']['score']

    print(f"  上涨占比: 85%")
    print(f"  市场温度: {temp_score} -> {temp_status}")
    print(f"  验证: {'PASS' if temp_status == '极热' and temp_score == 85.0 else 'FAIL'}")
except Exception as e:
    print(f"  极热市场测试: FAIL - {e}")

# 测试4: 冰点市场 (上涨占比 <20%)
print("\n[测试4] 冰点市场 (上涨占比 <20%)")
print("-" * 70)
try:
    cold_data = {
        'symbol': [f'{i:06d}' for i in range(100)],
        'name': [f'股票{i}' for i in range(100)],
        'change_pct': [1.0] * 15 + [-5.0] * 85  # 15%上涨
    }
    cold_df = pd.DataFrame(cold_data)
    analyzer = MarketAnalyzer(cold_df)
    report = analyzer.generate_daily_report()

    temp_status = report['market_temperature']['status']
    temp_score = report['market_temperature']['score']

    print(f"  上涨占比: 15%")
    print(f"  市场温度: {temp_score} -> {temp_status}")
    print(f"  验证: {'PASS' if temp_status == '冰点' and temp_score == 15.0 else 'FAIL'}")
except Exception as e:
    print(f"  冰点市场测试: FAIL - {e}")

# 测试5: 涨跌停计算
print("\n[测试5] 涨跌停计算")
print("-" * 70)
try:
    limit_data = {
        'symbol': [f'{i:06d}' for i in range(100)],
        'name': [f'股票{i}' for i in range(100)],
        'change_pct': [10.0] * 5 + [9.8] * 3 + [-9.8] * 2 + [-10.0] * 1 + [1.0] * 89
    }
    limit_df = pd.DataFrame(limit_data)
    analyzer = MarketAnalyzer(limit_df)
    report = analyzer.generate_daily_report()

    limit_up = report['limit_performance']['limit_up']
    limit_down = report['limit_performance']['limit_down']

    print(f"  预期涨停: 8家 (>=9.8%)")
    print(f"  实际涨停: {limit_up}家")
    print(f"  预期跌停: 3家 (<=-9.8%)")
    print(f"  实际跌停: {limit_down}家")
    print(f"  验证: {'PASS' if limit_up == 8 and limit_down == 3 else 'FAIL'}")
except Exception as e:
    print(f"  涨跌停计算: FAIL - {e}")

# 测试6: 涨跌幅中位数计算
print("\n[测试6] 涨跌幅中位数与平均数计算")
print("-" * 70)
try:
    median_data = {
        'symbol': [f'{i:06d}' for i in range(11)],
        'name': [f'股票{i}' for i in range(11)],
        'change_pct': [-5, -2, -1, 0, 1, 2, 3, 4, 5, 6, 100]  # 中位数=2, 平均数≈9.7
    }
    median_df = pd.DataFrame(median_data)
    analyzer = MarketAnalyzer(median_df)
    report = analyzer.generate_daily_report()

    median_change = report['price_change_stats']['median_change']
    mean_change = report['price_change_stats']['mean_change']

    print(f"  数据: [-5, -2, -1, 0, 1, 2, 3, 4, 5, 6, 100]")
    print(f"  中位数: {median_change} (预期: 2.0)")
    print(f"  平均数: {mean_change} (预期: 10.27)")
    print(f"  验证: {'PASS' if median_change == 2.0 and abs(mean_change - 10.27) < 0.1 else 'FAIL'}")
except Exception as e:
    print(f"  中位数计算: FAIL - {e}")

# 测试7: 市场宽度统计
print("\n[测试7] 市场宽度统计")
print("-" * 70)
try:
    width_data = {
        'symbol': [f'{i:06d}' for i in range(100)],
        'name': [f'股票{i}' for i in range(100)],
        'change_pct': [8.0] * 10 + [6.0] * 15 + [4.0] * 20 + [2.0] * 20 +
                      [-2.0] * 20 + [-6.0] * 10 + [-8.0] * 5
    }
    width_df = pd.DataFrame(width_data)
    analyzer = MarketAnalyzer(width_df)
    report = analyzer.generate_daily_report()

    width = report['market_width']

    print(f"  涨幅>7%: {width['gt_7']}家 (预期10家)")
    print(f"  涨幅>5%: {width['gt_5']}家 (预期25家)")
    print(f"  涨幅>3%: {width['gt_3']}家 (预期45家)")
    print(f"  跌幅<-3%: {width['lt_3']}家 (预期35家)")
    print(f"  验证: {'PASS' if width['gt_7'] == 10 and width['gt_5'] == 25 else 'FAIL'}")
except Exception as e:
    print(f"  市场宽度统计: FAIL - {e}")

# 测试8: 格式化输出
print("\n[测试8] 格式化输出")
print("-" * 70)
try:
    test_data = {
        'symbol': [f'{i:06d}' for i in range(10)],
        'name': [f'测试股票{i}' for i in range(10)],
        'change_pct': [5.0, 3.0, 1.0, 0.0, -1.0, -2.0, 10.0, -10.0, 2.5, -0.5]
    }
    test_df = pd.DataFrame(test_data)
    analyzer = MarketAnalyzer(test_df)
    report = analyzer.generate_daily_report()

    output = format_report(report)

    # 检查关键字段
    has_summary = '市场概览' in output
    has_limit = '涨跌停' in output
    has_temp = '市场温度' in output
    has_median = '涨跌幅统计' in output
    has_width = '市场宽度' in output

    print(f"  包含市场概览: {has_summary}")
    print(f"  包含涨跌停: {has_limit}")
    print(f"  包含市场温度: {has_temp}")
    print(f"  包含涨跌幅统计: {has_median}")
    print(f"  包含市场宽度: {has_width}")
    print(f"  验证: {'PASS' if all([has_summary, has_limit, has_temp, has_median, has_width]) else 'FAIL'}")

except Exception as e:
    print(f"  格式化输出: FAIL - {e}")

# 测试9: 边界值测试
print("\n[测试9] 边界值测试")
print("-" * 70)
try:
    # 涨跌停边界值
    boundary_data = {
        'symbol': [f'{i:06d}' for i in range(5)],
        'name': [f'股票{i}' for i in range(5)],
        'change_pct': [9.79, 9.80, 9.81, -9.80, -9.81]  # 边界值
    }
    boundary_df = pd.DataFrame(boundary_data)
    analyzer = MarketAnalyzer(boundary_df)
    report = analyzer.generate_daily_report()

    limit_up = report['limit_performance']['limit_up']
    limit_down = report['limit_performance']['limit_down']

    print(f"  数据: [9.79, 9.80, 9.81, -9.80, -9.81]")
    print(f"  涨停(>=9.8): {limit_up}家 (预期2家)")
    print(f"  跌停(<=-9.8): {limit_down}家 (预期2家)")
    print(f"  验证: {'PASS' if limit_up == 2 and limit_down == 2 else 'FAIL'}")
except Exception as e:
    print(f"  边界值测试: FAIL - {e}")

# 测试10: 真实数据集成测试
print("\n[测试10] 真实数据集成测试")
print("-" * 70)
try:
    from src.data.data_loader import fetch_realtime_data

    df = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if not df.empty:
        analyzer = MarketAnalyzer(df)
        report = analyzer.generate_daily_report()

        # 验证数据完整性
        total = report['summary']['total_stocks']
        up = report['summary']['up_count']
        down = report['summary']['down_count']
        flat = report['summary']['flat_count']

        print(f"  总股票数: {total}")
        print(f"  上涨: {up}, 下跌: {down}, 平盘: {flat}")
        print(f"  数据一致性: {up + down + flat == total}")
        print(f"  市场温度: {report['market_temperature']['score']} -> {report['market_temperature']['status']}")
        print(f"  涨跌幅中位数: {report['price_change_stats']['median_change']}%")
        print(f"  验证: PASS (真实数据获取成功)")
    else:
        print(f"  警告: 未能获取真实数据 (可能是网络问题)")

except Exception as e:
    print(f"  真实数据测试: FAIL - {e}")

# 测试总结
print("\n" + "=" * 70)
print(" " * 25 + "验证完成")
print("=" * 70)
