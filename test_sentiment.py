# -*- coding: utf-8 -*-
"""
测试市场情绪分析模块
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_loader import fetch_realtime_data
from src.sentiment.sentiment import MarketAnalyzer, format_report

def main():
    print("=" * 60)
    print("正在获取A股实时数据...")
    print("=" * 60)

    df = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if df.empty:
        print("错误: 未能获取到有效数据")
        return

    print(f"\n成功获取 {len(df)} 只股票数据\n")

    analyzer = MarketAnalyzer(df)
    report = analyzer.generate_daily_report()

    # 打印格式化报告
    report_text = format_report(report)
    print(report_text)

    # 保存到文件
    output_file = Path(__file__).parent / "logs" / "market_report.txt"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n报告已保存到: {output_file}")


if __name__ == "__main__":
    main()
