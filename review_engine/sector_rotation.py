"""板块轮动分析工具

分析板块资金流向，判断哪些板块加强、哪些退潮。
"""
from typing import Any

from backend.services import get_sector_fund_flow


def analyze_sector_rotation() -> dict[str, Any]:
    """分析板块轮动情况"""
    df = get_sector_fund_flow()
    if df is None or df.empty:
        return {"加强": [], "退潮": [], "top5": [], "bottom5": []}

    try:
        records = []
        for _, row in df.iterrows():
            change = _safe_float(row.get("今日涨跌幅", 0))
            flow = _safe_float(row.get("主力净流入-净额", 0))
            name = str(row.get("名称", ""))
            records.append({
                "name": name,
                "change": change,
                "flow": flow,
                "flow_yi": round(flow / 1e8, 2),
                "flow_unit": "亿",
            })

        # 加强：涨幅+资金流入双正
        加强 = [r for r in records if r["change"] > 0 and r["flow"] > 0]
        加强.sort(key=lambda x: x["flow"], reverse=True)

        # 退潮：跌幅+资金流出
        退潮 = [r for r in records if r["change"] < 0 and r["flow"] < 0]
        退潮.sort(key=lambda x: x["flow"])

        # Top 5 净流入
        sorted_by_flow = sorted(records, key=lambda x: x["flow"], reverse=True)
        top5 = sorted_by_flow[:5]
        bottom5 = sorted_by_flow[-5:]

        return {
            "加强": [{"name": r["name"], "change": r["change"], "flow": r["flow"]} for r in 加强[:5]],
            "退潮": [{"name": r["name"], "change": r["change"], "flow": r["flow"]} for r in 退潮[:5]],
            "top5": [{"name": r["name"], "change": r["change"], "flow_yi": r["flow_yi"], "flow_unit": r["flow_unit"]} for r in top5],
            "bottom5": [{"name": r["name"], "change": r["change"], "flow_yi": r["flow_yi"], "flow_unit": r["flow_unit"]} for r in bottom5],
        }
    except Exception:
        return {"加强": [], "退潮": [], "top5": [], "bottom5": []}


def _safe_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
