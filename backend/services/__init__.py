"""
数据服务层 — 使用 akshare 获取 A 股数据
所有数据获取逻辑集中在此，上层不直接调用 akshare

为减少对 akshare 的重复请求，对盘面级数据（涨停池/全市场行情快照/板块资金流向）
增加内存 TTL 缓存。个股级数据不缓存。
"""
import akshare as ak
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("market_engine.data")
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    force=True,
)

# 记录哪些股票在本请求中使用了 mock 数据（避免污染全局状态，每次查询前清空）
_MOCK_USED_SYMBOLS: set = set()
_MOCK_LOCK = threading.Lock()


def mark_mock_used(symbol: str):
    with _MOCK_LOCK:
        _MOCK_USED_SYMBOLS.add(symbol)


def pop_mock_used() -> bool:
    """查询并清除 mock 标记，返回当前是否有任何 symbol 使用了 mock"""
    with _MOCK_LOCK:
        if _MOCK_USED_SYMBOLS:
            _MOCK_USED_SYMBOLS.clear()
            return True
        return False


# ---------------- 简易 TTL 缓存 ----------------
_CACHE: Dict[str, tuple] = {}
_CACHE_LOCK = threading.Lock()
_DEFAULT_TTL = 60  # 秒


def _cache_get(key: str):
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item is None:
            return None
        value, expire_at = item
        if time.time() > expire_at:
            _CACHE.pop(key, None)
            return None
        return value


def _cache_set(key: str, value, ttl: int = _DEFAULT_TTL):
    with _CACHE_LOCK:
        _CACHE[key] = (value, time.time() + ttl)


def _try_akshare(func, default_return, *args, **kwargs):
    """安全调用 akshare，失败时返回默认值"""
    try:
        result = func(*args, **kwargs)
        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            return default_return
        return result
    except Exception as e:
        logger.warning("akshare 调用失败 (func=%s, symbol=%s, args=%s): %s",
                       func.__name__, kwargs.get("symbol", ""), str(args), e)
        return default_return


def _generate_mock_data(symbol: str, days: int = 120) -> pd.DataFrame:
    """生成模拟数据用于演示/开发"""
    mark_mock_used(symbol)
    logger.warning("⚠️ 使用模拟数据（非真实行情），symbol=%s", symbol)
    np.random.seed(hash(symbol) % (2**31))
    end = datetime.now()
    dates = [end - timedelta(days=i) for i in range(days, 0, -1)]

    base_price = 10.0 + (hash(symbol) % 200)
    prices = [base_price]
    for _ in range(days - 1):
        change = np.random.normal(0.001, 0.025)
        prices.append(prices[-1] * (1 + change))

    data = []
    for i, d in enumerate(dates):
        c = prices[i]
        o = c * (1 + np.random.normal(0, 0.01))
        h = max(o, c) * (1 + abs(np.random.normal(0, 0.005)))
        l = min(o, c) * (1 - abs(np.random.normal(0, 0.005)))
        v = np.random.exponential(500000)
        amt = v * c
        amp = (h - l) / o * 100
        pct = (c / prices[i-1] - 1) * 100 if i > 0 else 0
        chg = c - prices[i-1] if i > 0 else 0
        turn = np.random.uniform(0.5, 5)

        data.append({
            "date": d, "open": round(o, 2), "close": round(c, 2),
            "high": round(h, 2), "low": round(l, 2),
            "volume": int(v), "amount": round(amt, 2),
            "amplitude": round(amp, 2), "pct_change": round(pct, 2),
            "change": round(chg, 2), "turnover": round(turn, 2),
        })

    return pd.DataFrame(data)


