"""预期差分析 Agent (V3)

V3 变更: 接受 StockFeatures 输入，减少重复 services 调用。
"""
from typing import Any

from backend.feature_engine.stock_features import StockFeatures
from backend.services import get_realtime_quote, get_stock_financial, get_stock_fund_flow, get_stock_name


class ExpectationGapAgent:
    """预期差分析器 (V3)"""

    GAP_TYPES = [
        "利好不涨", "业绩增长反而跌", "利空落地反而涨",
        "放量涨次日跌", "缩量上涨", "高位放量滞涨",
    ]

    def analyze(
        self,
        symbol: str,
        stock_features: StockFeatures | None = None,
    ) -> dict[str, Any]:
        """分析个股是否存在预期差现象

        Args:
            symbol: 股票代码
            stock_features: 预计算的个股特征
        """
        if stock_features is not None and stock_features.close > 0:
            sf = stock_features
        else:
            sf = StockFeatures.compute(symbol)

        if sf.close == 0:
            return self._empty_result("数据不足")

        pct = sf.pct_change
        vol_ratio = sf.vol_ratio_vs_avg20
        turnover = sf.turnover
        main_flow = sf.main_flow
        cum_gain_60 = sf.cum_gain_60d

        # 近3日涨跌（从 kline_records 获取）
        last3_pct = None
        if sf.kline_records and len(sf.kline_records) >= 3:
            last3 = sf.kline_records[-3:]
            last3_pct = sum(r.get("pct_change", 0) for r in last3)

        financial = get_stock_financial(symbol)
        profit_growth = financial.get("净利润", 0) if financial else 0
        quote = get_realtime_quote(symbol)

        scores = {t: {"score": 0, "max": 4, "reasons": []} for t in self.GAP_TYPES}

        scores = self._score_利好不涨(scores, pct, last3_pct, main_flow, financial, quote)
        scores = self._score_业绩增长反而跌(scores, pct, profit_growth, financial, quote)
        scores = self._score_利空落地反而涨(scores, pct, sf.volume, sf.avg_vol_20, main_flow, financial)
        scores = self._score_放量涨次日跌(scores, pct, vol_ratio, main_flow)
        scores = self._score_缩量上涨(scores, pct, vol_ratio, turnover)
        scores = self._score_高位放量滞涨(scores, pct, vol_ratio, cum_gain_60, turnover, main_flow)

        best_type = None
        best_score = 0
        results = {}
        for t, v in scores.items():
            norm = v["score"] / v["max"] if v["max"] > 0 else 0
            results[t] = round(norm, 2)
            if norm > best_score:
                best_score = norm
                best_type = t

        if best_score < 0.4:
            return {
                "has_gap": False, "gap_type": None, "confidence": None,
                "description": "当前无明显预期差现象，量价关系正常。",
                "signals": [], "data_summary": self._build_summary(pct, vol_ratio, main_flow, cum_gain_60),
            }

        confidence = "高" if best_score >= 0.75 else ("中" if best_score >= 0.5 else "低")
        desc = self._get_description(best_type, best_score, sf.name, pct, main_flow, cum_gain_60, vol_ratio)

        return {
            "has_gap": True, "gap_type": best_type, "confidence": confidence,
            "description": desc, "signals": scores[best_type]["reasons"],
            "data_summary": self._build_summary(pct, vol_ratio, main_flow, cum_gain_60),
            "details": results,
        }

    def _score_利好不涨(self, scores, pct, pct_3day, main_flow, financial, quote):
        s = scores["利好不涨"]
        if financial and financial.get("净利润", 0) != 0:
            s["score"] += 1; s["reasons"].append("有财报数据")
        if pct <= 0:
            s["score"] += 1; s["reasons"].append("今日未涨")
        if pct_3day is not None and pct_3day <= 1:
            s["score"] += 1; s["reasons"].append("近3日涨幅有限")
        if main_flow < -500:
            s["score"] += 1; s["reasons"].append("主力借利好出货")
        return scores

    def _score_业绩增长反而跌(self, scores, pct, profit_growth, financial, quote):
        s = scores["业绩增长反而跌"]
        if profit_growth and profit_growth > 10:
            s["score"] += 1; s["reasons"].append("净利润增长")
        if pct < 0:
            s["score"] += 1; s["reasons"].append("业绩增长但股价下跌")
        if profit_growth and profit_growth > 30 and pct < -2:
            s["score"] += 1; s["reasons"].append("高增长反而大跌")
        return scores

    def _score_利空落地反而涨(self, scores, pct, volume, avg_vol, main_flow, financial):
        s = scores["利空落地反而涨"]
        if financial and financial.get("净利润", 0) and financial["净利润"] < -10:
            s["score"] += 1; s["reasons"].append("业绩下滑/亏损")
        if pct > 0:
            s["score"] += 1; s["reasons"].append("利空下股价不跌反涨")
        if volume > avg_vol * 1.5 and pct > 0:
            s["score"] += 1; s["reasons"].append("放量上涨")
        if main_flow > 500:
            s["score"] += 1; s["reasons"].append("主力逆势买入")
        return scores

    def _score_放量涨次日跌(self, scores, pct, vol_ratio, main_flow):
        s = scores["放量涨次日跌"]
        if vol_ratio > 1.5 and pct < 0:
            s["score"] += 1; s["reasons"].append("放量后下跌")
        if main_flow < -500:
            s["score"] += 1; s["reasons"].append("主力出货")
        if pct < -2:
            s["score"] += 1; s["reasons"].append("跌幅较大")
        return scores

    def _score_缩量上涨(self, scores, pct, vol_ratio, turnover):
        s = scores["缩量上涨"]
        if pct > 0:
            s["score"] += 1; s["reasons"].append("今日上涨")
        if vol_ratio < 0.8:
            s["score"] += 1; s["reasons"].append("缩量明显")
        if turnover < 2:
            s["score"] += 1; s["reasons"].append("筹码锁定良好")
        if pct > 0 and vol_ratio < 0.6:
            s["score"] += 1; s["reasons"].append("主力控盘特征")
        return scores

    def _score_高位放量滞涨(self, scores, pct, vol_ratio, cum_gain_60, turnover, main_flow):
        s = scores["高位放量滞涨"]
        if cum_gain_60 is not None and cum_gain_60 > 30:
            s["score"] += 1; s["reasons"].append("处于高位")
        if vol_ratio > 1.5 and pct < 1:
            s["score"] += 1; s["reasons"].append("量价背离")
        if turnover > 5:
            s["score"] += 1; s["reasons"].append("筹码大量交换")
        if main_flow < -500:
            s["score"] += 1; s["reasons"].append("出货特征")
        return scores

    def _get_description(self, gap_type, score, name, pct, main_flow, cum_gain, vol_ratio):
        descs = {
            "利好不涨": f"{name}有利好消息但股价未体现，主力借机出货。",
            "业绩增长反而跌": f"{name}业绩增长但股价下跌，预期差明显。",
            "利空落地反而涨": f"{name}有利空但不跌反涨，利空出尽走势。",
            "放量涨次日跌": f"{name}放量上涨后转跌，主力短期行为。",
            "缩量上涨": f"{name}缩量上涨，抛压轻，主力锁仓。",
            "高位放量滞涨": f"{name}高位放量滞涨，出货特征。",
        }
        desc = descs.get(gap_type, f"{name}存在预期差现象。")
        if score >= 0.75: desc += " 信号明确。"
        elif score >= 0.5: desc += " 需持续观察。"
        else: desc += " 信号不充分。"
        return desc

    def _build_summary(self, pct, vol_ratio, main_flow, cum_gain):
        return {
            "今日涨跌幅": f"{pct:+.2f}%",
            "量能比(20日均)": f"{vol_ratio:.2f}",
            "主力净流入": f"{main_flow:.0f}万元",
            "近60日涨幅": f"{cum_gain:.1f}%" if cum_gain is not None else "N/A",
        }

    def _empty_result(self, reason):
        return {"has_gap": False, "gap_type": None, "confidence": None, "description": reason, "signals": [], "data_summary": {}}
