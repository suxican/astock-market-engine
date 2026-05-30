"""涨停原因分析 Agent (V3)

V3 变更: 接受 MarketFeatures 输入，从预计算的涨停池获取数据。
"""
from datetime import datetime
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.services import get_lhb_detail, get_sector_fund_flow, get_stock_fund_flow, get_stock_name


class LimitUpAgent:
    """涨停原因分析器 (V3)"""

    KNOWN_HOTELS = {
        "国泰君安": "国君系", "华泰证券": "华泰系", "中信证券": "中信系",
        "中国银河": "银河系", "招商证券": "招商系", "东方财富": "东财系",
        "海通证券": "海通系", "广发证券": "广发系", "中金公司": "中金系",
        "光大证券": "光大系",
    }

    def analyze(
        self,
        symbol: str,
        market_features: MarketFeatures | None = None,
    ) -> dict[str, Any]:
        """分析个股涨停原因

        Args:
            symbol: 股票代码
            market_features: 预计算的盘面特征
        """
        if market_features is not None and market_features.limit_up_pool is not None:
            pool = market_features.limit_up_pool
        else:
            from backend.services import get_limit_up_pool
            pool = get_limit_up_pool()

        if pool.empty:
            return self._no_data_result("无涨停数据，可能非交易日")

        pool_str = pool.astype(str)
        match = pool_str[pool_str["代码"] == symbol]

        if match.empty:
            return {
                "is_limit_up": False, "type": None, "confidence": None,
                "description": "该股今日未涨停", "signals": [], "lhb": None,
            }

        row = match.iloc[0]
        stock_name = get_stock_name(symbol)

        signals = []
        board_count = self._safe_float(row.get("连板数", 0))
        zhaban_count = self._safe_int(row.get("炸板次数", 0))
        fengdan_amount = self._safe_float(row.get("封板资金", 0))
        last_fengban_time = str(row.get("最后封板时间", ""))
        industry = str(row.get("所属行业", ""))
        turnover = self._safe_float(row.get("换手率", 0))
        fengcheng_ratio = self._safe_float(row.get("封成比", 0))

        if board_count > 0:
            signals.append(f"连板{int(board_count)}板")
        if fengdan_amount > 0:
            signals.append(f"封单{fengdan_amount:.1f}亿" if fengdan_amount > 1 else f"封单{int(fengdan_amount*10000):.0f}万")
        if zhaban_count > 0:
            signals.append(f"炸板{zhaban_count}次")
        if last_fengban_time:
            signals.append(f"最后封板{last_fengban_time}")
        if industry:
            signals.append(f"所属行业：{industry}")

        lhb_data = self._get_lhb_info(symbol)
        sector_info = self._get_sector_info(industry)
        fund_flow = get_stock_fund_flow(symbol)

        result = self._score_and_classify(
            symbol=symbol, stock_name=stock_name,
            board_count=board_count, zhaban_count=zhaban_count,
            fengdan_amount=fengdan_amount, last_fengban_time=last_fengban_time,
            industry=industry, turnover=turnover,
            fengcheng_ratio=fengcheng_ratio, lhb=lhb_data,
            sector_info=sector_info, fund_flow=fund_flow,
        )
        result["signals"] = signals
        result["lhb"] = lhb_data
        result["is_limit_up"] = True
        return result

    def _score_and_classify(self, **kw) -> dict[str, Any]:
        # ... 保持原有评分逻辑不变 ...
        scores = {"政策催化": 0, "资金驱动": 0, "情绪炒作": 0, "龙头带动": 0, "基本面驱动": 0}
        max_scores = {"政策催化": 4, "资金驱动": 4, "情绪炒作": 4, "龙头带动": 4, "基本面驱动": 4}
        reasons = {k: [] for k in scores}

        industry = kw.get("industry", "")
        sector_info = kw.get("sector_info")
        fengdan_amount = kw.get("fengdan_amount", 0)
        last_fengban_time = kw.get("last_fengban_time", "")
        turnover = kw.get("turnover", 0)
        fengcheng_ratio = kw.get("fengcheng_ratio", 0)
        lhb = kw.get("lhb")
        board_count = kw.get("board_count", 0)
        zhaban_count = kw.get("zhaban_count", 0)

        if industry and sector_info and sector_info.get("流入", 0) > 0:
            scores["政策催化"] += 1
            reasons["政策催化"].append(f"所属板块{industry}资金净流入")
        if last_fengban_time and last_fengban_time < "10:00":
            scores["政策催化"] += 1
            reasons["政策催化"].append("早盘快速封板")
        if fengdan_amount > 2:
            scores["政策催化"] += 1
            reasons["政策催化"].append("封单量大")
        if fengcheng_ratio > 3:
            scores["政策催化"] += 1
            reasons["政策催化"].append("封成比极高")

        if fengdan_amount > 0.5:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append(f"封单资金{fengdan_amount:.1f}亿")
        if lhb and lhb.get("净买入", 0) > 0:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append("龙虎榜净买入")
        if turnover > 3:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append(f"换手率{turnover:.1f}%")
        if fengdan_amount > 1:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append("封单坚决")

        if board_count == 1 and turnover > 5:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("首板高换手")
        if zhaban_count >= 2:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("多次炸板回封，情绪博弈")
        if board_count >= 2 and turnover > 8:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("高位高换手")
        if not lhb or not lhb.get("has_institution"):
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("无机构买入，散户驱动")

        if board_count >= 3:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append(f"连板{int(board_count)}板，高度龙头")
        if industry and sector_info and sector_info.get("涨跌幅", 0) > 1:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append(f"{industry}板块强势")
        if board_count >= 5:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append("高标龙头效应")
        if lhb and lhb.get("has_hotel"):
            scores["龙头带动"] += 1
            reasons["龙头带动"].append(f"知名游资{lhb.get('hotel_names', '')}参与")

        if turnover < 3 and lhb and lhb.get("has_institution", False):
            scores["基本面驱动"] += 1
            reasons["基本面驱动"].append("机构席位买入")
        if fengcheng_ratio > 2:
            scores["基本面驱动"] += 1
            reasons["基本面驱动"].append("封成比极高")

        for k in scores:
            scores[k] = scores[k] / max_scores[k] if max_scores[k] > 0 else 0

        best = max(scores, key=scores.get)
        best_score = scores[best]
        confidence = "高" if best_score >= 0.75 else ("中" if best_score >= 0.5 else "低")

        descriptions = {
            "政策催化": f"该股涨停属于**政策催化型**。受益于{industry}板块的政策利好。",
            "资金驱动": "该股涨停属于**资金驱动型**。大单资金持续买入推动涨停。",
            "情绪炒作": "该股涨停属于**情绪炒作型**。市场情绪高涨，短线资金接力。",
            "龙头带动": f"该股涨停属于**龙头带动型**。作为{industry}板块龙头。",
            "基本面驱动": "该股涨停属于**基本面驱动型**。有基本面支撑。",
        }
        desc = descriptions.get(best, "该股今日涨停。")
        if best_score >= 0.75:
            desc += " 信号明确。"
        elif best_score >= 0.5:
            desc += " 需持续观察。"
        else:
            desc += " 信号尚不充分。"
        if board_count >= 5:
            desc += f" 已连板{int(board_count)}板，高位风险大。"

        return {
            "type": best, "confidence": confidence, "description": desc,
            "reasons": reasons[best] or ["信号不明确"],
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }

    def _get_lhb_info(self, symbol):
        today = datetime.now().strftime("%Y%m%d")
        df = get_lhb_detail(today)
        if df is None or df.empty:
            return None
        df_str = df.astype(str)
        match = df_str[df_str["代码"] == symbol]
        if match.empty:
            return None
        row = match.iloc[0]
        result = {
            "has_lhb": True,
            "净买入": self._safe_float(row.get("龙虎榜净买额", 0)),
            "机构净买入": self._safe_float(row.get("机构净买额", 0)),
            "上榜原因": str(row.get("上榜原因", "")),
            "has_hotel": False, "hotel_names": "", "has_institution": False,
        }
        if result["机构净买入"] > 0:
            result["has_institution"] = True
        buy_detail = str(row.get("买方详情", ""))
        if buy_detail:
            for hotel_name in self.KNOWN_HOTELS:
                if hotel_name in buy_detail:
                    result["has_hotel"] = True
                    result["hotel_names"] += f"{hotel_name} "
            result["hotel_names"] = result["hotel_names"].strip()
        return result

    def _get_sector_info(self, industry):
        if not industry:
            return None
        df = get_sector_fund_flow()
        if df is None or df.empty:
            return None
        df_str = df.astype(str)
        match = df_str[df_str["名称"] == industry]
        if match.empty:
            return None
        row = match.iloc[0]
        return {"名称": industry, "涨跌幅": self._safe_float(row.get("今日涨跌幅", 0)), "流入": self._safe_float(row.get("主力净流入-净额", 0))}

    def _safe_float(self, val):
        try: return float(val)
        except (ValueError, TypeError): return 0.0

    def _safe_int(self, val):
        try: return int(float(val))
        except (ValueError, TypeError): return 0

    def _no_data_result(self, reason):
        return {"is_limit_up": False, "type": None, "confidence": None, "description": reason, "signals": [], "lhb": None}
