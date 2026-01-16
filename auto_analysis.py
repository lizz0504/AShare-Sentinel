# -*- coding: utf-8 -*-
"""
AShare-Sentinel - 自动化分析脚本（定时版）
整合数据获取、策略筛选、AI 分析、数据库存储的完整流程
支持定时任务：每天 11:35 和 15:30 自动执行
新增功能：连板/强势股追踪（Trend Detection）

数据库支持：SQLite / PostgreSQL（通过 DATABASE_TYPE 环境变量切换）

依赖安装：
    pip install schedule sqlalchemy
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import schedule

from src.data.data_loader import fetch_realtime_data, get_stock_sector
from src.strategies.strategies import StrategyScanner
from ai_agent import AIStockAnalyzer
from src.database.db_manager import get_db_manager, DatabaseConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==================== 连板/强势股追踪功能 ====================

def check_streak(symbol: str, days: int = 5, score_threshold: int = 75) -> int:
    """
    查询股票在过去 N 天内，有多少天出现在高分榜单中

    支持 SQLite 和 PostgreSQL

    Args:
        symbol: 股票代码
        days: 查询过去 N 天（默认 5 天）
        score_threshold: 评分阈值（默认 75 分）

    Returns:
        int: 出现天数（去重后的日期数量）
    """
    try:
        db = get_db_manager()

        # 根据数据库类型使用不同的 SQL 语法
        if db.database_type == "postgresql":
            # PostgreSQL 语法
            query = f"""
                SELECT COUNT(DISTINCT DATE(created_at)) as streak_count
                FROM stock_analysis
                WHERE symbol = '{symbol}'
                AND ai_score >= {score_threshold}
                AND DATE(created_at) >= CURRENT_DATE - INTERVAL '{days} days'
                AND DATE(created_at) < CURRENT_DATE
            """
        else:
            # SQLite 语法
            query = f"""
                SELECT COUNT(DISTINCT DATE(created_at)) as streak_count
                FROM stock_analysis
                WHERE symbol = '{symbol}'
                AND ai_score >= {score_threshold}
                AND DATE(created_at) >= DATE('now', '-' || '{days}' || ' days')
                AND DATE(created_at) < DATE('now')
            """

        result = db.fetch_all(query)
        streak_count = result[0]['streak_count'] if result else 0
        logger.debug(f"{symbol} 过去{days}天内出现{streak_count}次高分")
        return streak_count

    except Exception as e:
        logger.error(f"查询连板数据失败 {symbol}: {e}")
        return 0


def get_trend_emoji(streak_count: int) -> str:
    """
    根据连榜天数返回对应的 emoji 和建议

    Args:
        streak_count: 连榜天数

    Returns:
        Tuple[str, str]: (emoji标记, 建议文案)
    """
    if streak_count >= 3:
        return "🔥", "妖股/强势"
    elif streak_count == 2:
        return "📈", "趋势确认"
    else:
        return "🆕", "首日突破"


def format_name_with_trend(name: str, streak_count: int) -> str:
    """
    在股票名称旁添加连榜标记

    Args:
        name: 股票名称
        streak_count: 连榜天数

    Returns:
        str: 带标记的股票名称
    """
    emoji, _ = get_trend_emoji(streak_count)
    if streak_count >= 3:
        return f"{name} {emoji} {streak_count}连榜"
    elif streak_count == 2:
        return f"{name} {emoji} 2连榜"
    else:
        return f"{name} {emoji} 新"


class AutoAnalysisEngine:
    """自动化分析引擎"""

    def __init__(self):
        """初始化分析引擎"""
        logger.info("=" * 60)
        logger.info("AShare-Sentinel 自动化分析引擎启动")
        logger.info("=" * 60)

    def run_analysis(self, max_candidates: int = 30, use_cache: bool = True, score_threshold: int = 75, progress_callback=None):
        """
        执行完整的自动化分析流程

        Args:
            max_candidates: 最多分析的候选股票数量
            use_cache: 是否使用缓存（数据获取）
            score_threshold: AI 评分阈值（默认 75 分以上才显示）
            progress_callback: 进度回调函数 callback(progress, message)
        """
        start_time = time.time()
        current_time = datetime.now().strftime("%H:%M")
        print(f"\n{'='*60}")
        print(f"[{current_time}] 开始执行扫描...")
        print(f"{'='*60}")

        # ========== 第一阶段：策略扫描 ==========
        print(f"[{datetime.now().strftime('%H:%M')}] [第一阶段] 策略扫描...")
        if progress_callback:
            progress_callback(10, "正在获取市场数据...")
        logger.info("\n[第一阶段] 策略扫描...")
        candidates = self._scan_strategies(use_cache)

        if not candidates:
            print(f"[{datetime.now().strftime('%H:%M')}] 未找到任何候选股票，结束分析")
            logger.warning("未找到任何候选股票，结束分析")
            self._print_summary_table([])
            return

        print(f"[{datetime.now().strftime('%H:%M')}] 策略扫描完成，共找到 {len(candidates)} 只候选股票")
        logger.info(f"策略扫描完成，共找到 {len(candidates)} 只候选股票")

        # ========== 第二阶段：去重与限制 ==========
        print(f"[{datetime.now().strftime('%H:%M')}] [第二阶段] 去重与筛选...")
        if progress_callback:
            progress_callback(30, "正在筛选候选股票...")
        logger.info("\n[第二阶段] 去重与筛选...")

        # 按 symbol 去重（保留首次出现的策略信息）
        unique_candidates = self._deduplicate_candidates(candidates)

        # 限制分析数量
        if len(unique_candidates) > max_candidates:
            unique_candidates = unique_candidates[:max_candidates]
            print(f"[{datetime.now().strftime('%H:%M')}] 限制分析数量为 {max_candidates} 只")
            logger.info(f"限制分析数量为 {max_candidates} 只")

        print(f"[{datetime.now().strftime('%H:%M')}] 去重后待分析: {len(unique_candidates)} 只股票")
        logger.info(f"去重后待分析: {len(unique_candidates)} 只股票")

        # ========== 第三阶段：AI 流水线 ==========
        print(f"[{datetime.now().strftime('%H:%M')}] [第三阶段] AI 深度分析...")
        if progress_callback:
            progress_callback(50, "正在进行 AI 智能分析...")
        logger.info("\n[第三阶段] AI 深度分析...")
        high_score_stocks = self._ai_analysis_pipeline(unique_candidates, score_threshold, progress_callback)

        # ========== 第四阶段：输出汇总表格 ==========
        self._print_summary_table(high_score_stocks)

        # ========== 完成 ==========
        elapsed = time.time() - start_time
        end_time = datetime.now().strftime("%H:%M")
        print(f"[{end_time}] 扫描结束，数据已入库")
        print(f"[{end_time}] 总耗时: {elapsed:.1f} 秒")
        print(f"{'='*60}\n")
        logger.info(f"\n分析完成！总耗时: {elapsed:.1f} 秒")
        logger.info("=" * 60)

    def _scan_strategies(self, use_cache: bool) -> List[Dict[str, Any]]:
        """
        策略扫描阶段

        Returns:
            List[Dict]: 候选股票列表
        """
        # 获取实时数据
        print(f"[{datetime.now().strftime('%H:%M')}] 正在获取实时行情数据...")
        logger.info("正在获取实时行情数据...")
        df, _ = fetch_realtime_data(filter_st=True, use_cache=use_cache, validate=True)

        if df.empty:
            print(f"[{datetime.now().strftime('%H:%M')}] 获取行情数据失败")
            logger.error("获取行情数据失败")
            return []

        print(f"[{datetime.now().strftime('%H:%M')}] 成功获取 {len(df)} 只股票数据")
        logger.info(f"成功获取 {len(df)} 只股票数据")

        # 初始化策略扫描器
        scanner = StrategyScanner(df)

        # 执行所有策略
        all_candidates = []

        # 策略A: 强势中军
        print(f"[{datetime.now().strftime('%H:%M')}] 执行策略A: 强势中军...")
        logger.info("执行策略A: 强势中军...")
        result_a = scanner.scan_volume_breakout(limit=10)
        self._add_candidates(result_a, all_candidates, "强势中军")

        # 策略B: 冲击涨停
        print(f"[{datetime.now().strftime('%H:%M')}] 执行策略B: 冲击涨停...")
        logger.info("执行策略B: 冲击涨停...")
        result_b = scanner.scan_limit_candidates(limit=10)
        self._add_candidates(result_b, all_candidates, "冲击涨停")

        # 策略C: 低位潜伏
        print(f"[{datetime.now().strftime('%H:%M')}] 执行策略C: 低位潜伏...")
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

    def _ai_analysis_pipeline(self, candidates: List[Dict[str, Any]], score_threshold: int = 75, progress_callback=None) -> List[Dict[str, Any]]:
        """
        AI 分析流水线（批量收集高分股票）

        Args:
            candidates: 待分析的候选股票列表
            score_threshold: AI 评分阈值（默认 75 分以上才收集）
            progress_callback: 进度回调函数 callback(progress, message)

        Returns:
            高分股票列表（评分 >= threshold）
        """
        # 初始化 AI 分析器
        try:
            ai_analyzer = AIStockAnalyzer()
        except Exception as e:
            logger.error(f"AI 分析器初始化失败: {e}")
            logger.error("请检查 .env 文件中的 DASHSCOPE_API_KEY 配置")
            return []

        # 初始化高分股票列表
        high_score_stocks = []
        success_count = 0
        fail_count = 0

        for idx, candidate in enumerate(candidates, 1):
            symbol = candidate['symbol']
            name = candidate['name']

            try:
                # 获取板块信息
                if idx % 5 == 0 or idx == len(candidates):
                    # 每5只股票或最后一只时打印进度
                    print(f"[{datetime.now().strftime('%H:%M')}] 进度: {idx}/{len(candidates)}")

                # 更新进度回调
                if progress_callback:
                    progress_pct = 50 + int(40 * idx / len(candidates))  # 50-90%
                    progress_callback(progress_pct, f"正在分析 {idx}/{len(candidates)}: {name}")

                logger.info(f"[{idx}/{len(candidates)}] 正在获取板块信息: {name} ({symbol})...")
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
                result = ai_analyzer.analyze_stock(stock_data, strategy_name=candidate['strategy'])

                score = result['score']
                suggestion = result['suggestion']
                reason = result['reason']

                if score > 0:
                    # 分析成功
                    success_count += 1
                    logger.info(f"[{idx}/{len(candidates)}] ✅ {name} - 评分: {score}/100 | 建议: {suggestion}")

                    # 如果评分达到阈值，添加到高分列表
                    if score >= score_threshold:
                        high_score_stocks.append({
                            'symbol': symbol,
                            'name': name,
                            'price': candidate['price'],
                            'change_pct': candidate['change_pct'],
                            'turnover': candidate['turnover'],
                            'volume_ratio': candidate['volume_ratio'],
                            'sector': sector,
                            'strategy': candidate['strategy'],
                            'score': score,
                            'suggestion': suggestion,
                            'reason': reason
                        })
                else:
                    # 分析返回默认结果（失败）
                    fail_count += 1
                    logger.warning(f"[{idx}/{len(candidates)}] ⚠️  {name} - AI 分析暂时不可用")

                # 保存到数据库（使用统一数据库管理器）
                try:
                    # 准备数据字典，确保数据类型正确
                    save_data = {
                        'symbol': str(symbol),
                        'name': str(name),
                        'price': float(candidate['price']) if candidate['price'] is not None else None,
                        'change_pct': float(candidate['change_pct']) if candidate['change_pct'] is not None else None,
                        'turnover': float(candidate['turnover']) if candidate['turnover'] is not None else None,
                        'volume_ratio': float(candidate['volume_ratio']) if candidate.get('volume_ratio') is not None else 1.0,
                        'sector': str(sector) if sector is not None else None,
                        'strategy': str(candidate['strategy']),
                        'ai_score': int(score) if score > 0 else None,
                        'ai_reason': str(reason) if reason is not None else None,
                        'ai_suggestion': str(suggestion) if suggestion is not None else None
                    }

                    # 使用 Pandas to_sql 写入数据库
                    df_to_save = pd.DataFrame([save_data])

                    # 确保文本字段为 String 类型（PostgreSQL 要求）
                    for col in ['symbol', 'name', 'sector', 'strategy', 'ai_reason', 'ai_suggestion']:
                        if col in df_to_save.columns:
                            df_to_save[col] = df_to_save[col].astype(str)

                    db = get_db_manager()
                    db.insert_df(df_to_save, 'stock_analysis', if_exists='append')

                    logger.debug(f"[{idx}/{len(candidates)}] {name} - 已保存到数据库")
                except Exception as db_error:
                    logger.error(f"[{idx}/{len(candidates)}] {name} - 保存数据库失败: {db_error}")

                # 避免请求过快
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"[{idx}/{len(candidates)}] ❌ {name} - 分析失败: {e}")
                fail_count += 1
                continue

        # 统计
        print(f"[{datetime.now().strftime('%H:%M')}] 分析统计: 成功 {success_count} 只, 失败 {fail_count} 只, 总计 {len(candidates)} 只")
        if progress_callback:
            progress_callback(95, "分析完成，正在保存数据...")
        logger.info(f"\n分析统计:")
        logger.info(f"  成功: {success_count} 只")
        logger.info(f"  失败: {fail_count} 只")
        logger.info(f"  总计: {len(candidates)} 只")
        logger.info(f"  高分股票 (≥{score_threshold}分): {len(high_score_stocks)} 只")

        # ========== 连板/强势股追踪 ==========
        print(f"[{datetime.now().strftime('%H:%M')}] 正在计算连榜数据...")
        high_score_stocks_with_trend = []
        for stock in high_score_stocks:
            symbol = stock['symbol']
            # 查询过去 5 天内的连榜次数
            streak_count = check_streak(symbol, days=5, score_threshold=score_threshold)
            # 添加连榜数据
            stock_with_trend = stock.copy()
            stock_with_trend['streak_count'] = streak_count
            stock_with_trend['trend_emoji'] = get_trend_emoji(streak_count)[0]
            stock_with_trend['trend_label'] = get_trend_emoji(streak_count)[1]
            high_score_stocks_with_trend.append(stock_with_trend)

        logger.info(f"连榜统计完成")

        # ========== 自动交易触发（三连榜买入） ==========
        from src.config import PortfolioConfig
        if PortfolioConfig.AUTO_TRADE_ENABLED:
            print(f"[{datetime.now().strftime('%H:%M')}] 正在检查自动交易信号...")
            logger.info("开始自动交易检查")

            try:
                from src.portfolio.manager import PortfolioManager
                portfolio_manager = PortfolioManager()
                today_date = datetime.now().strftime('%Y-%m-%d')

                # 遍历所有高分股票，检查连榜数
                for stock in high_score_stocks_with_trend:
                    streak_count = stock.get('streak_count', 0)

                    # 触发条件：连榜数达到阈值
                    if streak_count >= PortfolioConfig.STREAK_THRESHOLD:
                        symbol = stock['symbol']
                        name = stock['name']
                        price = stock['price']

                        # 执行买入
                        success, msg = portfolio_manager.buy_stock(
                            symbol=symbol,
                            name=name,
                            price=price,
                            date=today_date
                        )

                        if success:
                            logger.info(f"🚀 [自动交易] 三连榜买入: {name} ({symbol}) - ¥{price:.2f} - {msg}")
                            print(f"[{datetime.now().strftime('%H:%M')}] 🚀 自动买入: {name} ({symbol}) @ ¥{price:.2f}")
                        else:
                            logger.warning(f"⚠️ [自动交易] 买入失败: {name} ({symbol}) - {msg}")
                            print(f"[{datetime.now().strftime('%H:%M')}] ⚠️ 买入失败: {name} ({symbol}) - {msg}")

                # 显示账户摘要
                summary = portfolio_manager.get_summary()
                print(f"[{datetime.now().strftime('%H:%M')}] 模拟盘账户摘要:")
                print(f"  总资产: ¥{summary['total_assets']:,.2f} (现金 ¥{summary['cash']:,.2f} + 市值 ¥{summary['total_market_value']:,.2f})")
                print(f"  持仓数量: {summary['positions_count']} 只")

            except ImportError:
                logger.warning("PortfolioManager 未找到，跳过自动交易")
            except Exception as e:
                logger.error(f"自动交易执行失败: {e}")

        return high_score_stocks_with_trend

    def _print_summary_table(self, high_score_stocks: List[Dict[str, Any]]):
        """
        打印汇总表格（仅显示高分股票，含连板追踪）

        Args:
            high_score_stocks: 高分股票列表（含连榜数据）
        """
        print(f"\n{'='*130}")
        print(f"[第四阶段] 汇总表格输出（含趋势追踪）")
        print(f"{'='*130}")

        if not high_score_stocks:
            print("本次扫描未发现高分股票（≥75分）")
            print(f"{'='*130}\n")
            return

        # 先按连榜天数降序，再按评分降序排序
        high_score_stocks.sort(key=lambda x: (x.get('streak_count', 0), x['score']), reverse=True)

        # 打印表头
        print(f"\n{'序号':<4} {'代码':<8} {'名称':<18} {'现价':<8} {'涨跌幅':<8} {'换手率':<8} {'量比':<6} {'板块':<12} {'策略':<10} {'评分':<6} {'建议':<12}")
        print("-" * 130)

        # 打印每只股票
        for idx, stock in enumerate(high_score_stocks, 1):
            # 格式化名称（带连榜标记）
            streak_count = stock.get('streak_count', 0)
            if streak_count >= 3:
                display_name = f"{stock['name']} 🔥{streak_count}连榜"
            elif streak_count == 2:
                display_name = f"{stock['name']} 📈2连榜"
            else:
                display_name = f"{stock['name']} 🆕新"

            # 格式化建议（含趋势标签）
            suggestion = stock['suggestion']
            trend_label = stock.get('trend_label', '')
            if trend_label:
                display_suggestion = f"{trend_label}/{suggestion}"
            else:
                display_suggestion = suggestion

            print(f"{idx:<4} "
                  f"{stock['symbol']:<8} "
                  f"{display_name:<18} "
                  f"{stock['price']:<8.2f} "
                  f"{stock['change_pct']:<8.2f} "
                  f"{stock['turnover']:<8.2f} "
                  f"{stock['volume_ratio']:<6.1f} "
                  f"{stock['sector']:<12} "
                  f"{stock['strategy']:<10} "
                  f"{stock['score']:<6} "
                  f"{display_suggestion:<12}")

        print("-" * 130)

        # 统计连榜情况
        streak_3_plus = sum(1 for s in high_score_stocks if s.get('streak_count', 0) >= 3)
        streak_2 = sum(1 for s in high_score_stocks if s.get('streak_count', 0) == 2)
        streak_1 = sum(1 for s in high_score_stocks if s.get('streak_count', 0) <= 1)

        print(f"本次扫描共发现 {len(high_score_stocks)} 只高分股票 | 🔥3连以上: {streak_3_plus} | 📈2连榜: {streak_2} | 🆕首日: {streak_1}")
        print(f"{'='*130}\n")

        # 记录到日志
        logger.info(f"\n汇总表格 - 高分股票 ({len(high_score_stocks)} 只):")
        logger.info(f"  🔥3连以上: {streak_3_plus} | 📈2连榜: {streak_2} | 🆕首日: {streak_1}")
        for stock in high_score_stocks:
            streak_info = f"连榜{stock.get('streak_count', 0)}天" if stock.get('streak_count', 0) > 0 else "新"
            logger.info(f"  {stock['name']} ({stock['symbol']}) - 评分: {stock['score']}/100 | {streak_info} | {stock['suggestion']}")


# ==================== 定时任务配置 ====================

def job():
    """定时任务执行函数"""
    engine = AutoAnalysisEngine()
    engine.run_analysis(max_candidates=30, use_cache=True, score_threshold=75)


def setup_scheduler():
    """配置定时任务"""
    # 每天中午 11:35 执行（午盘扫描）
    schedule.every().day.at("11:35").do(job)
    print("✓ 已设置定时任务: 每天 11:35 (午盘扫描)")

    # 每天下午 15:30 执行（收盘扫描）
    schedule.every().day.at("15:30").do(job)
    print("✓ 已设置定时任务: 每天 15:30 (收盘扫描)")

    # 显示下次执行时间
    print("\n下次执行时间:")
    next_runs = schedule.next_runs()
    for i, next_run in enumerate(next_runs[:2], 1):
        print(f"  {i}. {next_run}")
    print()


def main():
    """主入口 - 定时任务守护进程"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     AShare-Sentinel 自动化分析引擎 (定时任务版)           ║
    ╠════════════════════════════════════════════════════════════╣
    ║  执行时间: 每天 11:35 (午盘) / 15:30 (收盘)               ║
    ║  流程: 策略扫描 -> 去重 -> AI 分析 -> 存储                  ║
    ║  按 Ctrl+C 停止程序                                        ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # 配置定时任务
    setup_scheduler()

    print("定时任务守护进程已启动，等待执行...")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 后台守护循环
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n用户中断，程序退出。")
            logger.info("用户中断，程序退出。")
            break
        except Exception as e:
            logger.error(f"定时任务执行出错: {e}")
            time.sleep(60)  # 出错后等待60秒再继续


if __name__ == "__main__":
    main()
