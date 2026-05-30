"""龙头股识别 Agent (V3 — 增强版)

V3 增强:
  - seal_ratio: 封单金额/流通市值 (衡量封板资金力度)
  - sector_rank: 板块内龙头排名 (同板块涨停股中连板数排名)
  - mention_count: 舆情提及次数 (集成事件引擎热词, 占位为0待扩展)

龙头评分逻辑:
  连板高度 (25) + 封板强度 (15) + seal_ratio (10) +
  板块影响力 (15) + 封板时间 (10) + 换手率 (10) +
  sector_rank (10) + mention_count (5)
"""
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.services import get_realtime_quote_map


class DragonLeaderAgent:
    """全市场龙头股识别器 (V3 增强版)"""

    def analyze(
        self,
        market: str = "all",
        market_features: MarketFeatures | None = None,
    ) -> dict[str, Any]:
        """分析全市场龙头股"""
        if market_features is not None and market_features.limit_up_pool is not None:
            pool = market_features.limit_up_pool
        else:
            from backend.services import get_limit_up_pool
            pool = get_limit_up_pool()

        if pool.empty:
            return self._empty_result("无涨停数据，可能非交易日")

        candidates = self._parse_candidates(pool)
        if not candidates:
            return self._empty_result("未找到涨停候选股")

        sector_stock_count = self._count_sector_stocks(candidates)
        sector_rank_map = self._calc_sector_ranks(candidates)

        scored = []
        for c in candidates:
            rank = sector_rank_map.get(c["symbol"], 1)
            score, details = self._score_stock(c, sector_stock_count, rank)
            c["score"] = round(score, 3)
            c["score_details"] = details
            c["seal_ratio"] = self._calc_seal_ratio(c)
            c["sector_rank"] = rank
            c["mention_count"] = 0  # 占位: 集成事件引擎热词时填充
            scored.append(c)

        scored.sort(key=lambda x: x["score"], reverse=True)

        top_leader = scored[0] if scored else None
        sector_leaders = self._find_sector_leaders(scored)
        日内龙头 = self._find_日内龙头(candidates)
        连板高标 = [s for s in scored if s["boards"] >= 5]

        return {
            "leaders": scored[:20],
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

    # ── 新增: 计算 seal_ratio ──

    def _calc_seal_ratio(self, c: dict) -> float:
        """封单强度 = 封单金额(亿) / 流通市值(亿)"""
        fengdan = c.get("fengdan", 0)  # 亿
        market_cap = c.get("market_cap", 0)  # 亿
        if market_cap > 0 and fengdan > 0:
            return round(fengdan / market_cap, 4)
        return 0.0

    # ── 新增: 计算板块内排名 ──

    def _calc_sector_ranks(self, candidates: list[dict]) -> dict[str, int]:
        """计算每只股票在其板块内的连板数排名 (1=最高)"""
        sector_groups: dict[str, list[dict]] = {}
        for c in candidates:
            ind = c.get("industry", "")
            if ind:
                sector_groups.setdefault(ind, []).append(c)

        rank_map: dict[str, int] = {}
        for ind, stocks in sector_groups.items():
            sorted_stocks = sorted(stocks, key=lambda x: x["boards"], reverse=True)
            for i, s in enumerate(sorted_stocks):
                rank_map[s["symbol"]] = i + 1
        return rank_map

    # ── 原有方法 (微调评分权重) ──

    def _parse_candidates(self, pool) -> list[dict[str, Any]]:
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
            r["main_flow"] = 0
            candidates.append(r)
        return candidates

    def _count_sector_stocks(self, candidates):
        counts = {}
        for c in candidates:
            ind = c.get("industry", "")
            if ind:
                counts[ind] = counts.get(ind, 0) + 1
        return counts

    def _score_stock(self, c, sector_stock_count, sector_rank=1) -> tuple[float, dict]:
        score = 0.0
        details = {}

        # 连板高度 (0-25)
        boards = c.get("boards", 0)
        board_score = min(25, boards * 5)
        score += board_score
        details["连板高度"] = board_score

        # 封板强度 (0-15)
        fengdan = c.get("fengdan", 0)
        feng_score = min(15, fengdan * 1.5)
        score += feng_score
        details["封板强度"] = feng_score

        # 封单/流通市值比 (0-10)
        seal = self._calc_seal_ratio(c)
        seal_score = min(10, seal * 100)  # seal=0.1 → 10分
        score += seal_score
        details["封单强度比"] = round(seal_score, 1)

        # 板块影响力 (0-15)
        industry = c.get("industry", "")
        sector_count = sector_stock_count.get(industry, 0)
        sector_score = min(15, sector_count * 3)
        score += sector_score
        details["板块影响力"] = sector_score

        # 封板时间 (0-10)
        first_time = c.get("first_time", "")
        if first_time and first_time < "10:00":
            time_score = 10
        elif first_time and first_time < "13:00":
            time_score = 7
        else:
            time_score = 3
        score += time_score
        details["封板时间"] = time_score

        # 换手率 (0-10)
        turnover = c.get("turnover", 0)
        if 3 <= turnover <= 15:
            turn_score = 10
        elif turnover < 3:
            turn_score = 7
        else:
            turn_score = 3
        score += turn_score
        details["换手率"] = turn_score

        # 板块内排名 (0-10, rank=1 → 10分)
        rank_score = max(0, 10 - (sector_rank - 1) * 3)
        score += rank_score
        details["板块排名"] = rank_score

        # 舆情热度 (0-5, 占位)
        mention = c.get("mention_count", 0)
        mention_score = min(5, mention * 0.5) if mention > 0 else 0
        score += mention_score
        details["舆情热度"] = mention_score

        return score, details

    def _find_sector_leaders(self, scored):
        seen = set()
        leaders = []
        for s in scored:
            ind = s.get("industry", "")
            if ind and ind not in seen:
                seen.add(ind)
                leaders.append(s)
        return leaders[:10]

    def _find_日内龙头(self, candidates):
        early = None
        for c in candidates:
            t = c.get("first_time", "")
            if t and (early is None or t < early.get("first_time", "zz")):
                early = c
        return early

    def _safe_float(self, val) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def _empty_result(self, reason):
        return {
            "leaders": [],
            "top_leader": None,
            "sector_leaders": [],
            "日内龙头": None,
            "连板高标": [],
            "market_summary": {"涨停数": 0, "连板股数": 0, "最高板": 0},
        }
