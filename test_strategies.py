# -*- coding: utf-8 -*-
"""
测试策略筛选模块
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_loader import fetch_realtime_data
from src.strategies.strategies import StrategyScanner, format_strategy_header

def main():
    print("=" * 70)
    print(" " * 20 + "短线策略扫描器测试")
    print("=" * 70)
    print("\n正在获取A股实时数据...")

    df = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if df.empty:
        print("错误: 未能获取到有效数据")
        return

    print(f"成功获取 {len(df)} 只股票数据\n")

    scanner = StrategyScanner(df)

    # 策略A: 强势中军 (Top 10)
    print(format_strategy_header(
        "策略A: 强势中军/主升浪 (Top 10)",
        "强势拉升股 (涨幅5-8%, 换手7-15%, 按换手率排序)"
    ))
    result_a = scanner.scan_volume_breakout(limit=10)
    print(scanner.format_output(result_a))
    print(f"总计: {len(result_a)} 只股票\n")

    # 策略B: 冲击涨停 (Top 10)
    print(format_strategy_header(
        "策略B: 冲击涨停/20cm博弈 (Top 10)",
        "即将封板股票 (涨幅8-20%, 换手>8%, 按涨幅排序)"
    ))
    result_b = scanner.scan_limit_candidates(limit=10)
    print(scanner.format_output(result_b))
    print(f"总计: {len(result_b)} 只股票\n")

    # 策略C: 温和放量 (Top 10)
    print(format_strategy_header(
        "策略C: 温和放量/趋势股 (Top 10)",
        "温和吸筹股 (涨幅2-5%, 换手>6%, 按换手率排序)"
    ))
    result_c = scanner.scan_turtle_stocks(limit=10)
    print(scanner.format_output(result_c))
    print(f"总计: {len(result_c)} 只股票\n")

    # 汇总统计
    print("=" * 70)
    print("策略扫描汇总 (Elite 10)")
    print("=" * 70)
    print(f"  总股票数: {len(df)}")
    print(f"  策略A (强势中军): {len(result_a)} 只")
    print(f"  策略B (冲击涨停): {len(result_b)} 只")
    print(f"  策略C (温和放量): {len(result_c)} 只")
    print(f"  合计机会: {len(result_a) + len(result_b) + len(result_c)} 只")
    print("=" * 70)


if __name__ == "__main__":
    main()
