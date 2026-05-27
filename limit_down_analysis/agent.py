"""跌停原因分析 Agent

基于文档第六章规则，识别跌停背后的真正原因：
公司暴雷、主力出货、板块退潮、情绪崩塌、高位补跌、流动性危机
"""
from typing import Dict, Any, Optional
from backend.services import (
    get_stock_daily, get_stock_fund_flow, get_stock_name,
    get_limit_down_pool, get_sector_fund_flow
)
import pandas as pd


class LimitDownAgent:
    """跌停原因分析器"""

    def analyze(self, symbol: str) -> Dict[str, Any]:
        """分析个股跌停原因"""
        # 获取当日跌停池
        pool = get_limit_down_pool()
        if pool.empty:
            return self._no_data_result("无跌停数据，可能非交易日")

        pool_str = pool.astype(str)
        match = pool_str[pool_str["代码"] == symbol]

        if match.empty:
            return {
                "is_limit_down": False,
                "type": None,
                "confidence": None,
                "description": "该股今日未跌停",
                "signals": [],
            }

        row = match.iloc[0]
        stock_name = get_stock_name(symbol)

        # 提取关键数据
        signals = []
        turnover = self._safe_float(row.get("换手率", 0))
        fengdan_amount = self._safe_float(row.get("封板资金", 0))
        kaiban_count = self._safe_int(row.get("开板次数", 0))
        industry = str(row.get("所属行业", ""))
        last_fengban_time = str(row.get("最后封板时间", ""))

        if industry:
            signals.append(f"所属行业：{industry}")
        if turnover > 0:
            signals.append(f"换手率：{turnover:.2f}%")
        if fengdan_amount != 0:
            signals.append(f"封单：{fengdan_amount:.1f}亿" if abs(fengdan_amount) > 1 else f"封单：{int(abs(fengdan_amount)*10000):.0f}万")
        if kaiban_count > 0:
            signals.append(f"开板{kaiban_count}次")
        if last_fengban_time:
            signals.append(f"封跌停时间：{last_fengban_time}")

        # 获取日K数据（一次调用，下游函数复用避免重复请求）
        df = get_stock_daily(symbol)

        # 获取个股资金流向
        fund_flow = get_stock_fund_flow(symbol)
        main_flow = fund_flow.get("主力净流入", 0) if fund_flow else 0
        if main_flow < 0:
            signals.append(f"主力净流出：{abs(main_flow):.0f}万元")

        # 获取板块信息
        sector_info = self._get_sector_info(industry)

        # 计算累计涨幅（复用上方已抓取的 df，避免再请求一次 akshare）
        cum_gain = self._calc_cumulative_gain_from_df(df)

        # 多条件打分
        result = self._score_and_classify(
            stock_name=stock_name,
            symbol=symbol,
            turnover=turnover,
            kaiban_count=kaiban_count,
            fengdan_amount=fengdan_amount,
            industry=industry,
            sector_info=sector_info,
            fund_flow=fund_flow,
            cum_gain=cum_gain,
        )

        result["signals"] = signals
        result["is_limit_down"] = True
        return result

    def _calc_cumulative_gain_from_df(self, df) -> Optional[float]:
        """基于已获取的 K 线 DataFrame 计算近 60 日累计涨幅，避免重复抓取"""
        try:
            if df is None or len(df) < 2 or not hasattr(df, "tail"):
                return None
            recent = df.tail(60)
            start_close = float(recent.iloc[0]["close"])
            end_close = float(recent.iloc[-1]["close"])
            if start_close <= 0:
                return None
            return (end_close / start_close - 1) * 100
        except Exception:
            return None

    def _score_and_classify(
        self, stock_name, symbol, turnover, kaiban_count,
        fengdan_amount, industry, sector_info, fund_flow, cum_gain,
    ) -> Dict[str, Any]:
        """多条件打分判定跌停类型"""
        scores = {
            "公司暴雷": 0,
            "主力出货": 0,
            "板块退潮": 0,
            "情绪崩塌": 0,
            "高位补跌": 0,
            "流动性危机": 0,
        }
        max_scores = {"公司暴雷": 3, "主力出货": 4, "板块退潮": 3, "情绪崩塌": 4, "高位补跌": 3, "流动性危机": 3}
        reasons = {k: [] for k in scores}

        main_flow = fund_flow.get("主力净流入", 0) if fund_flow else 0

        # --- 主力出货 ---
        if main_flow < -1000:
            scores["主力出货"] += 1
            reasons["主力出货"].append(f"主力净流出{abs(main_flow):.0f}万元")
        if turnover > 5:
            scores["主力出货"] += 1
            reasons["主力出货"].append(f"换手率{turnover:.1f}%，大量筹码转移")
        if fengdan_amount < 0 and abs(fengdan_amount) > 1:
            scores["主力出货"] += 1
            reasons["主力出货"].append("封单巨大，抛压沉重")
        if kaiban_count > 0:
            scores["主力出货"] += 1
            reasons["主力出货"].append(f"开板{kaiban_count}次，有资金试图托盘但抛压过大")

        # --- 情绪崩塌 ---
        if kaiban_count > 2:
            scores["情绪崩塌"] += 1
            reasons["情绪崩塌"].append(f"多次开板，多空分歧极大")
        if turnover > 10:
            scores["情绪崩塌"] += 1
            reasons["情绪崩塌"].append("超高换手，恐慌出逃")
        if cum_gain is not None and cum_gain > 30:
            scores["情绪崩塌"] += 1
            reasons["情绪崩塌"].append("前期涨幅较大，获利盘恐慌出逃")
        if 5 < turnover <= 10:
            scores["情绪崩塌"] += 1
            reasons["情绪崩塌"].append("换手率较高，市场恐慌情绪蔓延")

        # --- 板块退潮 ---
        if industry and sector_info and sector_info.get("涨跌幅", 0) < -2:
            scores["板块退潮"] += 1
            reasons["板块退潮"].append(f"所属板块{industry}整体走弱，跌幅{sector_info.get('涨跌幅', 0):.1f}%")
        if industry and sector_info and sector_info.get("流入", 0) < -1:
            scores["板块退潮"] += 1
            reasons["板块退潮"].append(f"板块资金大幅流出{sector_info.get('流入', 0):.1f}亿")
        if industry:
            scores["板块退潮"] += 1
            reasons["板块退潮"].append(f"所属板块{industry}集体走弱")

        # --- 高位补跌 ---
        if cum_gain is not None and cum_gain > 30:
            scores["高位补跌"] += 1
            reasons["高位补跌"].append(f"前期累计涨幅{cum_gain:.1f}%，有回调需求")
        if cum_gain is not None and cum_gain > 50:
            scores["高位补跌"] += 1
            reasons["高位补跌"].append(f"累计涨幅巨大（{cum_gain:.1f}%），补跌风险积累")
        if main_flow < -500:
            scores["高位补跌"] += 1
            reasons["高位补跌"].append("主力资金撤离，高位获利了结")

        # --- 流动性危机 ---
        if turnover < 1:
            scores["流动性危机"] += 1
            reasons["流动性危机"].append("换手率极低，无人接盘")
        if abs(fengdan_amount) > 2:
            scores["流动性危机"] += 1
            reasons["流动性危机"].append("封单巨大，市场承接力不足")
        if turnover < 0.5:
            scores["流动性危机"] += 1
            reasons["流动性危机"].append("流动性枯竭，开盘即封死跌停")

        # --- 公司暴雷（需要公告数据，用换手率+主力流向做辅助判断） ---
        if main_flow < -2000:
            scores["公司暴雷"] += 1
            reasons["公司暴雷"].append("主力资金大幅出逃，可能有未知利空")
        if turnover < 2 and main_flow < -1000:
            scores["公司暴雷"] += 1
            reasons["公司暴雷"].append("低换手+大单出逃，疑似利空导致的恐慌")
        if kaiban_count == 0 and turnover < 1:
            scores["公司暴雷"] += 1
            reasons["公司暴雷"].append("一字封死跌停，市场一致性看空")

        # 归一化打分
        for k in scores:
            scores[k] = scores[k] / max_scores[k] if max_scores[k] > 0 else 0

        # 取最高分
        best = max(scores, key=scores.get)
        best_score = scores[best]

        if best_score >= 0.75:
            confidence = "高"
        elif best_score >= 0.5:
            confidence = "中"
        else:
            confidence = "低"

        # 生成描述
        descriptions = {
            "公司暴雷": f"{stock_name}今日跌停属于**公司暴雷型**。疑似存在基本面利空或未知负面因素，资金不计成本出逃。",
            "主力出货": f"{stock_name}今日跌停属于**主力出货型**。主力资金持续净流出，高位派发迹象明显。",
            "板块退潮": f"{stock_name}今日跌停属于**板块退潮型**。所属{industry}板块整体走弱，资金集体撤离。",
            "情绪崩塌": f"{stock_name}今日跌停属于**情绪崩塌型**。市场恐慌情绪蔓延，多杀多导致踩踏。",
            "高位补跌": f"{stock_name}今日跌停属于**高位补跌型**。前期累计涨幅较大，获利盘集中兑现。",
            "流动性危机": f"{stock_name}今日跌停属于**流动性危机型**。市场承接力不足，少量抛压即可打至跌停。",
        }

        desc = descriptions.get(best, f"{stock_name}今日跌停。")
        if best_score >= 0.75:
            desc += " 信号明确。"
        elif best_score >= 0.5:
            desc += " 信号较明显，需持续观察。"
        else:
            desc += " 信号不充分，需结合更多信息。"

        return {
            "type": best,
            "confidence": confidence,
            "description": desc,
            "reasons": reasons[best] if reasons[best] else ["信号不明确"],
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }

    def _get_sector_info(self, industry: str) -> Optional[Dict[str, Any]]:
        """获取行业板块资金流向"""
        if not industry:
            return None
        try:
            from backend.services import get_sector_fund_flow
            df = get_sector_fund_flow()
            if df is None or df.empty:
                return None
            df_str = df.astype(str)
            match = df_str[df_str["名称"] == industry]
            if match.empty:
                return None
            row = match.iloc[0]
            return {
                "名称": industry,
                "涨跌幅": self._safe_float(row.get("今日涨跌幅", 0)),
                "流入": self._safe_float(row.get("主力净流入-净额", 0)),
            }
        except Exception:
            return None

    def _safe_float(self, val) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, val) -> int:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _no_data_result(self, reason: str) -> Dict[str, Any]:
        return {
            "is_limit_down": False,
            "type": None,
            "confidence": None,
            "description": reason,
            "signals": [],
        }
