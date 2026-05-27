"""特征引擎 — 统一特征计算层

MarketFeatures: 盘面级特征，一次计算，所有 Agent 共享
StockFeatures:  个股级特征，一次计算，所有 Agent 共享

目的: 消除 Agent 之间的重复计算，保证同一请求内数据一致性。
"""
from .market_features import MarketFeatures
from .stock_features import StockFeatures

__all__ = ["MarketFeatures", "StockFeatures"]
