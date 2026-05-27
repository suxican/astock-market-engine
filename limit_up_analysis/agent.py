"""涨停原因分析 Agent

基于文档第五章规则，识别涨停背后的真正原因：
政策催化、资金驱动、情绪炒作、龙头带动、基本面驱动
"""
from typing import Dict, Any, Optional
from datetime import datetime
from backend.services import (
    get_stock_daily, get_stock_fund_flow, get_stock_name,
    get_realtime_quote, get_limit_up_pool, get_lhb_detail,
    get_sector_fund_flow
)


class LimitUpAgent:
    """涨停原因分析器"""

    # 知名游资席位关键词（简化版，实际可从数据库加载）
    KNOWN_HOTELS = {
        "国泰君安": "国君系",
        "华泰证券": "华泰系",
        "中信证券": "中信系",
        "中国银河": "银河系",
        "招商证券": "招商系",
        "东方财富": "东财系",
        "海通证券": "海通系",
        "广发证券": "广发系",
        "中金公司": "中金系",
        "光大证券": "光大系",
    }

    def analyze(self, symbol: str) -> Dict[str, Any]:
        """分析个股涨停原因"""
        # 获取当日涨停池
        pool = get_limit_up_pool()
        if pool.empty:
            return self._no_data_result("无涨停数据，可能非交易日")

        # 查找该股是否在涨停池中
        pool_str = pool.astype(str)
        match = pool_str[pool_str["代码"] == symbol]

        if match.empty:
            return {
                "is_limit_up": False,
                "type": None,
                "confidence": None,
                "description": "该股今日未涨停",
                "signals": [],
                "lhb": None,
            }

        row = match.iloc[0]
        stock_name = get_stock_name(symbol)

        # 提取关键数据
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

        # 获取龙虎榜数据判断游资/机构
        lhb_data = self._get_lhb_info(symbol)

        # 获取板块资金流向
        sector_info = self._get_sector_info(industry)

        # 获取个股资金流向
        fund_flow = get_stock_fund_flow(symbol)

        # 多条件打分判定涨停类型
        result = self._score_and_classify(
            symbol=symbol,
            stock_name=stock_name,
            board_count=board_count,
            zhaban_count=zhaban_count,
            fengdan_amount=fengdan_amount,
            last_fengban_time=last_fengban_time,
            industry=industry,
            turnover=turnover,
            fengcheng_ratio=fengcheng_ratio,
            lhb=lhb_data,
            sector_info=sector_info,
            fund_flow=fund_flow,
        )

        result["signals"] = signals
        result["lhb"] = lhb_data
        result["is_limit_up"] = True
        return result

    def _score_and_classify(
        self, symbol, stock_name, board_count, zhaban_count,
        fengdan_amount, last_fengban_time, industry,
        turnover, fengcheng_ratio, lhb, sector_info, fund_flow,
    ) -> Dict[str, Any]:
        """多条件打分判定涨停类型"""
        scores = {
            "政策催化": 0,
            "资金驱动": 0,
            "情绪炒作": 0,
            "龙头带动": 0,
            "基本面驱动": 0,
        }
        max_scores = {"政策催化": 4, "资金驱动": 4, "情绪炒作": 4, "龙头带动": 4, "基本面驱动": 4}
        reasons = {k: [] for k in scores}

        # --- 政策催化 ---
        # 如果有明确的行业归属且板块资金流入
        if industry and sector_info and sector_info.get("流入", 0) > 0:
            scores["政策催化"] += 1
            reasons["政策催化"].append(f"所属板块{industry}资金净流入{sector_info.get('流入', 0):.1f}亿")
        # 早盘封板（政策驱动往往早盘快速封板）
        if last_fengban_time and last_fengban_time < "10:00":
            scores["政策催化"] += 1
            reasons["政策催化"].append("早盘快速封板，政策催化特征明显")
        # 封单大
        if fengdan_amount > 2:
            scores["政策催化"] += 1
            reasons["政策催化"].append("封单量大，资金坚决")
        # 低换手封板（惜售）
        if turnover < 3:
            scores["政策催化"] += 1
            reasons["政策催化"].append("换手率低，筹码锁定良好")

        # --- 资金驱动 ---
        main_flow = fund_flow.get("主力净流入", 0) if fund_flow else 0
        if main_flow > 0:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append(f"主力净流入{main_flow:.0f}万元")
        if fengdan_amount > 1:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append(f"封板资金{fengdan_amount:.1f}亿，资金实力强")
        if lhb and lhb.get("has_hotel", False):
            scores["资金驱动"] += 1
            reasons["资金驱动"].append(f"龙虎榜出现知名游资席位：{lhb.get('hotel_names', '')}")
        if turnover > 5:
            scores["资金驱动"] += 1
            reasons["资金驱动"].append("换手率超5%，资金博弈活跃")

        # --- 情绪炒作 ---
        if board_count >= 3:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append(f"已连板{int(board_count)}板，情绪驱动特征")
        if zhaban_count > 0:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append(f"炸板{zhaban_count}次后回封，多空分歧大")
        if turnover > 8:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("超高换手，短线资金博弈")
        if board_count >= 5:
            scores["情绪炒作"] += 1
            reasons["情绪炒作"].append("高度板，纯情绪博弈阶段")

        # --- 龙头带动 ---
        if board_count >= 3:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append(f"连板{int(board_count)}板，具备龙头气质")
        if fengcheng_ratio > 0:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append("封成比良好，封板决心强")
        if industry and sector_info and sector_info.get("涨跌幅", 0) > 2:
            scores["龙头带动"] += 1
            reasons["龙头带动"].append(f"所属板块{industry}涨幅{sector_info.get('涨跌幅', 0):.1f}%，板块联动")
        if last_fengban_time and last_fengban_time < "09:45":
            scores["龙头带动"] += 1
            reasons["龙头带动"].append("开盘即封板，龙头带动效应显著")

        # --- 基本面驱动 ---
        # 这个需要财报数据，先简单判断
        # 低换手+早盘封板+有龙虎榜机构买入 = 基本面驱动
        if turnover < 3 and lhb and lhb.get("has_institution", False):
            scores["基本面驱动"] += 1
            reasons["基本面驱动"].append("机构席位买入，基本面逻辑支撑")
        if fengcheng_ratio > 2:
            scores["基本面驱动"] += 1
            reasons["基本面驱动"].append("封成比极高，资金看好长期价值")

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
            "政策催化": f"该股涨停属于**政策催化型**。受益于{industry}板块的政策利好，资金抢筹明显，",
            "资金驱动": f"该股涨停属于**资金驱动型**。大单资金持续买入推动涨停，",
            "情绪炒作": f"该股涨停属于**情绪炒作型**。市场情绪高涨，短线资金接力推动封板，",
            "龙头带动": f"该股涨停属于**龙头带动型**。作为{industry}板块龙头，带动效应显著，",
            "基本面驱动": f"该股涨停属于**基本面驱动型**。有业绩/订单/重组等硬基本面支撑，",
        }

        desc = descriptions.get(best, "该股今日涨停，")
        if best_score >= 0.75:
            desc += "信号明确。"
        elif best_score >= 0.5:
            desc += "信号较为明确，需持续观察。"
        else:
            desc += "信号尚不充分，需结合更多信息判断。"

        # 补充风险提示
        if board_count >= 5:
            desc += f" 注意：已连板{int(board_count)}板，高位情绪博弈风险较大。"
        if turnover > 10:
            desc += " 换手率极高，注意资金分歧风险。"

        return {
            "type": best,
            "confidence": confidence,
            "description": desc,
            "reasons": reasons[best] if reasons[best] else ["信号不明确"],
            "all_scores": {k: round(v, 2) for k, v in scores.items()},
        }

    def _get_lhb_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取龙虎榜信息"""
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
            "has_hotel": False,
            "hotel_names": "",
            "has_institution": False,
        }

        # 判断是否有机构买入
        if result["机构净买入"] > 0:
            result["has_institution"] = True

        # 判断是否有知名游资（简化版，从买方席位判断）
        buy_detail = str(row.get("买方详情", ""))
        if buy_detail:
            for hotel_name in self.KNOWN_HOTELS:
                if hotel_name in buy_detail:
                    result["has_hotel"] = True
                    result["hotel_names"] += f"{hotel_name} "
            result["hotel_names"] = result["hotel_names"].strip()

        return result

    def _get_sector_info(self, industry: str) -> Optional[Dict[str, Any]]:
        """获取行业板块资金流向"""
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
        return {
            "名称": industry,
            "涨跌幅": self._safe_float(row.get("今日涨跌幅", 0)),
            "流入": self._safe_float(row.get("主力净流入-净额", 0)),
        }

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
            "is_limit_up": False,
            "type": None,
            "confidence": None,
            "description": reason,
            "signals": [],
            "lhb": None,
        }
