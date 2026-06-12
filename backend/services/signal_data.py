"""Signal data sources: THS hot stocks and theme attribution."""
from __future__ import annotations

import pandas as pd

from .enhanced_sources import fetch_ths_hotspot


def get_ths_hotspot() -> pd.DataFrame:
    """获取同花顺当日热点/强势股数据（可用时带 reason tags）。"""
    return fetch_ths_hotspot()

