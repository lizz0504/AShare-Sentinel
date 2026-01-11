# -*- coding: utf-8 -*-
"""
A股短线雷达 - 专业游资风格终端
实时扫描市场机会，打造专业交易体验
"""

import sys
from pathlib import Path
# 将项目根目录添加到Python路径
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from src.data.data_loader import fetch_realtime_data
from src.sentiment.sentiment import MarketAnalyzer
from src.strategies.strategies import StrategyScanner

# 页面配置
st.set_page_config(
    page_title="A股短线雷达",
    page_icon="radar",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS - 游资风格紧凑布局
st.markdown("""
<style>
    /* 隐藏Streamlit默认元素 */
    .stApp #MainMenu {visibility: hidden;}
    .stApp header {visibility: hidden;}
    .stApp footer {visibility: hidden;}

    /* 紧凑布局 - 减少间距 */
    .block-container {
        max-width: 1400px !important;
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    /* 主标题样式 */
    .main-title {
        font-size: 2rem !important;
        font-weight: 800;
        background: linear-gradient(90deg, #ff6b6b, #feca57);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
    }

    /* 数据卡片样式 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }

    /* 策略卡片容器 */
    .strategy-container {
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 0.8rem;
        background: #fafafa;
        height: 100%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* 表格样式优化 */
    .stDataFrame {
        font-size: 0.85rem !important;
    }

    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #ff6b6b, #feca57);
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #1e1e1e;
    }

    /* 刷新按钮样式 */
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)


def load_market_data():
    """
    加载市场数据

    Returns:
        tuple: (原始数据, 情绪报告, 策略结果A, 策略结果B, 策略结果C)
    """
    df = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

    if df.empty:
        return None, None, None, None, None

    analyzer = MarketAnalyzer(df)
    sentiment = analyzer.generate_daily_report()

    scanner = StrategyScanner(df)
    result_a = scanner.scan_volume_breakout(limit=10)
    result_b = scanner.scan_limit_candidates(limit=10)
    result_c = scanner.scan_turtle_stocks(limit=10)

    return df, sentiment, result_a, result_b, result_c


def render_metric_card(title, value, delta, color="blue"):
    """
    渲染数据卡片

    Args:
        title: 标题
        value: 数值
        delta: 变化
        color: 主题颜色
    """
    color_map = {
        "red": "linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)",
        "orange": "linear-gradient(135deg, #feca57 0%, #ff9f43 100%)",
        "blue": "linear-gradient(135deg, #54a0ff 0%, #5f27cd 100%)",
        "green": "linear-gradient(135deg, #1dd1a1 0%, #10ac84 100%)",
        "purple": "linear-gradient(135deg, #5f27cd 0%, #341f97 100%)",
    }

    bg = color_map.get(color, color_map["blue"])

    st.markdown(f"""
    <div style="background: {bg}; border-radius: 12px; padding: 1.2rem; margin: 0.3rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <div style="color: white; font-size: 0.9rem; opacity: 0.9;">{title}</div>
        <div style="color: white; font-size: 1.8rem; font-weight: bold; margin: 0.3rem 0;">{value}</div>
        <div style="color: white; font-size: 0.85rem; opacity: 0.9;">{delta}</div>
    </div>
    """, unsafe_allow_html=True)


def render_progress_table(df, title, emoji, color):
    """
    渲染带进度条的表格

    Args:
        df: 数据DataFrame
        title: 标题
        emoji: 表情符号
        color: 主题颜色
    """
    if df.empty:
        st.info(f"{emoji} {title}: 暂无数据")
        return

    # 处理数据
    display_df = df.copy()
    display_df['url'] = display_df['symbol'].apply(
        lambda x: f"http://quote.eastmoney.com/{x}.html"
    )

    # 格式化数据
    display_df['涨幅'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
    display_df['换手'] = display_df['turnover'].apply(lambda x: f"{x:.2f}%")
    display_df['价格'] = display_df['price'].apply(lambda x: f"¥{x:.2f}")

    # 重命名列
    display_df = display_df[['symbol', 'url', 'name', '涨幅', '换手', '价格']]
    display_df.columns = ['代码', 'url', '名称', '涨幅', '换手', '价格']

    # 配置列
    column_config = {
        '代码': st.column_config.TextColumn(
            '代码',
            width='small'
        ),
        'url': st.column_config.LinkColumn(
            '链接',
            width='small',
            help='点击查看详情',
            display_text='查看'
        ),
        '名称': st.column_config.TextColumn(
            '名称',
            width='medium'
        ),
        '涨幅': st.column_config.TextColumn(
            '涨幅',
            width='small',
            help='涨跌幅'
        ),
        '换手': st.column_config.ProgressColumn(
            '换手率',
            width='medium',
            help='换手率进度条',
            format='%.2f%%',
            min_value=0,
            max_value=20
        ),
        '价格': st.column_config.TextColumn(
            '现价',
            width='small'
        ),
    }

    # 标题
    st.markdown(f"""
    <div style="border-left: 4px solid {color}; padding-left: 10px; margin-bottom: 10px;">
        <span style="font-size: 1.2rem; font-weight: bold;">{emoji} {title}</span>
        <span style="color: #888; font-size: 0.9rem; margin-left: 10px;">(Top 10)</span>
    </div>
    """, unsafe_allow_html=True)

    # 显示表格
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=420
    )

    st.caption(f"共 {len(df)} 只股票 | 点击代码查看详情")


def render_market_overview(sentiment):
    """
    渲染市场概览

    Args:
        sentiment: 情绪报告
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        temp = sentiment['market_temperature']['score']
        status = sentiment['market_temperature']['status']
        render_metric_card("市场温度", f"{temp:.0f}", status, "red")

    with col2:
        up = sentiment['summary']['up_count']
        down = sentiment['summary']['down_count']
        ratio = sentiment['summary']['up_ratio']
        render_metric_card("涨跌分布", f"{up}:{down}", f"上涨 {ratio:.1f}%", "orange")

    with col3:
        limit_up = sentiment['limit_performance']['limit_up']
        limit_down = sentiment['limit_performance']['limit_down']
        render_metric_card("涨停家数", f"{limit_up}", f"跌停 {limit_down}", "blue")

    with col4:
        median = sentiment['price_change_stats']['median_change']
        mean = sentiment['price_change_stats']['mean_change']
        color = "red" if median >= 0 else "green"
        render_metric_card("中位数", f"{median:+.2f}%", f"平均 {mean:+.2f}%", color)

    # 温度进度条
    st.progress(temp / 100)
    st.caption(f"市场热度: {temp:.0f}/100 ({status})")


def render_trader_room(result_a, result_b, result_c):
    """
    渲染游资作战室

    Args:
        result_a: 策略A结果
        result_b: 策略B结果
        result_c: 策略C结果
    """
    col_b, col_a, col_c = st.columns(3)

    with col_b:
        render_progress_table(result_b, "冲击涨停", "🚀", "#ff6b6b")

    with col_a:
        render_progress_table(result_a, "强势中军", "🔥", "#feca57")

    with col_c:
        render_progress_table(result_c, "低位潜伏", "👀", "#54a0ff")


def main():
    """主应用"""

    # 顶部标题栏
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.markdown('<h1 class="main-title">🎯 A股短线雷达</h1>', unsafe_allow_html=True)

    with col_right:
        if st.button("🔄 刷新数据", type="primary", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # 加载数据
    with st.spinner("🔍 正在扫描全市场，分析5000+只股票..."):
        df, sentiment, result_a, result_b, result_c = load_market_data()

    if df is None:
        st.error("❌ 无法获取市场数据，请检查网络连接后刷新")
        st.stop()

    # 市场概览
    st.markdown("### 📊 市场概览")
    render_market_overview(sentiment)

    st.markdown("---")

    # 游资作战室
    st.markdown("### 🎯 机会扫描 (Top 10)")
    render_trader_room(result_a, result_b, result_c)

    # 底部信息
    st.markdown("---")
    col_l, col_m, col_r = st.columns([2, 1, 1])

    with col_l:
        st.caption(f"📡 数据来源: 东方财富 | 扫描: {len(df)}只股票 | 机会: {len(result_a)+len(result_b)+len(result_c)}只")

    with col_m:
        temp_level = sentiment['market_temperature']['level']
        if temp_level == 'scorching':
            st.warning("⚠️ 市场过热，注意风险")
        elif temp_level == 'frozen':
            st.info("❄️ 市场冰点，多看少动")

    with col_r:
        st.caption(f"⏰ {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # 隐蔽的自动刷新选项
    with st.expander("⚙️ 设置"):
        auto_refresh = st.checkbox("自动刷新 (每60秒)", value=False)
        if auto_refresh:
            st.toast("🔄 自动刷新已启用", icon="🔄")
            import time
            time.sleep(60)
            st.rerun()


if __name__ == "__main__":
    main()
