# AShare-Sentinel V2.1 使用说明

> A股短线雷达 - 专业量化交易分析终端

---

## 目录

1. [版本更新](#版本更新)
2. [快速开始](#快速开始)
3. [核心功能](#核心功能)
4. [使用指南](#使用指南)
5. [配置说明](#配置说明)
6. [常见问题](#常见问题)

---

## 版本更新

### V2.1 新功能

- **AI 投研日报**：基于通义千问的智能股票分析系统
- **量价时空评分**：Volume(40) + Trend(30) + Pattern(20) + Sentiment(10)
- **模拟操盘**：2连榜自动买入，完整持仓管理
- **多策略扫描**：放量突破、冲击涨停、低位潜伏
- **实时监控**：市场温度、涨停统计、机会分布

---

## 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/AShare-Sentinel.git
cd AShare-Sentinel

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 4. 启动应用
streamlit run app.py
```

### 访问应用

启动后访问：`http://localhost:8501`

---

## 核心功能

### 1. 市场数据

实时监控全市场 5000+ 只股票：

- **市场温度**：当前涨跌分布、涨停跌停统计
- **发现机会**：三大策略扫描结果
- **实时更新**：数据 5 分钟自动刷新

### 2. AI 投研日报

基于通义千问 API 的智能分析：

- **智能评分**：量价时空四维评分系统（满分100分）
- **买入建议**：强烈关注 / 关注 / 观望
- **深度分析**：技术面、资金面、情绪面综合评估
- **一键运行**：点击"运行AI分析"自动生成报告

**评分规则**：

| 维度 | 权重 | 说明 |
|------|------|------|
| 量能 | 40分 | 放量突破(35-40)、温和放量(25-34)、缩量锁死(70分封顶) |
| 趋势 | 30分 | 多头排列(25-30)、中期上涨(20-24)、年线下扣分 |
| 形态 | 20分 | 反包/突破(+5分)、长上影(-5分) |
| 情绪 | 10分 | 主流热点(8-10)、跟风上涨(3-7)、孤股(0-2) |

### 3. 模拟操盘

完整的模拟交易系统：

- **自动买入**：股票连续 2 次上榜自动触发买入
- **持仓管理**：实时成本、市值、盈亏统计
- **风控规则**：
  - 单次买入：5 万元
  - 初始资金：100 万元
  - 重复持仓检查
  - 资金充足性验证

---

## 使用指南

### 市场数据页面

1. **查看实时行情**
   - 涨跌幅分布饼图
   - 涨停/跌停统计
   - 市场温度指标

2. **查看策略机会**
   - **放量突破**：强势中军，换手率活跃
   - **冲击涨停**：接近涨停，主力拉升
   - **低位潜伏**：低位启动，潜在机会

3. **数据刷新**
   - 自动刷新：5 分钟
   - 手动刷新：点击"刷新"按钮

### AI 投研日报页面

#### 运行 AI 分析

1. 点击"运行AI分析"按钮
2. 系统自动扫描市场，筛选高分股票
3. 显示进度条和实时状态
4. 分析完成后自动刷新显示结果

#### 查看分析结果

**卡片信息**：

| 字段 | 说明 |
|------|------|
| 股票代码 | 6 位代码 |
| 股票名称 | 股票简称 |
| AI 评分 | 0-100 分，颜色区分 |
| 买入建议 | 强烈关注/关注/观望 |
| 现价 | 当前股价 |
| 涨幅 | 当日涨跌幅 |
| 换手率 | 换手率百分比 |
| 量比 | 当日量比 |
| AI 分析理由 | 详细分析说明 |

#### 状态管理

- **加入自选**：标记为 Watchlist（暂不影响持仓）
- **移出自选**：取消关注
- **已归档**：不再显示

### 模拟操盘页面

#### 查看持仓

- **持仓列表**：显示所有买入的股票
- **盈亏统计**：
  - 成本价 vs 现价
  - 盈亏金额和百分比
  - 涨跌颜色区分

#### 账户摘要

- **总资产** = 现金 + 持仓市值
- **持仓市值**：所有持仓的当前市值
- **可用资金**：可用于买入的现金

#### 自动交易逻辑

```
AI 分析完成
    ↓
计算连榜数
    ↓
发现股票连续 2 次上榜
    ↓
执行自动买入（5 万元）
    ↓
更新持仓记录
```

---

## 配置说明

### 环境变量

创建 `.env` 文件（可选）：

```bash
# 数据库类型（sqlite 或 postgresql）
DATABASE_TYPE=sqlite

# 通义千问 API Key（必需）
DASHSCOPE_API_KEY=your_api_key_here

# 日志级别
LOG_LEVEL=INFO

# 缓存开关
CACHE_ENABLED=true
```

### 获取 API Key

1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 开通通义千问服务
3. 创建 API Key
4. 填入 `.env` 文件

### 交易配置

编辑 `src/config.py`：

```python
class PortfolioConfig:
    # 初始资金
    INITIAL_CASH = 1000000  # 100万

    # 单笔买入金额
    TRADE_AMOUNT_PER_POS = 50000  # 5万

    # 连榜触发阈值
    STREAK_THRESHOLD = 2  # 连续2次上榜

    # 是否启用自动交易
    AUTO_TRADE_ENABLED = True
```

---

## 常见问题

### Q1: AI 分析显示"暂无分析记录"

**原因**：今天还没有运行过 AI 分析

**解决**：
- 点击"运行AI分析"按钮
- 或在命令行运行：`python auto_analysis.py`

### Q2: AI 分析失败

**原因**：
1. 未配置 API Key
2. API Key 无效
3. 网络连接问题

**解决**：
1. 检查 `.env` 文件中是否填写了 `DASHSCOPE_API_KEY`
2. 确认 API Key 有效
3. 检查网络连接

### Q3: 模拟操盘显示"暂无持仓"

**原因**：还没有触发自动买入

**解决**：
1. 多次运行"AI 分析"，让股票连榜
2. 当某只股票连续 2 次上榜时会自动买入

### Q4: 数据不更新

**原因**：缓存问题

**解决**：
1. 点击"清除缓存"按钮
2. 或按 Ctrl+F5 强制刷新浏览器

### Q5: 页面显示乱码

**原因**：编码问题

**解决**：
1. 确保使用 UTF-8 编码
2. 清除浏览器缓存
3. 尝试其他浏览器

---

## 项目结构

```
AShare-Sentinel/
├── src/
│   ├── config.py              # 配置管理
│   ├── data/
│   │   └── data_loader.py     # 数据加载（AKShare）
│   ├── database/
│   │   ├── database.py        # 数据库操作
│   │   └── db_manager.py      # 统一数据库管理
│   ├── portfolio/
│   │   └── manager.py         # 模拟操盘管理
│   ├── sentiment/
│   │   └── sentiment.py       # 市场情绪分析
│   ├── strategies/
│   │   └── strategies.py      # 三大策略扫描
│   └── utils/
│       ├── cache.py           # 缓存管理
│       ├── logger.py          # 日志系统
│       └── validator.py       # 数据验证
├── ai_agent.py                # AI 分析核心（量价时空）
├── app.py                     # Streamlit 主应用
├── auto_analysis.py           # 自动分析引擎
├── portfolio.json             # 持仓数据（自动生成）
├── sentinel.db                # SQLite 数据库（自动生成）
├── requirements.txt           # 依赖列表
└── .env.example               # 环境变量模板
```

---

## 技术架构

### 数据流

```
AKShare → 数据加载 → 策略扫描 → AI 分析 → 数据库 → Web 展示
                      ↓
                 模拟操盘
```

### 核心模块

| 模块 | 功能 |
|------|------|
| data_loader | 从 AKShare 获取实时行情 |
| strategies | 三大策略筛选 |
| ai_agent | 量价时空智能评分 |
| portfolio | 模拟交易管理 |
| db_manager | 统一数据库接口 |

### 数据库

- **默认**：SQLite（无需配置）
- **可选**：PostgreSQL（修改 `DATABASE_TYPE=postgresql`）

表结构：
- `stock_analysis`：AI 分析记录
- 字段：股票代码、名称、评分、建议、理由、时间戳等

---

## 命令行工具

### 运行 AI 分析

```bash
# 基础运行
python auto_analysis.py

# 指定分析数量
python auto_analysis.py --max-candidates 20

# 指定评分阈值
python auto_analysis.py --score-threshold 80
```

### 数据库操作

```bash
# 查看今天的分析记录
python -c "
from src.database.db_manager import get_db_manager
from datetime import datetime

db = get_db_manager()
today = datetime.now().strftime('%Y-%m-%d')
query = f\"SELECT * FROM stock_analysis WHERE DATE(created_at) = '{today}'\"
df = db.fetch_df(query)
print(df)
"
```

---

## 更新日志

### V2.1 (2025-01-16)

- [新增] AI 投研日报功能
- [新增] 量价时空评分系统
- [新增] 模拟操盘系统
- [新增] 2连榜自动买入
- [优化] SQLite 并发读取（WAL模式）
- [优化] Streamlit 缓存机制
- [修复] 数据加载空值问题
- [清理] 移除无用文件

### V2.0

- [新增] 市场数据实时监控
- [新增] 三大策略扫描
- [新增] 市场温度指标
- [重构] 统一数据库管理

---

## 免责声明

本工具仅用于技术学习和研究，不构成任何投资建议。

- 股市有风险，投资需谨慎
- AI 分析仅供参考，不作为买卖依据
- 模拟操盘不代表真实交易结果
- 用户需自行承担使用本工具的风险

---

## 开源协议

MIT License

---

## 联系方式

- GitHub Issues: [提交问题](https://github.com/yourusername/AShare-Sentinel/issues)
- 邮箱: your-email@example.com

**祝您投资顺利！**
