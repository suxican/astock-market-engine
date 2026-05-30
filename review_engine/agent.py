"""每日复盘 Agent (V3)

V3 变更: 接受 MarketFeatures + MarketScores 预计算数据。
减少重复 services 调用，收敛到 FeatureEngine → ScoreEngine → AI Explain Layer。
"""
from datetime import datetime
from typing import Any

from backend.feature_engine.market_features import MarketFeatures
from backend.score_engine.market_scores import MarketScores, compute_market_scores
from backend.score_engine.market_health import MarketHealthScore, compute_market_health


class MarketReviewAgent:
    """市场复盘分析器 (V3)"""

    def generate_review(
        self,
        mf: MarketFeatures | None = None,
        market_scores: MarketScores | None = None,
        market_health: MarketHealthScore | None = None,
    ) -> dict[str, Any]:
        """生成 AI 复盘

        Args:
            mf: 盘面特征快照（预计算）
            market_scores: 盘面评分（预计算）
            market_health: 综合健康分（预计算）
        """
        # 使用预计算数据或重新计算
        if mf is None:
            mf = MarketFeatures.compute()

        if market_scores is None:
            market_scores = compute_market_scores(mf)

        if market_health is None:
            market_health = compute_market_health(mf)

        # 板块轮动（独立服务，无法从 MF 获取）
        from review_engine.sector_rotation import analyze_sector_rotation
        sector = analyze_sector_rotation()

        # 构造复盘 prompt
        market_summary = self._build_market_text(mf, market_scores, market_health, sector)
        prompt = self._build_ai_review_prompt(market_summary)

        # RAG 增强
        similar_days = []
        today = datetime.now().strftime("%Y-%m-%d")
        market_data_for_rag = {
            "limit_up_count": mf.limit_up_count,
            "limit_down_count": mf.limit_down_count,
            "zhaban_rate": mf.zhaban_rate,
            "board_height": mf.max_board_height,
            "index_change": mf.index_pct_change,
            "up_down_ratio": mf.up_down_ratio,
        }

        enhancer = None
        enhanced_prompt = prompt
        try:
            from rag.retriever import ReviewEnhancer
            enhancer = ReviewEnhancer()
            enhanced_prompt, similar_days = enhancer.enhance_review_prompt(market_data_for_rag, prompt)
        except Exception:
            enhanced_prompt = prompt

        ai_review = self._call_ai_review(enhanced_prompt)

        if enhancer is not None:
            try:
                enhancer.persist_review(today, ai_review, market_data_for_rag, market_health.emotion.stage)
            except Exception:
                pass

        return {
            "ai_review": ai_review,
            "emotion": market_health.emotion.to_dict(),
            "market_health": market_health.to_dict(),
            "sector": sector,
            "limit_up_count": mf.limit_up_count,
            "limit_down_count": mf.limit_down_count,
            "zhaban_rate": mf.zhaban_rate,
            "top_boards": mf.top_boards,
            "similar_days": similar_days,
            "rag_enabled": True,
        }

    def _build_market_text(self, mf, market_scores, market_health, sector) -> str:
        lines = []
        lines.append(f"大盘：{mf.index_name} {mf.index_close} ({mf.index_pct_change:+.2f}%)")
        lines.append(f"涨停：{mf.limit_up_count}只 | 跌停：{mf.limit_down_count}只")
        if mf.zhaban_rate >= 0:
            lines.append(f"炸板率：{mf.zhaban_rate*100:.1f}%")
        if mf.top_boards:
            boards_str = " | ".join([f"{s['name']}({s['boards']}板,{s['industry']})" for s in mf.top_boards[:5]])
            lines.append(f"连板高度：{mf.max_board_height}板")
            lines.append(f"高标股：{boards_str}")

        emotion = market_health.emotion
        lines.append(f"情绪周期：{emotion.stage} — {emotion.suggestion}")
        lines.append(f"赚钱效应：{market_health.earning_effect.level}（{market_health.earning_effect.composite}分）")
        lines.append(f"综合健康分：{market_health.composite}/100（{market_health.level}）")

        if sector.get("top5"):
            lines.append("\n板块资金流入 Top5：")
            for s in sector["top5"][:5]:
                lines.append(f"  {s['name']} {s['change']:+.2f}% 净流入{s['flow_yi']}{s['flow_unit']}")

        if sector.get("bottom5"):
            lines.append("\n板块资金流出 Bottom5：")
            for s in sector["bottom5"][:5]:
                lines.append(f"  {s['name']} {s['change']:+.2f}% 净流出{abs(s['flow_yi'])}{s['flow_unit']}")

        return "\n".join(lines)

    def _build_ai_review_prompt(self, market_data_text: str) -> str:
        return f"""你是A股市场行为逻辑分析专家。请基于以下实时盘面数据，完成今日市场复盘分析。

## 盘面数据

{market_data_text}

## 分析要求

1. **主线梳理**: 今日主线是什么？哪个板块最强？资金从哪里来、往哪里去？
2. **情绪解读**: 当前情绪周期处于什么阶段？赚钱效应如何？是做多窗口还是防守窗口？
3. **龙头点评**: 今日龙头股表现如何？连板高度是否健康？有无龙头切换迹象？
4. **风险提示**: 当前最大的风险是什么？需要警惕什么信号？
5. **明日展望**: 基于今日盘面，明天大概率怎么走？关注什么方向？

## 输出要求

- 用大白话写，像老股民聊天一样
- 先说结论，再展开分析
- 每个要点 2-3 句话即可
- 总字数控制在 500 字以内"""

    def _call_ai_review(self, prompt: str) -> str:
        from backend.services.analysis.llm_client import call_llm
        try:
            return call_llm(prompt)
        except Exception as e:
            return f"AI 复盘生成失败: {e}"
