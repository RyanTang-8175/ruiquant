"""
AlphaEye v5.2 → v6.0 数据库迁移
新增所有 v6 表，保留现有数据不动。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.database import engine, Base
from src.data.models_v6 import (
    Stock, StockSnapshot, IntradayBar, DailyBar,
    ScoreRecordV6, AntiQuantRecord, StrategySignal,
    AISession, AIMessage, AIAnalysisRecord,
    StockMemoryEntry, VerificationRecord, VerificationBackfill,
    UserFeedback, UserPreference, DataQualityLog,
)


def migrate():
    print("AlphaEye v6 数据库迁移...")
    Base.metadata.create_all(engine)
    print("✓ 所有 v6 表已创建（现有表不受影响）")

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✓ 当前数据库共 {len(tables)} 张表:")
    for t in sorted(tables):
        print(f"  - {t}")


if __name__ == "__main__":
    migrate()
