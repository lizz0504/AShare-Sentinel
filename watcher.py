"""
AShare-Sentinel - 后台监控脚本
独立于 Streamlit 运行，用于捕捉稍纵即逝的"打板"机会
"""

import time
import sys
from datetime import datetime, time as dt_time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.data.data_loader import fetch_realtime_data
from src.strategies.strategies import StrategyScanner
from src.config import LOG_DIR


def is_trading_time() -> bool:
    """
    判断当前是否为交易时间

    交易时段:
    - 上午: 09:25 - 11:30
    - 下午: 13:00 - 15:00

    Returns:
        bool: True 表示在交易时间内
    """
    now = datetime.now()
    current_time = now.time()

    # 上午交易时段: 09:25 - 11:30
    morning_start = dt_time(9, 25)
    morning_end = dt_time(11, 30)

    # 下午交易时段: 13:00 - 15:00
    afternoon_start = dt_time(13, 0)
    afternoon_end = dt_time(15, 0)

    return (morning_start <= current_time <= morning_end or
            afternoon_start <= current_time <= afternoon_end)


def play_alert_sound():
    """播放报警提示音"""
    try:
        # 尝试使用系统蜂鸣
        print('\a', end='', flush=True)
        time.sleep(0.1)
        print('\a', end='', flush=True)
    except Exception:
        pass


def send_notification(title: str, message: str):
    """
    发送系统通知

    Args:
        title: 通知标题
        message: 通知内容
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="AShare-Sentinel",
            timeout=10  # 通知显示10秒
        )
    except ImportError:
        # plyer 未安装，跳过通知
        pass
    except Exception as e:
        print(f"[通知失败] {e}")


def format_alert_message(row) -> tuple:
    """
    格式化报警信息

    Args:
        row: 股票数据行

    Returns:
        (标题, 消息) 元组
    """
    symbol = row['symbol']
    name = row['name']
    price = row['price']
    change_pct = row['change_pct']
    turnover = row.get('turnover', 0)

    title = f"🔥 妖股预警!"
    message = f"{name} ({symbol}) 正在冲击涨停!\n现价: ¥{price:.2f} | 涨幅: +{change_pct:.2f}% | 换手: {turnover:.2f}%"

    return title, message


def print_alert_log(row):
    """
    打印控制台报警日志

    Args:
        row: 股票数据行
    """
    now = datetime.now().strftime("%H:%M:%S")
    symbol = row['symbol']
    name = row['name']
    change_pct = row['change_pct']
    price = row['price']

    print(f"\n[{now}] ⚠️  发现目标: {name} ({symbol})")
    print(f"         现价: ¥{price:.2f} | 涨幅: +{change_pct:.2f}%")
    print(f"         {'='*50}")


def run_watcher(scan_interval: int = 60, strategy_limit: int = 10):
    """
    运行监控主循环

    Args:
        scan_interval: 扫描间隔（秒），默认60秒
        strategy_limit: 策略返回的股票数量限制，默认10只
    """
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║           AShare-Sentinel 后台监控启动                      ║
    ╠════════════════════════════════════════════════════════════╣
    ║  监控策略: Strategy B - 冲击涨停                            ║
    ║  扫描频率: {scan_interval} 秒                                            ║
    ║  去重机制: 已启用                                              ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # 初始化策略扫描器
    scanner = StrategyScanner()

    # 已报警的股票代码集合（去重用）
    alerted_stocks = set()

    scan_count = 0

    try:
        while True:
            # 检查是否在交易时间
            if not is_trading_time():
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{now}] 🌙 休市中... 等待开盘", end='\r')
                time.sleep(scan_interval)
                continue

            # 在交易时间内，执行扫描
            scan_count += 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{now}] 🔍 第 {scan_count} 次扫描...")

            try:
                # 获取实时数据
                df = fetch_realtime_data()

                if df is None or df.empty:
                    print("  └─ 暂无数据，等待下次扫描...")
                    time.sleep(scan_interval)
                    continue

                # 运行 Strategy B: 冲击涨停
                candidates = scanner.scan_limit_candidates(df, limit=strategy_limit)

                if candidates.empty:
                    print(f"  └─ 未发现符合条件的股票")
                    time.sleep(scan_interval)
                    continue

                # 检查是否有新股票需要报警
                new_alerts = 0
                for _, row in candidates.iterrows():
                    symbol = row['symbol']

                    if symbol not in alerted_stocks:
                        # 新股票，触发报警
                        new_alerts += 1

                        # 播放声音
                        play_alert_sound()

                        # 打印日志
                        print_alert_log(row)

                        # 发送系统通知
                        title, message = format_alert_message(row)
                        send_notification(title, message)

                        # 加入已报警集合
                        alerted_stocks.add(symbol)

                if new_alerts == 0:
                    print(f"  └─ 监控中... 已跟踪 {len(alerted_stocks)} 只股票")
                else:
                    print(f"  └─ 本次发现 {new_alerts} 只新股票，总计跟踪 {len(alerted_stocks)} 只")

            except Exception as e:
                print(f"  └─ ❌ 扫描出错: {e}")

            # 等待下次扫描
            time.sleep(scan_interval)

    except KeyboardInterrupt:
        print(f"\n\n[{datetime.now().strftime('%H:%M:%S')}] 👋 监控已停止")
        print(f"总计扫描: {scan_count} 次")
        print(f"跟踪股票: {len(alerted_stocks)} 只")


def main():
    """主入口"""
    # 检查 plyer 是否安装
    try:
        import plyer
        has_plyer = True
    except ImportError:
        has_plyer = False
        print("⚠️  提示: plyer 库未安装，系统通知功能将不可用")
        print("   安装命令: pip install plyer")
        print()

    # 启动监控
    run_watcher(scan_interval=60, strategy_limit=10)


if __name__ == "__main__":
    main()
