"""
市场情绪分析模块
用于计算宏观市场情绪指标
"""

import sys
from pathlib import Path
# 将项目根目录添加到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from typing import Dict, Tuple, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarketAnalyzer:
    """
    市场情绪分析器
    基于全市场股票数据计算各类情绪指标
    """

    # 市场温度阈值定义
    TEMP_SCORCHING = 80
    TEMP_WARM = 50
    TEMP_COLD = 20

    # 涨跌停阈值（简化计算）
    LIMIT_UP_THRESHOLD = 9.8
    LIMIT_DOWN_THRESHOLD = -9.8

    # 市场状态描述
    STATUS_SCORCHING = "极热"
    STATUS_WARM = "温和"
    STATUS_COLD = "亏钱效应"
    STATUS_FROZEN = "冰点"

    def __init__(self, df: pd.DataFrame):
        """
        初始化市场分析器

        Args:
            df: 包含股票数据的DataFrame，必须包含 change_pct 列
        """
        self.df = df.copy() if df is not None else pd.DataFrame()

        if self.df.empty:
            logger.warning("输入的DataFrame为空，分析器将返回默认值")
        elif 'change_pct' not in self.df.columns:
            logger.error("DataFrame缺少必要的 change_pct 列")
            self.df = pd.DataFrame()

    def get_up_down_counts(self) -> Dict[str, int]:
        """
        计算上涨、下跌、平盘家数

        Returns:
            包含 up, down, flat 的字典
        """
        if self.df.empty:
            return {'up': 0, 'down': 0, 'flat': 0, 'total': 0}

        try:
            up = (self.df['change_pct'] > 0).sum()
            down = (self.df['change_pct'] < 0).sum()
            flat = (self.df['change_pct'] == 0).sum()
            total = len(self.df)

            result = {'up': int(up), 'down': int(down), 'flat': int(flat), 'total': total}

            logger.info(f"涨跌分布 - 上涨: {up}, 下跌: {down}, 平盘: {flat}, 总计: {total}")

            return result

        except Exception as e:
            logger.error(f"计算涨跌分布时出错: {e}")
            return {'up': 0, 'down': 0, 'flat': 0, 'total': 0}

    def get_limit_performance(self) -> Dict[str, int]:
        """
        计算涨停和跌停家数

        Returns:
            包含 limit_up, limit_down 的字典
        """
        if self.df.empty:
            return {'limit_up': 0, 'limit_down': 0, 'limit_up_rate': 0.0, 'limit_down_rate': 0.0}

        try:
            total = len(self.df)
            limit_up = (self.df['change_pct'] >= self.LIMIT_UP_THRESHOLD).sum()
            limit_down = (self.df['change_pct'] <= self.LIMIT_DOWN_THRESHOLD).sum()

            result = {
                'limit_up': int(limit_up),
                'limit_down': int(limit_down),
                'limit_up_rate': round(limit_up / total * 100, 2) if total > 0 else 0.0,
                'limit_down_rate': round(limit_down / total * 100, 2) if total > 0 else 0.0
            }

            logger.info(f"涨跌停 - 涨停: {limit_up} ({result['limit_up_rate']}%), "
                       f"跌停: {limit_down} ({result['limit_down_rate']}%)")

            return result

        except Exception as e:
            logger.error(f"计算涨跌停时出错: {e}")
            return {'limit_up': 0, 'limit_down': 0, 'limit_up_rate': 0.0, 'limit_down_rate': 0.0}

    def get_market_temperature(self) -> Dict[str, any]:
        """
        计算市场温度 (0-100)

        温度 = (上涨家数 / 总有效家数) * 100

        Returns:
            包含 score 和 status 的字典
        """
        if self.df.empty:
            return {'score': 0.0, 'status': self.STATUS_FROZEN, 'level': 'frozen'}

        try:
            counts = self.get_up_down_counts()
            total = counts['total']
            up = counts['up']

            if total == 0:
                return {'score': 0.0, 'status': self.STATUS_FROZEN, 'level': 'frozen'}

            score = round(up / total * 100, 2)

            # 根据分数确定市场状态
            if score >= self.TEMP_SCORCHING:
                status = self.STATUS_SCORCHING
                level = 'scorching'
            elif score >= self.TEMP_WARM:
                status = self.STATUS_WARM
                level = 'warm'
            elif score >= self.TEMP_COLD:
                status = self.STATUS_COLD
                level = 'cold'
            else:
                status = self.STATUS_FROZEN
                level = 'frozen'

            result = {'score': score, 'status': status, 'level': level}

            logger.info(f"市场温度: {score} ({status})")

            return result

        except Exception as e:
            logger.error(f"计算市场温度时出错: {e}")
            return {'score': 0.0, 'status': self.STATUS_FROZEN, 'level': 'frozen'}

    def get_market_median(self) -> Dict[str, float]:
        """
        计算全市场涨跌幅中位数

        Returns:
            包含 median_change 的字典
        """
        if self.df.empty:
            return {'median_change': 0.0, 'mean_change': 0.0}

        try:
            median_change = round(self.df['change_pct'].median(), 2)
            mean_change = round(self.df['change_pct'].mean(), 2)

            result = {
                'median_change': median_change,
                'mean_change': mean_change
            }

            logger.info(f"涨跌幅 - 中位数: {median_change}%, 平均数: {mean_change}%")

            return result

        except Exception as e:
            logger.error(f"计算涨跌幅中位数时出错: {e}")
            return {'median_change': 0.0, 'mean_change': 0.0}

    def get_width_statistics(self) -> Dict[str, any]:
        """
        计算市场宽度统计

        Returns:
            包含各涨跌幅区间的分布情况
        """
        if self.df.empty:
            return {
                'gt_7': 0, 'gt_5': 0, 'gt_3': 0, 'gt_0': 0,
                'lt_0': 0, 'lt_3': 0, 'lt_5': 0, 'lt_7': 0
            }

        try:
            total = len(self.df)

            gt_7 = int((self.df['change_pct'] > 7).sum())
            gt_5 = int((self.df['change_pct'] > 5).sum())
            gt_3 = int((self.df['change_pct'] > 3).sum())
            gt_0 = int((self.df['change_pct'] > 0).sum())
            lt_0 = int((self.df['change_pct'] < 0).sum())
            lt_3 = int((self.df['change_pct'] < -3).sum())
            lt_5 = int((self.df['change_pct'] < -5).sum())
            lt_7 = int((self.df['change_pct'] < -7).sum())

            result = {
                'gt_7': gt_7, 'gt_7_pct': round(gt_7 / total * 100, 2) if total > 0 else 0.0,
                'gt_5': gt_5, 'gt_5_pct': round(gt_5 / total * 100, 2) if total > 0 else 0.0,
                'gt_3': gt_3, 'gt_3_pct': round(gt_3 / total * 100, 2) if total > 0 else 0.0,
                'gt_0': gt_0, 'gt_0_pct': round(gt_0 / total * 100, 2) if total > 0 else 0.0,
                'lt_0': lt_0, 'lt_0_pct': round(lt_0 / total * 100, 2) if total > 0 else 0.0,
                'lt_3': lt_3, 'lt_3_pct': round(lt_3 / total * 100, 2) if total > 0 else 0.0,
                'lt_5': lt_5, 'lt_5_pct': round(lt_5 / total * 100, 2) if total > 0 else 0.0,
                'lt_7': lt_7, 'lt_7_pct': round(lt_7 / total * 100, 2) if total > 0 else 0.0,
            }

            return result

        except Exception as e:
            logger.error(f"计算市场宽度时出错: {e}")
            return {
                'gt_7': 0, 'gt_7_pct': 0.0,
                'gt_5': 0, 'gt_5_pct': 0.0,
                'gt_3': 0, 'gt_3_pct': 0.0,
                'gt_0': 0, 'gt_0_pct': 0.0,
                'lt_0': 0, 'lt_0_pct': 0.0,
                'lt_3': 0, 'lt_3_pct': 0.0,
                'lt_5': 0, 'lt_5_pct': 0.0,
                'lt_7': 0, 'lt_7_pct': 0.0,
            }

    def generate_daily_report(self) -> Dict[str, any]:
        """
        生成完整的市场日报

        Returns:
            包含所有关键指标的字典
        """
        logger.info("=" * 50)
        logger.info("开始生成市场情绪日报")

        up_down = self.get_up_down_counts()
        limit_perf = self.get_limit_performance()
        temperature = self.get_market_temperature()
        median = self.get_market_median()
        width = self.get_width_statistics()

        report = {
            'summary': {
                'total_stocks': up_down['total'],
                'up_count': up_down['up'],
                'down_count': up_down['down'],
                'flat_count': up_down['flat'],
                'up_ratio': round(up_down['up'] / up_down['total'] * 100, 2) if up_down['total'] > 0 else 0.0,
            },
            'limit_performance': {
                'limit_up': limit_perf['limit_up'],
                'limit_down': limit_perf['limit_down'],
                'limit_up_rate': limit_perf['limit_up_rate'],
                'limit_down_rate': limit_perf['limit_down_rate'],
            },
            'market_temperature': {
                'score': temperature['score'],
                'status': temperature['status'],
                'level': temperature['level'],
            },
            'price_change_stats': {
                'median_change': median['median_change'],
                'mean_change': median['mean_change'],
            },
            'market_width': width,
        }

        logger.info("市场情绪日报生成完成")
        logger.info("=" * 50)

        return report


