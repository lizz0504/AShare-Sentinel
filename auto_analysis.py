# -*- coding: utf-8 -*-
"""
AShare-Sentinel - 自动化分析脚本
整合数据获取、策略筛选、AI 分析、数据库存储的完整流程
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd

from src.data.data_loader import fetch_realtime_data, get_stock_sector
from src.strategies.strategies import StrategyScanner
from ai_agent import AIStockAnalyzer
from src.database import save_analysis
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AutoAnalysisEngine:
    """自动化分析引擎"""

    def __init__(self):
        """初始化分析引擎"""
        logger.info("=" * 60)
        logger.info("AShare-Sentinel 自动化分析引擎启动")
        logger.info("=" * 60)

    def run_analysis(self, max_candidates: int = 30, use_cache: bool = True):
        """
        执行完整的自动化分析流程

        Args:
            max_candidates: 最多分析的候选股票数量
            use_cache: 是否使用缓存（数据获取）
        """
        start_time = time.time()

        # ========== 第一阶段：策略扫描 ==========
        logger.info("\n[第一阶段] 策略扫描...")
        candidates = self._scan_strategies(use_cache)

        if not candidates:
            logger.warning("未找到任何候选股票，结束分析")
            return

        logger.info(f"策略扫描完成，共找到 {len(candidates)} 只候选股票")

        # ========== 第二阶段：去重与限制 ==========
        logger.info("\n[第二阶段] 去重与筛选...")

        # 按 symbol 去重（保留首次出现的策略信息）
        unique_candidates = self._deduplicate_candidates(candidates)

        # 限制分析数量
        if len(unique_candidates) > max_candidates:
            unique_candidates = unique_candidates[:max_candidates]
            logger.info(f"限制分析数量为 {max_candidates} 只")

        logger.info(f"去重后待分析: {len(unique_candidates)} 只股票")

        # ========== 第三阶段：AI 流水线 ==========
        logger.info("\n[第三阶段] AI 深度分析...")
        self._ai_analysis_pipeline(unique_candidates)

        # ========== 完成 ==========
        elapsed = time.time() - start_time
        logger.info(f"\n✅ 分析完成！总耗时: {elapsed:.1f} 秒")
        logger.info("=" * 60)

    def _scan_strategies(self, use_cache: bool) -> List[Dict[str, Any]]:
        """
        策略扫描阶段

        Returns:
            List[Dict]: 候选股票列表
        """
        # 获取实时数据
        logger.info("正在获取实时行情数据...")
        df, _ = fetch_realtime_data(filter_st=True, use_cache=use_cache, validate=True)

        if df.empty:
            logger.error("获取行情数据失败")
            return []

        logger.info(f"成功获取 {len(df)} 只股票数据")

        # 初始化策略扫描器
        scanner = StrategyScanner(df)

        # 执行所有策略
        all_candidates = []

        # 策略A: 强势中军
        logger.info("执行策略A: 强势中军...")
        result_a = scanner.scan_volume_breakout(limit=10)
        self._add_candidates(result_a, all_candidates, "强势中军")

        # 策略B: 冲击涨停
        logger.info("执行策略B: 冲击涨停...")
        result_b = scanner.scan_limit_candidates(limit=10)
        self._add_candidates(result_b, all_candidates, "冲击涨停")

        # 策略C: 低位潜伏
        logger.info("执行策略C: 低位潜伏...")
        result_c = scanner.scan_turtle_stocks(limit=10)
        self._add_candidates(result_c, all_candidates, "低位潜伏")

        return all_candidates

    def _add_candidates(self, df: pd.DataFrame, candidates: List[Dict[str, Any]], strategy_name: str):
        """
        将策略结果添加到候选列表

        Args:
            df: 策略返回的 DataFrame
            candidates: 候选列表
            strategy_name: 策略名称
        """
        if df.empty:
            return

        for _, row in df.iterrows():
            candidates.append({
                'symbol': row['symbol'],
                'name': row['name'],
                'price': float(row['price']),
                'change_pct': float(row['change_pct']),
                'turnover': float(row['turnover']),
                'volume_ratio': float(row.get('volume_ratio', 1.0)),
                'strategy': strategy_name
            })

    def _deduplicate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重候选股票（按 symbol）

        Args:
            candidates: 候选列表

        Returns:
            去重后的列表
        """
        seen: Set[str] = set()
        unique = []

        for candidate in candidates:
            symbol = candidate['symbol']
            if symbol not in seen:
                seen.add(symbol)
                unique.append(candidate)

        return unique

    def _ai_analysis_pipeline(self, candidates: List[Dict[str, Any]]):
        """
        AI 分析流水线

        Args:
            candidates: 待分析的候选股票列表
        """
        # 初始化 AI 分析器
        try:
            ai_analyzer = AIStockAnalyzer()
        except Exception as e:
            logger.error(f"AI 分析器初始化失败: {e}")
            logger.error("请检查 .env 文件中的 DASHSCOPE_API_KEY 配置")
            return

        total = len(candidates)
        success_count = 0
        fail_count = 0

        for idx, candidate in enumerate(candidates, 1):
            symbol = candidate['symbol']
            name = candidate['name']

            try:
                # 获取板块信息
                logger.info(f"[{idx}/{total}] 正在获取板块信息: {name} ({symbol})...")
                sector = get_stock_sector(symbol)

                # 构建 AI 分析数据
                stock_data = {
                    'symbol': symbol,
                    'name': name,
                    'price': candidate['price'],
                    'change_pct': candidate['change_pct'],
                    'turnover': candidate['turnover'],
                    'volume_ratio': candidate['volume_ratio'],
                    'sector': sector
                }

                # AI 分析
                logger.info(f"[{idx}/{total}] 正在分析 {name} ({symbol}) - 板块: {sector}...")
                result = ai_analyzer.analyze_stock(stock_data, strategy_name=candidate['strategy'])

                # 打印结果
                score = result['score']
                suggestion = result['suggestion']
                reason = result['reason']

                if score > 0:
                    # 分析成功
                    logger.info(f"[{idx}/{total}] ✅ {name} - 评分: {score}/100 | 建议: {suggestion}")
                    logger.info(f"      理由: {reason}")
                    success_count += 1
                else:
                    # 分析返回默认结果（失败）
                    logger.warning(f"[{idx}/{total}] ⚠️  {name} - AI 分析暂时不可用")
                    fail_count += 1

                # 保存到数据库
                try:
                    save_data = {
                        'symbol': symbol,
                        'name': name,
                        'price': candidate['price'],
                        'change_pct': candidate['change_pct'],
                        'turnover': candidate['turnover'],
                        'volume_ratio': candidate['volume_ratio'],
                        'sector': sector,
                        'strategy': candidate['strategy'],
                        'ai_score': score,
                        'ai_reason': reason,
                        'ai_suggestion': suggestion
                    }
                    save_analysis(save_data)
                    logger.debug(f"[{idx}/{total}] {name} - 已保存到数据库")
                except Exception as db_error:
                    logger.error(f"[{idx}/{total}] {name} - 保存数据库失败: {db_error}")

                # 避免请求过快
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"[{idx}/{total}] ❌ {name} - 分析失败: {e}")
                fail_count += 1
                continue

        # 统计
        logger.info(f"\n分析统计:")
        logger.info(f"  成功: {success_count} 只")
        logger.info(f"  失败: {fail_count} 只")
        logger.info(f"  总计: {total} 只")


def main():
    """主入口"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           AShare-Sentinel 自动化分析引擎                   ║
    ╠════════════════════════════════════════════════════════════╣
    ║  流程: 策略扫描 -> 去重 -> AI 分析 -> 存储                  ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    engine = AutoAnalysisEngine()
    engine.run_analysis(max_candidates=30, use_cache=True)


if __name__ == "__main__":
    main()
