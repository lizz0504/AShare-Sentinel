# -*- coding: utf-8 -*-
"""
模拟盘交易管理器
实现自动买入、持仓管理、交易记录等功能
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import PortfolioConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioManager:
    """
    模拟盘交易管理器

    功能：
    - 管理账户资金和持仓
    - 执行买入操作（带风控检查）
    - 记录所有交易历史
    - 持久化到 portfolio.json
    """

    def __init__(self, portfolio_file: Optional[str] = None):
        """
        初始化交易管理器

        Args:
            portfolio_file: portfolio.json 文件路径，默认为项目根目录下的 portfolio.json
        """
        if portfolio_file is None:
            # 默认路径：项目根目录 / portfolio.json
            project_root = Path(__file__).parent.parent.parent
            portfolio_file = project_root / "portfolio.json"

        self.portfolio_file = Path(portfolio_file)
        self.data = self._load_or_create()

        logger.info(f"交易管理器初始化完成")
        logger.info(f"  账户资金: ¥{self.data['cash']:,.2f}")
        logger.info(f"  持仓数量: {len(self.data['positions'])} 只")
        logger.info(f"  交易记录: {len(self.data['transactions'])} 笔")

    def _load_or_create(self) -> Dict:
        """
        加载或创建账户数据

        Returns:
            Dict: 账户数据字典
        """
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 验证数据结构
                required_keys = ['cash', 'positions', 'transactions']
                for key in required_keys:
                    if key not in data:
                        logger.warning(f"账户数据缺少 {key} 字段，使用默认值")
                        data[key] = [] if key != 'cash' else PortfolioConfig.INITIAL_CASH

                logger.info(f"从 {self.portfolio_file} 加载账户数据")
                return data

            except Exception as e:
                logger.error(f"加载账户数据失败: {e}，将创建新账户")
                return self._create_default_account()
        else:
            logger.info(f"账户文件不存在，创建新账户: {self.portfolio_file}")
            return self._create_default_account()

    def _create_default_account(self) -> Dict:
        """
        创建默认账户

        Returns:
            Dict: 默认账户数据
        """
        default_account = {
            "cash": PortfolioConfig.INITIAL_CASH,
            "positions": [],
            "transactions": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 保存到文件
        self._save(default_account)
        return default_account

    def _save(self, data: Optional[Dict] = None) -> None:
        """
        保存账户数据到文件

        Args:
            data: 要保存的数据，默认保存 self.data
        """
        if data is None:
            data = self.data

        # 更新时间戳
        data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"账户数据已保存到 {self.portfolio_file}")
        except Exception as e:
            logger.error(f"保存账户数据失败: {e}")

    def buy_stock(self, symbol: str, name: str, price: float, date: str) -> Tuple[bool, str]:
        """
        买入股票（带风控检查）

        Args:
            symbol: 股票代码
            name: 股票名称
            price: 当前价格
            date: 交易日期

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        # ========== 风控检查 ==========

        # 1. 检查是否已持仓
        for position in self.data['positions']:
            if position['symbol'] == symbol:
                msg = f"已持仓 {symbol} {name}，当前持仓 {position['shares']} 股"
                logger.warning(f"❌ [交易失败] {msg}")
                return False, "已持仓"

        # 2. 计算买入数量（必须是100的倍数）
        target_amount = PortfolioConfig.TRADE_AMOUNT_PER_POS
        shares = int(target_amount / price / 100) * 100

        if shares == 0:
            msg = f"资金不足，无法买入 100 股 (当前价格 ¥{price:.2f})"
            logger.warning(f"❌ [交易失败] {msg}")
            return False, "资金不足"

        # 3. 检查资金是否充足
        cost = shares * price
        if self.data['cash'] < cost:
            shortage = cost - self.data['cash']
            msg = f"资金不足 (需要 ¥{cost:,.2f}，缺口 ¥{shortage:,.2f})"
            logger.warning(f"❌ [交易失败] {msg}")
            return False, "资金不足"

        # ========== 执行买入 ==========

        # 扣除资金
        self.data['cash'] -= cost

        # 添加持仓
        position = {
            "symbol": symbol,
            "name": name,
            "shares": shares,
            "avg_price": price,
            "current_price": price,
            "cost": cost,
            "market_value": cost,
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "buy_date": date,
            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.data['positions'].append(position)

        # 记录交易
        transaction = {
            "type": "buy",
            "symbol": symbol,
            "name": name,
            "shares": shares,
            "price": price,
            "amount": cost,
            "date": date,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": f"触发三连榜自动买入"
        }

        self.data['transactions'].append(transaction)

        # 持久化到文件
        self._save()

        # 记录日志
        logger.info(f"🚀 [买入成功] {symbol} {name}")
        logger.info(f"  数量: {shares} 股 × ¥{price:.2f} = ¥{cost:,.2f}")
        logger.info(f"  剩余资金: ¥{self.data['cash']:,.2f}")
        logger.info(f"  持仓数量: {len(self.data['positions'])} 只")

        return True, "买入成功"

    def get_positions(self) -> List[Dict]:
        """
        获取所有持仓

        Returns:
            List[Dict]: 持仓列表
        """
        return self.data.get('positions', [])

    def get_cash(self) -> float:
        """
        获取当前可用资金

        Returns:
            float: 可用资金
        """
        return self.data.get('cash', 0.0)

    def get_transactions(self, limit: int = 10) -> List[Dict]:
        """
        获取最近交易记录

        Args:
            limit: 返回最近N笔交易

        Returns:
            List[Dict]: 交易记录列表（按时间倒序）
        """
        transactions = self.data.get('transactions', [])
        # 返回最近的交易（倒序）
        return list(reversed(transactions[-limit:]))

    def get_summary(self) -> Dict:
        """
        获取账户摘要

        Returns:
            Dict: 账户摘要信息
        """
        positions = self.data.get('positions', [])
        total_cost = sum(p['cost'] for p in positions)
        total_market_value = sum(p['market_value'] for p in positions)
        total_profit_loss = sum(p.get('profit_loss', 0) for p in positions)

        return {
            "cash": self.data['cash'],
            "positions_count": len(positions),
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "total_profit_loss": total_profit_loss,
            "total_assets": self.data['cash'] + total_market_value,
            "transactions_count": len(self.data.get('transactions', []))
        }

    def update_prices(self, price_dict: Dict[str, float]) -> None:
        """
        批量更新持仓价格（用于市值计算）

        Args:
            price_dict: {symbol: current_price} 字典
        """
        for position in self.data['positions']:
            symbol = position['symbol']
            if symbol in price_dict:
                old_price = position['current_price']
                position['current_price'] = price_dict[symbol]
                position['market_value'] = position['shares'] * price_dict[symbol]
                position['profit_loss'] = position['market_value'] - position['cost']
                position['profit_loss_pct'] = (position['profit_loss'] / position['cost']) * 100 if position['cost'] > 0 else 0

                if old_price != price_dict[symbol]:
                    logger.debug(f"更新价格: {symbol} ¥{old_price:.2f} -> ¥{price_dict[symbol]:.2f}")

        self._save()


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("Portfolio Manager 测试")
    print("="*60)

    manager = PortfolioManager()

    # 测试买入
    print("\n测试买入功能:")
    success, msg = manager.buy_stock(
        symbol="000001",
        name="平安银行",
        price=10.50,
        date="2026-01-13"
    )
    print(f"买入结果: {success}, {msg}")

    # 显示摘要
    print("\n账户摘要:")
    summary = manager.get_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: ¥{value:,.2f}")
        else:
            print(f"  {key}: {value}")

    print("\n测试完成！")
