"""数据库持久化服务 — SQLite / PostgreSQL 兼容"""
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import OperationalError

from backend.database.db import SessionLocal
from backend.database.models import MarketSnapshot, ReviewRecord, StockAnalysisRecord

_MAX_RETRIES = 2
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
STOCK_ANALYSIS_DEDUP_WINDOW_MINUTES = 3


def _get_session():
    return SessionLocal()


def _safe_commit(db) -> None:
    """事务提交（带 PG 连接断开重试）"""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            db.commit()
            return
        except OperationalError:
            if attempt < _MAX_RETRIES:
                db.rollback()
                time.sleep(0.2)
            else:
                raise


def _beijing_iso(value) -> str:
    """Serialize database datetimes as Beijing time."""
    if not value:
        return ""
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ).isoformat()


def save_market_snapshot(date: str, data: dict) -> bool:
    """保存或更新（upsert）市场快照"""
    try:
        db = _get_session()
        try:
            existing = db.query(MarketSnapshot).filter(MarketSnapshot.date == date).first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
            else:
                snapshot = MarketSnapshot(date=date, **data)
                db.add(snapshot)
            _safe_commit(db)
            return True
        finally:
            db.close()
    except Exception:
        return False


def save_review_record(date: str, review_text: str, emotion_stage: str = "") -> bool:
    """保存或更新复盘记录"""
    try:
        db = _get_session()
        try:
            existing = db.query(ReviewRecord).filter(ReviewRecord.date == date).first()
            if existing:
                existing.ai_review_text = review_text
                existing.emotion_stage = emotion_stage
            else:
                record = ReviewRecord(date=date, ai_review_text=review_text, emotion_stage=emotion_stage)
                db.add(record)
            _safe_commit(db)
            return True
        finally:
            db.close()
    except Exception:
        return False


def get_review_history(limit: int = 30) -> list:
    """获取最近 N 条复盘记录"""
    try:
        db = _get_session()
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
                    "created_at": _beijing_iso(r.created_at),
                }
                for r in records
            ]
        finally:
            db.close()
    except Exception:
        return []


def _analysis_to_text(analysis) -> str:
    if isinstance(analysis, str):
        return analysis
    if isinstance(analysis, dict):
        value = analysis.get("analysis") or analysis.get("text") or analysis.get("content")
        if value:
            return str(value)
    return str(analysis or "")


def _extract_stage(scores: dict | None) -> str:
    if not isinstance(scores, dict):
        return ""
    main_capital = scores.get("main_capital")
    if isinstance(main_capital, dict):
        return str(main_capital.get("stage") or "")
    return ""


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def save_stock_analysis_record(
    *,
    symbol: str,
    name: str,
    summary: dict,
    analysis,
    scores: dict | None = None,
    analysis_type: str = "comprehensive",
    is_mock_data: bool = False,
    is_degraded: bool = False,
) -> bool:
    """Persist one stock analysis result for later review."""
    try:
        db = _get_session()
        try:
            now = _utc_now_naive()
            cutoff = now - timedelta(minutes=STOCK_ANALYSIS_DEDUP_WINDOW_MINUTES)
            record = (
                db.query(StockAnalysisRecord)
                .filter(
                    StockAnalysisRecord.symbol == symbol,
                    StockAnalysisRecord.analysis_type == analysis_type,
                    StockAnalysisRecord.created_at >= cutoff,
                )
                .order_by(StockAnalysisRecord.created_at.desc(), StockAnalysisRecord.id.desc())
                .first()
            )
            if record is None:
                record = StockAnalysisRecord(symbol=symbol, analysis_type=analysis_type)
                db.add(record)

            record.name = name
            record.stage = _extract_stage(scores)
            record.summary_json = summary
            record.scores_json = scores
            record.analysis_json = analysis if isinstance(analysis, (dict, list)) else None
            record.analysis_text = _analysis_to_text(analysis)
            record.is_mock_data = 1 if is_mock_data else 0
            record.is_degraded = 1 if is_degraded else 0
            record.created_at = now
            _safe_commit(db)
            return True
        finally:
            db.close()
    except Exception:
        return False


def get_stock_analysis_history(limit: int = 50) -> list:
    """Return recent stock analysis records."""
    try:
        db = _get_session()
        try:
            _dedupe_recent_stock_analysis_records(db)
            records = (
                db.query(StockAnalysisRecord)
                .order_by(StockAnalysisRecord.created_at.desc(), StockAnalysisRecord.id.desc())
                .limit(max(1, min(limit, 200)))
                .all()
            )
            return [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "name": r.name,
                    "stage": r.stage,
                    "analysis_type": r.analysis_type,
                    "created_at": _beijing_iso(r.created_at),
                    "is_mock_data": bool(r.is_mock_data),
                    "is_degraded": bool(r.is_degraded),
                }
                for r in records
            ]
        finally:
            db.close()
    except Exception:
        return []


def _dedupe_recent_stock_analysis_records(db) -> None:
    """Remove duplicate records created in the same short analysis window."""
    records = (
        db.query(StockAnalysisRecord)
        .order_by(StockAnalysisRecord.created_at.desc(), StockAnalysisRecord.id.desc())
        .limit(300)
        .all()
    )
    keepers: dict[tuple[str, str], list[StockAnalysisRecord]] = {}
    deleted = 0
    for record in records:
        key = (record.symbol, record.analysis_type or "")
        bucket = keepers.setdefault(key, [])
        duplicate = False
        for keeper in bucket:
            if keeper.created_at and record.created_at:
                delta = abs(keeper.created_at - record.created_at)
                if delta <= timedelta(minutes=STOCK_ANALYSIS_DEDUP_WINDOW_MINUTES):
                    duplicate = True
                    break
        if duplicate:
            db.delete(record)
            deleted += 1
            continue
        bucket.append(record)
    if deleted:
        _safe_commit(db)


def get_stock_analysis_record(record_id: int) -> dict:
    """Return one stock analysis history record with full detail."""
    try:
        db = _get_session()
        try:
            r = db.query(StockAnalysisRecord).filter(StockAnalysisRecord.id == record_id).first()
            if r is None:
                return {}
            return {
                "id": r.id,
                "symbol": r.symbol,
                "name": r.name,
                "stage": r.stage,
                "analysis_type": r.analysis_type,
                "created_at": _beijing_iso(r.created_at),
                "summary": r.summary_json or {},
                "scores": r.scores_json,
                "analysis": r.analysis_json if r.analysis_json is not None else r.analysis_text,
                "is_mock_data": bool(r.is_mock_data),
                "is_degraded": bool(r.is_degraded),
            }
        finally:
            db.close()
    except Exception:
        return {}


def get_snapshot_by_date(date: str) -> dict:
    """获取指定日期的市场快照"""
    try:
        db = _get_session()
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
        db = _get_session()
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
