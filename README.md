# AShare-Sentinel

> A股短线雷达 - 实时捕捉市场机会的专业游资风格终端

## 项目简介

AShare-Sentinel 是一个专业的 A 股短线交易分析工具，通过实时扫描全市场 5000+ 只股票，运用三大精选策略捕捉短线机会，提供专业级的交易决策支持。

### 核心功能

- **市场温度监控** - 实时计算市场热度，判断情绪状态
- **三大策略扫描** - 强势中军、冲击涨停、低位潜伏
- **后台智能监控** - 自动预警打板机会，不漏单
- **专业游资界面** - 沉浸式交易终端体验

## 三大策略

| 策略 | 名称 | 筛选条件 | 排序 |
|------|------|----------|------|
| A | 强势中军 | 涨幅 5-8%, 换手 7-15%, 市值 10-200亿 | 按换手率 |
| B | 冲击涨停 | 涨幅 8-20%, 换手 >8% | 按涨幅 |
| C | 低位潜伏 | 涨幅 2-5%, 换手 >6% | 按换手率 |

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/AShare-Sentinel.git
cd AShare-Sentinel

# 安装依赖
pip install -r requirements.txt
```

## 使用

### 启动 Web 界面

```bash
streamlit run app.py
```

访问 `http://localhost:8501` 查看实时监控界面。

### 启动后台监控

```bash
python watcher.py
```

后台监控会每 60 秒扫描一次，发现冲击涨停机会时自动报警（蜂鸣 + 系统通知）。

## 项目结构

```
AShare-Sentinel/
├── src/
│   ├── config.py              # 配置常量
│   ├── data/
│   │   └── data_loader.py     # 数据获取模块
│   ├── sentiment/
│   │   └── sentiment.py       # 市场情绪分析
│   ├── strategies/
│   │   └── strategies.py      # 三大策略扫描
│   └── utils/
│       ├── cache.py           # 缓存管理
│       ├── logger.py          # 日志系统
│       └── validator.py       # 数据验证
├── app.py                     # Streamlit Web 界面
├── watcher.py                 # 后台监控脚本
├── test_*.py                  # 测试脚本
├── requirements.txt           # 依赖列表
└── README.md                  # 项目说明
```

## 数据来源

- [AkShare](https://github.com/akfamily/akshare) - 免费 A 股数据接口
- [东方财富网](http://quote.eastmoney.com/) - 实时行情

## 依赖

- `akshare>=1.12.0` - A 股数据获取
- `pandas>=2.0.0` - 数据处理
- `streamlit>=1.28.0` - Web 界面
- `plyer>=2.1.0` - 系统通知（可选）

## 免责声明

本工具仅用于技术学习和研究，不构成任何投资建议。股市有风险，投资需谨慎。

## License

MIT License
