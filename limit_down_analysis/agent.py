"""跌停原因分析 Agent (V3)

V3 变更: 接受 MarketFeatures 输入，从预计算的跌停池获取数据。
"""
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.services import get_sector_fund_flow, get_stock_fund_flow, get_stock_name


class LimitDownAgent:
    """跌停原因分析器 (V3)"""

    def analyze(
        self,
        symbol: str,
        market_features: MarketFeatures | None = None,
    ) -> dict[str, Any]:
        """分析个股跌停原因"""
        if market_features is not None and market_features.limit_down_pool is not None:
            pool = market_features.limit_down_pool
        else:
            from backend.services import get_limit_down_pool
            pool = get_limit_down_pool()

        if pool.empty:
            return self._no_data_result("无跌停数据")

        pool_str = pool.astype(str)
        match = pool_str[pool_str["代码"] == symbol]
        if match.empty:
            return {"is_limit_down": False, "type": None, "confidence": None, "description": "该股今日未跌停", "signals": []}

        row = match.iloc[0]
        stock_name = get_stock_name(symbol)
        board_count = self._safe_float(row.get("连板数", 0))
        kaiban_count = self._safe_int(row.get("开板次数", 0))
        fengdan_amount = self._safe_float(row.get("封单资金", 0))
        industry = str(row.get("所属行业", ""))
        turnover = self._safe_float(row.get("换手率", 0))

        fund_flow = get_stock_fund_flow(symbol)
        main_flow = fund_flow.get("主力净流入", 0) if fund_flow else 0
        cum_gain = self._get_cum_gain(symbol)

        return self._analyze_limit_down(
            stock_name=stock_name, symbol=symbol,
            board_count=board_count, kaiban_count=kaiban_count,
            fengdan_amount=fengdan_amount, industry=industry,
            turnover=turnover, main_flow=main_flow, cum_gain=cum_gain,
        )

    def _analyze_limit_down(self, **kw) -> dict[str, Any]:
        stock_name = kw["stock_name"]
        industry = kw.get("industry", "")
        main_flow = kw.get("main_flow", 0)
        cum_gain = kw.get("cum_gain")
        turnover = kw.get("turnover", 0)
        kaiban_count = kw.get("kaiban_count", 0)
        fengdan_amount = kw.get("fengdan_amount", 0)

        scores = {"公司暴雷": 0, "主力出货": 0, "板块退潮": 0, "情绪崩塌": 0, "高位补跌": 0, "流动性危机": 0}
        max_scores = {k: 3 for k in scores}
        reasons = {k: [] for k in scores}

        if main_flow < -2000:
            scores["公司暴雷"] += 1; reasons["公司暴雷"].append("主力大幅出逃")
        if turnover < 2 and main_flow < -1000:
            scores["公司暴雷"] += 1; reasons["公司暴雷"].append("低换手+大单出逃")
        if kaiban_count == 0 and turnover < 1:
            scores["公司暴雷"] += 1; reasons["公司暴雷"].append("一字封死跌停")

        if main_flow < -1000:
            scores["主力出货"] += 1; reasons["主力出货"].append("主力净流出")
        if cum_gain is not None and cum_gain > 20 and main_flow < -500:
            scores["主力出货"] += 1; reasons["主力出货"].append("高位+主力流出")
        if turnover > 5 and main_flow < -500:
            scores["主力出货"] += 1; reasons["主力出货"].append("高换手+资金流出")

        if industry:
            sector_info = self._get_sector_info(industry)
            if sector_info and sector_info.get("涨跌幅", 0) < -2:
                scores["板块退潮"] += 1; reasons["板块退潮"].append(f"{industry}板块大跌")
            if sector_info and sector_info.get("流入", 0) < -500:
                scores["板块退潮"] += 1; reasons["板块退潮"].append(f"{industry}板块资金出逃")

        if turnover > 8:
            scores["情绪崩塌"] += 1; reasons["情绪崩塌"].append("换手率极高，恐慌抛售")
        if kaiban_count >= 3:
            scores["情绪崩塌"] += 1; reasons["情绪崩塌"].append("多次开板，多空激烈博弈")
        if main_flow < -500:
            scores["情绪崩塌"] += 1; reasons["情绪崩塌"].append("资金不计成本出逃")

        if cum_gain is not None and cum_gain > 30:
            scores["高位补跌"] += 1; reasons["高位补跌"].append(f"累计涨幅{cum_gain:.1f}%")
        if cum_gain is not None and cum_gain > 50:
            scores["高位补跌"] += 1; reasons["高位补跌"].append("涨幅巨大")
        if main_flow < -500:
            scores["高位补跌"] += 1; reasons["高位补跌"].append("主力获利了结")

        if turnover < 1:
            scores["流动性危机"] += 1; reasons["流动性危机"].append("换手率极低")
        if abs(fengdan_amount) > 2:
            scores["流动性危机"] += 1; reasons["流动性危机"].append("封单巨大")
        if turnover < 0.5:
            scores["流动性危机"] += 1; reasons["流动性危机"].append("流动性枯竭")

        for k in scores:
            scores[k] = scores[k] / max_scores[k] if max_scores[k] > 0 else 0

        best = max(scores, key=scores.get)
        best_score = scores[best]
        confidence = "高" if best_score >= 0.75 else ("中" if best_score >= 0.5 else "低")

        descriptions = {
            "公司暴雷": f"{stock_name}今日跌停属于**公司暴雷型**。资金不计成本出逃。",
            "主力出货": f"{stock_name}今日跌停属于**主力出货型**。高位派发迹象明显。",
            "板块退潮": f"{stock_name}今日跌停属于**板块退潮型**。{industry}板块整体走弱。",
            "情绪崩塌": f"{stock_name}今日跌停属于**情绪崩塌型**。恐慌情绪蔓延。",
            "高位补跌": f"{stock_name}今日跌停属于**高位补跌型**。获利盘集中兑现。",
            "流动性危机": f"{stock_name}今日跌停属于**流动性危机型**。承接力不足。",
        }
        desc = descriptions.get(best, f"{stock_name}今日跌停。")
        if best_score >= 0.75: desc += " 信号明确。"
        elif best_score >= 0.5: desc += " 需持续观察。"
        else: desc += " 信号不充分。"

        return {
            "is_limit_down": True, "type": best, "confidence": confidence,
            "description": desc, "reasons": reasons[best] or ["信号不明确"],
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }

    def _get_sector_info(self, industry):
        if not industry: return None
        df = get_sector_fund_flow()
        if df is None or df.empty: return None
        df_str = df.astype(str)
        match = df_str[df_str["名称"] == industry]
        if match.empty: return None
        row = match.iloc[0]
        return {"名称": industry, "涨跌幅": self._safe_float(row.get("今日涨跌幅", 0)), "流入": self._safe_float(row.get("主力净流入-净额", 0))}

    def _get_cum_gain(self, symbol):
        try:
            from backend.services import get_stock_daily
            df = get_stock_daily(symbol)
            if df is None or len(df) < 2: return None
            recent = df.tail(60)
            if len(recent) < 2: return None
            return (float(recent.iloc[-1]["close"]) / float(recent.iloc[0]["close"]) - 1) * 100
        except Exception: return None

    def _safe_float(self, val):
        try: return float(val)
        except (ValueError, TypeError): return 0.0

    def _safe_int(self, val):
        try: return int(float(val))
        except (ValueError, TypeError): return 0

    def _no_data_result(self, reason):
        return {"is_limit_down": False, "type": None, "confidence": None, "description": reason, "signals": []}
