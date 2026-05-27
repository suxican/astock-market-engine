"""AI 分析服务 — 调用 Claude / OpenAI API 生成人话分析"""
import json
from typing import Optional
from openai import OpenAI
from backend.config import (
    CLAUDE_API_KEY, OPENAI_API_KEY, AI_PROVIDER,
    CLAUDE_MODEL, OPENAI_MODEL, CLAUDE_API_BASE,
    OPENAI_API_BASE,
)


def _build_analysis_prompt(
    stock_name: str,
    symbol: str,
    market_data: str,
    fund_flow_data: str,
    analysis_type: str = "comprehensive"
) -> str:
    """构建分析用的 prompt"""

    base_instruction = """你是一位有20年经验的A股市场分析师，擅长用大白话解释市场行为逻辑。
你的任务是分析以下A股数据，输出普通人能看懂的深度分析。

核心原则：
1. 禁止堆砌专业术语，全部翻译成人话
2. 禁止只说"可能上涨/下跌"，要说清楚谁在买/谁在卖/为什么
3. 重点分析市场行为逻辑，而不是预测涨跌
4. 如果信号不明确，诚实说"看不清楚"，不要硬编理由
5. 输出结构清晰，用标题分段
"""

    if analysis_type == "comprehensive":
        instruction = base_instruction + """
请从以下三个维度综合分析这只股票：

## 一、当前状态（一句话总结）
用一句话说清楚这只股票现在处于什么状态。

## 二、主力行为分析
结合量价关系和大单资金流向，判断主力当前在做什么：
- 是吸筹、洗盘、主升还是出货？
- 判断依据是什么？(成交量、价格位置、资金流向)
- 给出置信度（高/中/低）

## 三、市场情绪与位置
- 当前股价处于什么位置（低位/中位/高位）
- 市场情绪如何（冷清/温和/活跃/狂热）
- 成交量是否配合价格走势

## 四、风险与机会
- 当前最大的风险是什么？
- 当前最大的看点是什么？
- 给出操作建议（大白话）

记住：不确定就说"看不清楚"，不要糊弄。
"""
    elif analysis_type == "main_capital":
        instruction = base_instruction + """
请重点分析主力资金行为，严格按照以下规则判断：

**吸筹特征**：股价低于60日均价90%、成交量低于20日均量、大单连续3日净流入、换手率1%-3%、多根下影线
**洗盘特征**：在近期高点下方10%-20%、量缩至20日均量60%以下、大单小幅净流出、振幅小于3%、换手率低于1.5%
**主升特征**：突破前高站上全部均线、量高于20日均量150%、大单持续净流入、连续上涨不破MA5
**出货特征**：累计涨幅超30%、高位放量滞涨、大单净流出持续、换手率超5%

请判断当前主力处于哪个阶段，输出置信度，并用一句话解释判断依据。
"""
    elif analysis_type == "emotion":
        instruction = base_instruction + """
请分析当前市场情绪周期阶段：

判断标准：
- **冰点期**：涨停<10只，炸板率>60%，连板高度2板以下，成交量极度萎缩
- **修复期**：涨停10-20只，炸板率40-60%，连板高度3-4板，量能温和放大
- **主升期**：涨停20-50只，炸板率20-40%，连板高度5-8板，量能持续放大
- **高潮期**：涨停>50只，炸板率<20%，连板高度8板以上，天量
- **分歧期**：涨停30-50只，炸板率快速上升至30-50%，高标开始炸板
- **退潮期**：涨停<20只且快速下降，炸板率>50%，连板高度下降

请给出当前处于哪个阶段，以及判断的核心依据。
"""

    prompt = f"""{instruction}

【股票信息】
名称：{stock_name}（{symbol}）

【行情数据】
{market_data}

【资金流向数据】
{fund_flow_data}

请输出分析结果（用中文，大白话）：
"""
    return prompt


