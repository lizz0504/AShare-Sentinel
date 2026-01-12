# -*- coding: utf-8 -*-
"""
A股短线雷达 - 专业量化交易终端
设计原则：专业、易懂、实用
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from src.data.data_loader import fetch_realtime_data, clear_cache
from src.sentiment.sentiment import MarketAnalyzer
from src.strategies.strategies import StrategyScanner
from src.database import init_db, get_records, get_records_by_status, update_status, get_statistics

# =============================================================================
# 页面配置
# =============================================================================
st.set_page_config(
    page_title="A股短线雷达",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# =============================================================================
# 自定义CSS - 专业证券软件风格
# =============================================================================
st.markdown("""
<style>
    /* 隐藏Streamlit默认元素 */
    .stApp #MainMenu {visibility: hidden;}
    .stApp header {visibility: hidden;}
    .stApp footer {visibility: hidden;}

    /* 主体样式 */
    .main .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }

    /* ========== 颜色定义 ========== */
    :root {
        --primary-color: #1890ff;
        --success-color: #52c41a;
        --warning-color: #faad14;
        --danger-color: #ff4d4f;
        --text-primary: #262626;
        --text-secondary: #595959;
        --text-muted: #8c8c8c;
        --border-color: #d9d9d9;
        --bg-light: #fafafa;
        --bg-white: #ffffff;
    }

    /* ========== 标题样式 ========== */
    .app-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .app-subtitle {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }

    /* ========== 指标卡片样式 ========== */
    .metric-container {
        background: var(--bg-white);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 1rem;
    }

    .metric-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }

    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .metric-value.positive {
        color: var(--danger-color);
    }

    .metric-value.negative {
        color: var(--success-color);
    }

    /* ========== 数据表格样式 ========== */
    .data-table-container {
        background: var(--bg-white);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        overflow: hidden;
    }

    .table-header {
        background: var(--bg-light);
        padding: 0.75rem 1rem;
        font-weight: 600;
        font-size: 0.875rem;
        color: var(--text-primary);
        border-bottom: 1px solid var(--border-color);
    }

    /* ========== 信号卡片样式 ========== */
    .signal-card {
        background: var(--bg-white);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        transition: box-shadow 0.2s;
    }

    .signal-card:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }

    .signal-stock {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .signal-stock .code {
        color: var(--primary-color);
        font-family: 'Consolas', monospace;
    }

    .signal-score {
        font-size: 1.25rem;
        font-weight: 700;
        font-family: 'Consolas', monospace;
    }

    .signal-score.high {
        color: var(--danger-color);
    }

    .signal-score.medium {
        color: var(--warning-color);
    }

    .signal-score.low {
        color: var(--success-color);
    }

    /* ========== 按钮样式 ========== */
    .stButton > button {
        border-radius: 4px;
        border: 1px solid var(--border-color);
        background: var(--bg-white);
        color: var(--text-primary);
        font-size: 0.875rem;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
    }

    .stButton > button[kind="primary"] {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: white;
    }

    .stButton > button[kind="primary"]:hover {
        background: #40a9ff;
        border-color: #40a9ff;
    }

    /* ========== Tab样式 ========== */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 2px solid var(--border-color);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 0.75rem 1.5rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-secondary);
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--primary-color);
        border-bottom: 2px solid var(--primary-color);
        margin-bottom: -2px;
    }

    /* ========== Expander样式 ========== */
    .streamlit-expanderHeader {
        background: var(--bg-white);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .streamlit-expanderContent {
        background: var(--bg-light);
        border: 1px solid var(--border-color);
        border-top: none;
        border-radius: 0 0 6px 6px;
    }

    /* ========== 侧边栏样式 ========== */
    .css-1d391kg {
        background: var(--bg-white);
        border-right: 1px solid var(--border-color);
    }

    /* ========== 进度条样式 ========== */
    .stProgress > div > div > div > div {
        background: var(--primary-color);
    }

    /* ========== 工具类 ========== */
    .text-success { color: var(--success-color); }
    .text-warning { color: var(--warning-color); }
    .text-danger { color: var(--danger-color); }
    .text-primary { color: var(--primary-color); }
    .text-muted { color: var(--text-muted); }

    .font-mono {
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    }

    .badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 3px;
        background: var(--bg-light);
        color: var(--text-secondary);
    }

    .badge-success {
        background: #f6ffed;
        color: var(--success-color);
        border: 1px solid #b7eb8f;
    }

    .badge-warning {
        background: #fffbe6;
        color: var(--warning-color);
        border: 1px solid #ffe58f;
    }

    .badge-danger {
        background: #fff1f0;
        color: var(--danger-color);
        border: 1px solid #ffccc7;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# 数据加载函数
# =============================================================================
def load_market_data():
    """加载市场数据"""
    try:
        result = fetch_realtime_data(filter_st=True, use_cache=True, validate=True)

        # 处理返回值，确保是元组格式
        if isinstance(result, tuple):
            if len(result) == 2:
                df, update_time = result
            else:
                st.error(f"返回值格式错误: 期望2个值，实际{len(result)}个")
                return None, None, None, None, None, ""
        else:
            st.error(f"返回值类型错误: {type(result)}")
            return None, None, None, None, None, ""

        # 调试信息
        if df is None:
            st.error("调试：df is None")
            return None, None, None, None, None, ""

        if df.empty:
            st.error(f"调试：df.empty=True, len={len(df)}")
            return None, None, None, None, None, ""

        st.info(f"调试：成功加载 {len(df)} 只股票")

        analyzer = MarketAnalyzer(df)
        sentiment = analyzer.generate_daily_report()

        scanner = StrategyScanner(df)
        result_a = scanner.scan_volume_breakout(limit=10)
        result_b = scanner.scan_limit_candidates(limit=10)
        result_c = scanner.scan_turtle_stocks(limit=10)

        return df, sentiment, result_a, result_b, result_c, update_time
    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None, None, None, ""


# =============================================================================
# 渲染组件
# =============================================================================
def render_metric_card(label, value, delta=None, delta_color="normal"):
    """渲染指标卡片"""
    delta_html = ""
    if delta:
        color_class = "text-danger" if delta_color == "normal" and str(delta).startswith('+') else "text-success"
        if delta_color == "inverse":
            color_class = "text-success" if str(delta).startswith('+') else "text-danger"
        delta_html = f'<div class="metric-label {color_class}">{delta}</div>'

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_strategy_table(df, title):
    """渲染策略表格"""
    if df.empty:
        st.info(f"{title}：暂无数据")
        return

    display_df = df.copy()
    display_df['链接'] = display_df['symbol'].apply(
        lambda x: f"http://quote.eastmoney.com/{x}.html"
    )

    # 格式化列 - 直接使用数值，让Streamlit自动格式化
    display_df['代码'] = display_df['symbol']
    display_df['名称'] = display_df['name']
    display_df['涨幅%'] = display_df['change_pct']
    display_df['换手%'] = display_df['turnover']
    display_df['现价'] = display_df['price']

    display_df = display_df[['代码', '名称', '现价', '涨幅%', '换手%', '链接']]

    st.markdown(f"**{title}**")

    # 使用st.column_config来自定义列样式，添加涨跌幅颜色支持
    st.dataframe(
        display_df,
        column_config={
            "代码": st.column_config.TextColumn("代码", width="medium"),
            "名称": st.column_config.TextColumn("名称", width="short"),
            "现价": st.column_config.NumberColumn("现价", format="¥%.2f", width="small"),
            "涨幅%": st.column_config.NumberColumn(
                "涨幅%",
                format="%.2f%%",
                width="small",
                help="涨跌幅百分比"
            ),
            "换手%": st.column_config.NumberColumn(
                "换手%",
                format="%.2f%%",
                width="small"
            ),
            "链接": st.column_config.LinkColumn("详情", display_text="查看"),
        },
        hide_index=True,
        height=300,
        use_container_width=True
    )


def render_signal_card(record):
    """渲染信号卡片"""
    score = record.get('ai_score', 0)
    symbol = record.get('symbol', '')
    name = record.get('name', '')
    suggestion = record.get('ai_suggestion', '')
    ai_reason = record.get('ai_reason', '')

    # 评分等级
    if score >= 85:
        score_class = "high"
        badge_class = "badge-danger"
    elif score >= 75:
        score_class = "medium"
        badge_class = "badge-warning"
    else:
        score_class = "low"
        badge_class = "badge-success"

    # 建议标签
    if "买入" in suggestion:
        suggest_badge = "badge-danger"
        suggest_text = "买入"
    elif "观察" in suggestion:
        suggest_badge = "badge-warning"
        suggest_text = "观察"
    else:
        suggest_badge = "badge-success"
        suggest_text = "其他"

    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-header">
            <div class="signal-stock">
                <span class="code">{symbol}</span> {name}
            </div>
            <div class="signal-score {score_class}">{score}分</div>
        </div>
        <div style="margin-bottom: 0.75rem;">
            <span class="badge {suggest_badge}">{suggest_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("查看详情", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("现价", f"¥{record.get('price', 0):.2f}")
        with col2:
            st.metric("涨幅", f"{record.get('change_pct', 0):+.2f}%")
        with col3:
            st.metric("换手率", f"{record.get('turnover', 0):.2f}%")
        with col4:
            st.metric("量比", f"{record.get('volume_ratio', 1.0):.2f}")

        st.markdown(f"**分析理由**")
        st.info(ai_reason)

        col_w, col_i, col_r = st.columns(3)
        with col_w:
            if st.button("加入自选", key=f"watch_{record['id']}", use_container_width=True):
                update_status(record['id'], 'Watchlist')
                st.success("已加入自选")
                st.rerun()
        with col_i:
            if st.button("归档", key=f"ignore_{record['id']}", use_container_width=True):
                update_status(record['id'], 'Ignored')
                st.rerun()
        with col_r:
            if st.button("重置", key=f"reset_{record['id']}", use_container_width=True):
                update_status(record['id'], 'New')
                st.rerun()


# =============================================================================
# 标签页
# =============================================================================
def render_tab_market():
    """市场概览"""
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour
    current_weekday = now.weekday()
    is_trading_time = (current_weekday < 5) and (9 <= current_hour < 15)

    st.markdown('<div class="app-title">市场概览</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">实时扫描全市场，捕捉交易机会</div>', unsafe_allow_html=True)

    # 添加刷新按钮
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        pass
    with col2:
        if st.button("刷新数据", use_container_width=True):
            clear_cache()
            st.rerun()
    with col3:
        if not is_trading_time:
            st.caption("非交易时间")

    # 非交易时间提示
    if not is_trading_time:
        st.info("当前为非交易时间，显示当日收盘价格数据")

    with st.spinner("正在加载数据..."):
        df, sentiment, result_a, result_b, result_c, update_time = load_market_data()

    if df is None:
        st.error("""
        **无法获取市场数据**

        可能的原因：
        1. 网络连接问题
        2. 数据源服务暂时不可用
        3. 首次使用需要加载数据

        建议操作：
        - 点击上方「刷新数据」按钮
        - 检查网络连接
        - 稍后再试
        """)
        return

    if len(df) == 0:
        st.warning("当前没有可用数据，可能是数据源问题")
        return

    # 显示数据来源和时间
    if not is_trading_time:
        st.caption(f"数据来源：东方财富（收盘价）| 扫描：{len(df)}只股票 | 更新时间：{update_time}")
    else:
        st.caption(f"数据来源：东方财富（实时）| 扫描：{len(df)}只股票 | 更新时间：{update_time}")

    # 市场指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        temp = sentiment['market_temperature']['score']
        render_metric_card("市场温度", f"{temp:.0f}", sentiment['market_temperature']['status'])
    with col2:
        up = sentiment['summary']['up_count']
        down = sentiment['summary']['down_count']
        render_metric_card("涨跌比", f"{up}:{down}", f"上涨{sentiment['summary']['up_ratio']:.1f}%")
    with col3:
        render_metric_card("涨停数", sentiment['limit_performance']['limit_up'], f"跌停{sentiment['limit_performance']['limit_down']}")
    with col4:
        median = sentiment['price_change_stats']['median_change']
        color = "inverse" if median < 0 else "normal"
        render_metric_card("中位数", f"{median:+.2f}%", f"平均{sentiment['price_change_stats']['mean_change']:+.2f}%", color)

    st.markdown("---")

    # 策略结果
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        render_strategy_table(result_a, "强势中军")
    with col_b:
        render_strategy_table(result_b, "冲击涨停")
    with col_c:
        render_strategy_table(result_c, "低位潜伏")

    st.markdown("---")
    st.caption(f"发现机会：{len(result_a)+len(result_b)+len(result_c)}个")


def render_tab_signals():
    """AI信号"""
    st.markdown('<div class="app-title">AI投研日报</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">智能分析，辅助决策</div>', unsafe_allow_html=True)

    # 筛选栏
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_date = st.date_input("日期", datetime.now().date())
    with col2:
        status_filter = st.selectbox(
            "状态",
            ["全部", "待处理", "自选", "已归档"],
            label_visibility="collapsed"
        )
    with col3:
        if st.button("刷新", use_container_width=True):
            st.rerun()
    with col4:
        if st.button("运行AI分析", use_container_width=True, type="primary"):
            st.info("请在终端运行：python auto_analysis.py")

    date_str = selected_date.strftime('%Y-%m-%d')

    status_map = {"全部": None, "待处理": "New", "自选": "Watchlist", "已归档": "Ignored"}
    records = get_records_by_status(status=status_map[status_filter], date=date_str, limit=100)

    # 统计
    stats = get_statistics(days=7)
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        render_metric_card("本周分析", f"{stats['total_count']}", "条")
    with col_s2:
        render_metric_card("平均评分", f"{stats['avg_score']:.1f}", "分")
    with col_s3:
        watchlist_count = len(get_records_by_status('Watchlist', date_str))
        render_metric_card("自选股票", f"{watchlist_count}", "只")

    st.markdown("---")

    if not records:
        st.warning(f"""
        **{date_str} 暂无分析记录**

        请运行以下命令启动AI分析：
        ```bash
        python auto_analysis.py
        ```
        """)
    else:
        st.markdown(f"**找到 {len(records)} 条记录**")
        records = sorted(records, key=lambda x: x.get('ai_score', 0), reverse=True)
        for record in records:
            render_signal_card(record)


def render_tab_portfolio():
    """自选管理"""
    st.markdown('<div class="app-title">模拟操盘</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">跟踪自选，回顾历史</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**自选列表**")
        watchlist = get_records_by_status('Watchlist', limit=20)

        if watchlist:
            for record in watchlist:
                score = record.get('ai_score', 0)
                score_class = "high" if score >= 85 else "medium" if score >= 75 else "low"
                score_color = "text-danger" if score >= 85 else "text-warning" if score >= 75 else "text-success"

                with st.expander(f"<span class='code'>{record.get('symbol')}</span> {record.get('name')} | <span class='{score_color}'>{score}分</span>", expanded=False):
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("现价", f"¥{record.get('price', 0):.2f}")
                    with col_m2:
                        st.metric("涨幅", f"{record.get('change_pct', 0):+.2f}%")
                    with col_m3:
                        st.metric("换手", f"{record.get('turnover', 0):.2f}%")

                    st.markdown(f"**建议**: {record.get('ai_suggestion', '')}")
                    st.caption(f"{record.get('ai_reason', '')[:80]}...")

                    if st.button("移出", key=f"remove_{record['id']}", use_container_width=True):
                        update_status(record['id'], 'Ignored')
                        st.rerun()
        else:
            st.info("暂无自选股票，请从「AI投研日报」添加")

    with col2:
        st.markdown("**本周统计**")
        stats = get_statistics(days=7)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("总记录", stats['total_count'])
        with col_s2:
            st.metric("覆盖股票", stats['unique_symbols'])

        st.markdown("**建议分布**")
        for suggestion, count in stats.get('suggestions', {}).items():
            st.markdown(f"- {suggestion}: {count}只")

        st.markdown("---")
        st.markdown("**最近记录**")
        recent = get_records(limit=10)
        if recent:
            for r in recent[:5]:
                st.caption(f"{r.get('name')} | {r.get('ai_suggestion', '')} | {r.get('created_at', '')}")


def render_sidebar():
    """侧边栏"""
    with st.sidebar:
        st.markdown("**系统设置**")

        if st.button("清除缓存", use_container_width=True):
            clear_cache()
            st.success("已清除")
            st.rerun()

        st.markdown("---")

        st.markdown("**系统信息**")
        st.caption(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption("数据源: 东方财富")
        st.caption("AI引擎: 通义千问")

        st.markdown("---")

        st.markdown("**使用指南**")
        st.markdown("""
        1. **市场概览**: 查看实时市场数据
        2. **AI投研日报**: 查看AI分析结果
        3. **模拟操盘**: 管理自选股票
        """)


# =============================================================================
# 主程序
# =============================================================================
def main():
    """主应用"""

    # 标题
    st.markdown("""
    <div style="border-bottom: 2px solid #d9d9d9; padding-bottom: 1rem; margin-bottom: 1.5rem;">
        <div class="app-title">A股短线雷达</div>
        <div class="app-subtitle">专业量化交易终端</div>
    </div>
    """, unsafe_allow_html=True)

    # 侧边栏
    render_sidebar()

    # 标签页
    tab1, tab2, tab3 = st.tabs(["市场概览", "AI投研日报", "模拟操盘"])

    with tab1:
        render_tab_market()

    with tab2:
        render_tab_signals()

    with tab3:
        render_tab_portfolio()


if __name__ == "__main__":
    main()
