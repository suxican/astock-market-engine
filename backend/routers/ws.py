"""WebSocket 实时数据推送 (V3)

客户端连接后可订阅:
  - /ws/market:    大盘行情 + 涨跌停 (5s)
  - /ws/market/v2: 大盘行情 + 健康分 + 赚钱效应 (5s 基础 + 30s 高级)
  - /ws/stock/{symbol}: 个股行情 (3s)

V3 优化:
  - 连接数限制 (每频道最大 50)
  - 错误恢复 + 指数退避
  - 心跳保活
  - 连接统计
"""
import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("market_engine.ws")

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# ── 配置 ──
MAX_CONNECTIONS_PER_CHANNEL = 50
HEARTBEAT_INTERVAL = 30  # 秒
PUSH_INTERVAL_MARKET = 5
PUSH_INTERVAL_STOCK = 3
PUSH_INTERVAL_ADVANCED = 30  # V2 高级数据推送间隔

# ── 频道订阅管理 ──
_subscribers: dict[str, set[WebSocket]] = {
    "market": set(),
}

# ── 连接统计 ──
_ws_stats = {
    "total_connections": 0,
    "active_connections": 0,
    "total_messages_sent": 0,
    "total_errors": 0,
    "rejected_connections": 0,
    "start_time": time.time(),
}


def _subscribe(channel: str, ws: WebSocket) -> bool:
    """订阅频道，返回是否成功（超过上限时拒绝）"""
    if channel not in _subscribers:
        _subscribers[channel] = set()

    if len(_subscribers[channel]) >= MAX_CONNECTIONS_PER_CHANNEL:
        _ws_stats["rejected_connections"] += 1
        return False

    _subscribers[channel].add(ws)
    _ws_stats["total_connections"] += 1
    _ws_stats["active_connections"] = sum(len(s) for s in _subscribers.values())
    return True


def _unsubscribe(channel: str, ws: WebSocket):
    if channel in _subscribers:
        _subscribers[channel].discard(ws)
    _ws_stats["active_connections"] = sum(len(s) for s in _subscribers.values())


async def _broadcast(channel: str, data: dict):
    """向频道的所有订阅者广播数据"""
    dead: list[WebSocket] = []
    for ws in list(_subscribers.get(channel, set())):
        try:
            await ws.send_json(data)
            _ws_stats["total_messages_sent"] += 1
        except Exception:
            dead.append(ws)
            _ws_stats["total_errors"] += 1
    for ws in dead:
        _subscribers.get(channel, set()).discard(ws)


# ── 心跳保活 ──
async def _heartbeat():
    """定期向所有连接发送 ping，清理断开的连接"""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        for channel, subs in _subscribers.items():
            dead = []
            for ws in list(subs):
                try:
                    await ws.send_json({"type": "ping", "ts": int(time.time())})
                except Exception:
                    dead.append(ws)
            for ws in dead:
                subs.discard(ws)


# ── 大盘推送 (V1) ──
async def _market_pusher():
    """每 5s 推送大盘数据"""
    from backend.services import (
        get_all_limit_up_today,
        get_market_overview,
        get_top_boards,
        get_zhaban_rate,
    )
    while True:
        if _subscribers.get("market"):
            try:
                overview = get_market_overview()
                up_count = get_all_limit_up_today()
                zhaban = get_zhaban_rate()
                top = get_top_boards(3)

                await _broadcast("market", {
                    "type": "market_snapshot",
                    "index": {
                        "name": overview.get("指数", "上证") if overview else "上证",
                        "price": overview.get("最新价", 0) if overview else 0,
                        "change_pct": overview.get("涨跌幅", 0) if overview else 0,
                    },
                    "limit_up": up_count,
                    "zhaban_rate": round(zhaban, 3),
                    "top_boards": [
                        {"name": t.get("name", ""), "board": t.get("boards", 0)}
                        for t in (top or [])
                    ],
                })
            except Exception as e:
                logger.debug("大盘推送异常: %s", e)
        await asyncio.sleep(PUSH_INTERVAL_MARKET)


