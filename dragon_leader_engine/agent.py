"""龙头股识别 Agent

识别全市场龙头股，包括总龙头、板块龙头、连板高标、日内龙头。
"""
from datetime import datetime
from typing import Any

import pandas as pd

from backend.services import (
    get_limit_up_pool,
    get_realtime_quote_map,
)


class DragonLeaderAgent:
    """全市场龙头股识别器"""

    def analyze(self, market: str = "all") -> dict[str, Any]:
        """分析全市场龙头股

        Returns:
            leaders: 全量排名列表（按综合分降序）
            top_leader: 总龙头
            sector_leaders: 各板块龙头
            日内龙头: 首次封板最早的票
            连板高标: 连板数 >= 5 的票
            market_summary: 市场概况
        """
        pool = get_limit_up_pool()
        if pool.empty:
            return self._empty_result("无涨停数据，可能非交易日")

        # 解析候选股
        candidates = self._parse_candidates(pool)
        if not candidates:
            return self._empty_result("未找到涨停候选股")

        # 统计各板块涨停数（用于板块影响力评分）
        sector_stock_count = self._count_sector_stocks(candidates)

        # 逐股评分
        scored = []
        for c in candidates:
            score, details = self._score_stock(c, sector_stock_count)
            c["score"] = round(score, 3)
            c["score_details"] = details
            scored.append(c)

        # 按综合分降序
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 识别各类龙头
        top_leader = scored[0] if scored else None

        # 板块龙头（各行业最高分）
        sector_leaders = self._find_sector_leaders(scored)

        # 日内龙头（首次封板最早的票）
        日内龙头 = self._find_日内龙头(candidates)

        # 连板高标
        连板高标 = [s for s in scored if s["boards"] >= 5]

        return {
            "leaders": scored[:20],  # 最多返回20只
            "top_leader": top_leader,
            "sector_leaders": sector_leaders,
            "日内龙头": 日内龙头,
            "连板高标": 连板高标,
            "market_summary": {
                "涨停数": len(candidates),
                "连板股数": len([s for s in candidates if s["boards"] >= 2]),
                "最高板": scored[0]["boards"] if scored else 0,
            },
        }

    def _parse_candidates(self, pool: pd.DataFrame) -> list[dict[str, Any]]:
        """从涨停池解析候选股

        优化：先收集所有候选 symbol，再用 get_realtime_quote_map 一次性查询，
        避免对每只股票分别调用 akshare（N+1 问题，可能达到 50~100 次远程请求）。
        资金流向 (stock_individual_fund_flow) 没有批量接口，但龙头评分中
        资金力度仅占 10/100，且每股一次请求耗时较高，因此在此跳过个股资金流向，
        只用涨停池自带的 “封板资金” + “换手率” + “首次封板时间” 已可完成评分。
        """
        symbols = []
        rows_data = []
        for _, row in pool.iterrows():
            try:
                symbol = str(row.get("代码", ""))
                boards = self._safe_float(row.get("连板数", 0))
                if not symbol or boards <= 0:
                    continue
                symbols.append(symbol)
                rows_data.append({
                    "symbol": symbol,
                    "name": str(row.get("名称", "")),
                    "boards": int(boards),
                    "fengdan": self._safe_float(row.get("封板资金", 0)),
                    "fengcheng_ratio": self._safe_float(row.get("封成比", 0)),
                    "turnover": self._safe_float(row.get("换手率", 0)),
                    "industry": str(row.get("所属行业", "")),
                    "first_time": str(row.get("首次封板时间", "")),
                    "last_time": str(row.get("最后封板时间", "")),
                    "amount": self._safe_float(row.get("成交额", 0)),
                })
            except Exception:
                continue

        quote_map = get_realtime_quote_map(symbols) if symbols else {}
        candidates = []
        for r in rows_data:
            q = quote_map.get(r["symbol"], {})
            market_cap = q.get("总市值", 0) or 0
            r["market_cap"] = market_cap / 1e8 if market_cap else 0
            r["price"] = q.get("最新价", 0) or 0
            r["main_flow"] = 0  # 评分中此项默认 0，避免对每股请求资金流向
            candidates.append(r)
        return candidates

    def _count_sector_stocks(self, candidates: list[dict]) -> dict[str, int]:
        """统计各行业涨停股数"""
        counts = {}
        for c in candidates:
            ind = c.get("industry", "")
            if ind:
                counts[ind] = counts.get(ind, 0) + 1
        return counts

    def _score_stock(self, stock: dict, sector_counts: dict[str, int]) -> tuple:
        """多维度评分"""
        details = {}
        total = 0.0

        # 1. 连板高度 (0-30分)
        b = stock["boards"]
        board_score = min(b / 10, 1.0) * 30
        total += board_score
        details["连板高度"] = round(board_score, 1)

        # 2. 封板强度 (0-15分)
        if stock["amount"] > 0 and stock["fengdan"] > 0:
            strength = min(stock["fengdan"] / max(stock["amount"], 0.1), 5)
            fengdan_score = min(strength / 5, 1.0) * 15
        else:
            fengdan_score = 0
        total += fengdan_score
        details["封板强度"] = round(fengdan_score, 1)

        # 3. 板块影响力 (0-20分)
        ind = stock.get("industry", "")
        cnt = sector_counts.get(ind, 0)
        sector_score = min(cnt / 10, 1.0) * 20
        total += sector_score
        details["板块影响力"] = round(sector_score, 1)

        # 4. 封板时间 (0-15分)
        ft = stock.get("first_time", "")
        time_score = self._time_score(ft) * 15
        total += time_score
        details["封板时间"] = round(time_score, 1)

        # 5. 资金力度 (0-10分)
        if stock["main_flow"] > 0:
            flow_score = min(stock["main_flow"] / 10000, 1.0) * 10
        else:
            flow_score = 0
        total += flow_score
        details["资金力度"] = round(flow_score, 1)

        # 6. 换手率健康度 (0-10分)
        t = stock["turnover"]
        if 0 < t <= 5:
            turnover_score = 10  # 低换手 = 筹码锁定好
        elif t <= 10:
            turnover_score = 7
        elif t <= 20:
            turnover_score = 4
        else:
            turnover_score = 1
        total += turnover_score
        details["换手率健康度"] = turnover_score

        return total, details

    def _time_score(self, time_str: str) -> float:
        """封板时间打分: 越早越高"""
        if not time_str or time_str == "nan":
            return 0.3
        try:
            t = datetime.strptime(time_str.strip(), "%H:%M:%S")
            # 9:25 = 1.0, 10:00 = 0.8, 11:30 = 0.5, 15:00 = 0.0
            minutes = (t.hour - 9) * 60 + t.minute
            if t.hour < 9:
                return 1.0
            if minutes <= 0:
                return 1.0
            score = max(0, 1 - minutes / 300)
            return score
        except (ValueError, AttributeError):
            return 0.3

    def _find_sector_leaders(self, scored: list[dict]) -> list[dict]:
        """各行业最高分作为板块龙头"""
        seen = {}
        for s in scored:
            ind = s.get("industry", "")
            if not ind or ind == "nan":
                continue
            if ind not in seen:
                seen[ind] = s
        return list(seen.values())

    def _find_日内龙头(self, candidates: list[dict]) -> dict | None:
        """首次封板最早的票"""
        valid = [c for c in candidates if c.get("first_time") and c["first_time"] != "nan"]
        if not valid:
            return None
        valid.sort(key=lambda x: x["first_time"])
        return valid[0]

    def _safe_float(self, val) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "leaders": [],
            "top_leader": None,
            "sector_leaders": [],
            "日内龙头": None,
            "连板高标": [],
            "market_summary": {"涨停数": 0, "连板股数": 0, "最高板": 0},
            "description": reason,
        }
