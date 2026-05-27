"""每日复盘 Agent

AI 驱动的市场复盘，分析主线、板块轮动、情绪变化。
"""
from typing import Dict, Any, Optional
from datetime import datetime
from backend.services import (
    get_all_limit_up_today, get_zhaban_rate, get_top_boards,
    get_market_overview, get_limit_down_pool,
)
from backend.services.analysis_service import analyze_stock, _build_analysis_prompt
from backend.agents.emotion_cycle_agent import EmotionCycleAgent
from review_engine.sector_rotation import analyze_sector_rotation


class MarketReviewAgent:
    """市场复盘分析器"""

    def __init__(self):
        self.emotion_agent = EmotionCycleAgent()

    def generate_review(self) -> Dict[str, Any]:
        """生成 AI 复盘文本"""
        # 收集市场数据
        overview = get_market_overview()
        limit_up_count = get_all_limit_up_today()
        zhaban_rate = get_zhaban_rate()
        top_boards = get_top_boards(10)
        pool_down = get_limit_down_pool()
        limit_down_count = len(pool_down) if not pool_down.empty else 0
        sector = analyze_sector_rotation()

        # 情绪周期判断
        emotion = self.emotion_agent.judge(
            limit_up_count=limit_up_count if limit_up_count >= 0 else 0,
            limit_down_count=limit_down_count,
            zhaban_rate=zhaban_rate if zhaban_rate >= 0 else None,
            high_board_count=top_boards[0]["boards"] if top_boards else None,
        )

        # 构造复盘 prompt 所需的数据文本
        market_summary = self._build_market_text(
            overview, limit_up_count, limit_down_count,
            zhaban_rate, top_boards, sector, emotion
        )
        prompt = self._build_ai_review_prompt(market_summary)

        # RAG 增强：检索历史相似行情并注入 prompt
        similar_days = []
        today = datetime.now().strftime("%Y-%m-%d")
        market_data_for_rag = {
            "limit_up_count": limit_up_count if limit_up_count >= 0 else 0,
            "limit_down_count": limit_down_count,
            "zhaban_rate": zhaban_rate if zhaban_rate >= 0 else 0,
            "board_height": top_boards[0]["boards"] if top_boards else 0,
            "index_change": overview.get("涨跌幅", 0) if overview else 0,
            "up_down_ratio": limit_up_count / max(limit_down_count, 1) if limit_down_count > 0 else 0,
        }
        enhancer = None
        enhanced_prompt = prompt
        try:
            from rag.retriever import ReviewEnhancer
            enhancer = ReviewEnhancer()
            enhanced_prompt, similar_days = enhancer.enhance_review_prompt(market_data_for_rag, prompt)
        except Exception:
            enhanced_prompt = prompt

        # 调用 AI 生成复盘（使用增强后的 prompt）
        ai_review = self._call_ai_review(enhanced_prompt)

        # 持久化复盘结果到 RAG + SQLite（仅当 enhancer 成功初始化时）
        if enhancer is not None:
            try:
                enhancer.persist_review(today, ai_review, market_data_for_rag, emotion.get("stage", ""))
            except Exception:
                pass

        return {
            "ai_review": ai_review,
            "emotion": emotion,
            "sector": sector,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "zhaban_rate": zhaban_rate,
            "top_boards": top_boards,
            "similar_days": similar_days,
            "rag_enabled": True,
        }

    def _build_market_text(self, overview, up_count, down_count, zhaban, top_boards, sector, emotion) -> str:
        """构建市场数据文本"""
        lines = []
        if overview:
            idx = overview.get("指数", "上证指数")
            price = overview.get("最新价", "N/A")
            change = overview.get("涨跌幅", 0)
            lines.append(f"大盘：{idx} {price} ({change:+.2f}%)")

        lines.append(f"涨停：{up_count}只 | 跌停：{down_count}只")
        if zhaban >= 0:
            lines.append(f"炸板率：{zhaban*100:.1f}%")
        if top_boards:
            boards_str = " | ".join([f"{s['name']}({s['boards']}板,{s['industry']})" for s in top_boards[:5]])
            lines.append(f"连板高度：{top_boards[0]['boards']}板")
            lines.append(f"高标股：{boards_str}")
        lines.append(f"情绪周期：{emotion['stage']} — {emotion['description']}")

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
        """构建复盘 prompt（不调用 AI）"""
        return f"""你是一位有20年经验的A股复盘分析师，擅长用大白话复盘当日市场。

核心原则：
1. 禁止堆砌专业术语，全部翻译成人话
2. 重点分析市场行为逻辑，而不是预测涨跌
3. 给出明确的操作建议，不要模棱两可
4. 输出结构清晰，用标题分段

请根据以下今日市场数据，从这几个维度进行复盘分析：

## 一、今日盘面总览
一句话总结今日市场状态。

## 二、市场主线分析
资金集中在哪个板块/题材？持续性如何？

## 三、情绪周期判断
当前处于什么阶段？核心依据是什么？

## 四、板块轮动
哪些板块在加强？哪些在退潮？

## 五、高标股与龙头状态
连板高度如何？龙头是否强势？

## 六、风险与机会
当前最大的风险是什么？最大的机会在哪里？

## 七、明日策略
给出明确的操作建议。

【今日市场数据】
{market_data_text}

请输出复盘分析（用中文，大白话）：
"""

    def _call_ai_review(self, prompt: str) -> str:
        """调用 AI 生成复盘（传入完整 prompt，已被 RAG 增强）"""
        try:
            from backend.services.analysis_service import _call_claude, _call_openai
            from backend.config import AI_PROVIDER, CLAUDE_API_KEY, OPENAI_API_KEY

            if AI_PROVIDER == "claude" and CLAUDE_API_KEY:
                return _call_claude(prompt)
            elif OPENAI_API_KEY:
                return _call_openai(prompt)
            else:
                return self._fallback_review()
        except Exception:
            return self._fallback_review()

    def _fallback_review(self) -> str:
        """无 API key 时的本地复盘"""
        return """## 今日复盘

### 一、今日盘面总览
数据获取中

### 二、市场情绪
情绪数据获取中

### 三、板块资金
今日板块资金流向分化明显，关注资金持续流入的板块。

### 四、操作建议
建议结合自身持仓情况，参考情绪周期阶段制定策略。
注意控制仓位，不追高，不恐慌。

*以上为本地规则引擎生成，AI 复盘需配置 API key 后自动升级。*
"""