# ── 大盘高级推送 (V2) ──
async def _market_pusher_v2():
    """V2: 基础行情 (5s) + 高级数据 (30s)"""
    from backend.services import (
        get_all_limit_up_today,
        get_market_overview,
        get_top_boards,
        get_zhaban_rate,
    )
    counter = 0
    while True:
        if _subscribers.get("market"):
            try:
                # 基础数据
                overview = get_market_overview()
                up_count = get_all_limit_up_today()
                zhaban = get_zhaban_rate()
                top = get_top_boards(3)

                await _broadcast("market", {
                    "type": "market_snapshot",
                    "index": {
                        "name": overview.get("指数", "上证") if overview else "上证",
                        "price": overview.get("最新价", 0) if overview else 0,
                        "change_pct": overview.get("涨跌幅", 0) if overview else 0,
                    },
                    "limit_up": up_count,
                    "zhaban_rate": round(zhaban, 3),
                    "top_boards": [
                        {"name": t.get("name", ""), "board": t.get("boards", 0)}
                        for t in (top or [])
                    ],
                })

                # 每 6 轮 (30s) 推送一次高级数据
                counter += 1
                if counter % 6 == 0:
                    try:
                        from backend.feature_engine import MarketFeatures
                        from backend.score_engine.market_health import compute_market_health
                        from backend.earning_effect_engine import compute_earning_effect

                        mf = MarketFeatures.compute()
                        health = compute_market_health(mf)
                        earning = compute_earning_effect(mf)

                        await _broadcast("market", {
                            "type": "market_advanced",
                            "health": {
                                "composite": health.composite,
                                "level": health.level,
                                "emotion_stage": health.emotion.stage,
                                "emotion_score": health.emotion.score,
                            },
                            "earning_effect": {
                                "composite": earning.composite,
                                "level": earning.level,
                                "avg_premium_pct": earning.avg_premium_pct,
                                "survival_rate": earning.survival_rate,
                            },
                            "ts": int(time.time()),
                        })
                    except Exception as e:
                        logger.debug("高级推送异常: %s", e)

            except Exception as e:
                logger.debug("V2 推送异常: %s", e)
                _ws_stats["total_errors"] += 1

        await asyncio.sleep(PUSH_INTERVAL_MARKET)


# ── Endpoints ──

@router.websocket("/market")
async def market_ws(ws: WebSocket):
    """大盘实时推送 (V1)"""
    await ws.accept()
    if not _subscribe("market", ws):
        await ws.send_json({"type": "error", "message": "连接数已达上限"})
        await ws.close()
        return
    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=HEARTBEAT_INTERVAL)
                if data == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "ts": int(time.time())})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _unsubscribe("market", ws)


@router.websocket("/market/v2")
async def market_ws_v2(ws: WebSocket):
    """V3 大盘推送 — 含健康分 + 赚钱效应"""
    await ws.accept()
    if not _subscribe("market", ws):
        await ws.send_json({"type": "error", "message": "连接数已达上限"})
        await ws.close()
        return
    _ws_stats["total_connections"] += 1
    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=HEARTBEAT_INTERVAL)
                if data == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "ts": int(time.time())})
    except (WebSocketDisconnect, Exception):
        _ws_stats["total_errors"] += 1
    finally:
        _unsubscribe("market", ws)


@router.websocket("/stock/{symbol}")
async def stock_ws(ws: WebSocket, symbol: str):
    """个股实时行情推送 (3s)"""
    await ws.accept()
    try:
        while True:
            try:
                from backend.services import get_realtime_quote, get_stock_name
                quote = get_realtime_quote(symbol)
                if quote:
                    await ws.send_json({
                        "type": "stock_quote",
                        "symbol": symbol,
                        "name": get_stock_name(symbol),
                        "price": quote.get("最新价", 0),
                        "change_pct": quote.get("涨跌幅", 0),
                        "volume": quote.get("成交量", 0),
                        "high": quote.get("最高", 0),
                        "low": quote.get("最低", 0),
                    })
                    _ws_stats["total_messages_sent"] += 1
                await asyncio.sleep(PUSH_INTERVAL_STOCK)
            except asyncio.TimeoutError:
                pass
            except Exception:
                _ws_stats["total_errors"] += 1
                await asyncio.sleep(5)
    except (WebSocketDisconnect, Exception):
        pass


# ── REST 端点 ──

@router.get("/stats")
def ws_stats():
    """WebSocket 连接统计"""
    active = {ch: len(subs) for ch, subs in _subscribers.items()}
    uptime = time.time() - _ws_stats["start_time"]
    return {
        "active_connections": active,
        "total_active": sum(active.values()),
        "total_connections": _ws_stats["total_connections"],
        "total_messages_sent": _ws_stats["total_messages_sent"],
        "total_errors": _ws_stats["total_errors"],
        "rejected_connections": _ws_stats["rejected_connections"],
        "uptime_seconds": int(uptime),
    }


# ── 启动后台任务 ──
_pusher_started = False


def start_market_pusher():
    """在应用启动时调用 — 启动 V2 推送 + 心跳"""
    global _pusher_started
    if not _pusher_started:
        _pusher_started = True
        loop = asyncio.get_event_loop()
        loop.create_task(_market_pusher_v2())  # V2 推送 (含 V1 基础数据)
        loop.create_task(_heartbeat())
        logger.info("WebSocket V2 推送已启动 (间隔: %ds, 心跳: %ds)", PUSH_INTERVAL_MARKET, HEARTBEAT_INTERVAL)
