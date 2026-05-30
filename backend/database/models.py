"""SQLAlchemy 数据模型 — SQLite / PostgreSQL 兼容 (V3)

V3 新增:
  - User: role, preferences_json, last_login_at
  - UserWatchlist: 自选股列表
  - UserAlert: 用户告警配置
  - EarningEffectSnapshot: 赚钱效应历史
"""
from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MarketSnapshot(Base):
    """每日市场快照"""
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    limit_up_count = Column(Integer, default=0)
    limit_down_count = Column(Integer, default=0)
    zhaban_rate = Column(Float, default=0.0)
    board_height = Column(Integer, default=0)
    index_change = Column(Float, default=0.0)
    up_down_ratio = Column(Float, default=0.0)
    emotion_stage = Column(String(20), default="")
    earning_effect_score = Column(Integer, default=0)
    market_health_score = Column(Integer, default=0)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_snapshot_date", "date"),
        Index("idx_snapshot_emotion", "emotion_stage"),
    )


class ReviewRecord(Base):
    """AI 复盘记录"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ai_review_text = Column(Text, default="")
    emotion_stage = Column(String(20), default="")

    __table_args__ = (
        Index("idx_review_date", "date"),
        Index("idx_review_emotion", "emotion_stage"),
    )


class User(Base):
    """用户账户 (V3: 增加角色和偏好)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(20), default="viewer")  # admin / analyst / viewer
    is_active = Column(Integer, default=1)
    preferences_json = Column(JSON, nullable=True)  # 用户偏好设置
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_role", "role"),
    )


class UserWatchlist(Base):
    """用户自选股"""
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    name = Column(String(50), default="")
    note = Column(String(200), default="")
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_watchlist_user", "user_id"),
        Index("idx_watchlist_symbol", "symbol"),
    )


class UserAlert(Base):
    """用户告警配置"""
    __tablename__ = "user_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    alert_type = Column(String(30), nullable=False)  # price / emotion / earning
    symbol = Column(String(10), nullable=True)  # 个股告警才有
    condition_json = Column(JSON, nullable=False)  # 告警条件
    is_active = Column(Integer, default=1)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_alert_user", "user_id"),
        Index("idx_alert_type", "alert_type"),
    )


class EarningEffectSnapshot(Base):
    """赚钱效应历史快照"""
    __tablename__ = "earning_effect_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    composite = Column(Integer, default=0)
    level = Column(String(10), default="")
    premium_score = Column(Integer, default=0)
    survival_score = Column(Integer, default=0)
    dragon_premium_score = Column(Integer, default=0)
    loss_spread_score = Column(Integer, default=0)
    zhaban_reflow_score = Column(Integer, default=0)
    avg_premium_pct = Column(Float, default=0.0)
    survival_rate = Column(Float, default=0.0)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_earning_date", "date"),
    )
