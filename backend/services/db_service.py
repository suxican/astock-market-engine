"""数据库持久化服务"""
from datetime import datetime
from backend.database.models import MarketSnapshot, ReviewRecord
from backend.database.db import SessionLocal


def save_market_snapshot(date: str, data: dict) -> bool:
    """保存或更新（upsert）市场快照"""
    try:
        db = SessionLocal()
        try:
            existing = db.query(MarketSnapshot).filter(MarketSnapshot.date == date).first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
            else:
                snapshot = MarketSnapshot(date=date, **data)
                db.add(snapshot)
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        return False


def save_review_record(date: str, review_text: str, emotion_stage: str = "") -> bool:
    """保存或更新复盘记录"""
    try:
        db = SessionLocal()
        try:
            existing = db.query(ReviewRecord).filter(ReviewRecord.date == date).first()
            if existing:
                existing.ai_review_text = review_text
                existing.emotion_stage = emotion_stage
            else:
                record = ReviewRecord(date=date, ai_review_text=review_text, emotion_stage=emotion_stage)
                db.add(record)
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        return False


def get_review_history(limit: int = 30) -> list:
    """获取最近 N 条复盘记录"""
    try:
        db = SessionLocal()
        try:
            records = (
                db.query(ReviewRecord)
                .order_by(ReviewRecord.date.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "date": r.date,
                    "emotion_stage": r.emotion_stage,
                    "ai_review_text": r.ai_review_text[:500] if r.ai_review_text else "",
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in records
            ]
        finally:
            db.close()
    except Exception:
        return []


def get_snapshot_by_date(date: str) -> dict:
    """获取指定日期的市场快照"""
    try:
        db = SessionLocal()
        try:
            s = db.query(MarketSnapshot).filter(MarketSnapshot.date == date).first()
            if s is None:
                return {}
            return {
                "date": s.date,
                "limit_up_count": s.limit_up_count,
                "limit_down_count": s.limit_down_count,
                "zhaban_rate": s.zhaban_rate,
                "board_height": s.board_height,
                "index_change": s.index_change,
                "up_down_ratio": s.up_down_ratio,
                "emotion_stage": s.emotion_stage,
            }
        finally:
            db.close()
    except Exception:
        return {}


def get_snapshots_by_dates(dates: list) -> dict:
    """批量获取多个日期的市场快照"""
    try:
        db = SessionLocal()
        try:
            snapshots = db.query(MarketSnapshot).filter(MarketSnapshot.date.in_(dates)).all()
            return {s.date: {
                "date": s.date,
                "limit_up_count": s.limit_up_count,
                "limit_down_count": s.limit_down_count,
                "zhaban_rate": s.zhaban_rate,
                "board_height": s.board_height,
                "index_change": s.index_change,
                "emotion_stage": s.emotion_stage,
            } for s in snapshots}
        finally:
            db.close()
    except Exception:
        return {}
