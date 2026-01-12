# -*- coding: utf-8 -*-
"""
AShare-Sentinel - AI 分析模块
使用阿里云通义千问 (Qwen) 进行股票深度分析
通过 OpenAI 兼容接口调用
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# 设置控制台编码为 UTF-8 (Windows 兼容)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    raise ImportError(
        "请先安装 AI 依赖: pip install openai python-dotenv"
    )

# 加载环境变量
load_dotenv()


class AIStockAnalyzer:
    """AI 股票分析器 (基于通义千问 OpenAI 兼容接口)"""

    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = "qwen-plus"):
        """
        初始化 AI 分析器

        Args:
            api_key: 阿里云 DashScope API Key，默认从环境变量读取
            base_url: API 基础 URL，默认为通义千问兼容接口
            model_name: 模型名称，默认 qwen-plus
                       可选: qwen-turbo, qwen-plus, qwen-max, qwen-flash
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "未找到 DASHSCOPE_API_KEY！\n"
                "请在 .env 文件中设置: DASHSCOPE_API_KEY=your_key_here\n"
                "或访问: https://dashscope.console.aliyun.com/apiKey 获取"
            )

        # 通义千问 OpenAI 兼容接口地址
        self.base_url = base_url or os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        self.model_name = model_name

    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        strategy_name: str = "通用策略"
    ) -> Dict[str, Any]:
        """
        分析单只股票

        Args:
            stock_data: 股票数据字典，包含 {symbol, name, price, change_pct, turnover, volume_ratio, sector}
            strategy_name: 策略名称，用于上下文

        Returns:
            Dict: {
                "score": int,        # 0-100 打分
                "reason": str,       # 分析理由 (50字以内)
                "suggestion": str    # "买入" / "观察" / "放弃"
            }
        """
        symbol = stock_data.get("symbol", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        turnover = stock_data.get("turnover", 0)
        volume_ratio = stock_data.get("volume_ratio", 1.0)
        sector = stock_data.get("sector", "未知")

        # System prompt
        system_message = "你是一位犀利的A股游资操盘手。请根据量价数据分析主力意图。"

        # User prompt
        user_message = f"""请分析这只股票的量价关系和主力意图。

股票信息:
- 代码: {symbol}
- 名称: {name}
- 现价: ¥{price:.2f}
- 涨幅: {change_pct:+.2f}%
- 换手率: {turnover:.2f}%
- 量比: {volume_ratio:.2f}
- 板块: {sector}
- 策略: {strategy_name}

请以纯 JSON 格式返回分析结果（不要包含 markdown 代码块标记），必须包含以下字段:
{{
    "score": <0-100的打分>,
    "reason": "<50字以内的分析理由>",
    "suggestion": "<买入/观察/放弃>"
}}

评分标准:
- 90-100: 强力买入，主力意图明显
- 70-89: 可以关注，有启动迹象
- 50-69: 观望，信号不明
- 0-49: 放弃，风险大于机会
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500,
            )

            # 获取响应内容
            content = response.choices[0].message.content

            # 清理可能的 markdown 标记
            content = content.strip()
            content = content.replace("```json", "").replace("```", "").strip()

            # 解析 JSON
            result = json.loads(content)

            # 验证返回的数据格式
            required_keys = {"score", "reason", "suggestion"}
            if not all(key in result for key in required_keys):
                raise ValueError("AI 返回的 JSON 缺少必要字段")

            # 验证取值范围
            result["score"] = max(0, min(100, int(result["score"])))
            if result["suggestion"] not in ["买入", "观察", "放弃"]:
                result["suggestion"] = "观察"

            return result

        except json.JSONDecodeError as e:
            print(f"[AI分析失败] JSON解析错误: {e}")
            print(f"原始响应: {content if 'content' in locals() else 'N/A'}")
            return self._default_result()

        except Exception as e:
            print(f"[AI分析失败] {symbol} {name}: {e}")
            return self._default_result()

    def _default_result(self) -> Dict[str, Any]:
        """返回默认结果（分析失败时使用）"""
        return {
            "score": 0,
            "reason": "AI分析暂时不可用，请稍后重试",
            "suggestion": "观察"
        }

    def analyze_batch(
        self,
        stocks: list[Dict[str, Any]],
        strategy_name: str = "通用策略",
        max_concurrent: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量分析股票

        Args:
            stocks: 股票列表，每个元素包含 {symbol, name, price, change_pct, turnover, volume_ratio, sector}
            strategy_name: 策略名称
            max_concurrent: 最大并发数 (默认 5，避免 API 限流)

        Returns:
            Dict: {symbol: analysis_result}
        """
        results = {}

        for stock in stocks:
            symbol = stock.get("symbol")
            if not symbol:
                continue

            result = self.analyze_stock(stock, strategy_name)
            results[symbol] = result

        return results


def analyze_stock(
    stock_data: Dict[str, Any],
    strategy_name: str = "通用策略"
) -> Dict[str, Any]:
    """
    便捷函数: 分析单只股票

    Args:
        stock_data: 股票数据字典
        strategy_name: 策略名称

    Returns:
        Dict: 分析结果
    """
    analyzer = AIStockAnalyzer()
    return analyzer.analyze_stock(stock_data, strategy_name)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("AI 股票分析器测试 (通义千问 OpenAI 接口)")
    print("=" * 60)

    try:
        # 测试数据: 东方财富
        test_stock = {
            "symbol": "300059",
            "name": "东方财富",
            "price": 28.50,
            "change_pct": 8.5,
            "turnover": 12.3,
            "volume_ratio": 2.5,
            "sector": "证券"
        }

        print(f"\n正在分析: {test_stock['name']} ({test_stock['symbol']})")
        print(f"现价: ¥{test_stock['price']:.2f} | 涨幅: +{test_stock['change_pct']:.2f}%")
        print(f"策略: 冲击涨停")

        result = analyze_stock(test_stock, strategy_name="冲击涨停")

        print("\n" + "=" * 60)
        print("AI 分析结果:")
        print("=" * 60)
        print(f"评分: {result['score']}/100")
        print(f"建议: {result['suggestion']}")
        print(f"理由: {result['reason']}")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        print("\n请确保:")
        print("1. 已安装依赖: pip install openai python-dotenv")
        print("2. 已创建 .env 文件并设置 DASHSCOPE_API_KEY")
        print("3. API Key 有效且有配额")
        print("\n获取 API Key: https://dashscope.console.aliyun.com/apiKey")
