"""板块轮动分析 Agent

双维度分析（行业+概念板块），状态分类（加强/持续/退潮/反弹），涨停分布统计。
"""
from typing import Any

from backend.services import get_limit_up_pool, get_sector_fund_flow_by_type


class SectorRotationAgent:
    """板块轮动分析器"""

    def analyze(self) -> dict[str, Any]:
        """分析全市场板块轮动

        Returns:
            industry: 行业板块分析
            concept: 概念板块分析
            最强板块: 综合得分最高的板块
        """
        industry = self._analyze_type("行业资金流向")
        concept = self._analyze_type("概念资金流向")
        board_dist = self._analyze_board_distribution()

        # 综合最强板块
        最强 = None
        最强_score = 0
        for b in board_dist:
            if b["涨停数"] >= 3 and b.get("flow", 0) > 0:
                s = b["涨停数"] * 2 + b.get("change", 0)
                if s > 最强_score:
                    最强_score = s
                    最强 = b["name"] if b.get("name") else None

        return {
            "industry": industry,
            "concept": concept,
            "board_distribution": board_dist[:10],
            "最强板块": 最强 or "无明显最强板块",
            "最强板块涨停数": max([b["涨停数"] for b in board_dist], default=0),
        }

    def _analyze_type(self, sector_type: str) -> dict[str, Any]:
        """分析一类板块（行业/概念）"""
        df = get_sector_fund_flow_by_type(sector_type)
        if df is None or df.empty:
            return {"加强": [], "持续": [], "退潮": [], "反弹": []}

        records = []
        for _, row in df.iterrows():
            change = self._safe_float(row.get("今日涨跌幅", 0))
            flow = self._safe_float(row.get("主力净流入-净额", 0))
            name = str(row.get("名称", ""))
            records.append({
                "name": name,
                "change": round(change, 2),
                "flow": round(flow, 2),
                "flow_yi": round(flow / 1e8, 2),
            })

        # 状态分类
        result = {"加强": [], "持续": [], "退潮": [], "反弹": []}

        for r in records:
            if r["change"] > 0 and r["flow"] > 0:
                result["加强"].append(r)
            elif r["change"] > 0 and r["flow"] <= 0:
                result["持续"].append(r)
            elif r["change"] < 0 and r["flow"] < 0:
                result["退潮"].append(r)
            elif r["change"] < 0 and r["flow"] >= 0:
                result["反弹"].append(r)

        # 按资金流排序
        for k in result:
            result[k] = sorted(result[k], key=lambda x: abs(x["flow"]), reverse=True)[:10]

        return result

    def _analyze_board_distribution(self) -> list[dict]:
        """统计各行业涨停分布"""
        pool = get_limit_up_pool()
        if pool.empty:
            return []

        from collections import Counter
        industries = pool["所属行业"].dropna().astype(str).tolist()
        # 统计涨停数
        cnt = Counter(industries)
        # 获取板块资金流向
        df = get_sector_fund_flow_by_type("行业资金流向")
        flow_map = {}
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                name = str(row.get("名称", ""))
                flow_map[name] = {
                    "flow": self._safe_float(row.get("主力净流入-净额", 0)),
                    "change": self._safe_float(row.get("今日涨跌幅", 0)),
                }

        result = []
        for ind, count in cnt.most_common(20):
            info = flow_map.get(ind, {})
            result.append({
                "name": ind,
                "涨停数": count,
                "flow": info.get("flow", 0),
                "change": info.get("change", 0),
            })

        return result

    def _safe_float(self, val) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