def _call_claude(prompt: str) -> str:
    """调用 Claude API"""
    client = OpenAI(
        api_key=CLAUDE_API_KEY,
        base_url=f"{CLAUDE_API_BASE}/v1",
    )
    resp = client.chat.completions.create(
        model=CLAUDE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def _call_openai(prompt: str) -> str:
    """调用 OpenAI API / DeepSeek 等兼容接口"""
    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_API_BASE:
        kwargs["base_url"] = OPENAI_API_BASE
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def analyze_stock(
    stock_name: str,
    symbol: str,
    market_data: str,
    fund_flow_data: str,
    analysis_type: str = "comprehensive"
) -> str:
    """对股票进行AI分析，返回人话分析结果"""
    prompt = _build_analysis_prompt(
        stock_name, symbol, market_data, fund_flow_data, analysis_type
    )

    try:
        if AI_PROVIDER == "claude" and CLAUDE_API_KEY:
            return _call_claude(prompt)
        elif OPENAI_API_KEY:
            return _call_openai(prompt)
        else:
            return _fallback_analysis(stock_name, market_data, fund_flow_data, analysis_type)
    except Exception as e:
        return f"⚠️ AI 分析服务暂时不可用（{str(e)}），使用本地规则引擎生成基础分析。\n\n{_local_rule_analysis(stock_name, market_data, fund_flow_data, analysis_type)}"


def _fallback_analysis(
    stock_name: str,
    market_data: str,
    fund_flow_data: str,
    analysis_type: str
) -> str:
    """无API key时的本地规则分析"""
    return _local_rule_analysis(stock_name, market_data, fund_flow_data, analysis_type)


def _local_rule_analysis(
    stock_name: str,
    market_data_str: str,
    fund_flow_str: str,
    analysis_type: str
) -> str:
    """本地规则引擎分析（无需API key）"""
    # 解析行情数据
    lines = market_data_str.strip().split("\n")
    if len(lines) < 2:
        return f"## {stock_name} 分析结果\n\n数据不足，无法生成分析。"

    header = [h.strip() for h in lines[0].split("\t")]
    last = lines[-1].split("\t")

    try:
        close = float(last[header.index("close")])
        pct = float(last[header.index("pct_change")])
        vol = float(last[header.index("volume")])
        turnover = float(last[header.index("turnover")])
        high = float(last[header.index("high")])
        low = float(last[header.index("low")])
    except (ValueError, IndexError):
        return f"## {stock_name} 分析结果\n\n数据解析失败。"

    # 计算关键指标
    closes = []
    for line in lines[1:]:
        parts = line.split("\t")
        try:
            closes.append(float(parts[header.index("close")]))
        except (ValueError, IndexError):
            continue

    avg_close_60 = sum(closes[-60:]) / len(closes[-60:]) if len(closes) >= 60 else sum(closes) / len(closes)
    vol_values = [float(l.split("\t")[header.index("volume")]) for l in lines[-20:] if len(l.split("\t")) > header.index("volume")]
    avg_vol_20 = sum(vol_values) / len(vol_values) if len(vol_values) > 0 else vol

    # 分析主力行为
    cap_analysis = _analyze_main_capital_local(
        close=close, avg_close_60=avg_close_60, vol=vol, avg_vol_20=avg_vol_20,
        turnover=turnover, pct=pct, high=high, low=low
    )

    # 分析情绪
    emotion_analysis = _analyze_emotion_local(pct=pct, vol=vol)

    # 综合输出
    result = f"""## 📊 {stock_name} 综合分析

### 一、当前状态
{stock_name} 今日收盘 {close:.2f} 元，涨跌幅 {pct:+.2f}%。
{'📈 股价上涨' if pct > 0 else '📉 股价下跌' if pct < 0 else '➡️ 股价平收'}，
成交量 {vol:.0f} 手，换手率 {turnover:.2f}%。

### 二、{cap_analysis["title"]}
{cap_analysis["content"]}

**置信度**：{cap_analysis["confidence"]}

**判断依据**：
{cap_analysis["reasons"]}

### 三、市场情绪判断
{emotion_analysis}

### 四、风险与机会
{'📌 当前处于相对低位，若大单持续流入可关注。' if close < avg_close_60 * 0.9 else '📌 股价处于中等位置，需结合更多信息判断。' if close < avg_close_60 * 1.1 else '📌 股价处于相对高位，注意风险控制。'}
{'💡 成交量配合良好，趋势未破。' if pct > 0 and vol > avg_vol_20 else '💡 量能不足，上涨持续性存疑。' if pct > 0 else '💡 下跌缩量未必是坏事，关注后续能否企稳。'}
"""
    return result


def _analyze_main_capital_local(close, avg_close_60, vol, avg_vol_20, turnover, pct, high, low) -> dict:
    """本地规则引擎 — 主力行为识别（文档第十九章）"""
    confidence = "低"
    title = "主力行为分析（本地规则引擎）"

    # 计算价格位置
    price_ratio = close / avg_close_60 if avg_close_60 > 0 else 1
    vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1

    # 得分系统（每阶段独立 reasons，避免不同阶段的判断依据混淆）
    stage_reasons = {"吸筹": [], "洗盘": [], "主升": [], "出货": []}
    scores = {"吸筹": 0, "洗盘": 0, "主升": 0, "出货": 0}
    max_scores = {"吸筹": 5, "洗盘": 5, "主升": 5, "出货": 5}

    # 吸筹判断
    if price_ratio < 0.9: scores["吸筹"] += 1; stage_reasons["吸筹"].append("股价低于60日均价的90%，处于低位区间")
    if vol_ratio < 1.2: scores["吸筹"] += 1; stage_reasons["吸筹"].append("量能未明显放大")
    if 1 <= turnover <= 3: scores["吸筹"] += 1; stage_reasons["吸筹"].append("换手率1%-3%，温和换手")
    if pct > 0 and (high - close) < (close - low): scores["吸筹"] += 1; stage_reasons["吸筹"].append("收盘接近当日最高价，有下影线特征")

    # 洗盘判断（与 MainCapitalAgent 保持一致）
    if 0.8 <= price_ratio <= 0.95: scores["洗盘"] += 1; stage_reasons["洗盘"].append("股价在近期高点下方10%-20%")
    if vol_ratio < 0.6: scores["洗盘"] += 1; stage_reasons["洗盘"].append("成交量萎缩至20日均量60%以下")
    if abs(pct) < 2: scores["洗盘"] += 1; stage_reasons["洗盘"].append("振幅较小，无方向性大阴线")
    if turnover < 1.5: scores["洗盘"] += 1; stage_reasons["洗盘"].append("换手率低于1.5%")

    # 主升判断（与 MainCapitalAgent 保持一致）
    if price_ratio >= 1.05: scores["主升"] += 1; stage_reasons["主升"].append("股价站上60日均线")
    if vol_ratio >= 1.5: scores["主升"] += 1; stage_reasons["主升"].append("成交量高于20日均量150%")
    if pct > 0: scores["主升"] += 1; stage_reasons["主升"].append("今日上涨")
    if turnover > 3: scores["主升"] += 1; stage_reasons["主升"].append("换手活跃（>3%）")
    if (high - low) / close < 0.06: scores["主升"] += 1; stage_reasons["主升"].append("振幅适中，上涨稳健")

    # 出货判断
    if price_ratio >= 1.3: scores["出货"] += 1; stage_reasons["出货"].append("累计涨幅较大")
    if vol_ratio > 1.5 and pct < 1: scores["出货"] += 1; stage_reasons["出货"].append("放量滞涨")
    if turnover > 5: scores["出货"] += 1; stage_reasons["出货"].append("换手率超过5%")
    if pct < 0 and (high - low) / close > 0.05: scores["出货"] += 1; stage_reasons["出货"].append("下跌且振幅较大")

    # 归一化得分
    for k in scores:
        scores[k] = scores[k] / max_scores[k]

    # 取最高分行为
    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score >= 0.8:
        confidence = "高"
    elif best_score >= 0.6:
        confidence = "中"
    else:
        confidence = "低"

    # 中文输出
    behavior_names = {
        "吸筹": "疑似主力吸筹阶段",
        "洗盘": "疑似主力洗盘阶段",
        "主升": "疑似主升阶段",
        "出货": "疑似主力出货阶段"
    }

    behavior_desc = {
        "吸筹": "该股近期大单持续净流入，结合低位缩量特征，疑似主力悄悄建仓，散户恐慌出局反而给了机会。",
        "洗盘": "当前更像主力洗盘，而非资金出逃。缩量横盘是洗去浮筹信号，主力并未真正离场。",
        "主升": "该股进入主升段，量价配合良好，大单持续净流入。追涨需注意仓位控制，避免高位接盘。",
        "出货": "高位放量滞涨，大单净流出明显，出货特征较清晰。持仓者建议设好止损，谨慎追高。"
    }

    # 只返回最优阶段的判断理由
    best_reasons = stage_reasons[best]
    scored_reasons = []
    if best_reasons:
        scored_reasons = [f"✓ {r}" for r in best_reasons]
    else:
        scored_reasons = ["信号不明确，建议观望等待确认"]

    return {
        "title": f"主力行为分析：{behavior_names[best]}",
        "content": behavior_desc[best],
        "confidence": confidence,
        "reasons": "\n".join(scored_reasons)
    }


def _analyze_emotion_local(pct, vol) -> str:
    """本地情绪分析"""
    if pct > 5:
        return "🔥 **情绪活跃**：今日涨幅较大，市场关注度较高，但需警惕追高风险。"
    elif pct > 2:
        return "📈 **情绪偏暖**：温和上涨，市场情绪稳定。"
    elif pct > 0:
        return "➡️ **情绪平淡**：微涨，市场无明显情绪驱动。"
    elif pct > -3:
        return "📉 **情绪偏冷**：小幅下跌，市场情绪较弱。"
    else:
        return "❄️ **情绪冷淡**：跌幅较大，市场情绪低迷，观望为主。"