def format_report(report: Dict[str, any]) -> str:
    """
    格式化输出市场日报

    Args:
        report: generate_daily_report() 返回的字典

    Returns:
        格式化的字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append("                    A股市场情绪日报")
    lines.append("=" * 60)
    lines.append("")

    # 市场概览
    lines.append("【市场概览】")
    lines.append(f"  总股票数: {report['summary']['total_stocks']:,}")
    lines.append(f"  上涨: {report['summary']['up_count']:,} ({report['summary']['up_ratio']}%)")
    lines.append(f"  下跌: {report['summary']['down_count']:,}")
    lines.append(f"  平盘: {report['summary']['flat_count']:,}")
    lines.append("")

    # 涨跌停
    lines.append("【涨跌停】")
    lines.append(f"  涨停: {report['limit_performance']['limit_up']} 家 ({report['limit_performance']['limit_up_rate']}%)")
    lines.append(f"  跌停: {report['limit_performance']['limit_down']} 家 ({report['limit_performance']['limit_down_rate']}%)")
    lines.append("")

    # 市场温度
    temp_symbol = {
        'scorching': '[极热]',
        'warm': '[温暖]',
        'cold': '[偏冷]',
        'frozen': '[冰点]'
    }
    level = report['market_temperature']['level']
    lines.append("【市场温度】")
    lines.append(f"  分数: {report['market_temperature']['score']}")
    lines.append(f"  状态: {temp_symbol.get(level, '')} {report['market_temperature']['status']}")
    lines.append("")

    # 涨跌幅统计
    lines.append("【涨跌幅统计】")
    lines.append(f"  中位数: {report['price_change_stats']['median_change']:.2f}%")
    lines.append(f"  平均数: {report['price_change_stats']['mean_change']:.2f}%")
    lines.append("")

    # 市场宽度
    lines.append("【市场宽度】")
    width = report['market_width']
    lines.append(f"  涨幅 >7%: {width['gt_7']} 家 ({width['gt_7_pct']}%)")
    lines.append(f"  涨幅 >5%: {width['gt_5']} 家 ({width['gt_5_pct']}%)")
    lines.append(f"  涨幅 >3%: {width['gt_3']} 家 ({width['gt_3_pct']}%)")
    lines.append(f"  跌幅 <-3%: {width['lt_3']} 家 ({width['lt_3_pct']}%)")
    lines.append(f"  跌幅 <-5%: {width['lt_5']} 家 ({width['lt_5_pct']}%)")
    lines.append(f"  跌幅 <-7%: {width['lt_7']} 家 ({width['lt_7_pct']}%)")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    from src.data.data_loader import fetch_realtime_data

    print("=" * 60)
    print("正在获取A股实时数据...")
    print("=" * 60)

    df, _ = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if df.empty:
        print("错误: 未能获取到有效数据")
    else:
        print(f"\n成功获取 {len(df)} 只股票数据\n")

        analyzer = MarketAnalyzer(df)
        report = analyzer.generate_daily_report()

        print(format_report(report))
