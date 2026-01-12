# -*- coding: utf-8 -*-
"""
AShare-Sentinel - 系统健康检查脚本
逐一测试各个模块，确保后端系统健康
"""

import sys
import os
from pathlib import Path

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        # 如果修改失败，继续执行（可能在某些 IDE 中）
        pass

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_header(step: str, title: str):
    """打印测试步骤标题"""
    print(f"\n{'='*60}")
    print(f"  {step}: {title}")
    print(f"{'='*60}")


def print_success(message: str):
    """打印成功消息"""
    print(f"✅ {message}")


def print_error(message: str, error: Exception = None):
    """打印错误消息"""
    print(f"❌ {message}")
    if error:
        print(f"   Error: {error}")
    print("\n请修复此问题后重新运行检查")
    return False


def check_environment():
    """Step 1: 环境与密钥检查"""
    print_header("Step 1", "环境与密钥检查")

    try:
        # 检查 .env 文件
        env_path = project_root / '.env'
        if not env_path.exists():
            return print_error(".env 文件不存在")

        print_success(".env 文件存在")

        # 检查 API Key 是否加载
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return print_error("DASHSCOPE_API_KEY 未加载")

        # 隐藏中间部分，只显示前后几位
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "sk-..."
        print_success(f"DASHSCOPE_API_KEY 已加载 ({masked_key})")

        # 检查数据库文件
        db_path = project_root / 'sentinel.db'
        if not db_path.exists():
            print(f"⚠️  sentinel.db 不存在 (首次运行会自动创建)")
        else:
            print_success("sentinel.db 文件存在")

        return True

    except Exception as e:
        return print_error("环境检查失败", e)


def check_database():
    """Step 2: 数据库读写测试"""
    print_header("Step 2", "数据库读写测试")

    try:
        from src.database import init_db, save_analysis, get_analysis_today, get_latest_analysis

        # 初始化数据库
        init_db()
        print_success("数据库初始化成功")

        # 写入测试记录
        test_data = {
            'symbol': 'TEST001',
            'name': '测试股票',
            'price': 100.0,
            'change_pct': 5.0,
            'turnover': 10.0,
            'volume_ratio': 1.5,
            'sector': '测试板块',
            'strategy': '测试策略',
            'ai_score': 85,
            'ai_reason': '测试理由',
            'ai_suggestion': '买入'
        }

        save_analysis(test_data)
        print_success("数据库写入测试成功")

        # 读取测试记录
        latest = get_latest_analysis('TEST001')
        if latest and latest['symbol'] == 'TEST001':
            print_success("数据库读取测试成功")
            return True
        else:
            return print_error("数据库读取测试失败: 未找到测试记录")

    except Exception as e:
        return print_error("数据库测试失败", e)


def check_data_loader():
    """Step 3: 数据源测试"""
    print_header("Step 3", "数据源测试 (Data Loader)")

    try:
        from src.data.data_loader import get_stock_sector

        # 测试获取贵州茅台板块
        sector = get_stock_sector('600519')

        if sector and sector != "未知":
            print_success(f"贵州茅台板块获取成功: {sector}")
            return True
        else:
            return print_error("板块获取失败: 返回 '未知'")

    except Exception as e:
        return print_error("数据源测试失败", e)


def check_ai_agent():
    """Step 4: AI 连接测试"""
    print_header("Step 4", "AI 连接测试 (Qwen)")

    try:
        from ai_agent import AIStockAnalyzer

        # 初始化 AI 分析器
        analyzer = AIStockAnalyzer()
        print_success("AI 分析器初始化成功")

        # 使用 Mock 数据测试
        mock_data = {
            'symbol': '300059',
            'name': '东方财富',
            'price': 28.50,
            'change_pct': 10.0,
            'turnover': 12.3,
            'volume_ratio': 2.0,
            'sector': '证券'
        }

        print("正在测试 AI 分析...")
        result = analyzer.analyze_stock(mock_data, strategy_name="测试策略")

        # 验证返回结果
        if not isinstance(result, dict):
            return print_error(f"AI 返回类型错误: {type(result)}")

        required_keys = {'score', 'reason', 'suggestion'}
        missing_keys = required_keys - set(result.keys())

        if missing_keys:
            return print_error(f"AI 返回 JSON 缺少字段: {missing_keys}")

        if result['score'] <= 0:
            return print_error(f"AI 分析失败，返回 score: {result['score']}")

        print_success(f"AI (Qwen) 连接成功 - 评分: {result['score']}/100, 建议: {result['suggestion']}")
        return True

    except Exception as e:
        return print_error("AI 连接测试失败", e)


def check_auto_analysis():
    """Step 5: 综合流程测试"""
    print_header("Step 5", "综合流程测试 (Module Import)")

    try:
        # 尝试导入模块
        import auto_analysis
        print_success("auto_analysis 模块导入成功")

        # 检查关键类是否存在
        if hasattr(auto_analysis, 'AutoAnalysisEngine'):
            print_success("AutoAnalysisEngine 类存在")
            return True
        else:
            return print_error("AutoAnalysisEngine 类不存在")

    except ImportError as e:
        return print_error("auto_analysis 模块导入失败", e)
    except Exception as e:
        return print_error("综合流程测试失败", e)


def main():
    """主检查流程"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           AShare-Sentinel 系统健康检查                      ║
    ╠════════════════════════════════════════════════════════════╣
    ║  逐一测试各个模块，确保后端系统健康                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    results = []

    # 依次执行检查
    results.append(("环境检查", check_environment()))
    if not results[-1][1]:
        return  # 环境检查失败则停止

    results.append(("数据库", check_database()))
    if not results[-1][1]:
        return  # 数据库检查失败则停止

    results.append(("数据源", check_data_loader()))
    if not results[-1][1]:
        # 数据源检查失败不停止，继续测试其他模块
        pass

    results.append(("AI Agent", check_ai_agent()))
    if not results[-1][1]:
        # AI 检查失败不停止，继续测试其他模块
        pass

    results.append(("自动化分析", check_auto_analysis()))

    # 打印最终结果
    print(f"\n{'='*60}")
    print("  检查结果汇总")
    print(f"{'='*60}")

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status:10s} {name}")

    # 统计
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 项通过")

    if passed_count == total_count:
        print("\n🎉 所有检查通过！系统健康，可以开始使用。")
    else:
        print("\n⚠️  部分检查未通过，请修复后重试。")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
