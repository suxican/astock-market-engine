"""个股综合分析 Agent (V3)

V3 变更: 接受 StockFeatures + StockScores 输入，不再重复调用 services 层。
收敛到 FeatureEngine → ScoreEngine → AI Explain Layer 架构。
"""
from typing import Any

from backend.feature_engine.stock_features import StockFeatures
from backend.score_engine.stock_scores import StockScores, compute_stock_scores


class StockAnalysisAgent:
    """个股综合分析器 (V3)"""

    def analyze(
        self,
        sf: StockFeatures,
        scores: StockScores | None = None,
        fund_flow: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """综合分析一只股票

        Args:
            sf: 个股特征快照（从 FeatureEngine 预计算）
            scores: 个股评分（从 ScoreEngine 预计算，可选）
            fund_flow: 资金流向数据（可选，StockFeatures 已包含 main_flow 等）
        """
        if sf.close == 0:
            return {"error": "无数据"}

        # 复用预计算评分，避免重复计算
        if scores is None:
            scores = compute_stock_scores(sf)

        ff = fund_flow or {
            "主力净流入": sf.main_flow,
            "大单净流入": sf.large_order_flow,
            "小单净流入": sf.small_order_flow,
        }

        return {
            "latest_price": sf.close,
            "pct_change": sf.pct_change,
            "volume": sf.volume,
            "turnover": sf.turnover,
            "ma_20": sf.ma_20,
            "ma_60": sf.ma_60,
            "scores": scores.to_dict() if hasattr(scores, "to_dict") else {},
            "capital_analysis": {
                "stage": scores.main_capital.stage,
                "confidence": scores.main_capital.confidence,
                "description": scores.main_capital.advice,
                "details": scores.main_capital.factors,
                "all_scores": scores.main_capital.all_stage_scores,
            },
            "fund_flow": ff,
        }

    def generate_report(self, stock_name: str, symbol: str, analysis: dict[str, Any]) -> str:
        """生成大白话报告"""
        if "error" in analysis:
            return f"## {stock_name} 分析\n\n数据不足，无法分析。"

        p = analysis["latest_price"]
        change = analysis["pct_change"]
        cap = analysis["capital_analysis"]

        icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"

        report = f"""## {icon} {stock_name}（{symbol}）综合分析

### 一、当前状态
收盘 **{p:.2f}** 元，今日 **{change:+.2f}%**。
"""

        report += f"""
### 二、主力行为分析

**判断结果**：{cap['stage']}（置信度：{cap['confidence']}）

{cap.get('description', '')}

**关键信号**：
"""
        for reason in cap.get("details", []):
            report += f"- {reason}\n"

        report += f"""
### 三、技术位置
- MA20 均线：{analysis['ma_20']:.2f}
- MA60 均线：{analysis['ma_60']:.2f}
"""
        if p > analysis["ma_20"] and p > analysis["ma_60"]:
            report += "- ✅ 股价站上全部均线，趋势偏强"
        elif p < analysis["ma_20"] and p < analysis["ma_60"]:
            report += "- ❌ 股价跌破所有均线，趋势偏弱"
        else:
            report += "- ⚠️ 股价在均线之间，方向不明"

        ff = analysis.get("fund_flow", {})
        if ff:
            report += f"""
### 四、资金流向
- 主力净流入：{ff.get('主力净流入', 0):.0f} 万元
- 大单净流入：{ff.get('大单净流入', 0):.0f} 万元
- 小单净流入：{ff.get('小单净流入', 0):.0f} 万元
"""
            main_flow = ff.get("主力净流入", 0)
            if main_flow > 0:
                report += "- ✅ 主力资金净流入，资金看好"
            else:
                report += "- ❌ 主力资金净流出，资金离场"

        cap_stage = cap['stage']
        advice_map = {
            "吸筹": "中线关注，可小仓跟随主力建仓，设好止损。",
            "洗盘": "持股耐心等待，洗盘结束后大概率继续上行。",
            "主升": "趋势良好可持有，但注意不要追高加仓。",
            "出货": "建议减仓或离场，保住利润为主。",
        }
        report += f"""
### 五、综合评分
- 综合分：{analysis.get('scores', {}).get('composite', 'N/A')}/100

### 六、操作建议
{advice_map.get(cap_stage, '观望为主，等待明确信号。')}

---
*⚠️ 以上分析基于量价数据和资金流向，不构成投资建议。*
"""
        return report

    # ── 向后兼容: 旧接口仍可使用 ──
    def analyze_compat(self, df, fund_flow: dict[str, Any]) -> dict[str, Any]:
        """向后兼容接口: 接受原始 DataFrame"""
        from backend.feature_engine.stock_features import StockFeatures
        from backend.services import get_stock_name

        symbol = str(df.iloc[0].get("code", "")) if not df.empty and "code" in df.columns else ""
        sf = StockFeatures.compute(symbol) if symbol else StockFeatures(symbol=symbol)
        return self.analyze(sf, fund_flow=fund_flow)
