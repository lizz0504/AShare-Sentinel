# -*- coding: utf-8 -*-
"""
AShare-Sentinel 增强功能测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data.data_loader import (
    fetch_realtime_data,
    fetch_sector_data,
    fetch_concept_data,
    clear_cache
)
from src.config import CACHE_DIR, LOG_DIR


def main():
    print("="*60)
    print("AShare-Sentinel 增强功能测试")
    print("="*60)

    # 测试1: 获取实时数据（带缓存和验证）
    print("\n测试1: 获取实时数据（首次，无缓存）...")
    df1 = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)
    print(f"  获取到 {len(df1)} 只股票")

    # 测试2: 再次获取（应该使用缓存）
    print("\n测试2: 获取实时数据（第二次，应该使用缓存）...")
    df2 = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)
    print(f"  获取到 {len(df2)} 只股票")

    # 测试3: 获取板块数据
    print("\n测试3: 获取板块数据...")
    sectors = fetch_sector_data(top_n=5)
    print(f"  获取到 {len(sectors)} 个板块")

    # 测试4: 清空缓存并重新获取
    print("\n测试4: 清空缓存并重新获取...")
    clear_cache()
    df3 = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)
    print(f"  获取到 {len(df3)} 只股票")

    print("\n" + "="*60)
    print("测试完成！")
    print(f"  - 缓存目录: {CACHE_DIR}")
    print(f"  - 日志目录: {LOG_DIR}")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
