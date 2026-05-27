"""预期差分析 Agent

解释"利好不涨、利空不跌"等6种市场反常现象背后的因果逻辑。
"""
from typing import Dict, Any, Optional
from backend.services import (
    get_stock_daily, get_stock_fund_flow, get_stock_name,
    get_stock_financial, get_realtime_quote, get_sector_fund_flow
)
import pandas as pd


class ExpectationGapAgent:
    """预期差分析器 — 分析市场反常现象"""

    GAP_TYPES = [
        "利好不涨", "业绩增长反而跌", "利空落地反而涨",
        "放量涨次日跌", "缩量上涨", "高位放量滞涨",
    ]

    def analyze(self, symbol: str) -> Dict[str, Any]:
        """分析个股是否存在预期差现象"""
        df = get_stock_daily(symbol)
        if df is None or len(df) < 5:
            return self._empty_result("数据不足")

        stock_name = get_stock_name(symbol)
        latest = df.iloc[-1]
        recent = df.tail(20)

        # 提取核心数据
        close = float(latest["close"])
        pct = float(latest["pct_change"])
        volume = float(latest["volume"])
        turnover = float(latest["turnover"])
        high = float(latest["high"])
        low = float(latest["low"])

        # 计算均量和累计涨幅
        avg_vol_20 = recent["volume"].mean()
        vol_ratio = volume / avg_vol_20 if avg_vol_20 > 0 else 1
        cum_gain_60 = self._calc_cum_gain(df, 60)
        cum_gain_20 = self._calc_cum_gain(df, 20)

        # 近3日涨跌
        last3 = df.tail(3)
        pct_3day = sum(last3["pct_change"]) if len(last3) >= 3 else None

        # 资金流向
        fund_flow = get_stock_fund_flow(symbol)
        main_flow = fund_flow.get("主力净流入", 0) if fund_flow else 0

        # 财务数据
        financial = get_stock_financial(symbol)
        profit_growth = financial.get("净利润", 0) if financial else 0

        # 板块数据
        quote = get_realtime_quote(symbol)

        # 评分
        scores = {t: {"score": 0, "max": 4, "reasons": []} for t in self.GAP_TYPES}

        scores = self._score_利好不涨(scores, pct, pct_3day, main_flow, financial, quote)
        scores = self._score_业绩增长反而跌(scores, pct, profit_growth, financial, quote, df)
        scores = self._score_利空落地反而涨(scores, pct, volume, avg_vol_20, main_flow, financial)
        scores = self._score_放量涨次日跌(scores, pct, vol_ratio, main_flow, df)
        scores = self._score_缩量上涨(scores, pct, vol_ratio, turnover)
        scores = self._score_高位放量滞涨(scores, pct, vol_ratio, cum_gain_60, turnover, main_flow)

        # 归一化并取最高分
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
                "has_gap": False,
                "gap_type": None,
                "confidence": None,
                "description": "当前无明显预期差现象，量价关系正常。",
                "signals": [],
                "data_summary": self._build_summary(pct, vol_ratio, main_flow, cum_gain_60),
            }

        # 置信度
        if best_score >= 0.75:
            confidence = "高"
        elif best_score >= 0.5:
            confidence = "中"
        else:
            confidence = "低"

        desc = self._get_description(best_type, best_score, stock_name, pct, main_flow, cum_gain_60, vol_ratio)
        signals = scores[best_type]["reasons"]

        return {
            "has_gap": True,
            "gap_type": best_type,
            "confidence": confidence,
            "description": desc,
            "signals": signals,
            "data_summary": self._build_summary(pct, vol_ratio, main_flow, cum_gain_60),
            "details": results,
        }

    def _score_利好不涨(self, scores, pct, pct_3day, main_flow, financial, quote):
        """利好不涨：有利好消息但股价不涨"""
        s = scores["利好不涨"]
        # 有财务数据（意味着有财报发布）
        if financial and financial.get("净利润", 0) != 0:
            s["score"] += 1
            s["reasons"].append("近期有财报数据，可能有利好消息")
        # 股价不涨或下跌
        if pct <= 0:
            s["score"] += 1
            s["reasons"].append("今日股价未涨，与利好预期背离")
        if pct_3day is not None and pct_3day <= 1:
            s["score"] += 1
            s["reasons"].append("近3日涨幅有限，利好未反映在股价中")
        # 主力流出
        if main_flow < -500:
            s["score"] += 1
            s["reasons"].append(f"主力净流出{abs(main_flow):.0f}万元，借利好出货")
        return scores

    def _score_业绩增长反而跌(self, scores, pct, profit_growth, financial, quote, df):
        """业绩增长反而跌"""
        s = scores["业绩增长反而跌"]
        # 有净利润数据且为正
        if financial and profit_growth > 0:
            s["score"] += 1
            s["reasons"].append("净利润为正，基本面不差")
        # 但股价下跌
        if pct < -1:
            s["score"] += 1
            s["reasons"].append(f"今日下跌{pct:.1f}%，与业绩增长背离")
        if pct < 0 and profit_growth > 0:
            s["score"] += 1
            s["reasons"].append("业绩增长但股价下跌，存在预期差")
        # 前期已上涨（预期已定价）
        recent = df.tail(20)
        if len(recent) >= 20:
            cum = (float(recent.iloc[-1]["close"]) / float(recent.iloc[0]["close"]) - 1) * 100
            if cum > 5:
                s["score"] += 1
                s["reasons"].append(f"近20日已上涨{cum:.1f}%，利好可能已被提前定价")
        return scores

    def _score_利空落地反而涨(self, scores, pct, volume, avg_vol_20, main_flow, financial):
        """利空落地反而涨"""
        s = scores["利空落地反而涨"]
        if pct > 2:
            s["score"] += 1
            s["reasons"].append("今日逆势上涨")
        if volume < avg_vol_20 * 0.8:
            s["score"] += 1
            s["reasons"].append("缩量上涨，抛压轻")
        if main_flow > 0:
            s["score"] += 1
            s["reasons"].append("主力资金仍在流入")
        if volume < avg_vol_20 * 0.6:
            s["score"] += 1
            s["reasons"].append("极度缩量，利空已充分消化")
        return scores

    def _score_放量涨次日跌(self, scores, pct, vol_ratio, main_flow, df):
        """放量上涨但第二天跌"""
        s = scores["放量涨次日跌"]
        if len(df) < 3:
            return scores
        prev = df.iloc[-2]
        prev_pct = float(prev["pct_change"])
        prev_vol = float(prev["volume"])
        avg_vol_20 = df.tail(20)["volume"].mean()

        # 前一日放量上涨
        if prev_pct > 3 and prev_vol > avg_vol_20 * 1.3:
            s["score"] += 1
            s["reasons"].append("前日放量上涨，资金积极")
        # 今日下跌
        if pct < -1:
            s["score"] += 1
            s["reasons"].append(f"今日反转下跌{pct:.1f}%")
        # 量能反转
        if prev_vol > avg_vol_20 * 1.3 and pct < 0:
            s["score"] += 1
            s["reasons"].append("昨放量今缩量下跌，资金撤退")
        # 主力流向反转
        if main_flow < -500:
            s["score"] += 1
            s["reasons"].append(f"主力净流出{abs(main_flow):.0f}万元，出货迹象")
        return scores

    def _score_缩量上涨(self, scores, pct, vol_ratio, turnover):
        """缩量上涨：主力锁仓"""
        s = scores["缩量上涨"]
        if pct > 0:
            s["score"] += 1
            s["reasons"].append("今日上涨")
        if vol_ratio < 0.8:
            s["score"] += 1
            s["reasons"].append(f"量能仅为20日均量的{vol_ratio*100:.0f}%，缩量明显")
        if turnover < 2:
            s["score"] += 1
            s["reasons"].append(f"换手率{turnover:.1f}%，筹码锁定良好")
        if pct > 0 and vol_ratio < 0.6:
            s["score"] += 1
            s["reasons"].append("缩量上涨+上涨，主力控盘特征")
        return scores

    def _score_高位放量滞涨(self, scores, pct, vol_ratio, cum_gain_60, turnover, main_flow):
        """高位放量滞涨：出货特征"""
        s = scores["高位放量滞涨"]
        if cum_gain_60 is not None and cum_gain_60 > 30:
            s["score"] += 1
            s["reasons"].append(f"近60日累计涨幅{cum_gain_60:.1f}%，处于高位")
        if vol_ratio > 1.5 and pct < 1:
            s["score"] += 1
            s["reasons"].append("放量但涨幅有限，量价背离")
        if turnover > 5:
            s["score"] += 1
            s["reasons"].append(f"换手率{turnover:.1f}%>5%，筹码大量交换")
        if main_flow < -500:
            s["score"] += 1
            s["reasons"].append(f"主力净流出{abs(main_flow):.0f}万元，出货特征")
        return scores

    def _get_description(self, gap_type, score, name, pct, main_flow, cum_gain, vol_ratio) -> str:
        """生成大白话描述"""
        descs = {
            "利好不涨": (
                f"{name}近期有利好消息，但股价并未体现。"
                f"可能的原因是：市场已提前交易该利好，当前主力借机出货（净流出{abs(main_flow):.0f}万元）。"
                f"利好发布即出货时机，是A股常见现象。"
            ),
            "业绩增长反而跌": (
                f"{name}业绩增长但股价下跌，存在明显预期差。"
                f"通常原因是：市场对增长的预期更高，实际增速不及预期；"
                f"或者利好已在前期上涨中提前定价，当前是利好出尽。"
            ),
            "利空落地反而涨": (
                f'{name}有利空消息但股价不跌反涨，典型的"利空出尽"走势。'
                f"市场已提前消化利空，不确定性消除后反而吸引资金入场。"
            ),
            "放量涨次日跌": (
                f"{name}昨日放量上涨但今日转为下跌。"
                f"这是典型的主力短期行为：利用放量拉高吸引跟风盘，次日出货。"
                f"如果主力净流出持续，短线应注意风险。"
            ),
            "缩量上涨": (
                f"{name}当前缩量上涨，说明抛压很轻。"
                f"如果股价处于中低位，这通常是主力锁仓信号，后续可能有拉升动作；"
                f"但如果处于高位，则可能是买盘不足的上涨乏力信号。"
            ),
            "高位放量滞涨": (
                f"{name}处于高位区间且出现放量滞涨。"
                f"累计涨幅{cum_gain:.1f}%，今日放量但涨幅有限，叠加主力资金流出，"
                f"高位出货特征较为清晰。持仓者应注意风险控制。"
            ),
        }
        desc = descs.get(gap_type, f"{name}存在预期差现象。")
        if score >= 0.75:
            desc += " 信号明确。"
        elif score >= 0.5:
            desc += " 信号较为明显，需持续观察。"
        else:
            desc += " 信号尚不充分，需结合更多信息判断。"
        return desc

    def _build_summary(self, pct, vol_ratio, main_flow, cum_gain) -> Dict[str, Any]:
        return {
            "今日涨跌幅": f"{pct:+.2f}%",
            "量能比(20日均)": f"{vol_ratio:.2f}",
            "主力净流入": f"{main_flow:.0f}万元" if main_flow != 0 else "0",
            "近60日涨幅": f"{cum_gain:.1f}%" if cum_gain is not None else "N/A",
        }

    def _calc_cum_gain(self, df, days: int) -> Optional[float]:
        if df is None or len(df) < 2:
            return None
        recent = df.tail(min(days, len(df)))
        if len(recent) < 2:
            return None
        return (float(recent.iloc[-1]["close"]) / float(recent.iloc[0]["close"]) - 1) * 100

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        return {
            "has_gap": False,
            "gap_type": None,
            "confidence": None,
            "description": reason,
            "signals": [],
            "data_summary": {},
        }
