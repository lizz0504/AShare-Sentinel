# -*- coding: utf-8 -*-
"""
AShare-Sentinel - AI 分析模块 (量价时空四维评分体系)
使用阿里云通义千问 (Qwen) 进行股票深度分析
通过 OpenAI 兼容接口调用

升级版：采用"量价时空"四维评分体系，专为 A 股短线 (T+1) 博弈环境设计
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
    """AI 股票分析器 (量价时空四维评分体系)"""

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

    def generate_analysis_prompt(self, stock_data: Dict[str, Any], indicators: Dict[str, Any]) -> tuple:
        """
        生成 AI 分析的 Prompt（System + User）

        Args:
            stock_data: 股票基础数据
            indicators: 技术指标数据

        Returns:
            tuple: (system_message, user_message)
        """
        symbol = stock_data.get("symbol", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        turnover = stock_data.get("turnover", 0)
        volume_ratio = stock_data.get("volume_ratio", 1.0)
        sector = stock_data.get("sector", "未知")
        strategy_name = stock_data.get("strategy", "通用策略")

        # 从技术指标中提取数据
        ma5 = indicators.get('ma5')
        ma10 = indicators.get('ma10')
        ma20 = indicators.get('ma20')
        ma60 = indicators.get('ma60')
        calc_volume_ratio = indicators.get('volume_ratio')
        trend_status = indicators.get('trend_status', '未知')
        volume_status = indicators.get('volume_status', '未知')

        # 生成位置描述
        from src.data.data_loader import generate_position_desc
        position_desc = generate_position_desc(price, indicators)

        # ========== System Prompt (角色设定) ==========
        system_message = """你是一位拥有 15 年经验的 A 股游资操盘手，擅长通过量价关系捕捉短线爆发机会。

你必须严格遵守以下"量价时空"四维评分体系：

【评分规则】总分 100 分
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ 量能 (Volume, 40 分) - 核心权重
   ✓ 放量突破：量比 1.5-3.0，得分 35-40 分
   ✓ 温和放量：量比 1.2-1.5，得分 25-34 分
   ✗ 缩量上涨：量比 < 1.0，上限锁死 70 分！
   ✗ 天量：量比 > 3.0，主力出货嫌疑，扣 10 分

2️⃣ 趋势 (Trend, 30 分)
   ✓ 多头排列：价格在 MA5/MA10/MA20 之上，得分 25-30 分
   ✓ 中期上涨：站在 MA5 和 MA20 之上，得分 20-24 分
   ✓ 短期强势：仅站上 MA5，得分 15-19 分
   ✗ 长期下降：在 MA60 下方，扣 10 分

3️⃣ 形态 (Pattern, 20 分)
   加分项（各 +5 分）：
   • 反包：吞没昨日阴线，主力吸筹
   • 突破平台：突破前高压力位
   • N 字反转：二波启动确认

   扣分项（各 -5 分）：
   • 长上影线：上方抛压重
   • 长下影线：支撑不稳
   • 高开低走：诱多陷阱

4️⃣ 情绪 (Sentiment, 10 分)
   ✓ 主流热点：当日领涨板块，得 8-10 分
   ✓ 跟风上涨：非主流板块，得 3-7 分
   ✗ 孤股上涨：无板块配合，得 0-2 分

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【输出要求】
1. 评分必须精确到整数
2. 分析理由要犀利，直接指出"核心亮点"或"逻辑硬伤"
3. 严禁模棱两可的废话（如"谨慎关注""建议观望"）
4. 如果有明显风险，必须明确指出

【返回格式】纯 JSON（不要包含任何 markdown 标记）
{
    "score": 0-100 的整数评分,
    "reason": "30 字以内的犀利分析",
    "suggestion": "强力买入 / 买入 / 观望 / 放弃"
}"""

        # ========== User Prompt (具体分析任务) ==========
        user_message = f"""【标的】{name} ({symbol})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【核心数据】现价: ¥{price:.2f} (涨幅 {change_pct:+.2f}%)
换手: {turnover:.2f}%  |  量比: {volume_ratio:.2f}
板块: {sector}  |  策略: {strategy_name}

【均线系统】MA5: {ma5 if ma5 else 'N/A'}  |  MA20: {ma20 if ma20 else 'N/A'}  |  MA60: {ma60 if ma60 else 'N/A'}
趋势状态: {trend_status}
量能状态: {volume_status} (5日均量比: {calc_volume_ratio if calc_volume_ratio else 'N/A'})

【位置描述】{position_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【请按四维体系打分并给出操作建议】

特别注意：
- 如果是缩量上涨，评分不得超过 75 分
- 如果上方有 MA60 压制，评分不得超过 85 分
- 放量突破平台且站上所有均线，可给 90+ 分

请以纯 JSON 格式返回分析结果（不要包含 ```json 标记）：
{{
    "score": <0-100整数>,
    "reason": "<30字犀利分析，直指核心亮点或硬伤>",
    "suggestion": "<强力买入/买入/观望/放弃>"
}}"""

        return system_message, user_message

    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        strategy_name: str = "通用策略"
    ) -> Dict[str, Any]:
        """
        分析单只股票（使用量价时空四维评分体系）

        Args:
            stock_data: 股票数据字典，包含 {symbol, name, price, change_pct, turnover, volume_ratio, sector}
            strategy_name: 策略名称，用于上下文

        Returns:
            Dict: {
                "score": int,        # 0-100 打分
                "reason": str,       # 分析理由 (30字以内)
                "suggestion": str    # "强力买入" / "买入" / "观望" / "放弃"
            }
        """
        symbol = stock_data.get("symbol", "")
        name = stock_data.get("name", "")
        price = stock_data.get("price", 0)
        change_pct = stock_data.get("change_pct", 0)
        turnover = stock_data.get("turnover", 0)
        volume_ratio = stock_data.get("volume_ratio", 1.0)
        sector = stock_data.get("sector", "未知")

        # 计算技术指标
        from src.data.data_loader import calculate_technical_indicators
        indicators = calculate_technical_indicators(symbol, price, volume_ratio * 10000)  # 转换为手

        # 添加策略名称到 stock_data
        stock_data['strategy'] = strategy_name

        # 生成 Prompt
        system_message, user_message = self.generate_analysis_prompt(stock_data, indicators)

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

            # 规范化建议
            valid_suggestions = ["强力买入", "买入", "观望", "放弃"]
            if result["suggestion"] not in valid_suggestions:
                if result["suggestion"] in ["买入", "观察"]:
                    result["suggestion"] = "买入" if result["suggestion"] == "买入" else "观望"
                else:
                    result["suggestion"] = "观望"

            # 根据评分自动调整建议
            if result["score"] >= 90 and result["suggestion"] == "买入":
                result["suggestion"] = "强力买入"
            elif result["score"] < 60 and result["suggestion"] in ["强力买入", "买入"]:
                result["suggestion"] = "观望"

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
            "suggestion": "观望"
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
    print("AI 股票分析器测试 (量价时空四维评分体系)")
    print("=" * 60)

    try:
        # 测试数据
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
