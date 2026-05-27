"""SQLAlchemy 数据模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MarketSnapshot(Base):
    """每日市场快照"""
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    limit_up_count = Column(Integer, default=0)
    limit_down_count = Column(Integer, default=0)
    zhaban_rate = Column(Float, default=0.0)
    board_height = Column(Integer, default=0)
    index_change = Column(Float, default=0.0)
    up_down_ratio = Column(Float, default=0.0)
    emotion_stage = Column(String(20), default="")
    metadata_json = Column(JSON, nullable=True)


class ReviewRecord(Base):
    """AI 复盘记录"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ai_review_text = Column(Text, default="")
    emotion_stage = Column(String(20), default="")