def _fetch_stock_daily_curl(
    symbol: str,
    period: str = "daily",
    start_date: str = "19700101",
    end_date: str = "20500101",
    adjust: str = "",
) -> pd.DataFrame:
    """使用 curl_cffi 获取东方财富日K数据（绕过标准 requests 连接问题）

    替代 ak.stock_zh_a_hist，返回相同格式的 DataFrame，列名为中文。
    """
    try:
        from curl_cffi import requests as curl_requests

        market_code = 1 if symbol.startswith("6") else 0
        adjust_dict = {"qfq": "1", "hfq": "2", "": "0"}
        period_dict = {"daily": "101", "weekly": "102", "monthly": "103"}
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "klt": period_dict.get(period, "101"),
            "fqt": adjust_dict.get(adjust, "0"),
            "secid": f"{market_code}.{symbol}",
            "beg": start_date,
            "end": end_date,
        }
        r = curl_requests.get(url, params=params, impersonate="chrome", timeout=15)
        data_json = r.json()
        if not (data_json.get("data") and data_json["data"].get("klines")):
            return pd.DataFrame()

        temp_df = pd.DataFrame(
            [item.split(",") for item in data_json["data"]["klines"]]
        )
        temp_df["股票代码"] = symbol
        temp_df.columns = [
            "日期", "开盘", "收盘", "最高", "最低",
            "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率",
            "股票代码",
        ]
        for col in ["开盘", "收盘", "最高", "最低", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]:
            temp_df[col] = pd.to_numeric(temp_df[col], errors="coerce")
        temp_df["成交量"] = pd.to_numeric(temp_df["成交量"], errors="coerce").astype("int64")
        temp_df["日期"] = pd.to_datetime(temp_df["日期"], errors="coerce").dt.date

        return temp_df[
            ["日期", "股票代码", "开盘", "收盘", "最高", "最低",
             "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
        ]
    except Exception as e:
        logger.warning("curl_cffi 获取行情失败 (symbol=%s): %s", symbol, e)
        return pd.DataFrame()


def get_stock_daily(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """获取个股日K行情数据

    Args:
        symbol: 股票代码，如 "600519"
        start_date: 开始日期 "20240101"
        end_date: 结束日期 "20241231"
    """
    start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    end = end_date or datetime.now().strftime("%Y%m%d")

    # 1) 优先用 curl_cffi（绕过 Python requests 连接东方财富 API 的兼容性问题）
    df = _fetch_stock_daily_curl(symbol, period="daily", start_date=start, end_date=end, adjust="qfq")

    # 2) curl_cffi 也失败时，降级到 akshare（标准 requests）
    if df is None or df.empty:
        df = _try_akshare(
            ak.stock_zh_a_hist, None,
            symbol=symbol, period="daily",
            start_date=start, end_date=end, adjust="qfq"
        )

    # 3) 全部失败，使用模拟数据
    if df is None or df.empty:
        df = _generate_mock_data(symbol, days=120)

    # 统一列名为英文（兼容不同版本的 akshare）
    chinese_cols = list(df.columns)
    en_cols = ["date", "open", "close", "high", "low", "volume", "amount",
               "amplitude", "pct_change", "change", "turnover"]
    # 如果列数不匹配，尝试匹配已知的中文列名
    if len(chinese_cols) != len(en_cols):
        cn_map = {
            "日期": "date", "开盘": "open", "收盘": "close", "最高": "high",
            "最低": "low", "成交量": "volume", "成交额": "amount",
            "振幅": "amplitude", "涨跌幅": "pct_change", "涨跌额": "change",
            "换手率": "turnover",
        }
        mapped = []
        for c in chinese_cols:
            mapped.append(cn_map.get(c, c))
        df.columns = mapped
    else:
        df.columns = en_cols

    # 确保 date 列存在且为 datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def get_stock_fund_flow(symbol: str) -> Dict[str, Any]:
    """获取个股资金流向（大单/小单净流入）"""
    df = _try_akshare(
        ak.stock_individual_fund_flow,
        None,
        stock=symbol,
        market="sh" if symbol.startswith("6") else "sz"
    )
    if df is None:
        mark_mock_used(symbol)
        logger.warning("⚠️ 个股资金流向使用模拟数据（非真实数据），symbol=%s", symbol)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "主力净流入": round(np.random.uniform(-5000, 5000), 2),
            "小单净流入": round(np.random.uniform(-3000, 3000), 2),
            "中单净流入": round(np.random.uniform(-2000, 2000), 2),
            "大单净流入": round(np.random.uniform(-5000, 5000), 2),
            "超大单净流入": round(np.random.uniform(-3000, 3000), 2),
        }
    try:
        latest = df.iloc[-1]
        return {
            "date": str(latest.iloc[0]),
            "主力净流入": float(latest.iloc[1]),
            "小单净流入": float(latest.iloc[2]) if len(latest) > 2 else 0,
            "中单净流入": float(latest.iloc[3]) if len(latest) > 3 else 0,
            "大单净流入": float(latest.iloc[4]) if len(latest) > 4 else 0,
            "超大单净流入": float(latest.iloc[5]) if len(latest) > 5 else 0,
        }
    except Exception:
        return {}


def get_market_overview() -> Dict[str, Any]:
    """获取大盘概况"""
    df = _try_akshare(ak.stock_zh_index_daily, None, symbol="sh000001")
    if df is not None and not df.empty:
        try:
            latest = df.iloc[-1]
            close = float(latest["close"])
            # compute pct_change from last 2 close prices
            if len(df) >= 2:
                prev_close = float(df.iloc[-2]["close"])
                pct_change = round((close - prev_close) / prev_close * 100, 2)
            else:
                pct_change = 0.0
            return {
                "指数": "上证指数",
                "最新价": close,
                "涨跌幅": pct_change,
                "最高": float(latest["high"]),
                "最低": float(latest["low"]),
            }
        except Exception:
            pass
    return {"指数": "上证指数", "最新价": 3200.0, "涨跌幅": 0.0, "最高": 3210.0, "最低": 3190.0}


def get_limit_up_pool() -> pd.DataFrame:
    """获取今日涨停股池（带 60s TTL 缓存，避免 N+1）"""
    cached = _cache_get("limit_up_pool")
    if cached is not None:
        return cached
    df = _try_akshare(ak.stock_zt_pool_em, pd.DataFrame())
    _cache_set("limit_up_pool", df, ttl=60)
    return df


def get_limit_down_pool() -> pd.DataFrame:
    """获取今日跌停股池（带 60s TTL 缓存）"""
    cached = _cache_get("limit_down_pool")
    if cached is not None:
        return cached
    df = _try_akshare(ak.stock_zt_pool_dtgc_em, pd.DataFrame())
    _cache_set("limit_down_pool", df, ttl=60)
    return df


def get_lhb_detail(date: Optional[str] = None) -> pd.DataFrame:
    """获取龙虎榜详情"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    return _try_akshare(ak.stock_lhb_detail_em, pd.DataFrame(), date=date)


def get_sector_fund_flow() -> pd.DataFrame:
    """获取行业板块资金流向"""
    return get_sector_fund_flow_by_type("行业资金流向")


def get_sector_fund_flow_by_type(sector_type: str = "行业资金流向") -> pd.DataFrame:
    """获取板块资金流向（支持行业/概念，带 60s TTL 缓存）

    Args:
        sector_type: "行业资金流向" 或 "概念资金流向"
    """
    cache_key = f"sector_flow:{sector_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    df = _try_akshare(
        ak.stock_sector_fund_flow_rank,
        pd.DataFrame(),
        indicator="今日",
        sector_type=sector_type,
    )
    _cache_set(cache_key, df, ttl=60)
    return df


def get_stock_financial(symbol: str) -> Dict[str, Any]:
    """获取财报数据摘要"""
    df = _try_akshare(ak.stock_financial_abstract, None, symbol=symbol)
    if df is not None and not df.empty:
        try:
            latest = df.iloc[-1]
            return {
                "报告期": str(latest.iloc[0]),
                "营业收入": float(latest.iloc[1]) if pd.notna(latest.iloc[1]) else 0,
                "净利润": float(latest.iloc[2]) if pd.notna(latest.iloc[2]) else 0,
            }
        except Exception:
            pass
    return {}


def get_stock_name(symbol: str) -> str:
    """获取股票名称（带已知股票映射）"""
    name_map = {
        "600519": "贵州茅台", "000858": "五粮液", "300750": "宁德时代",
        "002594": "比亚迪", "601012": "隆基绿能", "000333": "美的集团",
        "600036": "招商银行", "601318": "中国平安", "000001": "平安银行",
        "002415": "海康威视", "600276": "恒瑞医药", "300059": "东方财富",
        "002115": "三维通信",
    }
    if symbol in name_map:
        return name_map[symbol]
    df = _try_akshare(ak.stock_zh_a_spot_em, None)
    if df is not None:
        try:
            match = df[df["代码"] == symbol]
            if not match.empty:
                return str(match.iloc[0]["名称"])
        except Exception:
            pass
    return symbol


def _get_spot_em_df() -> Optional[pd.DataFrame]:
    """获取全市场实时行情快照（带 30s TTL 缓存）

    akshare 的 stock_zh_a_spot_em() 单次返回全部 ~5000 只股票数据，
    缓存后所有 get_realtime_quote / get_realtime_quote_map 共享一次请求。
    """
    cached = _cache_get("spot_em_df")
    if cached is not None:
        return cached
    df = _try_akshare(ak.stock_zh_a_spot_em, None)
    if df is not None:
        _cache_set("spot_em_df", df, ttl=30)
    return df


def _row_to_quote(row) -> Dict[str, Any]:
    """spot DataFrame 单行 → 行情字典（安全转换）"""
    def _f(key, default=0.0):
        try:
            v = row[key]
            return float(v) if pd.notna(v) else default
        except (KeyError, TypeError, ValueError):
            return default
    return {
        "名称": str(row.get("名称", "")) if hasattr(row, "get") else str(row["名称"]),
        "最新价": _f("最新价"),
        "涨跌幅": _f("涨跌幅"),
        "涨跌额": _f("涨跌额"),
        "成交量": _f("成交量"),
        "成交额": _f("成交额"),
        "换手率": _f("换手率"),
        "最高": _f("最高"),
        "最低": _f("最低"),
        "今开": _f("今开"),
        "昨收": _f("昨收"),
        "总市值": _f("总市值"),
        "PE": _f("市盈率-动态"),
    }


def get_realtime_quote(symbol: str) -> Dict[str, Any]:
    """获取单只实时行情（基于全市场快照查询，零额外请求）"""
    df = _get_spot_em_df()
    if df is None:
        return {}
    try:
        match = df[df["代码"] == symbol]
        if not match.empty:
            return _row_to_quote(match.iloc[0])
    except Exception:
        pass
    return {}


def get_realtime_quote_map(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """批量获取实时行情（key=股票代码）

    Args:
        symbols: 指定股票列表；None 则返回全市场快照（数据量较大）
    """
    df = _get_spot_em_df()
    if df is None:
        return {}
    try:
        if symbols:
            df = df[df["代码"].isin(symbols)]
        return {str(row["代码"]): _row_to_quote(row) for _, row in df.iterrows()}
    except Exception:
        return {}


def get_all_limit_up_today() -> int:
    """获取今日涨停总数"""
    pool = get_limit_up_pool()
    return len(pool) if not pool.empty else -1


def get_zhaban_rate() -> float:
    """计算当日炸板率（文档第十八章定义）

    炸板率 = 当日炸板股数 / (当日涨停股数 + 当日炸板未回封股数)
    简化为：当日盘中曾被打开的涨停股数 / 总封板尝试数

    akshare 的 stock_zt_pool_em() 返回的是已封板的涨停股，"炸板次数 > 0"
    表示该股盘中被打开过但又重新封板。真正的炸板股池由 stock_zt_pool_zbgc_em 返回。
    炸板率应包含两者：分子 = 炸板股数（含回封），分母 = 涨停股数 + 真正炸板未回封股数。
    """
    pool = get_limit_up_pool()
    if pool.empty:
        return -1.0

    total_sealed = len(pool)
    if total_sealed == 0:
        return 0.0

    try:
        zhaban_in_pool = pool["炸板次数"].apply(
            lambda x: float(x) if str(x).replace(".", "").replace("-", "").isdigit() else 0
        ).gt(0).sum()
    except Exception:
        zhaban_in_pool = 0

    # 真正炸板未回封股池（带 60s TTL 缓存）
    cached = _cache_get("zhaban_pool")
    if cached is None:
        zhaban_only = _try_akshare(ak.stock_zt_pool_zbgc_em, pd.DataFrame())
        _cache_set("zhaban_pool", zhaban_only, ttl=60)
    else:
        zhaban_only = cached
    zhaban_only_count = len(zhaban_only) if zhaban_only is not None and not zhaban_only.empty else 0

    denominator = total_sealed + zhaban_only_count
    if denominator == 0:
        return 0.0
    numerator = int(zhaban_in_pool) + zhaban_only_count
    return round(numerator / denominator, 4)


def get_top_boards(n: int = 10) -> list:
    """获取连板高度排名 Top N"""
    pool = get_limit_up_pool()
    if pool.empty:
        return []
    try:
        df = pool.copy()
        df["连板数"] = pd.to_numeric(df["连板数"], errors="coerce").fillna(0)
        top = df.sort_values("连板数", ascending=False).head(n)
        result = []
        for _, row in top.iterrows():
            result.append({
                "symbol": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "boards": int(float(row.get("连板数", 0))),
                "industry": str(row.get("所属行业", "")),
                "fengdan": round(float(row.get("封板资金", 0)), 2),
                "turnover": round(float(row.get("换手率", 0)), 2),
            })
        return result
    except Exception:
        return []
