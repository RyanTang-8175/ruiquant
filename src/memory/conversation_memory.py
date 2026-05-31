"""
AI 会话记忆管理 —— 会话、消息、持久化
"""

import json, logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from src.utils.database import SessionLocal
from src.data.models_v6 import AISession, AIMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """AI 会话记忆管理器"""

    def __init__(self):
        self.db = SessionLocal()
        self._current_session_id = None

    def close(self):
        try: self.db.close()
        except: pass

    def create_session(self, session_type: str = "free_chat",
                       title: str = "") -> int:
        session = AISession(session_type=session_type, title=title)
        self.db.add(session)
        self.db.commit()
        self._current_session_id = session.id
        return session.id

    def get_or_create_session(self, session_type: str = "free_chat") -> int:
        if self._current_session_id:
            return self._current_session_id
        return self.create_session(session_type=session_type)

    def update_title(self, session_id: int, title: str):
        row = self.db.query(AISession).filter(AISession.id == session_id).first()
        if row:
            row.title = title
            row.updated_at = datetime.now()
            self.db.commit()

    def save_message(self, session_id: int, role: str, content: str,
                     stock_code: str = None, structured_output: dict = None,
                     tools_used: list = None, **kwargs):
        msg = AIMessage(
            session_id=session_id, stock_code=stock_code,
            role=role, content=content,
            structured_output=structured_output,
            tools_used=tools_used,
            **kwargs,
        )
        self.db.add(msg)
        self.db.commit()
        return msg.id

    def get_session_messages(self, session_id: int, limit: int = 50) -> list:
        rows = (self.db.query(AIMessage)
                .filter(AIMessage.session_id == session_id)
                .order_by(AIMessage.created_at)
                .limit(limit).all())
        return [
            {"role": r.role, "content": r.content,
             "structured_output": r.structured_output,
             "tools_used": r.tools_used,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def get_chat_history(self, session_id: int, limit: int = 20) -> list:
        msgs = self.get_session_messages(session_id, limit=limit * 2)
        history = []
        for m in msgs[-limit * 2:]:
            history.append({"role": m["role"], "content": m["content"]})
        return history

    def list_sessions(self, limit: int = 20) -> list:
        rows = (self.db.query(AISession)
                .order_by(desc(AISession.updated_at))
                .limit(limit).all())
        return [
            {"id": r.id, "type": r.session_type, "title": r.title,
             "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]

    def get_stock_conversations(self, code: str, limit: int = 10) -> list:
        rows = (self.db.query(AIMessage)
                .filter(AIMessage.stock_code == code)
                .order_by(desc(AIMessage.created_at))
                .limit(limit).all())
        return [
            {"role": r.role, "content": r.content[:500],
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def save_to_json(self, filepath: str):
        sessions = []
        for s in self.list_sessions():
            msgs = self.get_session_messages(s["id"])
            sessions.append({**s, "messages": msgs})
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
