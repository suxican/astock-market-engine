---
name: astock-mpquant-optimizer
description: mpquant 库集成优化工具 — Ashare(新浪+腾讯双源) + MyTT(技术指标)，用于优化 astock-copilot 项目的数据源和指标分析
metadata:
  type: skill
  author: mpquant
  source: https://github.com/mpquant
---

# astock-mpquant-optimizer

## 概述
将 mpquant 的两个核心库（Ashare + MyTT）集成到 astock-copilot 项目中，优化数据源稳定性和技术分析能力。

## 集成组件

### 1. Ashare 数据源
- **文件**: `backend/services/ashare_data.py`
- **数据源优先级**: 新浪财经(主) → 腾讯财经(备)
- **优势**: 无 IP 封禁，比 akshare East Money 更稳定
- **入口函数**: `get_price_daily(symbol, count=120)`
- **支持**: 日线 + 分钟线(1m/5m/15m/30m/60m)

### 2. MyTT 技术指标
- **文件**: `backend/services/technical_indicators.py`
- **功能**: 通达信/同花顺公式移植，纯 pandas 实现
- **入口函数**: `compute_indicators(df)` → dict
- **辅助函数**: `indicators_to_text(dict)` → AI prompt
- **信号函数**: `analyze_signal(dict)` → {"signal": "偏多/偏空/中性", "score": int}

## 数据源降级链路
Ashare(新浪) → Ashare(腾讯) → akshare stock_zh_a_daily → akshare stock_zh_a_hist → 模拟数据

## 使用方式
```python
# 数据获取
from backend.services.ashare_data import get_price_daily
df = get_price_daily("600519", count=120)

# 技术指标
from backend.services.technical_indicators import compute_indicators, indicators_to_text
indicators = compute_indicators(df)
text = indicators_to_text(indicators)
```
